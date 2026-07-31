"""Deterministic (rule-based) scoring. Implemented here: required/forbidden
phrase matching, talk ratio (when speaker labels are available), greeting/
closing detection, question count, call duration. NOT implemented yet
(needs finer-grained audio analysis than this MVP's segment data supports):
interruption count, pause/silence detection, speech tempo, precise
time-to-first-response. Those are documented future work, not silent gaps."""

from dataclasses import dataclass

DEFAULT_GREETING_KEYWORDS = [
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "приветствую",
]
DEFAULT_CLOSING_KEYWORDS = [
    "до свидания",
    "всего доброго",
    "хорошего дня",
    "спасибо за звонок",
    "всего хорошего",
]


def find_phrase_occurrence(text: str, phrase: str) -> str | None:
    """Case-insensitive substring search; returns the matched substring with
    its original casing from `text`, or None if not found."""
    idx = text.lower().find(phrase.lower())
    if idx == -1:
        return None
    return text[idx : idx + len(phrase)]


@dataclass
class RuleEvaluation:
    score: float
    rationale: str
    quote: str | None
    quote_verified: bool


def evaluate_phrase_criterion(
    transcript_text: str,
    max_score: int,
    required_phrases: list[str] | None,
    forbidden_phrases: list[str] | None,
) -> RuleEvaluation:
    """Scores a single rule-based criterion. A forbidden phrase found is
    always a hard failure (score=1); otherwise the score is the share of
    required phrases that were found, scaled to max_score."""
    required_phrases = required_phrases or []
    forbidden_phrases = forbidden_phrases or []

    for phrase in forbidden_phrases:
        occurrence = find_phrase_occurrence(transcript_text, phrase)
        if occurrence:
            return RuleEvaluation(
                score=1.0,
                rationale=f'Forbidden phrase detected: "{phrase}".',
                quote=occurrence,
                quote_verified=True,
            )

    if required_phrases:
        found = [(p, find_phrase_occurrence(transcript_text, p)) for p in required_phrases]
        found_phrases = [p for p, occ in found if occ]
        missing = [p for p in required_phrases if p not in found_phrases]
        ratio = len(found_phrases) / len(required_phrases)
        score = max(1.0, round(ratio * max_score, 2))
        rationale = (
            "All required phrases present."
            if not missing
            else f"Missing required phrase(s): {', '.join(missing)}."
        )
        quote = next((occ for _, occ in found if occ), None)
        return RuleEvaluation(score=score, rationale=rationale, quote=quote, quote_verified=quote is not None)

    return RuleEvaluation(
        score=float(max_score),
        rationale="No forbidden phrases detected.",
        quote=None,
        quote_verified=False,
    )


def compute_talk_ratio(segments: list[dict]) -> dict | None:
    """agent/customer speaking time and the agent's share of total talk time.
    Returns None (explicitly, not a fabricated 50/50 guess) when segments
    carry no speaker labels - i.e. the source audio was mono."""
    if not segments or not any(s.get("speaker") for s in segments):
        return None

    agent_seconds = sum(
        s["end"] - s["start"] for s in segments if s.get("speaker") == "agent"
    )
    customer_seconds = sum(
        s["end"] - s["start"] for s in segments if s.get("speaker") == "customer"
    )
    total = agent_seconds + customer_seconds
    return {
        "agent_seconds": round(agent_seconds, 2),
        "customer_seconds": round(customer_seconds, 2),
        "agent_ratio": round(agent_seconds / total, 3) if total else None,
    }


def detect_keyword(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def count_questions(text: str) -> int:
    return text.count("?")


def call_duration_seconds(segments: list[dict]) -> float | None:
    if not segments:
        return None
    return round(max(s["end"] for s in segments), 2)
