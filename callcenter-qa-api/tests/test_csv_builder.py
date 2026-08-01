from datetime import datetime, timezone

from app.reports.csv_builder import ReportRow, build_calls_csv


def _row(**overrides) -> ReportRow:
    defaults = dict(
        call_date=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        agent="Ivan Petrov",
        team="Team A",
        direction="inbound",
        queue=None,
        status="completed",
        overall_score=4.2,
        flags=[],
        notes="ok",
        criterion_scores={"politeness": ("Politeness & Tone", 5.0)},
    )
    defaults.update(overrides)
    return ReportRow(**defaults)


def test_csv_has_fixed_headers_plus_dynamic_criterion_columns():
    csv_text = build_calls_csv(
        [
            _row(criterion_scores={"politeness": ("Politeness & Tone", 5.0)}),
            _row(criterion_scores={"empathy": ("Empathy", 3.0)}),
        ]
    )
    header = csv_text.splitlines()[0]
    # Union of criteria across rows, ordered by key: empathy < politeness.
    assert header.endswith("notes,Empathy,Politeness & Tone")


def test_csv_row_values_and_gaps():
    csv_text = build_calls_csv(
        [
            _row(criterion_scores={"politeness": ("Politeness & Tone", 5.0)}),
            _row(
                agent="Petr Sidorov",
                team=None,
                overall_score=None,
                notes=None,
                flags=["insufficient_transcript"],
                criterion_scores={"empathy": ("Empathy", 3.0)},
            ),
        ]
    )
    lines = csv_text.splitlines()
    assert lines[1].endswith(",5.0")  # politeness column last, empathy empty
    assert ",insufficient_transcript," in lines[2]
    assert lines[2].endswith("3.0,")  # empathy filled, politeness empty
    assert ",," in lines[2]  # empty team and overall_score


def test_csv_empty_report_is_just_headers():
    csv_text = build_calls_csv([])
    lines = csv_text.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("call_date,agent,team")


def test_csv_escapes_commas_and_quotes_in_text():
    csv_text = build_calls_csv([_row(notes='Said "hi", then hung up')])
    assert '"Said ""hi"", then hung up"' in csv_text
