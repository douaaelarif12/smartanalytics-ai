import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { BarChart3, ArrowRight, LockKeyhole } from "lucide-react";
import { authApi } from "./authApi";
import { useAuth } from "./authContext";
import "./auth.css";

function AuthForm({ register }: { register: boolean }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const from =
    typeof location.state?.from === "string" &&
    (location.state.from === "/app" || location.state.from.startsWith("/app/"))
      ? location.state.from
      : "/app";
  if (auth.status === "ready" && auth.user)
    return <Navigate to={from} replace />;
  async function submit() {
    if (pending) return;
    setPending(true);
    setError("");
    try {
      const session = await (register
        ? authApi.register(email, password)
        : authApi.login(email, password));
      auth.accept(session);
      setPassword("");
      navigate(from, { replace: true });
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Authentication failed. Please retry.",
      );
    } finally {
      setPending(false);
    }
  }
  return (
    <main className="sa-auth-page">
      <Link to="/" className="sa-auth-brand">
        <BarChart3 size={27} />
        SmartAnalytics <span>AI</span>
      </Link>
      <section className="sa-auth-card">
        <span className="sa-auth-overline">A PERSONAL SPACE FOR YOUR DATA</span>
        <h1>{register ? "Make room for clarity." : "Welcome back."}</h1>
        <p>
          {register
            ? "Create an account to explore your own datasets and ask better questions."
            : "Sign in to your datasets, analyses and AI assistant."}
        </p>
        {(error || auth.error) && (
          <p className="sa-auth-error" role="alert">
            {error || auth.error}
          </p>
        )}
        {auth.status === "error" && (
          <button type="button" onClick={auth.retry}>
            Retry session restoration
          </button>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <label htmlFor="account-email">Email address</label>
          <input
            id="account-email"
            type="email"
            autoComplete="username"
            required
            maxLength={320}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={pending}
          />
          <label htmlFor="account-password">Password</label>
          <input
            id="account-password"
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            required
            minLength={register ? 15 : 1}
            maxLength={128}
            aria-describedby={register ? "password-guidance" : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={pending}
          />
          {register && (
            <small id="password-guidance">
              15–128 characters, including uppercase, lowercase, a number and a
              symbol.
            </small>
          )}
          <button
            className="sa-auth-submit"
            type="submit"
            disabled={pending || auth.status === "loading"}
          >
            {pending ? "Please wait…" : register ? "Create account" : "Sign in"}
            <ArrowRight size={17} />
          </button>
        </form>
        <p className="sa-auth-switch">
          {register ? "Already have an account?" : "New here?"}{" "}
          <Link to={register ? "/login" : "/register"} state={{ from }}>
            {register ? "Sign in" : "Create an account"}
          </Link>
        </p>
        <span className="sa-auth-security">
          <LockKeyhole size={14} />
          Your datasets are private to your account.
        </span>
      </section>
      <Link to="/" className="sa-auth-back">
        Back to the website
      </Link>
    </main>
  );
}
export function LoginPage() {
  return <AuthForm register={false} />;
}
export function RegisterPage() {
  return <AuthForm register />;
}
