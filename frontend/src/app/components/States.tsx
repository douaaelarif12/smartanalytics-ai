import { Database, LoaderCircle, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({
  label = "Preparing your view…",
  description = "This should only take a moment.",
}: {
  label?: string;
  description?: string;
}) {
  return (
    <div className="sa-state sa-state-loading" role="status" aria-live="polite">
      <LoaderCircle size={27} className="sa-loader" />
      <h2>{label}</h2>
      <p>{description}</p>
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="sa-state sa-state-empty">
      <span className="sa-state-icon">
        <Database size={26} />
      </span>
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="sa-state sa-state-error" role="alert">
      <span className="sa-state-icon">
        <TriangleAlert size={26} />
      </span>
      <h2>We couldn’t load this view.</h2>
      <p>{message}</p>
      <button className="sa-btn" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
