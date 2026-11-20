import { lazy, Suspense } from "react";
import type {
  ApiColumnMetadata,
  DatasetProfileResponse,
} from "../api/types";

const ProfileVisualizations = lazy(() => import("./ProfileVisualizations"));

const number = (value: number | null, maximumFractionDigits = 2) =>
  value === null
    ? "—"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits }).format(value);

export function ProfileSummary({ profile }: { profile: DatasetProfileResponse }) {
  const completeness = profile.quality.completeness_percentage;

  return (
    <div className="sa-quality-grid" aria-label="Dataset quality summary">
      <div><small>ROWS</small><strong>{profile.row_count.toLocaleString()}</strong></div>
      <div><small>COLUMNS</small><strong>{profile.column_count.toLocaleString()}</strong></div>
      <div><small>COMPLETENESS</small><strong>{completeness === null ? "—" : `${completeness.toFixed(1)}%`}</strong></div>
      <div><small>MISSING CELLS</small><strong>{profile.quality.missing_cell_count.toLocaleString()}</strong></div>
      <div><small>DUPLICATE ROWS</small><strong>{profile.quality.duplicate_row_count.toLocaleString()}</strong></div>
    </div>
  );
}

export function ColumnTypeSummary({ columns }: { columns: readonly ApiColumnMetadata[] }) {
  const counts = columns.reduce<Record<string, number>>((result, column) => {
    result[column.type] = (result[column.type] ?? 0) + 1;
    return result;
  }, {});

  return (
    <div className="sa-type-summary" aria-label="Detected column type distribution">
      {Object.entries(counts).map(([type, count]) => (
        <span key={type}><strong>{count}</strong> {type}</span>
      ))}
    </div>
  );
}

export default function DatasetProfileInsights({ profile }: { profile: DatasetProfileResponse }) {
  const hasStatistics = profile.numeric.length > 0 || profile.categorical.length > 0;

  if (!hasStatistics) {
    return (
      <div className="sa-profile-empty" role="status">
        This dataset has no populated numeric or categorical columns to summarize.
      </div>
    );
  }

  return (
    <div className="sa-profile-insights">
      {profile.numeric.length > 0 && (
        <section className="sa-profile-section" aria-labelledby="numeric-profile-title">
          <div className="sa-profile-heading">
            <div><span className="sa-overline">NUMERIC PROFILE</span><h3 id="numeric-profile-title">Distribution at a glance</h3></div>
            <span className="sa-badge">{profile.numeric.length} COLUMNS</span>
          </div>
          <div className="sa-table-scroll">
            <table className="sa-profile-table">
              <thead><tr><th>Column</th><th>Count</th><th>Missing</th><th>Min</th><th>Mean</th><th>Median</th><th>Max</th><th>Std. dev.</th></tr></thead>
              <tbody>
                {profile.numeric.map((statistic) => (
                  <tr key={statistic.column}>
                    <th scope="row">{statistic.column}</th>
                    <td>{statistic.count.toLocaleString()}</td>
                    <td>{statistic.missing_count.toLocaleString()}</td>
                    <td>{number(statistic.min)}</td>
                    <td>{number(statistic.mean)}</td>
                    <td>{number(statistic.median)}</td>
                    <td>{number(statistic.max)}</td>
                    <td>{number(statistic.std)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {profile.categorical.length > 0 && (
        <section className="sa-profile-section" aria-labelledby="categorical-profile-title">
          <div className="sa-profile-heading">
            <div><span className="sa-overline">CATEGORICAL PROFILE</span><h3 id="categorical-profile-title">Most frequent values</h3></div>
            <span className="sa-badge">{profile.categorical.length} COLUMNS</span>
          </div>
          <div className="sa-category-profile-grid">
            {profile.categorical.map((statistic) => {
              const maximum = statistic.top_values[0]?.count ?? 0;
              return (
                <article className="sa-category-profile" key={statistic.column}>
                  <div><strong>{statistic.column}</strong><small>{statistic.unique_count.toLocaleString()} unique · {statistic.missing_count.toLocaleString()} missing</small></div>
                  {statistic.top_values.length > 0 ? (
                    <ol>
                      {statistic.top_values.map((item) => (
                        <li key={`${statistic.column}:${item.value}`}>
                          <div><span title={item.value}>{item.value || "(empty)"}</span><strong>{item.count.toLocaleString()}</strong></div>
                          <span className="sa-profile-bar" aria-hidden="true"><i style={{ width: `${maximum ? (item.count / maximum) * 100 : 0}%` }} /></span>
                        </li>
                      ))}
                    </ol>
                  ) : <p>No frequent values available.</p>}
                </article>
              );
            })}
          </div>
        </section>
      )}

      <Suspense fallback={<div className="sa-profile-empty" role="status">Preparing advanced visualizations…</div>}>
        <ProfileVisualizations profile={profile} />
      </Suspense>
    </div>
  );
}
