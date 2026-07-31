from app.models.rubric import RubricCriterion

# Structured-outputs JSON Schema does not support numeric constraints
# (minimum/maximum) - the score range is enforced via prompt instructions
# instead (see prompt.py) and clamped programmatically after the fact
# (see app/qa_evaluation/scoring.py:clamp_score).


def llm_scored_criteria(criteria: list[RubricCriterion]) -> list[RubricCriterion]:
    """Criteria with required/forbidden phrases are scored deterministically
    by app/qa_evaluation/rules.py instead - they never reach the model."""
    return [c for c in criteria if not c.is_rule_based]


def build_qa_schema(criteria: list[RubricCriterion]) -> dict:
    """Builds the local LLM's required JSON output schema from the
    LLM-scored subset of the active rubric's criteria. Each criterion
    becomes a required {score, rationale, quote} property - this is the
    mechanism that makes the rubric data-driven: adding/removing a criterion
    changes what the model is constrained to return, with zero code changes.
    `quote` must be verbatim from the transcript - see evidence.py, which
    verifies it and drops it if it can't be found."""
    criteria_properties = {
        c.key: {
            "type": "object",
            "properties": {
                "score": {
                    "type": "integer",
                    "description": f"Score from 1 (poor) to {c.max_score} (excellent).",
                },
                "rationale": {
                    "type": "string",
                    "description": "Short rationale grounded in the transcript.",
                },
                "quote": {
                    "type": "string",
                    "description": (
                        "A short excerpt copied VERBATIM from the transcript that "
                        "supports this score. Empty string if no specific excerpt applies."
                    ),
                },
            },
            "required": ["score", "rationale", "quote"],
            "additionalProperties": False,
        }
        for c in criteria
    }

    return {
        "type": "object",
        "properties": {
            "overall_score": {
                "type": "number",
                "description": "Overall call score from 1 (poor) to 5 (excellent).",
            },
            "notes": {"type": "string", "description": "Short summary of the call."},
            "flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Compliance/escalation/notable-issue flags; empty if none.",
            },
            "criteria": {
                "type": "object",
                "properties": criteria_properties,
                "required": list(criteria_properties.keys()),
                "additionalProperties": False,
            },
        },
        "required": ["overall_score", "notes", "flags", "criteria"],
        "additionalProperties": False,
    }
