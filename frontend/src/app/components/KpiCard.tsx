import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { percent } from "../format";

export default function KpiCard({
  label,
  value,
  icon: Icon,
  change,
  note,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  change?: number | null;
  note?: string;
}) {
  const Direction =
    change === null || change === undefined || change === 0
      ? Minus
      : change > 0
        ? ArrowUpRight
        : ArrowDownRight;
  return (
    <article className="sa-card sa-kpi">
      <div className="sa-kpi-label">
        <span>{label}</span>
        <span className="sa-kpi-icon">
          <Icon size={18} />
        </span>
      </div>
      <strong className="sa-kpi-value">{value}</strong>
      <div className="sa-kpi-comparison">
        {change !== undefined && (
          <span
            className={`sa-change${change !== null && change < 0 ? " sa-negative" : ""}`}
          >
            <Direction size={13} />
            {change === null ? "No baseline" : percent(change)}
          </span>
        )}
        <span>{note ?? "vs. previous period"}</span>
      </div>
    </article>
  );
}
