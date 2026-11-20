import { createContext, useContext } from "react";
import type { Session, User } from "./authApi";
export interface AuthState {
  status: "loading" | "ready" | "error";
  user: User | null;
  error: string;
  accept: (session: Session) => void;
  retry: () => void;
  logout: () => Promise<void>;
}
export const AuthContext = createContext<AuthState | null>(null);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("Authentication provider is required.");
  return value;
}
