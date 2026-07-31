# Call Center QA — Frontend

Next.js (App Router, TypeScript) admin UI for the local-only Call Center QA
platform. Talks only to the backend at `NEXT_PUBLIC_API_BASE_URL`
(`callcenter-qa-api`, default `http://localhost:8000`) — no other network
calls, no cloud services.

## Local development

```
npm install
cp .env.example .env.local   # adjust NEXT_PUBLIC_API_BASE_URL if needed
npm run dev
```

Requires the backend (`../callcenter-qa-api`) running separately — see its
README for the full stack (`docker compose up`).

## Scripts

- `npm run dev` — dev server
- `npm run build` / `npm run start` — production build/serve
- `npm run lint` — ESLint (flat config, `eslint-config-next`)
- `npm run typecheck` — `tsc --noEmit`
- `npm run test` — Vitest (unit tests for pure logic in `src/lib/`)

## Structure

- `src/lib/api-client.ts` — fetch wrapper: attaches the bearer token, retries
  once through `/api/v1/auth/refresh` on 401, redirects to `/login` if that
  fails too.
- `src/lib/auth-context.tsx` — React context holding the current user; tokens
  live in `localStorage` (acceptable trade-off for a local admin tool — not
  httpOnly cookies, noted here deliberately).
- `src/messages/ru.ts` — flat UI-string dictionary. To add a language, create
  `en.ts`/`es.ts` with the same shape and switch which one is imported.
- `src/app/*` — pages: `/login`, `/setup` (first-admin), `/` (dashboard),
  `/calls` (list + upload), `/calls/[id]` (player synced to transcript + QA
  results), `/rubric` (criteria/version CRUD, admin-only writes).

## Known gaps (Stage 1)

- Only Russian UI strings exist; the `en`/`es` extension point is there but
  unused.
- No dedicated pages yet for: user/team management, processing queue,
  error/system log, analytics beyond the dashboard summary, PDF/CSV/XLSX
  export.
