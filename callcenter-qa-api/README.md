# Call Center QA Platform — local-only MVP

Upload a call recording, transcribe it locally (faster-whisper), score it
against a configurable rubric, and browse the results and analytics — with
**no cloud AI dependency**. Audio, transcripts, prompts, and evaluation
results never leave your machine.

**No external AI API is called by this application.** Claude/Anthropic,
OpenAI, AssemblyAI, Gemini, Azure AI, AWS Transcribe, and Google Cloud AI are
not used anywhere in the pipeline. Transcription runs via `faster-whisper`
(local). QA scoring runs via a locally-hosted LLM through
[Ollama](https://ollama.com) (`app/llm/`), or deterministic rule matching
(`app/qa_evaluation/rules.py`) for phrase-based criteria. When
`OFFLINE_MODE=true` (the default), the app actively refuses any outbound
HTTP request to a non-local host — see `app/security/offline_guard.py`.

Two repositories make up the system:

- `callcenter-qa-api` (this repo) — FastAPI backend, worker, Postgres, Redis.
- `callcenter-qa-frontend` (sibling directory, `../callcenter-qa-frontend`)
  — Next.js admin UI (Russian).

This is a **Stage 2 MVP**: local LLM instead of Claude, full 7-role
permission-based RBAC with team-scoped visibility, PowerShell scripts for
Windows setup/start/stop/diagnostics, and a working admin UI (login, call
list/upload, call detail with synced player+transcript+QA results, rubric
editor, users, teams). See "What's not built yet" below for what's
deliberately deferred.

## Requirements

- **OS**: Windows 10/11 with Docker Desktop (WSL2 backend).
- **RAM**: 16 GB minimum, 32 GB recommended if you run a 7B+ local LLM
  alongside Postgres/Redis/Whisper.
- **Disk**: ~10 GB for Docker images/models, more depending on the Whisper
  and Ollama models you choose.
- **GPU**: optional. `WHISPER_DEVICE=auto` and Ollama both use a local NVIDIA
  GPU automatically if present; both run on CPU otherwise (slower).
- **Docker Desktop**: https://www.docker.com/products/docker-desktop/
- **Ollama**: https://ollama.com/download (install natively on Windows —
  simplest way to get GPU access; see "Local LLM setup" below).
- FFmpeg is **not** required on the host — it's installed inside the API/
  worker Docker image (see `Dockerfile`) for audio format handling.

## Local LLM setup (Ollama)

1. Install Ollama from https://ollama.com/download and make sure it's
   running (it starts a local server at `http://localhost:11434`).
2. Pull a model. Pick one that fits your hardware:

   | Profile | Command | Notes |
   |---|---|---|
   | CPU / low-spec | `ollama pull qwen2.5:3b` | Small, runs on CPU, lower QA quality |
   | CPU recommended / GPU 6–8 GB | `ollama pull qwen2.5:7b` | Default (`LOCAL_LLM_MODEL` in `.env.example`) |
   | GPU 12 GB+ | `ollama pull qwen2.5:14b` | Better QA quality, needs more VRAM/RAM |

   Any Ollama model that supports JSON-mode output works — these are
   reasonable defaults, not a hard requirement.
3. Verify it works: `ollama run qwen2.5:7b "Reply with the single word OK"`.

**No model is downloaded automatically by this app.** You choose and pull
the model yourself, per the table above.

## Running everything

### Quick start (PowerShell scripts, Windows)

```powershell
.\scripts\setup.ps1            # checks prerequisites, creates .env, generates a real JWT secret
.\scripts\start.ps1             # docker compose up --build, waits for /healthz, runs migrations + seed
.\scripts\create-admin.ps1      # creates the first admin account (one-time)
.\scripts\check.ps1              # diagnostics: containers, API, Postgres, Redis, Ollama, disk, RAM
.\scripts\download-models.ps1   # interactive: pull an Ollama model / pre-warm a Whisper model
.\scripts\stop.ps1               # docker compose down (add -RemoveVolumes to also wipe data)
```

All scripts live in `scripts/*.ps1` and only touch this repo's Docker
Compose project — none of them were executed end-to-end in the environment
this was built in (no Docker there); they were parse-checked for syntax
errors only. See "Not verified in this environment" below.

### Manual steps (what the scripts above do, spelled out)

1. Copy `.env.example` to `.env`. The defaults assume Ollama is installed
   natively on Windows and reachable from Docker via `host.docker.internal`
   — no changes needed for the default setup. Set `JWT_SECRET_KEY` to a real
   secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
2. From this directory:
   ```
   docker compose up --build
   ```
   This starts: `db` (Postgres), `redis`, `api`, `worker`, `frontend`
   (built from `../callcenter-qa-frontend` — that directory must exist as a
   sibling of this one), and `metabase`.
3. Apply migrations (first run only):
   ```
   docker compose exec api alembic upgrade head
   ```
4. Seed a default rubric (idempotent — safe to re-run):
   ```
   docker compose exec api python scripts/seed_rubric.py
   ```
5. Open http://localhost:3000 — the first visit redirects to **first-admin
   setup**. Create your admin account (email + password).
6. In the UI: **Чек-лист** (rubric) already has the seeded default criteria
   and an active version. Add/edit criteria there (requires `rubric:write`,
   e.g. `admin`), or via `POST /api/v1/rubric/criteria`.
7. **Звонки** (calls) → **Загрузить звонок** (upload) → pick an agent, a
   date, and an audio file (WAV/MP3/M4A/OGG/FLAC). The call processes in the
   background (transcribe → evaluate); refresh to see status move to
   `Готово` (completed).
8. Click the call to see the synced audio player + transcript + QA results
   with evidence quotes.
9. **Пользователи** (users) and **Команды** (teams) pages (`admin`/
   `super_admin` only) let you create additional accounts with any of the 7
   roles and assign them to a team or a specific agent — see "Roles &
   permissions" below.

API docs: http://localhost:8000/docs · Frontend: http://localhost:3000 ·
Metabase: http://localhost:3001

### If you'd rather run Ollama in Docker too

Uncomment the `ollama` service in `docker-compose.yml`, set
`LOCAL_LLM_BASE_URL=http://ollama:11434` in `.env`, then
`docker compose exec ollama ollama pull qwen2.5:7b`. GPU passthrough into
Docker on Windows needs WSL2 + the NVIDIA container toolkit; CPU-only works
out of the box but is slow for anything beyond small models.

## Diagnostics (manual, for now)

There's no dedicated diagnostics UI page yet (deferred - see below). To
check things manually:

```
docker compose ps                          # which services are up
curl http://localhost:8000/healthz          # API alive
docker compose exec db pg_isready -U callcenter
docker compose exec redis redis-cli ping
curl http://localhost:11434/api/tags        # Ollama reachable + models pulled
```

## Environment variables

See `.env.example` for the full annotated list. Key ones:

- `WHISPER_MODEL` (`tiny`/`base`/`small`/`medium`/`large-v3`), `WHISPER_DEVICE`
  and `WHISPER_COMPUTE_TYPE` (`auto` detects GPU vs CPU).
- `LOCAL_LLM_PROVIDER` (only `ollama` implemented), `LOCAL_LLM_BASE_URL`,
  `LOCAL_LLM_MODEL`, `LOCAL_LLM_TIMEOUT`, `LOCAL_LLM_TEMPERATURE`,
  `LOCAL_LLM_MAX_TOKENS`, `LOCAL_LLM_MAX_RETRIES`.
- `OFFLINE_MODE` (default `true`) — blocks any HTTP request to a non-local
  host from the app's own LLM client.
- `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_TTL_MINUTES`, `JWT_REFRESH_TOKEN_TTL_DAYS`,
  `LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`.
- `CORS_ALLOWED_ORIGINS` — must include the frontend's origin.

## Processing pipeline

`uploaded → transcribing → transcribed → evaluating → completed`
(or `transcription_failed` / `evaluation_failed`, retryable via
`POST /api/v1/calls/{id}/retry`). Rule-based criteria (required/forbidden
phrases) are scored and committed first, so a down/unreachable local LLM
doesn't lose that deterministic scoring work — the evaluation is marked
failed but keeps what it already computed.

## Rubric & hybrid scoring

Rubric criteria and versions are fully data-driven (`/api/v1/rubric/*`).
Each criterion can carry `required_phrases`/`forbidden_phrases` (scored
deterministically, `source=rule`) or be left semantic (scored by the local
LLM, `source=local_llm`). The LLM must quote verbatim from the transcript;
every quote is verified against the actual transcript text before being
trusted (`app/qa_evaluation/evidence.py`) — an unverifiable quote is dropped,
not silently kept. The overall score is computed in code from weighted
per-criterion scores, never taken directly from the model's own claim.

Editing criteria creates a new `RubricVersion` rather than mutating history,
so past evaluations stay interpretable against the rubric that was active
when they ran; the exact rendered prompt is snapshotted per evaluation too.

## Auth

Argon2id password hashing, JWT access tokens (15 min default) + DB-revocable
opaque refresh tokens (30 days default, rotated on each refresh), account
lockout after repeated failed logins, and a login journal
(`login_attempts` table).

## Roles & permissions

Access control is a genuine **permission model**, not role-name checks
scattered through the code: named permission strings (`rubric:write`,
`calls:view:team`, ...) live in `app/auth/permissions.py` as a
`ROLE_PERMISSIONS` matrix, and every protected endpoint depends on
`require_permission(PERMISSION)` (`app/api/deps.py`) rather than checking
`user.role` directly. Adding a permission or changing what a role can do
means editing that one matrix, not hunting through routers.

| Role | Key permissions | Call/analytics visibility |
|---|---|---|
| `super_admin` | everything, incl. `users:manage`, `teams:manage` | all calls, org-wide analytics |
| `admin` | everything except managing other super_admins | all calls, org-wide analytics |
| `qa_manager` | `rubric:write`, `calls:upload`, `calls:retry` | all calls, org-wide analytics |
| `team_lead` | `rubric:read`, `calls:upload`, `calls:retry` | own team's calls, team analytics |
| `reviewer` | `rubric:read` (read-only) | all calls (no analytics) |
| `agent` | — | only their own calls (linked via `User.agent_id`) |
| `viewer` | `rubric:read` (read-only) | all calls, org-wide analytics, no writes |

Visibility scoping (`app/auth/scoping.py`) is enforced server-side on every
call/analytics read: `calls:view:all` sees everything, `calls:view:team`
joins `Agent.team_id == user.team_id`, `calls:view:own` filters
`Call.agent_id == user.agent_id`, and a user with none of those gets a 403 —
scoping is never done in the frontend alone.

**Team** (`app/models/team.py`) is the org-substructure primitive for this
stage — an `Agent` belongs to a `Team`, and a `User` can be linked to a
`Team` (for `team_lead`/`reviewer`-style scoping) and/or a specific `Agent`
(for the `agent` role, so they see only their own calls). A separate
`Project` entity from the original spec was intentionally not added — `Team`
covers the same scoping need without an extra layer with no concrete use
yet.

Manage users and teams via the **Пользователи**/**Команды** pages in the UI
(`users:manage`/`teams:manage`, `admin`/`super_admin` by default), or
directly: `POST/GET/PATCH /api/v1/users`, `POST/GET/PATCH /api/v1/teams`.
The very first admin account can only be created once, via
`POST /api/v1/auth/setup` (`.\scripts\create-admin.ps1`) — every account
after that is created through the Users page/API by an existing
`users:manage`-permitted account.

## Backup / restore

```
# Backup
docker compose exec db pg_dump -U callcenter callcenter_qa > backup.sql
docker cp $(docker compose ps -q api):/data/audio ./audio_backup

# Restore
cat backup.sql | docker compose exec -T db psql -U callcenter callcenter_qa
docker cp ./audio_backup/. $(docker compose ps -q api):/data/audio
```

## Updating

```
git pull            # or apply your changes
docker compose exec api alembic upgrade head
docker compose up --build
```

## What's not built yet (deferred, not claimed as done)

- Multi-organization support — `organization_id` exists on every row as a
  seam for the future but is not exposed via API; there is effectively one
  organization today.
- Project-level scoping as a separate entity from Team (see "Roles &
  permissions" above for why Team was chosen to cover this instead).
- pyannote.audio diarization for mono recordings — stereo channel-based
  diarization works today; mono files are transcribed as a single
  unlabeled stream.
- The other UI screens from the full spec (dedicated diagnostics page,
  processing queue view, error log view, templates/prompt-version
  management as separate entities).
- PDF/CSV/XLSX export, manual QA-reviewer score correction with audit log.
- Full 11-state pipeline (`preprocessing`/`diarizing`/`analyzing_rules`/
  `analyzing_llm`/`validating`/`cancelled`/`partial_completed` as distinct
  statuses), job cancellation, per-job idempotency tokens.
- pgvector/rate limiting/CSP/antivirus-hook/PII log masking/data-retention
  auto-purge.

## Tests

```
pip install -r requirements-dev.txt
pytest
```

Frontend (from `../callcenter-qa-frontend`):
```
npm install
npm run test
npm run lint
npm run typecheck
npm run build
```

## Not verified in this development environment

Docker wasn't available where this was built, so the following are
**believed correct but not actually run end-to-end**: `docker compose up`
itself, live Postgres/Redis/arq wiring, a real Ollama call, the frontend
talking to a running backend in a browser, and the `scripts/*.ps1` PowerShell
scripts (parse-checked for syntax errors only, never executed against a
running Docker Compose stack). What *was* verified directly: 122 backend
pytest tests pass (including the new RBAC/permission/scoping tests), all
SQLAlchemy models compile to valid PostgreSQL DDL, all 37 API routes
register with no import errors, `faster-whisper` (tiny model) ran a real
local transcription, JWT/Argon2id logic was exercised directly, and the
frontend's `lint`/`typecheck`/`build`/`vitest` (15 tests, including the new
permission-matrix tests) all pass with a real production build that
generates the new `/users` and `/teams` routes. Run the steps above on your
machine to confirm the full pipeline before relying on this.
