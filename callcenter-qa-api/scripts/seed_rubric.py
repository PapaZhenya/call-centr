"""Seed a default rubric (criteria + an activated version). Idempotent: safe to
re-run; skips criteria that already exist and does nothing if an active
version already exists.

Run with: docker compose exec api python -m scripts.seed_rubric
"""
import asyncio

from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.rubric import RubricCriterion, RubricVersion, RubricVersionCriterion

DEFAULT_CRITERIA = [
    {
        "key": "script_adherence",
        "label": "Script Adherence",
        "description": "Did the agent follow the required call script/greeting/closing structure?",
    },
    {
        "key": "politeness",
        "label": "Politeness & Tone",
        "description": "Was the agent polite, patient, and professional in tone throughout the call?",
    },
    {
        "key": "compliance_disclosure",
        "label": "Compliance Disclosure",
        "description": "Did the agent state all legally/contractually required disclosures, verbatim or in substance?",
    },
    {
        "key": "resolution",
        "label": "Issue Resolution",
        "description": "Was the customer's issue resolved, or was a clear and correct next step communicated?",
    },
    {
        "key": "empathy",
        "label": "Empathy",
        "description": "Did the agent acknowledge the customer's situation or frustration appropriately?",
    },
]


async def seed() -> None:
    async with async_session_factory() as db:
        criteria = []
        for item in DEFAULT_CRITERIA:
            result = await db.execute(
                select(RubricCriterion).where(RubricCriterion.key == item["key"])
            )
            existing = result.scalar_one_or_none()
            criteria.append(existing or RubricCriterion(**item))
            if existing is None:
                db.add(criteria[-1])
        await db.flush()

        result = await db.execute(select(RubricVersion).where(RubricVersion.is_active.is_(True)))
        if result.scalar_one_or_none() is not None:
            print("An active rubric version already exists - skipping version creation.")
            await db.commit()
            return

        version = RubricVersion(
            version_number=1,
            name="Default QA Rubric",
            llm_model_id=settings.local_llm_model,
            is_active=True,
        )
        db.add(version)
        await db.flush()

        for criterion in criteria:
            db.add(
                RubricVersionCriterion(
                    rubric_version_id=version.id,
                    rubric_criterion_id=criterion.id,
                    weight=1.0,
                )
            )

        await db.commit()
        print(f"Seeded rubric version {version.version_number} with {len(criteria)} criteria.")


if __name__ == "__main__":
    asyncio.run(seed())
