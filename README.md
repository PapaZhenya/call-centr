# Call Center QA Platform

Local-only платформа контроля качества звонков колл-центра: транскрибация
(faster-whisper) и оценка по чек-листу локальной LLM (Ollama), без единого
запроса во внешние сервисы.

- [`callcenter-qa-api`](callcenter-qa-api/) — FastAPI-бэкенд, воркер, docker-compose
  всего стека (Postgres, Redis, Metabase). Установка и запуск: см. его README
  и скрипты в `callcenter-qa-api/scripts/`.
- [`callcenter-qa-frontend`](callcenter-qa-frontend/) — Next.js админ-UI
  (звонки, чек-лист, пользователи, команды). Собирается контейнером из
  docker-compose бэкенда.

Быстрый старт (Windows, из `callcenter-qa-api/`):

```
.\scripts\setup.ps1
.\scripts\start.ps1
.\scripts\create-admin.ps1
.\scripts\download-models.ps1
```
