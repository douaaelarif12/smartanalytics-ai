export type ApiColumnType = "integer" | "number" | "boolean" | "datetime" | "text";

export interface ApiColumnMetadata {
  name: string;
  type: ApiColumnType;
  pandas_dtype: string;
  missing_count: number;
  missing_percentage: number;
}

export interface UploadedDataset {
  id: string;
  name: string;
  original_filename: string;
  file_type: "csv" | "xlsx";
  file_size_bytes: number;
  row_count: number;
  column_count: number;
  missing_cell_count: number;
  created_at: string;
  columns: ApiColumnMetadata[];
  source: "upload";
}

export interface DatasetPreviewResponse {
  dataset_id: string;
  offset: number;
  limit: number;
  total_rows: number;
  columns: ApiColumnMetadata[];
  rows: Record<string, unknown>[];
}

export interface NumericStatistics {
  column: string;
  /** Non-null values, including non-finite numeric values, for compatibility. */
  count: number;
  finite_count: number;
  non_finite_count: number;
  missing_count: number;
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
  std: number | null;
  q1: number | null;
  q3: number | null;
  iqr: number | null;
  lower_fence: number | null;
  upper_fence: number | null;
  lower_whisker: number | null;
  upper_whisker: number | null;
  outlier_count: number;
  iqr_is_zero: boolean;
  warnings: ("no_finite_values" | "small_sample" | "zero_iqr")[];
  histogram: {
    bins: { lower_bound: number; upper_bound: number; count: number }[];
    source_count: number;
    sample_count: number;
    sampled: boolean;
  };
}

export interface CategoricalStatistics {
  column: string;
  count: number;
  missing_count: number;
  unique_count: number;
  top_values: { value: string; count: number; value_truncated: boolean }[];
  other_count: number;
}

export interface DatasetProfileResponse {
  profile_version: "3.0";
  dataset_id: string;
  row_count: number;
  column_count: number;
  quality: {
    completeness_percentage: number | null;
    missing_cell_count: number;
    duplicate_row_count: number;
  };
  columns: {
    column: string;
    type: ApiColumnType;
    non_null_count: number;
    missing_count: number;
    missing_percentage: number;
    unique_count: number;
    cardinality_percentage: number | null;
    constant: boolean;
  }[];
  numeric: NumericStatistics[];
  categorical: CategoricalStatistics[];
  correlation: {
    method: "pearson";
    columns: string[];
    matrix: (number | null)[][];
    finite_pair_counts: number[][];
    minimum_finite_pairs: number;
    sampled: boolean;
    source_row_count: number;
    sample_row_count: number;
    excluded_columns: { column: string; reason: "boolean" | "non_numeric" | "column_limit" }[];
    excluded_count: number;
    columns_truncated: boolean;
    exclusions_truncated: boolean;
    correlation_does_not_imply_causation: boolean;
  };
  temporal: {
    column: string;
    granularity: "day" | "month" | "year";
    bucket_size: number;
    points: { period: string; count: number }[];
    source_count: number;
    missing_count: number;
    coarsened: boolean;
    truncated: boolean;
  }[];
  methodology: {
    quartiles: "linear_interpolation";
    standard_deviation: "sample_ddof_1";
    outliers: "tukey_iqr_1_5";
    minimum_recommended_outlier_sample: number;
    histograms: "sturges_bounded_5_30";
    correlations: "pearson_pairwise_complete";
    correlation_note: string;
    visualization_sample_limit: number;
    correlation_max_columns: number;
    temporal_max_points: number;
    category_top_limit: number;
    category_label_max_characters: number;
  };
}

export interface ApiErrorBody {
  error?: { code?: string; message?: string; details?: Record<string, unknown> };
  detail?: string | { msg?: string }[];
}

export type FilterOperator = "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "contains" | "starts_with" | "is_null" | "not_null" | "in";
export type AggregateFunction = "count" | "sum" | "avg" | "min" | "max";
export type DateGranularity = "day" | "month" | "year";

export interface AnalyticsFilter { column: string; operator: FilterOperator; value?: unknown }
export interface AnalyticsSort { column: string; direction: "asc" | "desc" }
export interface AnalyticsAggregation { function: AggregateFunction; column?: string; alias: string }
export interface AnalyticsQuerySpec {
  columns: string[];
  filters: AnalyticsFilter[];
  sorts: AnalyticsSort[];
  group_by: string[];
  date_group?: { column: string; granularity: DateGranularity; alias: string };
  aggregations: AnalyticsAggregation[];
  offset: number;
  limit: number;
}
export interface AnalyticsResult {
  dataset_id: string;
  columns: string[];
  rows: Record<string, unknown>[];
  offset: number;
  limit: number;
  total_rows: number;
  grouped: boolean;
  chart: { dimension: string; series: string[]; rows: Record<string, unknown>[] } | null;
}


export interface AssistantResponse {
  status: "answer" | "clarification" | "unsupported" | "empty";
  answer: string;
  query: AnalyticsQuerySpec | null;
  results: AnalyticsResult | null;
  chart: (NonNullable<AnalyticsResult["chart"]> & { type: "bar" | "line" }) | null;
  warnings: string[];
}
