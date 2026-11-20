import { useState } from "react";
import { LogOut } from "lucide-react";
import { useAuth } from "./authContext";
export default function AccountMenu() {
  const { user, logout } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function signOut() {
    setPending(true);
    setError("");
    try {
      await logout();
    } catch {
      setError("Sign out failed. Please retry.");
      setPending(false);
    }
  }
  return (
    <details className="sa-account-menu">
      <summary aria-label="User account">
        <span>{user?.email.slice(0, 2).toUpperCase()}</span>
        <strong>{user?.email}</strong>
      </summary>
      <div>
        <small>PERSONAL ACCOUNT</small>
        <p>{user?.email}</p>
        <button type="button" disabled={pending} onClick={() => void signOut()}>
          <LogOut size={15} />
          {pending ? "Signing out…" : "Sign out"}
        </button>
        {error && <p role="alert">{error}</p>}
      </div>
    </details>
  );
}
