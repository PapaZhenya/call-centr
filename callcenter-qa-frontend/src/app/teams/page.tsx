"use client";

import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/app-shell";
import { ApiError, api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { TEAMS_MANAGE, hasPermission } from "@/lib/permissions";
import type { Team } from "@/lib/types";
import { ru } from "@/messages/ru";

async function reloadTeams(setTeams: (teams: Team[]) => void, setError: (m: string | null) => void) {
  try {
    const data = await api.get<Team[]>("/api/v1/teams");
    setTeams(data);
  } catch (err) {
    setError(err instanceof ApiError ? err.message : ru.common.error);
  }
}

export default function TeamsPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, TEAMS_MANAGE);

  const [teams, setTeams] = useState<Team[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.get<Team[]>("/api/v1/teams");
        if (!cancelled) setTeams(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : ru.common.error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setIsSaving(true);
    setError(null);
    try {
      await api.post("/api/v1/teams", { name: name.trim() });
      setName("");
      await reloadTeams(setTeams, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    } finally {
      setIsSaving(false);
    }
  }

  function startEditing(team: Team) {
    setEditingId(team.id);
    setEditingName(team.name);
  }

  async function handleRename(teamId: string) {
    if (!editingName.trim()) return;
    setError(null);
    try {
      await api.patch(`/api/v1/teams/${teamId}`, { name: editingName.trim() });
      setEditingId(null);
      await reloadTeams(setTeams, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  return (
    <AppShell>
      <div className="stack">
        <h1>{ru.teams.title}</h1>
        {error && <p className="error-text">{error}</p>}
        {!canManage && <p className="muted">{ru.teams.accessDenied}</p>}

        <div className="card stack">
          <table>
            <thead>
              <tr>
                <th>{ru.teams.name}</th>
                {canManage && <th />}
              </tr>
            </thead>
            <tbody>
              {teams === null ? (
                <tr>
                  <td className="muted">{ru.common.loading}</td>
                </tr>
              ) : teams.length === 0 ? (
                <tr>
                  <td className="muted">{ru.teams.noTeams}</td>
                </tr>
              ) : (
                teams.map((team) => (
                  <tr key={team.id}>
                    <td>
                      {editingId === team.id ? (
                        <input
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                        />
                      ) : (
                        team.name
                      )}
                    </td>
                    {canManage && (
                      <td>
                        {editingId === team.id ? (
                          <button type="button" onClick={() => void handleRename(team.id)}>
                            {ru.teams.save}
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="secondary"
                            onClick={() => startEditing(team)}
                          >
                            {ru.teams.rename}
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {canManage && (
            <form className="row" onSubmit={handleCreate}>
              <div className="field">
                <label htmlFor="teamName">{ru.teams.newTeam}</label>
                <input id="teamName" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div>
                <button type="submit" disabled={isSaving}>
                  {ru.teams.create}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </AppShell>
  );
}
