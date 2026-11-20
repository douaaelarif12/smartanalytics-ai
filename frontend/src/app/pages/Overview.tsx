import { lazy, Suspense, useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CircleDollarSign,
  ShoppingBag,
  TrendingUp,
  Upload,
  Wallet,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useWorkspace } from "../workspace";
import KpiCard from "../components/KpiCard";
import DatasetSummary from "../components/DatasetSummary";
import InsightsPreview from "../components/InsightsPreview";
import UploadedDatasetOverview from "../components/UploadedDatasetOverview";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { demoAnalyticsService } from "../services/demoAnalyticsService";
import { displayDate, integer, money, percent } from "../format";
import type { AnalyticsSnapshot, PeriodMonths } from "../types";

const AnalyticsCharts = lazy(() => import("../components/AnalyticsCharts"));
export default function Overview() {
  const { dataset, uploadedDataset, openUpload, selectDataset } = useWorkspace();
  const [months, setMonths] = useState<PeriodMonths>(6);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    data?: AnalyticsSnapshot;
    error?: string;
  } | null>(null);
  const requestKey = `${dataset?.id ?? "uploaded"}:${months}:${attempt}`;
  useEffect(() => {
    if (!dataset) return;
    let active = true;
    demoAnalyticsService
      .getOverview(dataset.id, months)
      .then((data) => {
        if (active) setResult({ key: requestKey, data });
      })
      .catch(() => {
        if (active)
          setResult({
            key: requestKey,
            error: "Please try again or select another demo dataset.",
          });
      });
    return () => {
      active = false;
    };
  }, [dataset, months, requestKey]);
  const analytics = result?.key === requestKey ? result.data : undefined;
  if (uploadedDataset) {
    return <UploadedDatasetOverview dataset={uploadedDataset} />;
  }
  if (!dataset) return <LoadingState />;
  return (
    <>
      <section className="sa-welcome">
        <div>
          <span className="sa-overline">YOUR WORKSPACE, IN PERSPECTIVE</span>
          <h1>
            A clearer view. <br className="sa-mobile-break" />{" "}
            <em>A smarter next step.</em>
          </h1>
          <p>
            Welcome to your overview. Find the story behind your sample sales
            data.
          </p>
        </div>
        <div className="sa-welcome-actions">
          <button className="sa-btn" onClick={openUpload}>
            <Upload size={16} /> Upload Dataset
          </button>
          <Link className="sa-btn sa-btn-secondary" to="/app/explorer">
            Explore Data <ArrowRight size={16} />
          </Link>
        </div>
      </section>
      <div className="sa-section-toolbar">
        <div>
          <h2>
            Business overview <span className="sa-badge">DEMO ANALYTICS</span>
          </h2>
          <p>
            {analytics
              ? `${displayDate(analytics.startDate)} – ${displayDate(analytics.endDate)}`
              : "Preparing the selected period…"}
            <span> · {dataset.name}</span>
          </p>
        </div>
        <label className="sa-period-control">
          <CalendarDays size={16} />
          <span className="sr-only">Analytics time period</span>
          <select
            value={months}
            onChange={(event) =>
              setMonths(Number(event.target.value) as PeriodMonths)
            }
          >
            <option value={1}>Last month</option>
            <option value={3}>Last 3 months</option>
            <option value={6}>Last 6 months</option>
          </select>
        </label>
      </div>
      <p className="sa-period-note">
        Sample timeline ends {displayDate(dataset.referenceDate)}. Comparisons
        use the preceding{" "}
        {months === 1 ? "calendar month" : `${months} calendar months`}.
      </p>
      {result?.key === requestKey && result.error ? (
        <ErrorState
          message={result.error}
          onRetry={() => setAttempt((value) => value + 1)}
        />
      ) : !analytics ? (
        <LoadingState />
      ) : !analytics.orders ? (
        <>
          <EmptyState
            title="A fresh canvas for your data."
            action={
              <button
                className="sa-btn"
                onClick={() => selectDataset("northstar-sales")}
              >
                Choose a sample dataset <ArrowUpRight size={16} />
              </button>
            }
          >
            There are no orders in this dataset for the selected period. Choose
            Northstar Sales in the header to explore the demo.
          </EmptyState>
          <DatasetSummary dataset={dataset} />
        </>
      ) : (
        <>
          <div
            className="sa-kpi-grid"
            aria-label="Demo sales key performance indicators"
          >
            <KpiCard
              label="Total Revenue"
              value={money(analytics.revenue)}
              icon={CircleDollarSign}
              change={analytics.comparison.revenue}
            />
            <KpiCard
              label="Total Orders"
              value={integer(analytics.orders)}
              icon={ShoppingBag}
              change={analytics.comparison.orders}
            />
            <KpiCard
              label="Average Order Value"
              value={money(analytics.averageOrderValue)}
              icon={Wallet}
              change={analytics.comparison.averageOrderValue}
            />
            <KpiCard
              label="Growth Rate"
              value={percent(analytics.growth)}
              icon={TrendingUp}
              note={
                analytics.growth === null
                  ? "No previous revenue baseline"
                  : "Revenue vs. previous period"
              }
            />
          </div>
          <div className="sa-analytics-grid">
            <Suspense
              fallback={
                <div className="sa-charts-loading">
                  <LoadingState label="Preparing sample visualizations…" />
                </div>
              }
            >
              <AnalyticsCharts analytics={analytics} />
            </Suspense>
            <DatasetSummary dataset={dataset} />
          </div>
          <InsightsPreview analytics={analytics} />
        </>
      )}
    </>
  );
}
