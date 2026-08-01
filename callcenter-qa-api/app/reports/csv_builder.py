"""Pure CSV assembly for call reports - no DB access, fully unit-testable.

The router (app/reports/router.py) fetches scoped rows and hands them here.
Criterion columns are dynamic: the union of criteria present in the exported
evaluations, ordered by key, so the report follows whatever rubric versions
the data was scored against.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

FIXED_HEADERS = [
    "call_date",
    "agent",
    "team",
    "direction",
    "queue",
    "status",
    "overall_score",
    "flags",
    "notes",
]


@dataclass
class ReportRow:
    call_date: datetime
    agent: str
    team: str | None
    direction: str | None
    queue: str | None
    status: str
    overall_score: float | None
    flags: list[str] = field(default_factory=list)
    notes: str | None = None
    # {criterion_key: (label, score)}
    criterion_scores: dict[str, tuple[str, float]] = field(default_factory=dict)


def build_calls_csv(rows: list[ReportRow]) -> str:
    """Returns the report as CSV text (no BOM - the HTTP layer adds it)."""
    criterion_keys = sorted({key for row in rows for key in row.criterion_scores})
    criterion_labels = {}
    for row in rows:
        for key, (label, _) in row.criterion_scores.items():
            criterion_labels.setdefault(key, label)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(FIXED_HEADERS + [criterion_labels[key] for key in criterion_keys])

    for row in rows:
        writer.writerow(
            [
                row.call_date.isoformat(),
                row.agent,
                row.team or "",
                row.direction or "",
                row.queue or "",
                row.status,
                "" if row.overall_score is None else row.overall_score,
                "; ".join(row.flags),
                row.notes or "",
            ]
            + [
                "" if key not in row.criterion_scores else row.criterion_scores[key][1]
                for key in criterion_keys
            ]
        )
    return buffer.getvalue()
