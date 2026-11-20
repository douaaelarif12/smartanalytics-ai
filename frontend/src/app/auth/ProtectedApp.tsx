import { lazy } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./authContext";
const Layout = lazy(() => import("../components/AppLayout"));
export default function ProtectedApp() {
  const auth = useAuth();
  const location = useLocation();
  if (auth.status === "loading")
    return (
      <div role="status" className="sa-session-feedback">
        Restoring your secure session…
      </div>
    );
  if (auth.status === "error")
    return (
      <div role="alert" className="sa-session-feedback">
        <p>{auth.error}</p>
        <button type="button" className="button" onClick={auth.retry}>
          Retry
        </button>
      </div>
    );
  if (!auth.user)
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  return <Layout key={auth.user.id} />;
}
