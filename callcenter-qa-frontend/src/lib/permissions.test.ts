import { describe, expect, it } from "vitest";
import {
  ANALYTICS_VIEW_ALL,
  ANALYTICS_VIEW_TEAM,
  CALLS_RETRY,
  CALLS_UPLOAD,
  CALLS_VIEW_ALL,
  CALLS_VIEW_OWN,
  CALLS_VIEW_TEAM,
  RUBRIC_WRITE,
  TEAMS_MANAGE,
  USERS_MANAGE,
  hasPermission,
} from "./permissions";
import type { CurrentUser, UserRole } from "./types";

function user(role: UserRole): CurrentUser {
  return { id: "u1", email: "u@example.com", role, is_active: true, team_id: null, agent_id: null };
}

describe("hasPermission", () => {
  it("returns false for a null user", () => {
    expect(hasPermission(null, CALLS_VIEW_ALL)).toBe(false);
  });

  it("grants admin and super_admin full access, including user/team management", () => {
    for (const role of ["admin", "super_admin"] as UserRole[]) {
      expect(hasPermission(user(role), USERS_MANAGE)).toBe(true);
      expect(hasPermission(user(role), TEAMS_MANAGE)).toBe(true);
      expect(hasPermission(user(role), CALLS_VIEW_ALL)).toBe(true);
      expect(hasPermission(user(role), ANALYTICS_VIEW_ALL)).toBe(true);
    }
  });

  it("scopes team_lead to team-level calls and analytics only", () => {
    const teamLead = user("team_lead");
    expect(hasPermission(teamLead, CALLS_VIEW_TEAM)).toBe(true);
    expect(hasPermission(teamLead, ANALYTICS_VIEW_TEAM)).toBe(true);
    expect(hasPermission(teamLead, CALLS_UPLOAD)).toBe(true);
    expect(hasPermission(teamLead, CALLS_RETRY)).toBe(true);
    expect(hasPermission(teamLead, CALLS_VIEW_ALL)).toBe(false);
    expect(hasPermission(teamLead, RUBRIC_WRITE)).toBe(false);
  });

  it("limits agent role to viewing only their own calls", () => {
    const agent = user("agent");
    expect(hasPermission(agent, CALLS_VIEW_OWN)).toBe(true);
    expect(hasPermission(agent, CALLS_VIEW_TEAM)).toBe(false);
    expect(hasPermission(agent, CALLS_VIEW_ALL)).toBe(false);
    expect(hasPermission(agent, ANALYTICS_VIEW_ALL)).toBe(false);
  });

  it("keeps viewer read-only org-wide with no write permissions", () => {
    const viewer = user("viewer");
    expect(hasPermission(viewer, CALLS_VIEW_ALL)).toBe(true);
    expect(hasPermission(viewer, ANALYTICS_VIEW_ALL)).toBe(true);
    expect(hasPermission(viewer, RUBRIC_WRITE)).toBe(false);
    expect(hasPermission(viewer, CALLS_UPLOAD)).toBe(false);
    expect(hasPermission(viewer, USERS_MANAGE)).toBe(false);
  });
});
