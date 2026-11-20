import ProtectedApp from "./app/auth/ProtectedApp";
import { LoginPage, RegisterPage } from "./app/auth/AuthPage";
import type { RouteObject } from "react-router-dom";
import {
  Overview,
  Datasets,
  DataExplorer,
  Assistant,
  PlannedPage,
  LandingRoute,
  NotFound,
} from "./RouteScreens";

export const routes: RouteObject[] = [
  { path: "/", element: <LandingRoute /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    path: "/app",
    element: <ProtectedApp />,
    children: [
      { index: true, element: <Overview /> },
      { path: "datasets", element: <Datasets /> },
      { path: "explorer", element: <DataExplorer /> },
      { path: "assistant", element: <Assistant /> },
      ...["dashboards", "settings", "*"].map((path) => ({
        path,
        element: <PlannedPage />,
      })),
    ],
  },
  { path: "*", element: <NotFound /> },
];
