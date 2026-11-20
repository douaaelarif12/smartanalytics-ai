import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
  LineChart as LineIcon,
  PieChart as PieIcon,
  Play,
  Plus,
  RotateCcw,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { Link } from "react-router-dom";
import { datasetsApi } from "../api/datasetsApi";
import type {
  AggregateFunction,
  AnalyticsFilter,
  AnalyticsQuerySpec,
  AnalyticsResult,
  FilterOperator,
} from "../api/types";
import { useWorkspace } from "../workspace";
import { EmptyState, LoadingState } from "../components/States";
import {
  addExplorerFilter,
  enableAggregation,
  initialExplorerQuery,
  normalizeExplorerQuery,
  safeAlias,
  uploadedDatasetKey,
} from "../explorerState";

const ExplorerChart = lazy(() => import("../components/ExplorerChart"));
const FILTER_OPERATORS: { value: FilterOperator; label: string }[] = [
  { value: "eq", label: "equals" },
  { value: "neq", label: "does not equal" },
  { value: "gt", label: "greater than" },
  { value: "gte", label: "at least" },
  { value: "lt", label: "less than" },
  { value: "lte", label: "at most" },
  { value: "contains", label: "contains" },
  { value: "starts_with", label: "starts with" },
  { value: "is_null", label: "is empty" },
  { value: "not_null", label: "is not empty" },
  { value: "in", label: "is one of" },
];
const valueOf = (value: unknown) => (value == null ? "" : String(value));
const errorMessage = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "The analytical query could not be completed.";

export function ExplorerFeedback({
  loading,
  error,
  result,
  onRetry,
}: {
  loading: boolean;
  error: string;
  result: AnalyticsResult | null;
  onRetry: () => void;
}) {
  if (loading) return <LoadingState label="Running the validated query…" />;
  if (error)
    return (
      <div className="sa-inline-status is-error" role="alert">
        <span>{error}</span>
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      </div>
    );
  if (result && !result.rows.length)
    return (
      <div className="sa-result-empty">
        <Filter size={25} />
        <strong>No rows match this query.</strong>
        <p>
          Adjust the filters or reset the query. No analytical values were
          generated.
        </p>
      </div>
    );
  return null;
}

export default function DataExplorer() {
  const { uploadedDataset } = useWorkspace();
  return <DatasetExplorer key={uploadedDataset?.id ?? "none"} />;
}

function DatasetExplorer() {
  const { uploadedDataset, uploadedDatasets, selectDataset } = useWorkspace();
  const [draft, setDraft] = useState<AnalyticsQuerySpec | null>(() =>
    uploadedDataset ? initialExplorerQuery(uploadedDataset) : null,
  );
  const [applied, setApplied] = useState<AnalyticsQuerySpec | null>(() =>
    uploadedDataset ? initialExplorerQuery(uploadedDataset) : null,
  );
  const [result, setResult] = useState<AnalyticsResult | null>(null);
  const [loading, setLoading] = useState(!!uploadedDataset);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const exportController = useRef<AbortController | null>(null);
  useEffect(() => () => exportController.current?.abort(), []);
  const [chartType, setChartType] = useState<"bar" | "line" | "pie">("bar");

  const datasetId = uploadedDataset?.id;
  useEffect(() => {
    if (!datasetId || !applied) return;
    let active = true;
    datasetsApi
      .query(datasetId, applied)
      .then((next) => {
        if (active) setResult(next);
      })
      .catch((reason) => {
        if (active) {
          setResult(null);
          setError(errorMessage(reason));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [datasetId, applied]);

  const numericColumns = useMemo(
    () =>
      uploadedDataset?.columns.filter(
        (column) => column.type === "integer" || column.type === "number",
      ) ?? [],
    [uploadedDataset],
  );
  if (!uploadedDataset || !draft) {
    return (
      <section className="sa-explorer-empty">
        <EmptyState
          title="Choose an uploaded dataset to explore."
          action={
            <Link className="sa-btn" to="/app/datasets">
              Upload a dataset
            </Link>
          }
        >
          The bundled sales demo remains available on Overview, but the real
          Data Explorer only queries files processed by your local backend.
        </EmptyState>
        {uploadedDatasets.length > 0 && (
          <div className="sa-explorer-dataset-list">
            <span>Or select an uploaded dataset:</span>
            {uploadedDatasets.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => selectDataset(uploadedDatasetKey(item.id))}
              >
                {item.name}
              </button>
            ))}
          </div>
        )}
      </section>
    );
  }
  const activeDataset = uploadedDataset;

  function updateFilter(index: number, patch: Partial<AnalyticsFilter>) {
    setDraft(
      (current) =>
        current && {
          ...current,
          offset: 0,
          filters: current.filters.map((item, itemIndex) =>
            itemIndex === index ? { ...item, ...patch } : item,
          ),
        },
    );
  }
  function applyQuery(query: AnalyticsQuerySpec) {
    setResult(null);
    setLoading(true);
    setError("");
    setApplied(query);
  }
  function run(offset = 0) {
    applyQuery(normalizeExplorerQuery({ ...draft!, offset }, activeDataset));
  }
  function toggleColumn(column: string) {
    setDraft((current) => {
      if (!current) return current;
      const selected = current.columns.includes(column)
        ? current.columns.filter((item) => item !== column)
        : [...current.columns, column];
      return { ...current, columns: selected, offset: 0 };
    });
  }
  function setAggregation(enabled: boolean) {
    setDraft(
      (current) =>
        current &&
        (enabled
          ? {
              ...current,
              ...enableAggregation(activeDataset),
              sorts: [],
              offset: 0,
            }
          : {
              ...initialExplorerQuery(activeDataset),
              filters: current.filters,
            }),
    );
  }
  async function exportCsv() {
    if (!result || !applied || exporting) return;
    const controller = new AbortController();
    exportController.current = controller;
    setExporting(true);
    setExportError("");
    try {
      const blob = await datasetsApi.export(
        activeDataset.id,
        applied,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${activeDataset.name}-analysis.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      if (!controller.signal.aborted) setExportError(errorMessage(reason));
    } finally {
      if (!controller.signal.aborted) setExporting(false);
    }
  }

  const aggregateMode = draft.aggregations.length > 0;
  return (
    <>
      <section className="sa-explorer-heading">
        <div>
          <span className="sa-overline">REAL DATA · VALIDATED QUERIES</span>
          <h1>Explore without writing SQL.</h1>
          <p>
            Shape, filter and summarize the rows from your uploaded dataset.
            Every operation is validated against its detected schema.
          </p>
        </div>
        <label>
          <span>Dataset</span>
          <select
            value={uploadedDataset.id}
            onChange={(event) =>
              selectDataset(uploadedDatasetKey(event.target.value))
            }
          >
            {uploadedDatasets.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </section>
      <div className="sa-explorer-layout">
        <aside className="sa-card sa-query-builder">
          <div className="sa-card-heading">
            <div>
              <span className="sa-overline">QUERY BUILDER</span>
              <h2>Configure analysis</h2>
            </div>
            <SlidersHorizontal size={19} />
          </div>
          <fieldset className="sa-builder-section">
            <legend>Mode</legend>
            <div className="sa-segmented">
              <button
                type="button"
                className={!aggregateMode ? "is-active" : ""}
                onClick={() => setAggregation(false)}
              >
                Rows
              </button>
              <button
                type="button"
                className={aggregateMode ? "is-active" : ""}
                onClick={() => setAggregation(true)}
              >
                Aggregate
              </button>
            </div>
          </fieldset>
          {!aggregateMode && (
            <fieldset className="sa-builder-section">
              <legend>Columns</legend>
              <div className="sa-column-picker">
                {uploadedDataset.columns.map((column) => (
                  <label key={column.name}>
                    <input
                      type="checkbox"
                      checked={draft.columns.includes(column.name)}
                      onChange={() => toggleColumn(column.name)}
                    />
                    <span>
                      {column.name}
                      <small>{column.type}</small>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          {aggregateMode && (
            <fieldset className="sa-builder-section">
              <legend>Group by</legend>
              <select
                aria-label="Group by column"
                value={
                  draft.date_group
                    ? `date:${draft.date_group.column}`
                    : (draft.group_by[0] ?? "")
                }
                onChange={(event) => {
                  const value = event.target.value;
                  const date = value.startsWith("date:");
                  setDraft({
                    ...draft,
                    group_by: date || !value ? [] : [value],
                    date_group: date
                      ? {
                          column: value.slice(5),
                          granularity: "month",
                          alias: "period",
                        }
                      : undefined,
                    sorts: [],
                  });
                }}
              >
                <option value="">No dimension</option>
                {uploadedDataset.columns
                  .filter((column) => column.type !== "datetime")
                  .map((column) => (
                    <option key={column.name} value={column.name}>
                      {column.name}
                    </option>
                  ))}
                {uploadedDataset.columns
                  .filter((column) => column.type === "datetime")
                  .map((column) => (
                    <option key={column.name} value={`date:${column.name}`}>
                      {column.name} (date)
                    </option>
                  ))}
              </select>
              {draft.date_group && (
                <select
                  aria-label="Date grouping granularity"
                  value={draft.date_group.granularity}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      date_group: {
                        ...draft.date_group!,
                        granularity: event.target.value as
                          "day" | "month" | "year",
                      },
                    })
                  }
                >
                  <option value="day">Day</option>
                  <option value="month">Month</option>
                  <option value="year">Year</option>
                </select>
              )}
            </fieldset>
          )}
          {aggregateMode && (
            <fieldset className="sa-builder-section">
              <legend>Aggregations</legend>
              <div className="sa-aggregation-list">
                {draft.aggregations.map((aggregation, index) => (
                  <div
                    className="sa-aggregation-row"
                    key={`${aggregation.alias}-${index}`}
                  >
                    <select
                      aria-label={`Aggregation ${index + 1} function`}
                      value={aggregation.function}
                      onChange={(event) => {
                        const fn = event.target.value as AggregateFunction;
                        const column =
                          fn === "count"
                            ? undefined
                            : (aggregation.column ?? numericColumns[0]?.name);
                        setDraft({
                          ...draft,
                          aggregations: draft.aggregations.map(
                            (item, itemIndex) =>
                              itemIndex === index
                                ? {
                                    function: fn,
                                    column,
                                    alias:
                                      fn === "count"
                                        ? "row_count"
                                        : `${fn}_${safeAlias(column ?? "value")}`,
                                  }
                                : item,
                          ),
                        });
                      }}
                    >
                      {["count", "sum", "avg", "min", "max"].map((fn) => (
                        <option key={fn} value={fn}>
                          {fn.toUpperCase()}
                        </option>
                      ))}
                    </select>
                    {aggregation.function !== "count" && (
                      <select
                        aria-label={`Aggregation ${index + 1} column`}
                        value={aggregation.column}
                        onChange={(event) =>
                          setDraft({
                            ...draft,
                            aggregations: draft.aggregations.map(
                              (item, itemIndex) =>
                                itemIndex === index
                                  ? {
                                      ...item,
                                      column: event.target.value,
                                      alias: `${item.function}_${safeAlias(event.target.value)}`,
                                    }
                                  : item,
                            ),
                          })
                        }
                      >
                        {numericColumns.map((column) => (
                          <option key={column.name}>{column.name}</option>
                        ))}
                      </select>
                    )}
                    <input
                      aria-label={`Aggregation ${index + 1} alias`}
                      value={aggregation.alias}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          aggregations: draft.aggregations.map(
                            (item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, alias: event.target.value }
                                : item,
                          ),
                        })
                      }
                    />
                    <button
                      type="button"
                      aria-label={`Remove aggregation ${index + 1}`}
                      disabled={draft.aggregations.length === 1}
                      onClick={() =>
                        setDraft({
                          ...draft,
                          aggregations: draft.aggregations.filter(
                            (_, itemIndex) => itemIndex !== index,
                          ),
                        })
                      }
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>
              <button
                className="sa-builder-add"
                type="button"
                disabled={draft.aggregations.length >= 5}
                onClick={() =>
                  setDraft({
                    ...draft,
                    aggregations: [
                      ...draft.aggregations,
                      {
                        function: "count",
                        alias: `row_count_${draft.aggregations.length + 1}`,
                      },
                    ],
                  })
                }
              >
                <Plus size={14} /> Add aggregation
              </button>
            </fieldset>
          )}
          <fieldset className="sa-builder-section">
            <legend>Filters</legend>
            <div className="sa-filter-list">
              {draft.filters.map((filter, index) => (
                <div className="sa-filter-row" key={index}>
                  <select
                    aria-label={`Filter ${index + 1} column`}
                    value={filter.column}
                    onChange={(event) =>
                      updateFilter(index, { column: event.target.value })
                    }
                  >
                    {uploadedDataset.columns.map((column) => (
                      <option key={column.name}>{column.name}</option>
                    ))}
                  </select>
                  <select
                    aria-label={`Filter ${index + 1} operator`}
                    value={filter.operator}
                    onChange={(event) =>
                      updateFilter(index, {
                        operator: event.target.value as FilterOperator,
                      })
                    }
                  >
                    {FILTER_OPERATORS.map((operator) => (
                      <option key={operator.value} value={operator.value}>
                        {operator.label}
                      </option>
                    ))}
                  </select>
                  {!(["is_null", "not_null"] as string[]).includes(
                    filter.operator,
                  ) && (
                    <input
                      aria-label={`Filter ${index + 1} value`}
                      value={valueOf(filter.value)}
                      placeholder={
                        filter.operator === "in" ? "A, B, C" : "Value"
                      }
                      onChange={(event) =>
                        updateFilter(index, { value: event.target.value })
                      }
                    />
                  )}
                  <button
                    type="button"
                    aria-label={`Remove filter ${index + 1}`}
                    onClick={() =>
                      setDraft({
                        ...draft,
                        filters: draft.filters.filter(
                          (_, itemIndex) => itemIndex !== index,
                        ),
                      })
                    }
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
            <button
              className="sa-builder-add"
              type="button"
              onClick={() =>
                setDraft({
                  ...draft,
                  filters: addExplorerFilter(draft.filters, uploadedDataset),
                })
              }
            >
              <Plus size={14} /> Add filter
            </button>
          </fieldset>
          <div className="sa-builder-actions">
            <button
              className="sa-btn"
              type="button"
              disabled={loading || (!aggregateMode && !draft.columns.length)}
              onClick={() => run()}
            >
              <Play size={15} /> Run analysis
            </button>
            <button
              className="sa-icon-button"
              type="button"
              aria-label="Reset query"
              onClick={() => {
                const query = initialExplorerQuery(uploadedDataset);
                setDraft(query);
                applyQuery(query);
              }}
            >
              <RotateCcw size={16} />
            </button>
          </div>
        </aside>
        <section className="sa-explorer-results">
          <div className="sa-card sa-result-card">
            <div className="sa-card-heading">
              <div>
                <span className="sa-overline">LIVE RESULT</span>
                <h2>{uploadedDataset.name}</h2>
              </div>
              <button
                className="sa-btn sa-btn-secondary"
                type="button"
                disabled={
                  exporting || loading || !!error || !result?.rows.length
                }
                onClick={() => void exportCsv()}
              >
                <Download size={15} /> {exporting ? "Exporting…" : "Export CSV"}
              </button>
            </div>
            {exportError && (
              <p role="alert" className="sa-inline-status is-error">
                {exportError}
              </p>
            )}
            {loading || error || (result && !result.rows.length) ? (
              <ExplorerFeedback
                loading={loading}
                error={error}
                result={result}
                onRetry={() =>
                  applyQuery(
                    normalizeExplorerQuery({ ...draft }, activeDataset),
                  )
                }
              />
            ) : result ? (
              <>
                <div className="sa-result-meta">
                  <span>
                    {result.total_rows.toLocaleString()} result
                    {result.total_rows === 1 ? "" : "s"}
                  </span>
                  <span>
                    {result.grouped ? "Aggregated result" : "Row-level result"}
                  </span>
                </div>
                <div className="sa-table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {result.columns.map((column) => (
                          <th key={column}>
                            <button
                              type="button"
                              onClick={() => {
                                const current = draft.sorts.find(
                                  (item) => item.column === column,
                                );
                                const direction =
                                  current?.direction === "asc" ? "desc" : "asc";
                                const next = {
                                  ...draft,
                                  sorts: [
                                    { column, direction },
                                  ] as AnalyticsQuerySpec["sorts"],
                                  offset: 0,
                                };
                                setDraft(next);
                                applyQuery(
                                  normalizeExplorerQuery(next, activeDataset),
                                );
                              }}
                            >
                              {column}
                              {draft.sorts[0]?.column === column
                                ? draft.sorts[0].direction === "asc"
                                  ? " ↑"
                                  : " ↓"
                                : ""}
                            </button>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, index) => (
                        <tr key={result.offset + index}>
                          {result.columns.map((column) => (
                            <td key={column}>
                              {row[column] == null ? (
                                <span className="sa-null">null</span>
                              ) : (
                                valueOf(row[column])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="sa-table-pagination">
                  <span>
                    {result.total_rows
                      ? `${result.offset + 1}–${Math.min(result.offset + result.rows.length, result.total_rows)} of ${result.total_rows.toLocaleString()}`
                      : "0 rows"}
                  </span>
                  <div>
                    <button
                      type="button"
                      aria-label="Previous result page"
                      disabled={result.offset === 0}
                      onClick={() =>
                        run(Math.max(0, result.offset - result.limit))
                      }
                    >
                      <ChevronLeft size={17} />
                    </button>
                    <button
                      type="button"
                      aria-label="Next result page"
                      disabled={
                        result.offset + result.rows.length >= result.total_rows
                      }
                      onClick={() => run(result.offset + result.limit)}
                    >
                      <ChevronRight size={17} />
                    </button>
                  </div>
                </div>
              </>
            ) : null}
          </div>
          {!loading && !error && result?.chart && result.rows.length > 0 && (
            <div className="sa-card sa-explorer-chart">
              <div className="sa-card-heading">
                <div>
                  <span className="sa-overline">CHART-READY RESULT</span>
                  <h2>Visual analysis</h2>
                </div>
                <div className="sa-chart-switch" aria-label="Chart type">
                  <button
                    className={chartType === "bar" ? "is-active" : ""}
                    onClick={() => setChartType("bar")}
                    aria-label="Bar chart"
                  >
                    <BarChart3 size={16} />
                  </button>
                  <button
                    className={chartType === "line" ? "is-active" : ""}
                    onClick={() => setChartType("line")}
                    aria-label="Line chart"
                  >
                    <LineIcon size={16} />
                  </button>
                  <button
                    className={chartType === "pie" ? "is-active" : ""}
                    onClick={() => setChartType("pie")}
                    aria-label="Pie chart"
                  >
                    <PieIcon size={16} />
                  </button>
                </div>
              </div>
              <Suspense fallback={<LoadingState label="Preparing chart…" />}>
                <ExplorerChart chart={result.chart} type={chartType} />
              </Suspense>
              <p className="sa-chart-note">
                The chart uses the same rows returned by the current analytical
                query.
              </p>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
