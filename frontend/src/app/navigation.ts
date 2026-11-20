import {
  Database,
  LayoutDashboard,
  PanelsTopLeft,
  Settings,
  Sparkles,
  Table2,
} from "lucide-react";

export const appNavigation = [
  { path: "/app", title: "Overview", icon: LayoutDashboard, description: "" },
  {
    path: "/app/datasets",
    title: "Datasets",
    icon: Database,
    description: "Upload, profile and preview local CSV or Excel datasets.",
  },
  {
    path: "/app/explorer",
    title: "Data Explorer",
    icon: Table2,
    description: "Filter, group, aggregate and visualize uploaded datasets.",
  },
  {
    path: "/app/dashboards",
    title: "Dashboards",
    icon: PanelsTopLeft,
    description:
      "Custom dashboards and saved reports are planned. The Overview is the only analytics dashboard implemented in this phase.",
  },
  {
    path: "/app/assistant",
    title: "AI Assistant",
    icon: Sparkles,
    description:
      "Ask analytical questions about uploaded datasets with validated, computed results.",
  },
  {
    path: "/app/settings",
    title: "Settings",
    icon: Settings,
    description:
      "Workspace preferences are planned. Your authenticated account and sign-out are available in the account menu.",
  },
];
