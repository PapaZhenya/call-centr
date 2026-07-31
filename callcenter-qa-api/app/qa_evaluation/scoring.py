"""Programmatic scoring: the model (or a rule) proposes a score, but the
number that actually gets stored/aggregated is always computed or clamped in
code - never trusted verbatim from the LLM. See service.py for where this is
wired into the evaluation flow."""

from dataclasses import dataclass


def clamp_score(score: float, max_score: int, min_score: float = 1.0) -> float:
    """A local model can (and sometimes will) return a score outside the
    criterion's valid range - clamp it rather than trusting it."""
    return max(min_score, min(float(score), float(max_score)))


@dataclass
class ScoreEntry:
    score: float
    weight: float
    max_score: int
    is_critical: bool = False


def _normalize(entry: ScoreEntry) -> float:
    # Scores range 1..max_score (never 0), so normalize against that range -
    # score/max_score alone would put the worst possible score above 0.
    if entry.max_score <= 1:
        return 1.0
    return (entry.score - 1) / (entry.max_score - 1)


def compute_weighted_overall(entries: list[ScoreEntry]) -> float | None:
    """Weighted average of per-criterion scores, each normalized to a 0-1
    scale by its own [1, max_score] range before weighting, then rescaled to
    a 1-5 overall figure so it's comparable across rubrics with different
    per-criterion scales. This - not the model's self-reported overall_score
    - is what's persisted as QAEvaluation.overall_score."""
    if not entries:
        return None
    total_weight = sum(e.weight for e in entries)
    if total_weight <= 0:
        return None
    normalized_avg = sum(_normalize(e) * e.weight for e in entries) / total_weight
    return round(1 + normalized_avg * 4, 2)


def has_critical_violation(entries: list[ScoreEntry], threshold_ratio: float = 0.5) -> bool:
    """A critical criterion (e.g. "requested payment card details") scoring
    below half its max is treated as a critical violation regardless of what
    the model's `flags` array says."""
    return any(e.is_critical and e.score < e.max_score * threshold_ratio for e in entries)
