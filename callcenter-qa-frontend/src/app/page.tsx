"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { ApiError, api } from "@/lib/api-client";
import type { AnalyticsOverview } from "@/lib/types";
import { ru } from "@/messages/ru";

export default function DashboardPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AnalyticsOverview>("/api/v1/analytics/overview")
      .then(setOverview)
      .catch((err) => setError(err instanceof ApiError ? err.message : ru.common.error));
  }, []);

  return (
    <AppShell>
      <div className="stack">
        <h1>{ru.dashboard.title}</h1>
        {error && <p className="error-text">{error}</p>}
        {!overview ? (
          <p className="muted">{ru.common.loading}</p>
        ) : (
          <div className="grid">
            <div className="card">
              <p className="muted">{ru.dashboard.totalCalls}</p>
              <h2>{overview.total_calls}</h2>
            </div>
            <div className="card">
              <p className="muted">{ru.dashboard.averageScore}</p>
              <h2>{overview.average_score ?? "—"}</h2>
            </div>
            <div className="card">
              <p className="muted">{ru.dashboard.bestCriterion}</p>
              <h2>{overview.best_criterion?.label ?? "—"}</h2>
            </div>
            <div className="card">
              <p className="muted">{ru.dashboard.worstCriterion}</p>
              <h2>{overview.worst_criterion?.label ?? "—"}</h2>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
