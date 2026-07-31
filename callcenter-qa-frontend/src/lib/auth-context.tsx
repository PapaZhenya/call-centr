"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/api-client";
import type { CurrentUser } from "@/lib/types";

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await api.get<CurrentUser>("/api/v1/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!getAccessToken()) {
        if (!cancelled) setIsLoading(false);
        return;
      }
      try {
        const me = await api.get<CurrentUser>("/api/v1/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (accessToken: string, refreshToken: string) => {
      setTokens(accessToken, refreshToken);
      await refreshUser();
    },
    [refreshUser],
  );

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) {
        await api.post("/api/v1/auth/logout", { refresh_token: refreshToken });
      }
    } catch {
      // best effort - clear local state regardless of server response
    }
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
