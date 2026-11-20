import type { ApiErrorBody } from "./types";

export const API_BASE_URL = (
  import.meta.env?.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export class DatasetApiError extends Error {
  readonly status?: number;
  readonly code?: string;

  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = "DatasetApiError";
    this.status = status;
    this.code = code;
  }
}

async function parseError(response: Response): Promise<DatasetApiError> {
  let body: ApiErrorBody = {};
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    // A non-JSON proxy/server response still becomes a useful client error.
  }
  const validation = Array.isArray(body.detail)
    ? body.detail[0]?.msg
    : body.detail;
  return new DatasetApiError(
    body.error?.message ||
      validation ||
      `The dataset request failed (${response.status}).`,
    response.status,
    body.error?.code,
  );
}

export async function request<T>(
  path: string,
  init?: RequestInit,
  format: "json" | "blob" = "json",
): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(init?.headers);
    if (init?.method && !["GET", "HEAD", "OPTIONS"].includes(init.method)) {
      headers.set("X-CSRF-Token", await ensureCsrf());
    }
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      credentials: "include",
      signal: init?.signal ?? AbortSignal.timeout(30_000),
    });
  } catch {
    throw new DatasetApiError(
      "The dataset service is unavailable. Start the FastAPI backend and try again.",
    );
  }
  if (response.status === 401 && !path.startsWith("/api/auth/"))
    sessionExpired();
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (
    format === "blob" ? await response.blob() : await response.json()
  ) as T;
}

let csrfToken: string | null = null;
let bootstrap: Promise<string> | null = null;
export function setCsrfToken(value: string | null) {
  csrfToken = value;
}
export function sessionExpired() {
  csrfToken = null;
  if (typeof window !== "undefined")
    window.dispatchEvent(new window.Event("smartanalytics:session-expired"));
}
export async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  if (!bootstrap) {
    bootstrap = request<{ csrf_token: string }>("/api/auth/session")
      .then((session) => {
        csrfToken = session.csrf_token;
        return session.csrf_token;
      })
      .finally(() => {
        bootstrap = null;
      });
  }
  return bootstrap;
}
