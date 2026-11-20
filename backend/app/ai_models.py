from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .models import AnalyticsQuerySpec, AnalyticsResult, QueryFilter

class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value.strip()

class PlanFilter(QueryFilter):
    value: str | float | bool | list[str | float | bool] | None

class PlanQuery(AnalyticsQuerySpec):
    columns: list[str] = Field(max_length=30, description="Raw record selection only. Must be empty for every aggregation.")
    filters: list[PlanFilter] = Field(max_length=10)

class AnalyticalPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["answer", "clarification", "unsupported"]
    message: str = Field(max_length=1000)
    query: PlanQuery | None

class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    explanation: str = Field(max_length=3000)

class AskResponse(BaseModel):
    status: Literal["answer", "clarification", "unsupported", "empty"]
    answer: str
    query: AnalyticsQuerySpec | None = None
    results: AnalyticsResult | None = None
    chart: dict | None = None
    warnings: list[str] = Field(default_factory=list)
