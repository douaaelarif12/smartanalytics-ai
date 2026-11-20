import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { authApi } from "./authApi";
import type { Session, User } from "./authApi";
import { AuthContext } from "./authContext";
import { DatasetApiError, setCsrfToken } from "../api/http";

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{
    status: "loading" | "ready" | "error";
    user: User | null;
    error: string;
  }>({ status: "loading", user: null, error: "" });
  const [attempt, setAttempt] = useState(0);
  const channel = useRef<BroadcastChannel | null>(null);
  useEffect(() => {
    if (typeof window.BroadcastChannel !== "function") return;
    const connection = new window.BroadcastChannel("smartanalytics-session");
    channel.current = connection;
    connection.onmessage = () => {
      setCsrfToken(null);
      setState({ status: "loading", user: null, error: "" });
      setAttempt((value) => value + 1);
    };
    return () => {
      channel.current = null;
      connection.close();
    };
  }, []);
  useEffect(() => {
    let active = true;
    authApi
      .session()
      .then((session) => {
        if (active)
          setState({ status: "ready", user: session.user, error: "" });
      })
      .catch(() => {
        if (active)
          setState({
            status: "error",
            user: null,
            error:
              "Your session could not be restored. Check the local API and retry.",
          });
      });
    return () => {
      active = false;
    };
  }, [attempt]);
  useEffect(() => {
    const expired = () => {
      setCsrfToken(null);
      setState({
        status: "ready",
        user: null,
        error: "Your session expired. Please sign in again.",
      });
    };
    window.addEventListener("smartanalytics:session-expired", expired);
    return () =>
      window.removeEventListener("smartanalytics:session-expired", expired);
  }, []);
  function accept(session: Session) {
    setCsrfToken(session.csrf_token);
    setState({ status: "ready", user: session.user, error: "" });
    channel.current?.postMessage("session-changed");
  }
  async function logout() {
    try {
      await authApi.logout();
    } catch (error) {
      if (!(error instanceof DatasetApiError) || error.status !== 401)
        throw error;
    }
    setCsrfToken(null);
    setState({ status: "ready", user: null, error: "" });
    channel.current?.postMessage("session-changed");
  }
  return (
    <AuthContext.Provider
      value={{
        ...state,
        accept,
        logout,
        retry: () => {
          setState({ status: "loading", user: null, error: "" });
          setAttempt((value) => value + 1);
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
