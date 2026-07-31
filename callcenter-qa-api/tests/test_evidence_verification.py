from app.qa_evaluation.evidence import locate_segment, verify_quote

TRANSCRIPT = "Agent: Hello and thank you for calling support. Customer: Hi, I have an issue."


def test_verify_quote_exact_match():
    assert verify_quote("thank you for calling", TRANSCRIPT) is True


def test_verify_quote_case_and_whitespace_insensitive():
    assert verify_quote("THANK   YOU for   calling", TRANSCRIPT) is True


def test_verify_quote_not_present():
    assert verify_quote("this text never appears anywhere in it", TRANSCRIPT) is False


def test_verify_quote_empty_string():
    assert verify_quote("", TRANSCRIPT) is False
    assert verify_quote("   ", TRANSCRIPT) is False


def test_verify_quote_near_match_within_fuzzy_threshold():
    # one character changed near the end - fuzzy fallback should still pass
    assert verify_quote("thank you for callingx", TRANSCRIPT, fuzzy_threshold=0.85) is True


def test_locate_segment_finds_containing_segment():
    segments = [
        {"speaker": "agent", "start": 0.0, "end": 3.0, "text": "Hello and thank you for calling support."},
        {"speaker": "customer", "start": 3.0, "end": 5.0, "text": "Hi, I have an issue."},
    ]
    segment = locate_segment("thank you for calling", segments)
    assert segment is not None
    assert segment["speaker"] == "agent"


def test_locate_segment_returns_none_when_not_found():
    segments = [{"speaker": "agent", "start": 0.0, "end": 3.0, "text": "Hello."}]
    assert locate_segment("nonexistent phrase", segments) is None


def test_locate_segment_empty_quote_returns_none():
    segments = [{"speaker": "agent", "start": 0.0, "end": 3.0, "text": "Hello."}]
    assert locate_segment("", segments) is None
