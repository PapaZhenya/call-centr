import type { TokenResponse } from "@/lib/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const ACCESS_TOKEN_KEY = "callcenter_access_token";
const REFRESH_TOKEN_KEY = "callcenter_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;

  const data = (await response.json()) as TokenResponse;
  setTokens(data.access_token, data.refresh_token);
  return true;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  isFormData?: boolean;
  skipAuth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, isFormData = false, skipAuth = false } = options;

  const doFetch = (): Promise<Response> => {
    const headers: Record<string, string> = {};
    if (!isFormData && body !== undefined) headers["Content-Type"] = "application/json";
    if (!skipAuth) {
      const token = getAccessToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body:
        body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
    });
  };

  let response = await doFetch();

  if (response.status === 401 && !skipAuth) {
    if (!refreshPromise) {
      refreshPromise = tryRefresh().finally(() => {
        refreshPromise = null;
      });
    }
    const refreshed = await refreshPromise;
    if (refreshed) {
      response = await doFetch();
    } else {
      clearTokens();
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new ApiError(401, "Not authenticated");
    }
  }

  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      if (data?.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // response body wasn't JSON - keep statusText
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, options?: Partial<RequestOptions>) =>
    request<T>(path, { method: "POST", body, ...options }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
};
