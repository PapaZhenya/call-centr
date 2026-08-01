import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.factory import get_llm_provider
from app.models.call import Call
from app.models.qa_evaluation import (
    SOURCE_LOCAL_LLM,
    SOURCE_RULE,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    QAEvaluation,
    QAEvaluationScore,
)
from app.models.rubric import RubricCriterion
from app.qa_evaluation import rules
from app.qa_evaluation.evidence import locate_segment, verify_quote
from app.qa_evaluation.prompt import build_system_prompt, build_user_prompt
from app.qa_evaluation.rubric_schema import build_qa_schema, llm_scored_criteria
from app.qa_evaluation.rubric_service import get_active_version
from app.qa_evaluation.scoring import (
    ScoreEntry,
    clamp_score,
    compute_weighted_overall,
    has_critical_violation,
)


def _build_score(
    evaluation_id: uuid.UUID,
    criterion: RubricCriterion,
    score: float,
    rationale: str | None,
    quote: str | None,
    quote_verified: bool,
    source: str,
    segments: list[dict],
) -> QAEvaluationScore:
    segment = locate_segment(quote, segments) if quote else None
    return QAEvaluationScore(
        qa_evaluation_id=evaluation_id,
        rubric_criterion_id=criterion.id,
        score=score,
        rationale=rationale,
        source=source,
        quote=quote,
        quote_verified=quote_verified,
        evidence_start=segment["start"] if segment else None,
        evidence_end=segment["end"] if segment else None,
        evidence_speaker=segment.get("speaker") if segment else None,
    )


async def evaluate_call(
    db: AsyncSession, call: Call, transcript_text: str, segments: list[dict] | None = None
) -> QAEvaluation:
    """Hybrid scoring: criteria with required/forbidden phrases are scored
    deterministically by app/qa_evaluation/rules.py; everything else goes to
    the local LLM. Rule-based scores are committed before the LLM call, so a
    down/unreachable model doesn't lose deterministic scoring work - the
    evaluation is marked failed but keeps whatever it already computed."""
    rubric_version = await get_active_version(db)
    if rubric_version is None:
        raise ValueError("No active rubric version configured")

    segments = segments or []
    all_criteria = [link.rubric_criterion for link in rubric_version.criteria_links]
    rule_criteria = [c for c in all_criteria if c.is_rule_based]
    llm_criteria = llm_scored_criteria(all_criteria)

    # Created in_progress and flipped to completed at the very end, so a
    # concurrent /qa read never mistakes a half-built evaluation (committed
    # rule scores, no overall yet) for a finished one.
    evaluation = QAEvaluation(
        call_id=call.id,
        rubric_version_id=rubric_version.id,
        status=STATUS_IN_PROGRESS,
        flags=[],
    )
    db.add(evaluation)
    await db.flush()  # assign evaluation.id before adding scores

    entries: list[ScoreEntry] = []

    for criterion in rule_criteria:
        result = rules.evaluate_phrase_criterion(
            transcript_text, criterion.max_score, criterion.required_phrases, criterion.forbidden_phrases
        )
        db.add(
            _build_score(
                evaluation.id,
                criterion,
                result.score,
                result.rationale,
                result.quote,
                result.quote_verified,
                SOURCE_RULE,
                segments,
            )
        )
        entries.append(ScoreEntry(result.score, float(criterion.weight), criterion.max_score, criterion.is_critical))

    await db.commit()  # rule-based results survive even if the LLM call below fails

    notes: str | None = None
    model_flags: list[str] = []

    # Deterministic guard: near-empty speech can't demonstrate quality, and a
    # local LLM asked to grade silence tends to hallucinate a decent call.
    # Score every LLM criterion at the minimum and skip the model entirely.
    insufficient = len(transcript_text.split()) < settings.qa_min_transcript_words
    if insufficient and llm_criteria:
        for criterion in llm_criteria:
            db.add(
                _build_score(
                    evaluation.id,
                    criterion,
                    1.0,
                    "Transcript contains too little speech to evaluate this criterion.",
                    None,
                    False,
                    SOURCE_RULE,
                    segments,
                )
            )
            entries.append(ScoreEntry(1.0, float(criterion.weight), criterion.max_score, criterion.is_critical))
        model_flags = ["insufficient_transcript"]
        notes = "Call contains too little speech for QA evaluation."

    if llm_criteria and not insufficient:
        schema = build_qa_schema(llm_criteria)
        system_prompt = build_system_prompt(llm_criteria)
        user_prompt = build_user_prompt(transcript_text)
        evaluation.system_prompt_snapshot = system_prompt

        try:
            provider = get_llm_provider()
            result = await provider.generate_json(
                system_prompt=system_prompt, user_prompt=user_prompt, json_schema=schema
            )
        except Exception as exc:
            evaluation.status = STATUS_FAILED
            evaluation.error_message = str(exc)
            await db.commit()
            raise

        parsed = result.parsed
        evaluation.raw_llm_response = result.raw_response
        notes = parsed.get("notes")
        model_flags = parsed.get("flags") or []

        criteria_by_key = {c.key: c for c in llm_criteria}
        for key, score_data in parsed["criteria"].items():
            criterion = criteria_by_key[key]
            score = clamp_score(score_data["score"], criterion.max_score)
            quote = (score_data.get("quote") or "").strip()
            quote_verified = bool(quote) and verify_quote(quote, transcript_text)
            # The prompt demands a verbatim quote for any score above the
            # scale midpoint; local models don't always comply, so enforce it
            # here - unevidenced praise is capped, never trusted.
            midpoint = (1 + criterion.max_score) / 2
            if not quote_verified and score > midpoint:
                score = midpoint
            db.add(
                _build_score(
                    evaluation.id,
                    criterion,
                    score,
                    score_data.get("rationale"),
                    quote if quote_verified else None,
                    quote_verified,
                    SOURCE_LOCAL_LLM,
                    segments,
                )
            )
            entries.append(ScoreEntry(score, float(criterion.weight), criterion.max_score, criterion.is_critical))

    flags = list(model_flags)
    if has_critical_violation(entries):
        flags.append("critical_violation")

    evaluation.overall_score = compute_weighted_overall(entries)
    evaluation.notes = notes
    evaluation.flags = flags
    evaluation.status = STATUS_COMPLETED

    await db.commit()
    await db.refresh(evaluation)
    return evaluation
