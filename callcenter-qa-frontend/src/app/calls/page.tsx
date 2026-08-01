"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/app-shell";
import { API_BASE_URL, ApiError, api, getAccessToken } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { statusBadgeClass } from "@/lib/format";
import { CALLS_RETRY, CALLS_UPLOAD, hasPermission } from "@/lib/permissions";
import type { Agent, Call } from "@/lib/types";
import { ru } from "@/messages/ru";

async function reloadCalls(
  setCalls: (calls: Call[]) => void,
  setError: (message: string | null) => void,
) {
  try {
    const data = await api.get<Call[]>("/api/v1/calls");
    setCalls(data);
  } catch (err) {
    setError(err instanceof ApiError ? err.message : ru.common.error);
  }
}

export default function CallsPage() {
  const { user } = useAuth();
  const canUpload = hasPermission(user, CALLS_UPLOAD);
  const canRetry = hasPermission(user, CALLS_RETRY);
  const [calls, setCalls] = useState<Call[] | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [agentId, setAgentId] = useState("");
  const [callDate, setCallDate] = useState("");
  const [direction, setDirection] = useState("");
  const [queue, setQueue] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.get<Call[]>("/api/v1/calls");
        if (!cancelled) setCalls(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : ru.common.error);
      }
      try {
        const agentsData = await api.get<Agent[]>("/api/v1/agents");
        if (!cancelled) setAgents(agentsData);
      } catch {
        // agent list is a convenience for the upload form - not critical
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!file || !agentId || !callDate) return;
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("agent_id", agentId);
      formData.append("call_date", new Date(callDate).toISOString());
      if (direction) formData.append("direction", direction);
      if (queue) formData.append("queue", queue);

      await api.post("/api/v1/calls", formData, { isFormData: true });
      setFile(null);
      setCallDate("");
      setDirection("");
      setQueue("");
      await reloadCalls(setCalls, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleExport() {
    setError(null);
    try {
      const token = getAccessToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/calls.csv`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new ApiError(response.status, ru.common.error);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `calls-report-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  async function handleRetry(callId: string) {
    try {
      await api.post(`/api/v1/calls/${callId}/retry`);
      await reloadCalls(setCalls, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  const agentLabel = (id: string) => agents.find((a) => a.id === id)?.display_name ?? id;

  return (
    <AppShell>
      <div className="stack">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h1 style={{ margin: 0 }}>{ru.calls.title}</h1>
          <button type="button" className="secondary" onClick={() => void handleExport()}>
            {ru.calls.exportCsv}
          </button>
        </div>

        {canUpload && (
        <form className="card stack" onSubmit={handleUpload}>
          <h2>{ru.calls.upload}</h2>
          <div className="grid">
            <div className="field">
              <label htmlFor="file">{ru.calls.uploadFile}</label>
              <input
                id="file"
                type="file"
                accept="audio/wav,audio/mpeg,audio/mp4,audio/x-m4a,audio/ogg,audio/flac"
                required
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <div className="field">
              <label htmlFor="agent">{ru.calls.uploadAgent}</label>
              <select
                id="agent"
                required
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
              >
                <option value="" disabled>
                  —
                </option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="callDate">{ru.calls.uploadDate}</label>
              <input
                id="callDate"
                type="datetime-local"
                required
                value={callDate}
                onChange={(e) => setCallDate(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="direction">{ru.calls.uploadDirection}</label>
              <select
                id="direction"
                value={direction}
                onChange={(e) => setDirection(e.target.value)}
              >
                <option value="">—</option>
                <option value="inbound">Входящий</option>
                <option value="outbound">Исходящий</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="queue">{ru.calls.uploadQueue}</label>
              <input
                id="queue"
                type="text"
                value={queue}
                onChange={(e) => setQueue(e.target.value)}
              />
            </div>
          </div>
          <div>
            <button type="submit" disabled={isUploading}>
              {isUploading ? ru.calls.uploading : ru.calls.uploadSubmit}
            </button>
          </div>
        </form>
        )}

        {error && <p className="error-text">{error}</p>}

        <div className="card">
          {calls === null ? (
            <p className="muted">{ru.common.loading}</p>
          ) : calls.length === 0 ? (
            <p className="muted">{ru.calls.noCalls}</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>{ru.calls.date}</th>
                  <th>{ru.calls.agent}</th>
                  <th>{ru.calls.status}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {calls.map((call) => (
                  <tr key={call.id}>
                    <td>
                      <Link href={`/calls/${call.id}`}>
                        {new Date(call.call_date).toLocaleString("ru-RU")}
                      </Link>
                    </td>
                    <td>{agentLabel(call.agent_id)}</td>
                    <td>
                      <span className={statusBadgeClass(call.status)}>
                        {ru.calls.statusValues[call.status] ?? call.status}
                      </span>
                    </td>
                    <td>
                      {canRetry && call.status.endsWith("_failed") && (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => void handleRetry(call.id)}
                        >
                          {ru.calls.retry}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppShell>
  );
}
