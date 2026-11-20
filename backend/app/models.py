from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ColumnKind = Literal["integer", "number", "boolean", "datetime", "text"]


class ColumnMetadata(BaseModel):
    name: str
    type: ColumnKind
    pandas_dtype: str
    missing_count: int = Field(ge=0)
    missing_percentage: float = Field(ge=0, le=100)


class DatasetMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    original_filename: str
    file_type: Literal["csv", "xlsx"]
    file_size_bytes: int = Field(ge=0)
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    missing_cell_count: int = Field(ge=0)
    created_at: datetime
    columns: list[ColumnMetadata]
    source: Literal["upload"] = "upload"


class DatasetListResponse(BaseModel):
    items: list[DatasetMetadata]
    total: int = Field(ge=0)


class DatasetPreview(BaseModel):
    dataset_id: str
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    total_rows: int = Field(ge=0)
    columns: list[ColumnMetadata]
    rows: list[dict[str, Any]]


class HistogramBin(BaseModel):
    lower_bound: float
    upper_bound: float
    count: int = Field(ge=0)


class NumericHistogram(BaseModel):
    bins: list[HistogramBin]
    source_count: int = Field(ge=0)
    sample_count: int = Field(ge=0)
    sampled: bool


class NumericStatistics(BaseModel):
    column: str
    # ``count`` is kept for API compatibility and means non-null values,
    # including +/- infinity. Descriptive statistics only use finite values.
    count: int = Field(ge=0)
    finite_count: int = Field(ge=0)
    non_finite_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q1: float | None = None
    q3: float | None = None
    iqr: float | None = None
    lower_fence: float | None = None
    upper_fence: float | None = None
    lower_whisker: float | None = None
    upper_whisker: float | None = None
    outlier_count: int = Field(default=0, ge=0)
    iqr_is_zero: bool = False
    warnings: list[Literal["no_finite_values", "small_sample", "zero_iqr"]] = Field(default_factory=list)
    histogram: NumericHistogram


class CategoryValue(BaseModel):
    value: str
    count: int = Field(ge=0)
    value_truncated: bool = False


class CategoricalStatistics(BaseModel):
    column: str
    count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    top_values: list[CategoryValue]
    other_count: int = Field(default=0, ge=0)


class CorrelationExclusion(BaseModel):
    column: str
    reason: Literal["boolean", "non_numeric", "column_limit"]


class CorrelationMatrix(BaseModel):
    method: Literal["pearson"] = "pearson"
    columns: list[str]
    matrix: list[list[float | None]]
    finite_pair_counts: list[list[int]]
    minimum_finite_pairs: int = Field(default=3, ge=1)
    sampled: bool
    source_row_count: int = Field(ge=0)
    sample_row_count: int = Field(ge=0)
    excluded_columns: list[CorrelationExclusion]
    excluded_count: int = Field(ge=0)
    columns_truncated: bool
    exclusions_truncated: bool
    correlation_does_not_imply_causation: bool = True


class TemporalPoint(BaseModel):
    period: str
    count: int = Field(ge=0)


class TemporalSeries(BaseModel):
    column: str
    granularity: Literal["day", "month", "year"]
    bucket_size: int = Field(default=1, ge=1)
    points: list[TemporalPoint]
    source_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    coarsened: bool
    truncated: bool


class DatasetQuality(BaseModel):
    completeness_percentage: float | None = Field(default=None, ge=0, le=100)
    missing_cell_count: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)


class ColumnQuality(BaseModel):
    column: str
    type: ColumnKind
    non_null_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    missing_percentage: float = Field(ge=0, le=100)
    unique_count: int = Field(ge=0)
    cardinality_percentage: float | None = Field(default=None, ge=0, le=100)
    constant: bool


class ProfileMethodology(BaseModel):
    quartiles: Literal["linear_interpolation"] = "linear_interpolation"
    standard_deviation: Literal["sample_ddof_1"] = "sample_ddof_1"
    outliers: Literal["tukey_iqr_1_5"] = "tukey_iqr_1_5"
    minimum_recommended_outlier_sample: int = Field(default=20, ge=1)
    histograms: Literal["sturges_bounded_5_30"] = "sturges_bounded_5_30"
    correlations: Literal["pearson_pairwise_complete"] = "pearson_pairwise_complete"
    correlation_note: str = "Correlation does not imply causation."
    visualization_sample_limit: int = 50_000
    correlation_max_columns: int = 12
    temporal_max_points: int = 60
    category_top_limit: int = 10
    category_label_max_characters: int = 160


class DatasetProfile(BaseModel):
    profile_version: Literal["3.0"] = "3.0"
    dataset_id: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    quality: DatasetQuality
    columns: list[ColumnQuality] = Field(default_factory=list)
    numeric: list[NumericStatistics]
    categorical: list[CategoricalStatistics]
    correlation: CorrelationMatrix
    temporal: list[TemporalSeries] = Field(default_factory=list)
    methodology: ProfileMethodology = Field(default_factory=ProfileMethodology)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "smartanalytics-api"


FilterOperator = Literal["eq", "neq", "gt", "gte", "lt", "lte", "contains", "starts_with", "is_null", "not_null", "in"]
AggregateFunction = Literal["count", "sum", "avg", "min", "max"]
SortDirection = Literal["asc", "desc"]
DateGranularity = Literal["day", "month", "year"]


class QueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str
    operator: FilterOperator
    value: Any | None = None


class QuerySort(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str
    direction: SortDirection = "asc"


class QueryAggregation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    function: AggregateFunction
    column: str | None = None
    alias: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")


class DateGrouping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str
    granularity: DateGranularity
    alias: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")


class AnalyticsQuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    columns: list[str] = Field(default_factory=list, max_length=30)
    filters: list[QueryFilter] = Field(default_factory=list, max_length=10)
    sorts: list[QuerySort] = Field(default_factory=list, max_length=3)
    group_by: list[str] = Field(default_factory=list, max_length=2)
    date_group: DateGrouping | None = None
    aggregations: list[QueryAggregation] = Field(default_factory=list, max_length=5)
    offset: int = Field(default=0, ge=0, le=10_000_000)
    limit: int = Field(default=50, ge=1, le=200)


class AnalyticsResult(BaseModel):
    dataset_id: str
    columns: list[str]
    rows: list[dict[str, Any]]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    total_rows: int = Field(ge=0)
    grouped: bool
    chart: dict[str, Any] | None = None

