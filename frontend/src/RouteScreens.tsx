import { lazy, useEffect } from "react";
import { Link } from "react-router-dom";
import Landing from "./Landing";

export const AppLayout = lazy(() => import("./app/components/AppLayout"));
export const Overview = lazy(() => import("./app/pages/Overview"));
export const Datasets = lazy(() => import("./app/pages/Datasets"));
export const DataExplorer = lazy(() => import("./app/pages/DataExplorer"));
export const Assistant = lazy(() => import("./app/pages/Assistant"));
export const PlannedPage = lazy(() => import("./app/pages/PlannedPage"));

export function LandingRoute() {
  useEffect(() => {
    document.title = "SmartAnalytics AI — A little more clarity";
  }, []);
  return <Landing />;
}
export function NotFound() {
  return (
    <main style={{ padding: "80px 24px", maxWidth: 700, margin: "auto" }}>
      <h1>Page not found</h1>
      <p>This address does not exist.</p>
      <Link className="button" to="/">
        Back to the website
      </Link>
    </main>
  );
}
