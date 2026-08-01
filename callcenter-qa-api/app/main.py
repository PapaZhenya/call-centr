from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analytics import router as analytics_router
from app.api.routers import agents as agents_router
from app.api.routers import auth as auth_router
from app.api.routers import calls as calls_router
from app.api.routers import rubrics as rubrics_router
from app.api.routers import teams as teams_router
from app.api.routers import users as users_router
from app.config import settings
from app.ingestion import router as ingestion_router
from app.reports import router as reports_router

app = FastAPI(title="Call Center QA Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(ingestion_router.router)
app.include_router(calls_router.router)
app.include_router(agents_router.router)
app.include_router(rubrics_router.router)
app.include_router(analytics_router.router)
app.include_router(reports_router.router)
app.include_router(teams_router.router)
app.include_router(users_router.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
