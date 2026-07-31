import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.auth.permissions import RUBRIC_WRITE
from app.database import get_db
from app.qa_evaluation import rubric_service
from app.schemas.rubric import (
    RubricCriterionCreate,
    RubricCriterionRead,
    RubricCriterionUpdate,
    RubricVersionCreate,
    RubricVersionRead,
)

router = APIRouter(prefix="/api/v1/rubric", tags=["rubric"], dependencies=[Depends(get_current_user)])
_require_rubric_write = Depends(require_permission(RUBRIC_WRITE))


@router.get("/criteria", response_model=list[RubricCriterionRead])
async def list_criteria(db: AsyncSession = Depends(get_db)):
    return await rubric_service.list_criteria(db)


@router.post(
    "/criteria", response_model=RubricCriterionRead, status_code=201, dependencies=[_require_rubric_write]
)
async def create_criterion(data: RubricCriterionCreate, db: AsyncSession = Depends(get_db)):
    return await rubric_service.create_criterion(db, data)


@router.patch(
    "/criteria/{criterion_id}", response_model=RubricCriterionRead, dependencies=[_require_rubric_write]
)
async def update_criterion(
    criterion_id: uuid.UUID, data: RubricCriterionUpdate, db: AsyncSession = Depends(get_db)
):
    criterion = await rubric_service.update_criterion(db, criterion_id, data)
    if criterion is None:
        raise HTTPException(status_code=404, detail="Criterion not found")
    return criterion


@router.get("/versions", response_model=list[RubricVersionRead])
async def list_versions(db: AsyncSession = Depends(get_db)):
    return await rubric_service.list_versions(db)


@router.post(
    "/versions", response_model=RubricVersionRead, status_code=201, dependencies=[_require_rubric_write]
)
async def create_version(data: RubricVersionCreate, db: AsyncSession = Depends(get_db)):
    return await rubric_service.create_version(db, data)


@router.post(
    "/versions/{version_id}/activate",
    response_model=RubricVersionRead,
    dependencies=[_require_rubric_write],
)
async def activate_version(version_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    version = await rubric_service.activate_version(db, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Rubric version not found")
    return version
