from app.models.rubric import RubricCriterion


def build_system_prompt(criteria: list[RubricCriterion]) -> str:
    """Stable across every call scored against a given rubric version."""
    lines = [
        "You are an expert call center QA analyst. Evaluate the call transcript "
        "strictly against the rubric criteria below.",
        "",
        "For each criterion, give an integer score, a short rationale grounded in "
        "specific parts of the transcript, and a short quote copied VERBATIM from "
        "the transcript that supports the score (character-for-character - do not "
        "paraphrase, correct, or summarize it; leave quote empty only if no single "
        "excerpt applies).",
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
