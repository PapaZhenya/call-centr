"""Permission model: single source of truth for what each role may do.

Access checks throughout the app go through `has_permission(user, X)` / the
`require_permission(X)` FastAPI dependency (see app/api/deps.py) - never a
bare `if user.role == "admin"`. Adding a permission or changing what a role
can do means editing ROLE_PERMISSIONS here, not hunting through endpoints.
"""

from app.models.user import (
    ROLE_ADMIN,
    ROLE_AGENT,
    ROLE_QA_MANAGER,
    ROLE_REVIEWER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_LEAD,
    ROLE_VIEWER,
)

# --- Permissions -------------------------------------------------------
RUBRIC_WRITE = "rubric:write"
RUBRIC_READ = "rubric:read"
TEAMS_MANAGE = "teams:manage"
USERS_MANAGE = "users:manage"
CALLS_UPLOAD = "calls:upload"
CALLS_RETRY = "calls:retry"
CALLS_VIEW_ALL = "calls:view:all"
CALLS_VIEW_TEAM = "calls:view:team"
CALLS_VIEW_OWN = "calls:view:own"
ANALYTICS_VIEW_ALL = "analytics:view:all"
ANALYTICS_VIEW_TEAM = "analytics:view:team"

_BASE_READ = frozenset({RUBRIC_READ})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_SUPER_ADMIN: frozenset(
        {
            RUBRIC_WRITE,
            RUBRIC_READ,
            TEAMS_MANAGE,
            USERS_MANAGE,
            CALLS_UPLOAD,
            CALLS_RETRY,
            CALLS_VIEW_ALL,
            ANALYTICS_VIEW_ALL,
        }
    ),
    ROLE_ADMIN: frozenset(
        {
            RUBRIC_WRITE,
            RUBRIC_READ,
            TEAMS_MANAGE,
            USERS_MANAGE,
            CALLS_UPLOAD,
            CALLS_RETRY,
            CALLS_VIEW_ALL,
            ANALYTICS_VIEW_ALL,
        }
    ),
    ROLE_QA_MANAGER: frozenset(
        {RUBRIC_WRITE, RUBRIC_READ, CALLS_UPLOAD, CALLS_RETRY, CALLS_VIEW_ALL, ANALYTICS_VIEW_ALL}
    ),
    ROLE_TEAM_LEAD: frozenset(
        _BASE_READ | {CALLS_UPLOAD, CALLS_RETRY, CALLS_VIEW_TEAM, ANALYTICS_VIEW_TEAM}
    ),
    ROLE_REVIEWER: frozenset(_BASE_READ | {CALLS_VIEW_ALL}),
    ROLE_AGENT: frozenset({CALLS_VIEW_OWN}),
    ROLE_VIEWER: frozenset(_BASE_READ | {CALLS_VIEW_ALL, ANALYTICS_VIEW_ALL}),
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
