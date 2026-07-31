from app.models.rubric import RubricCriterion
from app.qa_evaluation.prompt import build_system_prompt, build_user_prompt
from app.qa_evaluation.rubric_schema import build_qa_schema, llm_scored_criteria


def _criterion(key: str, label: str, description: str, **kwargs) -> RubricCriterion:
    # Column defaults only apply on DB flush - set them explicitly here since
    # these tests build transient (never-flushed) instances.
    return RubricCriterion(
        key=key,
        label=label,
        description=description,
        max_score=kwargs.pop("max_score", 5),
        weight=kwargs.pop("weight", 1.0),
        is_critical=kwargs.pop("is_critical", False),
        **kwargs,
    )


def test_build_qa_schema_includes_all_criteria():
    criteria = [
        _criterion("script_adherence", "Script Adherence", "Followed script."),
        _criterion("politeness", "Politeness", "Was polite."),
    ]
    schema = build_qa_schema(criteria)

    criteria_schema = schema["properties"]["criteria"]
    assert set(criteria_schema["properties"].keys()) == {"script_adherence", "politeness"}
    assert criteria_schema["required"] == ["script_adherence", "politeness"]
    assert schema["additionalProperties"] is False
    assert criteria_schema["additionalProperties"] is False

    for prop in criteria_schema["properties"].values():
        assert prop["required"] == ["score", "rationale", "quote"]
        assert prop["additionalProperties"] is False
        # Structured-outputs schemas reject numeric constraints (minimum/maximum).
        assert "minimum" not in prop["properties"]["score"]
        assert "maximum" not in prop["properties"]["score"]


def test_build_qa_schema_uses_criterion_max_score():
    criteria = [_criterion("politeness", "Politeness", "Was polite.", max_score=10)]
    schema = build_qa_schema(criteria)
    description = schema["properties"]["criteria"]["properties"]["politeness"]["properties"]["score"][
        "description"
    ]
    assert "10" in description


def test_build_qa_schema_empty_criteria():
    schema = build_qa_schema([])
    assert schema["properties"]["criteria"]["properties"] == {}
    assert schema["properties"]["criteria"]["required"] == []


def test_llm_scored_criteria_excludes_rule_based():
    llm_only = _criterion("empathy", "Empathy", "Acknowledges frustration.")
    rule_only = _criterion(
        "greeting", "Greeting", "Greets the customer.", required_phrases=["hello"]
    )
    assert llm_scored_criteria([llm_only, rule_only]) == [llm_only]


def test_build_system_prompt_lists_each_criterion():
    criteria = [_criterion("empathy", "Empathy", "Acknowledges frustration.")]
    prompt = build_system_prompt(criteria)
    assert "empathy (Empathy): Acknowledges frustration." in prompt


def test_build_user_prompt_includes_transcript_text():
    prompt = build_user_prompt("Agent: hi")
    assert "Agent: hi" in prompt
