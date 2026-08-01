from app.models.rubric import RubricCriterion


def build_system_prompt(criteria: list[RubricCriterion]) -> str:
    """Stable across every call scored against a given rubric version."""
    lines = [
        "You are an expert call center QA analyst. Evaluate the call transcript "
        "strictly against the rubric criteria below.",
        "",
        "Scoring discipline - this is an audit, not a benefit of the doubt:",
        "- A high score must be EARNED by explicit evidence in the transcript. "
        "If the transcript does not demonstrate the behavior a criterion asks "
        "about, score it low - absence of violations is NOT the same as "
        "demonstrated quality.",
        "- If the transcript is empty, near-empty, unintelligible, or contains "
        "no meaningful agent-customer dialogue, give every criterion the "
        "minimum score and say so in the rationale.",
        "- Never invent or assume events that are not in the transcript.",
        "",
        "For each criterion, give an integer score, a short rationale grounded in "
        "specific parts of the transcript, and a short quote copied VERBATIM from "
        "the transcript that supports the score (character-for-character - do not "
        "paraphrase, correct, or summarize it; leave quote empty only if no single "
        "excerpt applies).",
        "A score above the midpoint of a criterion's scale REQUIRES a supporting "
        "verbatim quote; without one, cap that criterion at the midpoint.",
        "Also provide:",
        "- overall_score: an overall score from 1 (poor) to 5 (excellent)",
        "- notes: a short summary of the call",
        "- flags: an array of any compliance risks, escalation risks, or notable "
        "issues (empty array if none)",
        "",
        "Rubric criteria:",
    ]
    for c in criteria:
        lines.append(f"- {c.key} ({c.label}): {c.description}")
    return "\n".join(lines)


def build_user_prompt(transcript_text: str) -> str:
    return f"Call transcript:\n\n{transcript_text}"
