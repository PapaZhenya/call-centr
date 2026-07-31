from app.auth.permissions import (
    ANALYTICS_VIEW_ALL,
    ANALYTICS_VIEW_TEAM,
    CALLS_RETRY,
    CALLS_UPLOAD,
    CALLS_VIEW_ALL,
    CALLS_VIEW_OWN,
    CALLS_VIEW_TEAM,
    ROLE_PERMISSIONS,
    RUBRIC_READ,
    RUBRIC_WRITE,
    TEAMS_MANAGE,
    USERS_MANAGE,
    has_permission,
)
from app.models.user import (
    ROLE_ADMIN,
    ROLE_AGENT,
    ROLE_QA_MANAGER,
    ROLE_REVIEWER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_LEAD,
    ROLE_VIEWER,
)


def test_every_role_has_a_permission_set_defined():
    for role in (
        ROLE_SUPER_ADMIN,
        ROLE_ADMIN,
        ROLE_QA_MANAGER,
        ROLE_TEAM_LEAD,
        ROLE_REVIEWER,
        ROLE_AGENT,
        ROLE_VIEWER,
    ):
        assert role in ROLE_PERMISSIONS


def test_super_admin_and_admin_can_manage_users_and_teams():
    for role in (ROLE_SUPER_ADMIN, ROLE_ADMIN):
        assert has_permission(role, USERS_MANAGE)
        assert has_permission(role, TEAMS_MANAGE)
        assert has_permission(role, CALLS_VIEW_ALL)
        assert has_permission(role, ANALYTICS_VIEW_ALL)


def test_qa_manager_can_write_rubric_and_view_all_but_not_manage_users_or_teams():
    assert has_permission(ROLE_QA_MANAGER, RUBRIC_WRITE)
    assert has_permission(ROLE_QA_MANAGER, CALLS_VIEW_ALL)
    assert has_permission(ROLE_QA_MANAGER, ANALYTICS_VIEW_ALL)
    assert not has_permission(ROLE_QA_MANAGER, USERS_MANAGE)
    assert not has_permission(ROLE_QA_MANAGER, TEAMS_MANAGE)


def test_team_lead_is_scoped_to_team_not_all():
    assert has_permission(ROLE_TEAM_LEAD, CALLS_VIEW_TEAM)
    assert has_permission(ROLE_TEAM_LEAD, ANALYTICS_VIEW_TEAM)
    assert has_permission(ROLE_TEAM_LEAD, CALLS_UPLOAD)
    assert has_permission(ROLE_TEAM_LEAD, CALLS_RETRY)
    assert not has_permission(ROLE_TEAM_LEAD, CALLS_VIEW_ALL)
    assert not has_permission(ROLE_TEAM_LEAD, ANALYTICS_VIEW_ALL)
    assert not has_permission(ROLE_TEAM_LEAD, RUBRIC_WRITE)


def test_reviewer_is_read_only_across_all_calls():
    assert has_permission(ROLE_REVIEWER, CALLS_VIEW_ALL)
    assert has_permission(ROLE_REVIEWER, RUBRIC_READ)
    assert not has_permission(ROLE_REVIEWER, RUBRIC_WRITE)
    assert not has_permission(ROLE_REVIEWER, CALLS_UPLOAD)
    assert not has_permission(ROLE_REVIEWER, CALLS_RETRY)
    assert not has_permission(ROLE_REVIEWER, ANALYTICS_VIEW_ALL)


def test_agent_can_only_view_own_calls():
    assert ROLE_PERMISSIONS[ROLE_AGENT] == frozenset({CALLS_VIEW_OWN})
    assert not has_permission(ROLE_AGENT, CALLS_VIEW_TEAM)
    assert not has_permission(ROLE_AGENT, CALLS_VIEW_ALL)
    assert not has_permission(ROLE_AGENT, ANALYTICS_VIEW_ALL)
    assert not has_permission(ROLE_AGENT, ANALYTICS_VIEW_TEAM)


def test_viewer_is_read_only_org_wide_with_no_writes():
    assert has_permission(ROLE_VIEWER, CALLS_VIEW_ALL)
    assert has_permission(ROLE_VIEWER, ANALYTICS_VIEW_ALL)
    assert not has_permission(ROLE_VIEWER, RUBRIC_WRITE)
    assert not has_permission(ROLE_VIEWER, CALLS_UPLOAD)
    assert not has_permission(ROLE_VIEWER, CALLS_RETRY)
    assert not has_permission(ROLE_VIEWER, USERS_MANAGE)
    assert not has_permission(ROLE_VIEWER, TEAMS_MANAGE)


def test_has_permission_returns_false_for_unknown_role():
    assert has_permission("not-a-real-role", CALLS_VIEW_ALL) is False
