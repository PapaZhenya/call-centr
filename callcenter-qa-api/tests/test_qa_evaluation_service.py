import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.base import LLMResult
from app.models.qa_evaluation import SOURCE_LOCAL_LLM, STATUS_COMPLETED
from app.qa_evaluation.service import apply_manual_correction, evaluate_call

# Long enough to clear settings.qa_min_transcript_words - shorter transcripts
# skip the LLM entirely (see the insufficient-transcript tests below).
TRANSCRIPT = (
    "Agent: Hello and thank you for calling our support line today. "
    "Customer: Hi there, my internet stopped working this morning. "
    "Agent: Let me check your line right away and get this resolved for you."
)


def _mock_db() -> MagicMock:
    # AsyncSession.add() is synchronous; only commit/flush/refresh/execute are async.
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _criterion(key: str, label: str, *, max_score=5, weight=1.0, is_critical=False):
    return SimpleNamespace(
        id=uuid.uuid4(),
        key=key,
        label=label,
        description=label,
        max_score=max_score,
        weight=weight,
        is_critical=is_critical,
        required_phrases=None,
        forbidden_phrases=None,
        is_rule_based=False,
    )


def _rubric_version(criteria):
    criteria_links = [SimpleNamespace(rubric_criterion=c) for c in criteria]
    return SimpleNamespace(id=uuid.uuid4(), llm_model_id="qwen2.5:7b", criteria_links=criteria_links)


@pytest.mark.asyncio
async def test_evaluate_call_persists_score_for_each_criterion_and_computes_overall():
    politeness = _criterion("politeness", "Politeness")
    clarity = _criterion("clarity", "Clarity")
    rubric_version = _rubric_version([politeness, clarity])
    call = SimpleNamespace(id=uuid.uuid4())

    fake_result = LLMResult(
        parsed={
            # Deliberately wrong - must NOT end up as the persisted overall_score;
            # that's computed programmatically from the per-criterion scores.
            "overall_score": 4,
            "notes": "Good call.",
            "flags": [],
            "criteria": {
                "politeness": {
                    "score": 5,
                    "rationale": "Very polite.",
                    "quote": "thank you for calling",  # present in TRANSCRIPT
                },
                "clarity": {
                    "score": 1,
                    "rationale": "Unclear.",
                    "quote": "this exact phrase never appears anywhere",  # not present
                },
            },
        },
        raw_text="{...}",
        raw_response={"id": "resp_123"},
    )

    provider = AsyncMock()
    provider.generate_json = AsyncMock(return_value=fake_result)

    db = _mock_db()

    with (
        patch(
            "app.qa_evaluation.service.get_active_version",
            AsyncMock(return_value=rubric_version),
        ),
        patch("app.qa_evaluation.service.get_llm_provider", return_value=provider),
    ):
        evaluation = await evaluate_call(db, call, TRANSCRIPT, segments=[])

    assert evaluation.call_id == call.id
    assert evaluation.rubric_version_id == rubric_version.id
    assert evaluation.status == STATUS_COMPLETED
    # politeness normalizes to 1.0 (perfect), clarity to 0.0 (worst) -> avg 0.5
    # -> rescaled to the 1..5 range -> 3.0
    assert evaluation.overall_score == 3.0

    added = [c.args[0] for c in db.add.call_args_list if type(c.args[0]).__name__ == "QAEvaluationScore"]
    scores = {s.rubric_criterion_id: s for s in added}
    politeness_score = scores[politeness.id]
    clarity_score = scores[clarity.id]

    assert politeness_score.source == SOURCE_LOCAL_LLM
    assert politeness_score.quote == "thank you for calling"
    assert politeness_score.quote_verified is True

    # The LLM's quote doesn't actually appear in the transcript - never trust
    # it blindly, drop it instead.
    assert clarity_score.quote is None
    assert clarity_score.quote_verified is False


@pytest.mark.asyncio
async def test_evaluate_call_clamps_out_of_range_scores():
    criterion = _criterion("politeness", "Politeness", max_score=5)
    rubric_version = _rubric_version([criterion])
    call = SimpleNamespace(id=uuid.uuid4())

    fake_result = LLMResult(
        parsed={
            "overall_score": 4,
            "notes": None,
            "flags": [],
            # Verified quote so only clamping is under test (an unverified
            # quote would additionally cap the score at the midpoint).
            "criteria": {"politeness": {"score": 999, "rationale": "r", "quote": "thank you for calling"}},
        },
        raw_text="{...}",
        raw_response={},
    )
    provider = AsyncMock()
    provider.generate_json = AsyncMock(return_value=fake_result)
    db = _mock_db()

    with (
        patch(
            "app.qa_evaluation.service.get_active_version",
            AsyncMock(return_value=rubric_version),
        ),
        patch("app.qa_evaluation.service.get_llm_provider", return_value=provider),
    ):
        await evaluate_call(db, call, TRANSCRIPT, segments=[])

    added_score = next(
        c.args[0] for c in db.add.call_args_list if type(c.args[0]).__name__ == "QAEvaluationScore"
    )
    assert added_score.score == 5  # clamped to max_score, never trusted at 999


@pytest.mark.asyncio
async def test_evaluate_call_caps_unevidenced_high_scores_at_midpoint():
    criterion = _criterion("politeness", "Politeness", max_score=5)
    rubric_version = _rubric_version([criterion])
    call = SimpleNamespace(id=uuid.uuid4())

    fake_result = LLMResult(
        parsed={
            "overall_score": 5,
            "notes": None,
            "flags": [],
            # High score with no quote at all - the prompt forbids this, and
            # the code must enforce it when the model doesn't comply.
            "criteria": {"politeness": {"score": 5, "rationale": "r", "quote": ""}},
        },
        raw_text="{...}",
        raw_response={},
    )
    provider = AsyncMock()
    provider.generate_json = AsyncMock(return_value=fake_result)
    db = _mock_db()

    with (
        patch(
            "app.qa_evaluation.service.get_active_version",
            AsyncMock(return_value=rubric_version),
        ),
        patch("app.qa_evaluation.service.get_llm_provider", return_value=provider),
    ):
        await evaluate_call(db, call, TRANSCRIPT, segments=[])

    added_score = next(
        c.args[0] for c in db.add.call_args_list if type(c.args[0]).__name__ == "QAEvaluationScore"
    )
    assert added_score.score == 3.0  # (1 + max_score) / 2


@pytest.mark.asyncio
async def test_evaluate_call_critical_criterion_below_threshold_adds_flag():
    critical = _criterion("no_card_request", "No card request", is_critical=True)
    rubric_version = _rubric_version([critical])
    call = SimpleNamespace(id=uuid.uuid4())

    fake_result = LLMResult(
        parsed={
            "overall_score": 5,
            "notes": None,
            "flags": [],
            "criteria": {"no_card_request": {"score": 1, "rationale": "r", "quote": ""}},
        },
        raw_text="{...}",
        raw_response={},
    )
    provider = AsyncMock()
    provider.generate_json = AsyncMock(return_value=fake_result)
    db = _mock_db()

    with (
        patch(
            "app.qa_evaluation.service.get_active_version",
            AsyncMock(return_value=rubric_version),
        ),
        patch("app.qa_evaluation.service.get_llm_provider", return_value=provider),
    ):
        evaluation = await evaluate_call(db, call, TRANSCRIPT, segments=[])

    assert "critical_violation" in evaluation.flags


@pytest.mark.asyncio
async def test_evaluate_call_insufficient_transcript_skips_llm_and_scores_minimum():
    politeness = _criterion("politeness", "Politeness")
    resolution = _criterion("resolution", "Resolution")
    rubric_version = _rubric_version([politeness, resolution])
    call = SimpleNamespace(id=uuid.uuid4())

    provider = AsyncMock()
    db = _mock_db()

    with (
        patch(
            "app.qa_evaluation.service.get_active_version",
            AsyncMock(return_value=rubric_version),
        ),
        patch("app.qa_evaluation.service.get_llm_provider", return_value=provider),
    ):
        evaluation = await evaluate_call(db, call, "You", segments=[])

    provider.generate_json.assert_not_called()  # silence never reaches the model
    assert evaluation.status == STATUS_COMPLETED  # in_progress only while computing
    assert "insufficient_transcript" in evaluation.flags
    assert evaluation.overall_score == 1.0  # every criterion at minimum

    added = [c.args[0] for c in db.add.call_args_list if type(c.args[0]).__name__ == "QAEvaluationScore"]
    assert len(added) == 2
    assert all(s.score == 1.0 for s in added)


@pytest.mark.asyncio
async def test_evaluate_call_insufficient_transcript_still_runs_rule_criteria():
    rule = _criterion("greeting", "Greeting")
    rule.is_rule_based = True
    rule.required_phrases = ["hello"]
    rubric_version = _rubric_version([rule, _criterion("politeness", "Politeness")])
    call = SimpleNamespace(id=uuid.uuid4())

    provider = AsyncMock()
    db = _mock_db()

    with (
        patch(
            "app.qa_evaluation.service.get_active_version",
            AsyncMock(return_value=rubric_version),
        ),
        patch("app.qa_evaluation.service.get_llm_provider", return_value=provider),
    ):
        evaluation = await evaluate_call(db, call, "Hello there", segments=[])

    provider.generate_json.assert_not_called()
    # Rule criterion scored on its own merits (phrase present -> max), the
    # LLM criterion floored at 1 - the overall reflects both.
    added = [c.args[0] for c in db.add.call_args_list if type(c.args[0]).__name__ == "QAEvaluationScore"]
    assert len(added) == 2
    assert "insufficient_transcript" in evaluation.flags


class _FakeScore:
    """Mimics QAEvaluationScore closely enough for apply_manual_correction:
    plain attributes plus the effective_score property."""

    def __init__(self, score, criterion):
        self.score = score
        self.rubric_criterion = criterion
        self.manual_score = None
        self.manual_comment = None
        self.corrected_by_user_id = None
        self.corrected_at = None

    @property
    def effective_score(self):
        return float(self.manual_score if self.manual_score is not None else self.score)


@pytest.mark.asyncio
async def test_manual_correction_overrides_and_recomputes_overall():
    criterion = _criterion("politeness", "Politeness")
    score_row = _FakeScore(5.0, criterion)
    evaluation = SimpleNamespace(scores=[score_row], flags=[], overall_score=5.0)
    db = AsyncMock()
    reviewer_id = uuid.uuid4()

    await apply_manual_correction(db, evaluation, score_row, 2.0, "too generous", reviewer_id)

    assert score_row.manual_score == 2.0
    assert score_row.score == 5.0  # model's number preserved
    assert score_row.manual_comment == "too generous"
    assert score_row.corrected_by_user_id == reviewer_id
    assert score_row.corrected_at is not None
    # (2-1)/(5-1) = 0.25 -> 1 + 0.25*4 = 2.0
    assert evaluation.overall_score == 2.0
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_manual_correction_clear_reverts_to_model_score():
    criterion = _criterion("politeness", "Politeness")
    score_row = _FakeScore(4.0, criterion)
    evaluation = SimpleNamespace(scores=[score_row], flags=[], overall_score=None)
    db = AsyncMock()

    await apply_manual_correction(db, evaluation, score_row, 1.0, None, uuid.uuid4())
    assert evaluation.overall_score == 1.0

    await apply_manual_correction(db, evaluation, score_row, None, None, uuid.uuid4())

    assert score_row.manual_score is None
    assert score_row.corrected_at is None
    assert evaluation.overall_score == 4.0  # back to the model's value


@pytest.mark.asyncio
async def test_manual_correction_on_critical_criterion_updates_flag():
    critical = _criterion("no_card_request", "No card request", is_critical=True)
    score_row = _FakeScore(5.0, critical)
    evaluation = SimpleNamespace(scores=[score_row], flags=["model_flag"], overall_score=5.0)
    db = AsyncMock()

    await apply_manual_correction(db, evaluation, score_row, 1.0, None, uuid.uuid4())
    assert "critical_violation" in evaluation.flags
    assert "model_flag" in evaluation.flags  # other flags untouched

    await apply_manual_correction(db, evaluation, score_row, None, None, uuid.uuid4())
    assert "critical_violation" not in evaluation.flags


@pytest.mark.asyncio
async def test_manual_correction_clamps_to_criterion_scale():
    criterion = _criterion("politeness", "Politeness", max_score=5)
    score_row = _FakeScore(3.0, criterion)
    evaluation = SimpleNamespace(scores=[score_row], flags=[], overall_score=None)
    db = AsyncMock()

    await apply_manual_correction(db, evaluation, score_row, 99.0, None, uuid.uuid4())

    assert score_row.manual_score == 5.0


@pytest.mark.asyncio
async def test_evaluate_call_raises_without_active_rubric():
    db = AsyncMock()
    call = SimpleNamespace(id=uuid.uuid4())

    with patch("app.qa_evaluation.service.get_active_version", AsyncMock(return_value=None)):
        with pytest.raises(ValueError):
            await evaluate_call(db, call, "transcript")
