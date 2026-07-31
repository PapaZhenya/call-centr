// Mirrors app/auth/permissions.py. This is a UI convenience for
// hiding/showing controls only - the backend is the real enforcement
// boundary and re-checks every request.
import type { CurrentUser, UserRole } from "@/lib/types";

export const RUBRIC_WRITE = "rubric:write";
export const RUBRIC_READ = "rubric:read";
export const TEAMS_MANAGE = "teams:manage";
export const USERS_MANAGE = "users:manage";
export const CALLS_UPLOAD = "calls:upload";
export const CALLS_RETRY = "calls:retry";
export const CALLS_VIEW_ALL = "calls:view:all";
export const CALLS_VIEW_TEAM = "calls:view:team";
export const CALLS_VIEW_OWN = "calls:view:own";
export const ANALYTICS_VIEW_ALL = "analytics:view:all";
export const ANALYTICS_VIEW_TEAM = "analytics:view:team";

export type Permission =
  | typeof RUBRIC_WRITE
  | typeof RUBRIC_READ
  | typeof TEAMS_MANAGE
  | typeof USERS_MANAGE
  | typeof CALLS_UPLOAD
  | typeof CALLS_RETRY
  | typeof CALLS_VIEW_ALL
  | typeof CALLS_VIEW_TEAM
  | typeof CALLS_VIEW_OWN
  | typeof ANALYTICS_VIEW_ALL
  | typeof ANALYTICS_VIEW_TEAM;

const BASE_READ: Permission[] = [RUBRIC_READ];

export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  super_admin: [
    RUBRIC_WRITE,
    RUBRIC_READ,
    TEAMS_MANAGE,
    USERS_MANAGE,
    CALLS_UPLOAD,
    CALLS_RETRY,
    CALLS_VIEW_ALL,
    ANALYTICS_VIEW_ALL,
  ],
  admin: [
    RUBRIC_WRITE,
    RUBRIC_READ,
    TEAMS_MANAGE,
    USERS_MANAGE,
    CALLS_UPLOAD,
    CALLS_RETRY,
    CALLS_VIEW_ALL,
    ANALYTICS_VIEW_ALL,
  ],
  qa_manager: [RUBRIC_WRITE, RUBRIC_READ, CALLS_UPLOAD, CALLS_RETRY, CALLS_VIEW_ALL, ANALYTICS_VIEW_ALL],
  team_lead: [...BASE_READ, CALLS_UPLOAD, CALLS_RETRY, CALLS_VIEW_TEAM, ANALYTICS_VIEW_TEAM],
  reviewer: [...BASE_READ, CALLS_VIEW_ALL],
  agent: [CALLS_VIEW_OWN],
  viewer: [...BASE_READ, CALLS_VIEW_ALL, ANALYTICS_VIEW_ALL],
};

export function hasPermission(user: CurrentUser | null, permission: Permission): boolean {
  if (!user) return false;
  return ROLE_PERMISSIONS[user.role]?.includes(permission) ?? false;
}
