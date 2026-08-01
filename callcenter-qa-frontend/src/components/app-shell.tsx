"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  ANALYTICS_VIEW_ALL,
  ANALYTICS_VIEW_TEAM,
  TEAMS_MANAGE,
  USERS_MANAGE,
  hasPermission,
} from "@/lib/permissions";
import { ru } from "@/messages/ru";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return <div className="center-page">{ru.common.loading}</div>;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <nav className="app-nav">
          <strong>{ru.appName}</strong>
          <Link href="/">{ru.nav.dashboard}</Link>
          <Link href="/calls">{ru.nav.calls}</Link>
          <Link href="/rubric">{ru.nav.rubric}</Link>
          {(hasPermission(user, ANALYTICS_VIEW_ALL) || hasPermission(user, ANALYTICS_VIEW_TEAM)) && (
            <Link href="/analytics">{ru.nav.analytics}</Link>
          )}
          {hasPermission(user, USERS_MANAGE) && <Link href="/users">{ru.nav.users}</Link>}
          {hasPermission(user, TEAMS_MANAGE) && <Link href="/teams">{ru.nav.teams}</Link>}
        </nav>
        <div className="row">
          <span className="muted">
            {user.email} ({ru.roles[user.role] ?? user.role})
          </span>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              void logout().then(() => router.replace("/login"));
            }}
          >
            {ru.nav.logout}
          </button>
        </div>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}
