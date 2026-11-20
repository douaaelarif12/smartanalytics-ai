import { useEffect, useState } from "react";
import { ArrowRight, Columns3, CopyCheck, Rows3, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { datasetsApi } from "../api/datasetsApi";
import type { DatasetProfileResponse, UploadedDataset } from "../api/types";
import DatasetProfileInsights, { ColumnTypeSummary } from "./DatasetProfileInsights";
import KpiCard from "./KpiCard";
import { ErrorState, LoadingState } from "./States";

const messageOf = (error: unknown) =>
  error instanceof Error ? error.message : "The dataset profile could not be loaded.";

export default function UploadedDatasetOverview({ dataset }: { dataset: UploadedDataset }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{
    key: string;
    profile?: DatasetProfileResponse;
    error?: string;
  } | null>(null);
  const requestKey = `${dataset.id}:${attempt}`;

  useEffect(() => {
    let active = true;
    datasetsApi.profile(dataset.id)
      .then((profile) => { if (active) setState({ key: requestKey, profile }); })
      .catch((error) => { if (active) setState({ key: requestKey, error: messageOf(error) }); });
    return () => { active = false; };
  }, [dataset.id, requestKey]);

  const current = state?.key === requestKey ? state : null;

  return (
    <>
      <section className="sa-uploaded-overview sa-card">
        <div>
          <span className="sa-badge">PRIVATE DATASET</span>
          <h1>{dataset.name}</h1>
          <p>
            A factual overview generated from the stored dataset profile. Metrics describe structure and quality only—business KPIs require explicit field mapping.
          </p>
          <ColumnTypeSummary columns={dataset.columns} />
        </div>
        <div className="sa-welcome-actions">
          <Link className="sa-btn" to="/app/explorer">Explore data <ArrowRight size={16} /></Link>
          <Link className="sa-btn sa-btn-secondary" to={`/app/datasets?dataset=${dataset.id}`}>Preview rows</Link>
        </div>
      </section>

      {current?.error ? (
        <ErrorState message={current.error} onRetry={() => setAttempt((value) => value + 1)} />
      ) : !current?.profile ? (
        <LoadingState label="Loading the dataset profile…" description="Calculating a trustworthy structural overview." />
      ) : (
        <>
          <div className="sa-kpi-grid" aria-label="Uploaded dataset key metrics">
            <KpiCard label="Rows" value={current.profile.row_count.toLocaleString()} icon={Rows3} note="Stored records" />
            <KpiCard label="Columns" value={current.profile.column_count.toLocaleString()} icon={Columns3} note="Detected fields" />
            <KpiCard label="Completeness" value={current.profile.quality.completeness_percentage === null ? "—" : `${current.profile.quality.completeness_percentage.toFixed(1)}%`} icon={ShieldCheck} note="Populated cells" />
            <KpiCard label="Duplicate rows" value={current.profile.quality.duplicate_row_count.toLocaleString()} icon={CopyCheck} note="Exact row matches" />
          </div>
          <DatasetProfileInsights profile={current.profile} />
        </>
      )}
    </>
  );
}
