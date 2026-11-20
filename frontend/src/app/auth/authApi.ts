import { request, setCsrfToken } from "../api/http";
export interface User {
  id: string;
  email: string;
}
export interface Session {
  user: User | null;
  csrf_token: string;
}
async function sessionRequest(
  path: string,
  credentials?: { email: string; password: string },
) {
  const session = await request<Session>(
    `/api/auth/${path}`,
    credentials
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(credentials),
        }
      : undefined,
  );
  setCsrfToken(session.csrf_token);
  return session;
}
let restoring: Promise<Session> | null = null;
export const authApi = {
  session: () => {
    if (!restoring)
      restoring = sessionRequest("session").finally(() => {
        restoring = null;
      });
    return restoring;
  },
  login: (email: string, password: string) =>
    sessionRequest("login", { email, password }),
  register: (email: string, password: string) =>
    sessionRequest("register", { email, password }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
};
