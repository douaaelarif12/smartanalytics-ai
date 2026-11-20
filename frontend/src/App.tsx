import { Suspense } from "react";
import { BrowserRouter, useRoutes } from "react-router-dom";
import AuthProvider from "./app/auth/AuthProvider";
import "./app/auth/auth.css";
import { routes } from "./routes";

export function AppRoutes() {
  const content = useRoutes(routes);
  return (
    <Suspense
      fallback={
        <div
          role="status"
          style={{
            padding: "60px 24px",
            textAlign: "center",
            color: "#71786f",
          }}
        >
          Loading SmartAnalytics…
        </div>
      }
    >
      {content}
    </Suspense>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
