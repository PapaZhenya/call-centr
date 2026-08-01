"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { ApiError, api } from "@/lib/api-client";
import type {
  Agent,
  AgentSummary,
  AnalyticsOverview,
  ScoreByCriterion,
  TrendPoint,
} from "@/lib/types";
import { ru } from "@/messages/ru";

const MAX_SCORE = 5;
const BAR_COLOR = "#2563eb"; // the app accent; single series, so one hue and no legend

function ScoreBar({ label, value, count }: { label: string; value: number | null; count?: number }) {
  const width = value === null ? 0 : Math.min(100, (value / MAX_SCORE) * 100);
  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span>{label}</span>
        <span className="muted">
          {value === null ? "—" : value.toFixed(2)}
          {count !== undefined && ` · ${count}`}
        </span>
      </div>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: "color-mix(in srgb, currentColor 12%, transparent)",
        }}
      >
        <div
          style={{
            width: `${width}%`,
            height: "100%",
            borderRadius: 4,
            background: BAR_COLOR,
          }}
        />
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState("");
  const [summary, setSummary] = useState<AgentSummary | null>(null);
  const [criteria, setCriteria] = useState<ScoreByCriterion[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [interval, setInterval] = useState("week");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AnalyticsOverview>("/api/v1/analytics/overview")
      .then(setOverview)
      .catch((err) => setError(err instanceof ApiError ? err.message : ru.common.error));
    api
      .get<Agent[]>("/api/v1/agents")
      .then(setAgents)
      .catch(() => {
        // agent picker is a convenience; overview still renders without it
      });
  }, []);

  useEffect(() => {
    // When no agent is selected the sections below render a placeholder and
    // never read summary/criteria/trend, so stale state needs no reset here.
    if (!agentId) return;
    let cancelled = false;
    setError(null);
    Promise.all([
      api.get<AgentSummary>(`/api/v1/analytics/agents/${agentId}/summary`),
      api.get<ScoreByCriterion[]>(`/api/v1/analytics/agents/${agentId}/score-by-criterion`),
      api.get<TrendPoint[]>(`/api/v1/analytics/agents/${agentId}/trend?interval=${interval}`),
    ])
      .then(([summaryData, criteriaData, trendData]) => {
        if (cancelled) return;
        setSummary(summaryData);
        setCriteria(criteriaData);
        setTrend(trendData);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : ru.common.error);
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, interval]);

  return (
    <AppShell>
      <div className="stack">
        <h1>{ru.analytics.title}</h1>
        {error && <p className="error-text">{error}</p>}

        <div className="card stack">
          <h2>{ru.analytics.orgSection}</h2>
          {!overview ? (
            <p className="muted">{ru.common.loading}</p>
          ) : (
            <>
              <div className="grid">
                <div>
                  <p className="muted">{ru.dashboard.totalCalls}</p>
                  <h2>{overview.total_calls}</h2>
                </div>
                <div>
                  <p className="muted">{ru.dashboard.averageScore}</p>
                  <h2>{overview.average_score?.toFixed(2) ?? "—"}</h2>
                </div>
              </div>
              <h3>{ru.analytics.byCriterion}</h3>
              {overview.criteria.length === 0 ? (
                <p className="muted">{ru.analytics.noData}</p>
              ) : (
                <div className="stack">
                  {overview.criteria.map((c) => (
                    <ScoreBar key={c.key} label={c.label} value={c.average_score} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div className="card stack">
          <h2>{ru.analytics.agentSection}</h2>
          <div className="row">
            <div className="field">
              <label htmlFor="agent">{ru.analytics.selectAgent}</label>
              <select id="agent" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                <option value="">—</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="interval">{ru.analytics.interval}</label>
              <select
                id="interval"
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
              >
                <option value="day">{ru.analytics.intervalDay}</option>
                <option value="week">{ru.analytics.intervalWeek}</option>
                <option value="month">{ru.analytics.intervalMonth}</option>
              </select>
            </div>
          </div>

          {!agentId ? (
            <p className="muted">{ru.analytics.noAgentSelected}</p>
          ) : !summary ? (
            <p className="muted">{ru.common.loading}</p>
          ) : (
            <div className="stack">
              <div className="grid">
                <div>
                  <p className="muted">{ru.analytics.callCount}</p>
                  <h2>{summary.call_count}</h2>
                </div>
                <div>
                  <p className="muted">{ru.analytics.averageScore}</p>
                  <h2>{summary.average_score?.toFixed(2) ?? "—"}</h2>
                </div>
              </div>

              <h3>{ru.analytics.byCriterion}</h3>
              {criteria.length === 0 ? (
                <p className="muted">{ru.analytics.noData}</p>
              ) : (
                <div className="stack">
                  {criteria.map((c) => (
                    <ScoreBar
                      key={c.rubric_criterion_id}
                      label={c.label}
                      value={c.average_score}
                      count={c.count}
                    />
                  ))}
                </div>
              )}

              <h3>{ru.analytics.trend}</h3>
              {trend.length === 0 ? (
                <p className="muted">{ru.analytics.noData}</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>{ru.analytics.period}</th>
                      <th>{ru.analytics.averageScore}</th>
                      <th>{ru.analytics.calls}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trend.map((point) => (
                      <tr key={point.period}>
                        <td>{new Date(point.period).toLocaleDateString("ru-RU")}</td>
                        <td style={{ minWidth: 180 }}>
                          <ScoreBar label="" value={point.average_score} />
                        </td>
                        <td>{point.call_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
