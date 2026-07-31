from app.qa_evaluation.rules import (
    call_duration_seconds,
    compute_talk_ratio,
    count_questions,
    detect_keyword,
    evaluate_phrase_criterion,
    find_phrase_occurrence,
)

TRANSCRIPT = "Agent: Hello, thank you for calling. May I have your card number please?"


def test_find_phrase_occurrence_case_insensitive():
    assert find_phrase_occurrence(TRANSCRIPT, "HELLO") == "Hello"


def test_find_phrase_occurrence_not_found():
    assert find_phrase_occurrence(TRANSCRIPT, "goodbye") is None


def test_evaluate_phrase_criterion_forbidden_phrase_forces_min_score():
    result = evaluate_phrase_criterion(TRANSCRIPT, max_score=5, required_phrases=None,
                                        forbidden_phrases=["card number"])
    assert result.score == 1.0
    assert result.quote_verified is True
    assert "card number" in result.quote.lower()


def test_evaluate_phrase_criterion_all_required_present():
    result = evaluate_phrase_criterion(TRANSCRIPT, max_score=5, required_phrases=["hello", "thank you"],
                                        forbidden_phrases=None)
    assert result.score == 5.0
    assert "missing" not in result.rationale.lower()


def test_evaluate_phrase_criterion_partial_required_scaled():
    result = evaluate_phrase_criterion(
        TRANSCRIPT, max_score=4, required_phrases=["hello", "goodbye"], forbidden_phrases=None
    )
    # 1 of 2 required phrases found -> half of max_score
    assert result.score == 2.0
    assert "goodbye" in result.rationale


def test_evaluate_phrase_criterion_forbidden_takes_priority_over_required():
    result = evaluate_phrase_criterion(
        TRANSCRIPT, max_score=5, required_phrases=["hello"], forbidden_phrases=["card number"]
    )
    assert result.score == 1.0


def test_evaluate_phrase_criterion_no_lists_is_full_score():
    result = evaluate_phrase_criterion(TRANSCRIPT, max_score=5, required_phrases=None, forbidden_phrases=None)
    assert result.score == 5.0


def test_compute_talk_ratio_none_without_speaker_labels():
    segments = [{"start": 0, "end": 5, "text": "hi", "speaker": None}]
    assert compute_talk_ratio(segments) is None


def test_compute_talk_ratio_with_speaker_labels():
    segments = [
        {"speaker": "agent", "start": 0, "end": 6, "text": "a"},
        {"speaker": "customer", "start": 6, "end": 10, "text": "b"},
    ]
    result = compute_talk_ratio(segments)
    assert result["agent_seconds"] == 6
    assert result["customer_seconds"] == 4
    assert result["agent_ratio"] == 0.6


def test_detect_keyword():
    assert detect_keyword(TRANSCRIPT, ["thank you"]) is True
    assert detect_keyword(TRANSCRIPT, ["goodbye"]) is False


def test_count_questions():
    assert count_questions("What is your name? Is this correct?") == 2
    assert count_questions("No questions here.") == 0


def test_call_duration_seconds():
    segments = [{"start": 0, "end": 5, "text": "a"}, {"start": 5, "end": 12.5, "text": "b"}]
    assert call_duration_seconds(segments) == 12.5


def test_call_duration_seconds_empty():
    assert call_duration_seconds([]) is None
