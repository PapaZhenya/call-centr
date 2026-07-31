"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { TokenResponse } from "@/lib/types";
import { ru } from "@/messages/ru";

export default function SetupPage() {
  const router = useRouter();
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) router.replace("/");
  }, [user, router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const tokens = await api.post<TokenResponse>(
        "/api/v1/auth/setup",
        { email, password },
        { skipAuth: true },
      );
      await login(tokens.access_token, tokens.refresh_token);
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        router.replace("/login");
        return;
      }
      setError(ru.auth.genericError);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="center-page">
      <form className="card auth-card stack" onSubmit={handleSubmit}>
        <h1>{ru.auth.setupTitle}</h1>
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
          <label htmlFor="password">{ru.auth.newPassword}</label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button type="submit" disabled={isSubmitting}>
          {ru.auth.setupSubmit}
        </button>
      </form>
    </div>
  );
}
