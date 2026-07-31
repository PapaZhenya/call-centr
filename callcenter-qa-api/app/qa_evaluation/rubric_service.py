import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rubric import RubricCriterion, RubricVersion, RubricVersionCriterion
from app.schemas.rubric import RubricCriterionCreate, RubricCriterionUpdate, RubricVersionCreate


async def create_criterion(db: AsyncSession, data: RubricCriterionCreate) -> RubricCriterion:
    criterion = RubricCriterion(**data.model_dump())
    db.add(criterion)
    await db.commit()
    await db.refresh(criterion)
    return criterion


async def list_criteria(db: AsyncSession) -> list[RubricCriterion]:
    result = await db.execute(select(RubricCriterion).order_by(RubricCriterion.key))
    return list(result.scalars().all())


async def update_criterion(
    db: AsyncSession, criterion_id: uuid.UUID, data: RubricCriterionUpdate
) -> RubricCriterion | None:
    criterion = await db.get(RubricCriterion, criterion_id)
    if criterion is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(criterion, field, value)
    await db.commit()
    await db.refresh(criterion)
    return criterion


async def _next_version_number(db: AsyncSession) -> int:
    result = await db.execute(select(func.max(RubricVersion.version_number)))
    return (result.scalar() or 0) + 1


async def create_version(db: AsyncSession, data: RubricVersionCreate) -> RubricVersion:
    version = RubricVersion(
        version_number=await _next_version_number(db),
        name=data.name,
        llm_model_id=data.llm_model_id,
    )
    db.add(version)
    await db.flush()  # assign version.id before creating the criteria links

    for item in data.criteria:
        db.add(
            RubricVersionCriterion(
                rubric_version_id=version.id,
                rubric_criterion_id=item.rubric_criterion_id,
                weight=item.weight,
            )
        )

    await db.commit()
    await db.refresh(version)
    return version


async def list_versions(db: AsyncSession) -> list[RubricVersion]:
    result = await db.execute(select(RubricVersion).order_by(RubricVersion.version_number.desc()))
    return list(result.scalars().all())


async def activate_version(db: AsyncSession, version_id: uuid.UUID) -> RubricVersion | None:
    version = await db.get(RubricVersion, version_id)
    if version is None:
        return None
    await db.execute(update(RubricVersion).values(is_active=False))  # only one active at a time
    version.is_active = True
    await db.commit()
    await db.refresh(version)
    return version


async def get_active_version(db: AsyncSession) -> RubricVersion | None:
    stmt = (
        select(RubricVersion)
        .where(RubricVersion.is_active.is_(True))
        .options(
            selectinload(RubricVersion.criteria_links).selectinload(
                RubricVersionCriterion.rubric_criterion
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
