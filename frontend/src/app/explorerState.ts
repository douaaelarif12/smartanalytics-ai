import type { AnalyticsAggregation, AnalyticsFilter, AnalyticsQuerySpec, UploadedDataset } from "./api/types";

export const uploadedDatasetKey = (datasetId: string) => `upload:${datasetId}`;

export function initialExplorerQuery(dataset: UploadedDataset): AnalyticsQuerySpec {
  return { columns: dataset.columns.slice(0, 30).map((column) => column.name), filters: [], sorts: [], group_by: [], aggregations: [], offset: 0, limit: 25 };
}

export function addExplorerFilter(filters: AnalyticsFilter[], dataset: UploadedDataset): AnalyticsFilter[] {
  const column = dataset.columns[0];
  if (!column || filters.length >= 10) return filters;
  return [...filters, { column: column.name, operator: column.type === "text" ? "contains" : "eq", value: "" }];
}

export function enableAggregation(dataset: UploadedDataset): Pick<AnalyticsQuerySpec, "columns" | "group_by" | "date_group" | "aggregations"> {
  const dimension = dataset.columns.find((column) => column.type === "text" || column.type === "boolean");
  const date = dataset.columns.find((column) => column.type === "datetime");
  const numeric = dataset.columns.find((column) => column.type === "integer" || column.type === "number");
  const aggregation: AnalyticsAggregation = numeric
    ? { function: "sum", column: numeric.name, alias: `sum_${safeAlias(numeric.name)}` }
    : { function: "count", alias: "row_count" };
  return {
    columns: [],
    group_by: dimension ? [dimension.name] : [],
    date_group: !dimension && date ? { column: date.name, granularity: "month", alias: "period" } : undefined,
    aggregations: [aggregation],
  };
}

export function safeAlias(value: string): string {
  const normalized = value.replace(/[^A-Za-z0-9_]/g, "_").replace(/^[^A-Za-z]+/, "");
  return (normalized || "value").slice(0, 48);
}

export function normalizeExplorerQuery(query: AnalyticsQuerySpec, dataset: UploadedDataset): AnalyticsQuerySpec {
  const kinds = new Map(dataset.columns.map((column) => [column.name, column.type]));
  return {
    ...query,
    filters: query.filters.map((filter) => {
      if (filter.operator === "in") {
        const values = String(filter.value ?? "").split(",").map((value) => value.trim()).filter(Boolean);
        return { ...filter, value: values.map((value) => numericValue(value, kinds.get(filter.column))) };
      }
      if (filter.operator === "is_null" || filter.operator === "not_null") return { column: filter.column, operator: filter.operator };
      return { ...filter, value: numericValue(filter.value, kinds.get(filter.column)) };
    }),
  };
}

function numericValue(value: unknown, kind: string | undefined): unknown {
  if ((kind === "integer" || kind === "number") && value !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : value;
  }
  if (kind === "boolean" && typeof value === "string") return value.toLowerCase() === "true" ? true : value.toLowerCase() === "false" ? false : value;
  return value;
}
