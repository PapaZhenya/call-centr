"use client";

import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/app-shell";
import { ApiError, api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { USERS_MANAGE, hasPermission } from "@/lib/permissions";
import type { Agent, ManagedUser, Team, UserRole } from "@/lib/types";
import { ru } from "@/messages/ru";

const ALL_ROLES: UserRole[] = [
  "super_admin",
  "admin",
  "qa_manager",
  "team_lead",
  "reviewer",
  "agent",
  "viewer",
];

async function reloadUsers(setUsers: (u: ManagedUser[]) => void, setError: (m: string | null) => void) {
  try {
    const data = await api.get<ManagedUser[]>("/api/v1/users");
    setUsers(data);
  } catch (err) {
    setError(err instanceof ApiError ? err.message : ru.common.error);
  }
}

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const canManage = hasPermission(currentUser, USERS_MANAGE);

  const [users, setUsers] = useState<ManagedUser[] | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("viewer");
  const [teamId, setTeamId] = useState("");
  const [agentId, setAgentId] = useState("");

  useEffect(() => {
    if (!canManage) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api.get<ManagedUser[]>("/api/v1/users");
        if (!cancelled) setUsers(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : ru.common.error);
      }
      try {
        const [teamsData, agentsData] = await Promise.all([
          api.get<Team[]>("/api/v1/teams"),
          api.get<Agent[]>("/api/v1/agents"),
        ]);
        if (!cancelled) {
          setTeams(teamsData);
          setAgents(agentsData);
        }
      } catch {
        // convenience lookups for the form - not critical if they fail
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [canManage]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password) return;
    setIsSaving(true);
    setError(null);
    try {
      await api.post("/api/v1/users", {
        email: email.trim(),
        password,
        role,
        team_id: teamId || null,
        agent_id: agentId || null,
      });
      setEmail("");
      setPassword("");
      setRole("viewer");
      setTeamId("");
      setAgentId("");
      await reloadUsers(setUsers, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRoleChange(userId: string, newRole: UserRole) {
    setError(null);
    try {
      await api.patch(`/api/v1/users/${userId}`, { role: newRole });
      await reloadUsers(setUsers, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  async function handleTeamChange(userId: string, newTeamId: string) {
    setError(null);
    try {
      await api.patch(`/api/v1/users/${userId}`, { team_id: newTeamId || null });
      await reloadUsers(setUsers, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  async function handleAgentChange(userId: string, newAgentId: string) {
    setError(null);
    try {
      await api.patch(`/api/v1/users/${userId}`, { agent_id: newAgentId || null });
      await reloadUsers(setUsers, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  async function handleToggleActive(u: ManagedUser) {
    setError(null);
    try {
      await api.patch(`/api/v1/users/${u.id}`, { is_active: !u.is_active });
      await reloadUsers(setUsers, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  if (!canManage) {
    return (
      <AppShell>
        <div className="stack">
          <h1>{ru.users.title}</h1>
          <p className="muted">{ru.users.accessDenied}</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="stack">
        <h1>{ru.users.title}</h1>
        {error && <p className="error-text">{error}</p>}

        <div className="card stack">
          <table>
            <thead>
              <tr>
                <th>{ru.users.email}</th>
                <th>{ru.users.role}</th>
                <th>{ru.users.team}</th>
                <th>{ru.users.agent}</th>
                <th>{ru.users.active}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users === null ? (
                <tr>
                  <td className="muted">{ru.common.loading}</td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td>
                      <select
                        value={u.role}
                        onChange={(e) => void handleRoleChange(u.id, e.target.value as UserRole)}
                      >
                        {ALL_ROLES.map((r) => (
                          <option key={r} value={r}>
                            {ru.roles[r] ?? r}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        value={u.team_id ?? ""}
                        onChange={(e) => void handleTeamChange(u.id, e.target.value)}
                      >
                        <option value="">{ru.users.noTeam}</option>
                        {teams.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        value={u.agent_id ?? ""}
                        onChange={(e) => void handleAgentChange(u.id, e.target.value)}
                      >
                        <option value="">{ru.users.noAgent}</option>
                        {agents.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.display_name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${u.is_active ? "success" : "muted"}`}>
                        {u.is_active ? ru.users.active : ru.users.inactive}
                      </span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => void handleToggleActive(u)}
                      >
                        {u.is_active ? ru.users.deactivate : ru.users.activate}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          <form className="stack" onSubmit={handleCreate}>
            <h3>{ru.users.newUser}</h3>
            <div className="grid">
              <div className="field">
                <label htmlFor="userEmail">{ru.users.email}</label>
                <input
                  id="userEmail"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="userPassword">{ru.users.password}</label>
                <input
                  id="userPassword"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="userRole">{ru.users.role}</label>
                <select
                  id="userRole"
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                >
                  {ALL_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {ru.roles[r] ?? r}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="userTeam">{ru.users.team}</label>
                <select id="userTeam" value={teamId} onChange={(e) => setTeamId(e.target.value)}>
                  <option value="">{ru.users.noTeam}</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="userAgent">{ru.users.agent}</label>
                <select id="userAgent" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                  <option value="">{ru.users.noAgent}</option>
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.display_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <button type="submit" disabled={isSaving}>
                {ru.users.create}
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
