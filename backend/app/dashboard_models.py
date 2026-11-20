from __future__ import annotations

from datetime import datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import AnalyticsQuerySpec


SAFE_RESULT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
VisualizationType = Literal["table", "kpi", "bar", "line", "pie"]
WidgetDatasetStatus = Literal["ready", "dataset_deleted"]


def _clean_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("The value must not be blank.")
    return cleaned


def _canonical_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError):
        raise ValueError("A canonical UUID is required.") from None


class DashboardVisualizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: VisualizationType
    series: list[str] = Field(default_factory=list, max_length=5)
    value_column: str | None = None
    show_legend: bool = True
    show_data_table: bool = True

    @field_validator("series")
    @classmethod
    def safe_series(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)) or any(not SAFE_RESULT_NAME.fullmatch(value) for value in values):
            raise ValueError("Visualization series must be unique analytical result aliases.")
        return values

    @field_validator("value_column")
    @classmethod
    def safe_value_column(cls, value: str | None) -> str | None:
        if value is not None and not SAFE_RESULT_NAME.fullmatch(value):
            raise ValueError("The KPI value column must be a safe analytical result alias.")
        return value


class SavedWidgetDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: AnalyticsQuerySpec
    visualization: DashboardVisualizationConfig

    @model_validator(mode="after")
    def compatible_query_and_visualization(self):
        query = self.query
        visualization = self.visualization
        dimensions = len(query.group_by) + (1 if query.date_group else 0)
        aliases = [aggregation.alias for aggregation in query.aggregations]
        selected_series = visualization.series

        if query.aggregations and query.columns:
            raise ValueError("Aggregated saved analyses cannot select raw columns.")
        if (query.group_by or query.date_group) and not query.aggregations:
            raise ValueError("A saved grouped analysis requires an aggregation.")

        if visualization.type == "table":
            if selected_series or visualization.value_column is not None:
                raise ValueError("Table widgets do not accept chart series or a KPI value column.")
            return self

        if visualization.type == "kpi":
            if dimensions or len(aliases) != 1 or query.columns:
                raise ValueError("A KPI requires exactly one aggregation and no dimension or raw column.")
            if selected_series or visualization.value_column != aliases[0]:
                raise ValueError("A KPI value column must match its single aggregation alias.")
            return self

        if dimensions != 1 or not aliases or query.columns:
            raise ValueError("Bar, line and pie widgets require one dimension and at least one aggregation.")
        if not selected_series or any(series not in aliases for series in selected_series):
            raise ValueError("Chart series must reference saved aggregation aliases.")
        if visualization.type == "pie" and len(selected_series) != 1:
            raise ValueError("A pie widget requires exactly one analytical series.")
        if visualization.value_column is not None:
            raise ValueError("Only KPI widgets accept a value column.")
        return self


class DashboardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    _name = field_validator("name")(_clean_text)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class DashboardUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return _clean_text(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def has_change(self):
        if not ({"name", "description"} & self.model_fields_set):
            raise ValueError("At least one dashboard field must be updated.")
        return self


class DashboardWidgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    dataset_id: str
    title: str = Field(min_length=1, max_length=120)
    query: AnalyticsQuerySpec
    visualization: DashboardVisualizationConfig
    position: int | None = Field(default=None, ge=0, lt=12)
    width_columns: int = Field(default=6, ge=1, le=12)
    height_rows: int = Field(default=4, ge=2, le=12)

    _dataset_id = field_validator("dataset_id")(_canonical_uuid)
    _title = field_validator("title")(_clean_text)

    @model_validator(mode="after")
    def valid_definition(self):
        SavedWidgetDefinition(query=self.query, visualization=self.visualization)
        return self


class DashboardWidgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    dataset_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    query: AnalyticsQuerySpec | None = None
    visualization: DashboardVisualizationConfig | None = None
    position: int | None = Field(default=None, ge=0, lt=12)
    width_columns: int | None = Field(default=None, ge=1, le=12)
    height_rows: int | None = Field(default=None, ge=2, le=12)

    @field_validator("dataset_id")
    @classmethod
    def canonical_dataset(cls, value: str | None) -> str | None:
        return _canonical_uuid(value) if value is not None else None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return _clean_text(value) if value is not None else None

    @model_validator(mode="after")
    def has_change(self):
        mutable = {"dataset_id", "title", "query", "visualization", "position", "width_columns", "height_rows"}
        if not (mutable & self.model_fields_set):
            raise ValueError("At least one widget field must be updated.")
        return self


class DashboardSummary(BaseModel):
    id: str
    name: str
    description: str | None
    revision: int
    widget_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class DashboardWidgetResponse(BaseModel):
    id: str
    dashboard_id: str
    dataset_id: str | None
    dataset_id_snapshot: str
    dataset_name_snapshot: str
    dataset_status: WidgetDatasetStatus
    title: str
    query_version: Literal[1] = 1
    query: AnalyticsQuerySpec
    visualization: DashboardVisualizationConfig
    position: int
    width_columns: int
    height_rows: int
    created_at: datetime
    updated_at: datetime


class DashboardDetail(DashboardSummary):
    widgets: list[DashboardWidgetResponse]


class DashboardListResponse(BaseModel):
    items: list[DashboardSummary]
    total: int = Field(ge=0)
