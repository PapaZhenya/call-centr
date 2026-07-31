"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { TokenResponse } from "@/lib/types";
import { ru } from "@/messages/ru";

export default function LoginPage() {
  const router = useRouter();
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [checkingSetup, setCheckingSetup] = useState(true);

  useEffect(() => {
    if (user) router.replace("/");
  }, [user, router]);

  useEffect(() => {
    api
      .get<{ setup_required: boolean }>("/api/v1/auth/setup-required")
      .then((res) => {
        if (res.setup_required) router.replace("/setup");
        else setCheckingSetup(false);
      })
      .catch(() => setCheckingSetup(false));
  }, [router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const tokens = await api.post<TokenResponse>(
        "/api/v1/auth/login",
        { email, password },
        { skipAuth: true },
      );
      await login(tokens.access_token, tokens.refresh_token);
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 423) setError(ru.auth.accountLocked);
        else if (err.status === 401) setError(ru.auth.invalidCredentials);
        else setError(ru.auth.genericError);
      } else {
        setError(ru.auth.genericError);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (checkingSetup) {
    return <div className="center-page">{ru.common.loading}</div>;
  }

  return (
    <div className="center-page">
      <form className="card auth-card stack" onSubmit={handleSubmit}>
        <h1>{ru.auth.loginTitle}</h1>
        <div className="field">
          <label htmlFor="email">{ru.auth.email}</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">{ru.auth.password}</label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button type="submit" disabled={isSubmitting}>
          {ru.auth.submit}
        </button>
      </form>
    </div>
  );
}
