"""Evidence grounding: never trust a quote the model produced without
confirming it actually occurs in the transcript. See rubric_schema.py for
where the model is instructed to quote verbatim, and service.py for how an
unverifiable quote is handled (dropped, quote_verified=False)."""

import difflib
import re


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_quote(quote: str, transcript_text: str, fuzzy_threshold: float = 0.85) -> bool:
    """True only if `quote` genuinely appears in the transcript: an exact
    (whitespace/case-normalized) substring match, or - as a fallback for
    minor punctuation/whitespace drift a local model can introduce when
    "copying" text - a large contiguous overlap (>= fuzzy_threshold of the
    quote's length) with the transcript."""
    quote = quote.strip()
    if not quote:
        return False

    normalized_quote = _normalize(quote)
    normalized_transcript = _normalize(transcript_text)
    if normalized_quote in normalized_transcript:
        return True

    matcher = difflib.SequenceMatcher(a=normalized_quote, b=normalized_transcript)
    match = matcher.find_longest_match(0, len(normalized_quote), 0, len(normalized_transcript))
    if match.size == 0:
        return False
    return (match.size / len(normalized_quote)) >= fuzzy_threshold


def locate_segment(quote: str, segments: list[dict]) -> dict | None:
    """Finds the transcript segment containing `quote`, to attach
    start/end/speaker evidence to a score. Returns None if no single segment
    contains it (e.g. the model's quote spans a segment boundary, or
    segments have no speaker labels because the source audio was mono)."""
    normalized_quote = _normalize(quote)
    if not normalized_quote:
        return None
    for segment in segments:
        if normalized_quote in _normalize(segment.get("text", "")):
            return segment
    return None
