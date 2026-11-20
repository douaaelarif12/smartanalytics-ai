from __future__ import annotations

import re
import math
from threading import Timer
from typing import Any

import duckdb
import pandas as pd

from .errors import ApiError
from .models import AnalyticsQuerySpec, AnalyticsResult, ColumnMetadata
from .profiling import json_value


NUMERIC_KINDS = {"integer", "number"}
GROUPABLE_KINDS = {"text", "boolean", "integer", "number"}
ALIAS_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


class AnalyticsEngine:
    """Validated analytics compiler. It never accepts client-provided SQL fragments."""

    def execute(
        self,
        frame: pd.DataFrame,
        dataset_id: str,
        schema: list[ColumnMetadata],
        spec: AnalyticsQuerySpec,
    ) -> AnalyticsResult:
        kinds = {column.name: column.type for column in schema}
        self._validate(spec, kinds)
        grouped = bool(spec.group_by or spec.date_group or spec.aggregations)
        select_sql, output_columns, group_sql = self._select_clause(spec, kinds, grouped)
        where_sql, parameters = self._where_clause(spec, kinds)
        base_sql = f"SELECT {select_sql} FROM dataset_frame{where_sql}{group_sql}"
        output_set = set(output_columns)
        order_parts = []
        for sort in spec.sorts:
            if sort.column not in output_set:
                raise ApiError(422, "invalid_sort_column", "Sort columns must be present in the analytical result.", {"column": sort.column})
            order_parts.append(f"{quote_identifier(sort.column)} {sort.direction.upper()}")
        ordered_sql = base_sql + (" ORDER BY " + ", ".join(order_parts) if order_parts else "")

        connection = duckdb.connect(database=":memory:", config={"threads": 2, "memory_limit": "256MB"})
        timer=Timer(10,connection.interrupt)
        timer.daemon=True
        try:
            connection.register("dataset_frame", frame)
            timer.start()
            total = int(connection.execute(f"SELECT COUNT(*) FROM ({base_sql}) AS result_count", parameters).fetchone()[0])
            result_frame = connection.execute(
                ordered_sql + " LIMIT ? OFFSET ?", [*parameters, spec.limit, spec.offset]
            ).fetchdf()
        except duckdb.Error as exc:
            raise ApiError(422, "analytics_query_failed", "The validated analytical query could not be executed.") from exc
        finally:
            timer.cancel()
            if timer.ident is not None:
                timer.join()
            connection.close()

        rows = [
            {str(key): json_value(value) for key, value in row.items()}
            for row in result_frame.to_dict(orient="records")
        ]
        chart = None
        dimension_count = len(spec.group_by) + (1 if spec.date_group else 0)
        chart_series = [item.alias for item in spec.aggregations if item.function == "count" or kinds.get(item.column) in NUMERIC_KINDS]
        if grouped and dimension_count == 1 and chart_series:
            chart = {
                "dimension": output_columns[0],
                "series": chart_series,
                "rows": rows,
            }
        return AnalyticsResult(
            dataset_id=dataset_id,
            columns=output_columns,
            rows=rows,
            offset=spec.offset,
            limit=spec.limit,
            total_rows=total,
            grouped=grouped,
            chart=chart,
        )

    def _validate(self, spec: AnalyticsQuerySpec, kinds: dict[str, str]) -> None:
        if len(set(spec.columns)) != len(spec.columns) or len(set(spec.group_by)) != len(spec.group_by):
            raise ApiError(422, "duplicate_columns", "Column selections and groups must not contain duplicates.")
        requested = list(spec.columns) + list(spec.group_by)
        requested += [item.column for item in spec.filters]
        requested += [item.column for item in spec.sorts if item.column in kinds]
        requested += [item.column for item in spec.aggregations if item.column]
        if spec.date_group:
            requested.append(spec.date_group.column)
        unknown = sorted({column for column in requested if column not in kinds})
        if unknown:
            raise ApiError(422, "invalid_column", "One or more requested columns do not exist.", {"columns": unknown})
        if spec.aggregations and spec.columns:
            raise ApiError(422, "invalid_query_shape", "Raw column selection cannot be combined with aggregations.")
        if (spec.group_by or spec.date_group) and not spec.aggregations:
            raise ApiError(422, "aggregation_required", "Grouping requires at least one aggregation.")
        if spec.aggregations and not spec.group_by and not spec.date_group and len(spec.aggregations) > 5:
            raise ApiError(422, "query_too_complex", "Too many aggregations were requested.")
        aliases = [item.alias for item in spec.aggregations]
        if spec.date_group:
            aliases.append(spec.date_group.alias)
        result_names = [*spec.group_by, *aliases]
        if len(result_names) != len({name.casefold() for name in result_names}) or any(not ALIAS_PATTERN.fullmatch(alias) for alias in aliases):
            raise ApiError(422, "invalid_alias", "Result aliases must be unique safe identifiers.")
        for column in spec.group_by:
            if kinds[column] not in GROUPABLE_KINDS:
                raise ApiError(422, "invalid_group_column", "This column type cannot be used as a categorical group.", {"column": column})
        if spec.date_group and kinds[spec.date_group.column] != "datetime":
            raise ApiError(422, "invalid_date_group", "Date grouping requires a detected datetime column.", {"column": spec.date_group.column})
        for aggregation in spec.aggregations:
            if aggregation.function == "count":
                continue
            if aggregation.column is None:
                raise ApiError(422, "aggregation_column_required", f"{aggregation.function.upper()} requires a column.")
            kind = kinds[aggregation.column]
            allowed = NUMERIC_KINDS | ({"datetime"} if aggregation.function in {"min", "max"} else set())
            if kind not in allowed:
                raise ApiError(422, "invalid_aggregation", f"{aggregation.function.upper()} is not valid for this column type.", {"column": aggregation.column, "type": kind})
        for item in spec.filters:
            values = item.value if item.operator == "in" and isinstance(item.value, list) else [item.value]
            if item.operator not in {"is_null", "not_null"}:
                if any(not isinstance(value, (str, int, float, bool)) or
                       (isinstance(value, float) and not math.isfinite(value)) or
                       (isinstance(value, str) and len(value) > 4000) for value in values):
                    raise ApiError(422, "invalid_filter_value", "Filters require finite scalar values of at most 4000 characters.")
            kind = kinds[item.column]
            if item.operator in {"contains", "starts_with"} and kind != "text":
                raise ApiError(422, "invalid_operator", "Text operators require a text column.", {"column": item.column})
            if item.operator in {"gt", "gte", "lt", "lte"} and kind not in NUMERIC_KINDS | {"datetime"}:
                raise ApiError(422, "invalid_operator", "Comparison operators require a numeric or datetime column.", {"column": item.column})
            if item.operator == "in":
                if not isinstance(item.value, list) or not 1 <= len(item.value) <= 50:
                    raise ApiError(422, "invalid_filter_value", "IN requires a list containing between 1 and 50 values.")
            elif item.operator not in {"is_null", "not_null"} and item.value is None:
                raise ApiError(422, "filter_value_required", "This filter operator requires a value.")

    def _select_clause(self, spec: AnalyticsQuerySpec, kinds: dict[str, str], grouped: bool) -> tuple[str, list[str], str]:
        if not grouped:
            columns = spec.columns or list(kinds)
            return ", ".join(quote_identifier(column) for column in columns), columns, ""
        expressions: list[str] = []
        output: list[str] = []
        groups: list[str] = []
        for column in spec.group_by:
            quoted = quote_identifier(column)
            expressions.append(quoted)
            output.append(column)
            groups.append(quoted)
        if spec.date_group:
            expression = f"DATE_TRUNC('{spec.date_group.granularity}', {quote_identifier(spec.date_group.column)})"
            expressions.append(f"{expression} AS {quote_identifier(spec.date_group.alias)}")
            output.append(spec.date_group.alias)
            groups.append(expression)
        for aggregation in spec.aggregations:
            target = "*" if aggregation.function == "count" and aggregation.column is None else quote_identifier(aggregation.column or "")
            function = "AVG" if aggregation.function == "avg" else aggregation.function.upper()
            expressions.append(f"{function}({target}) AS {quote_identifier(aggregation.alias)}")
            output.append(aggregation.alias)
        return ", ".join(expressions), output, (" GROUP BY " + ", ".join(groups) if groups else "")

    def _where_clause(self, spec: AnalyticsQuerySpec, kinds: dict[str, str]) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        operators = {"eq": "=", "neq": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
        for item in spec.filters:
            column = quote_identifier(item.column)
            if item.operator == "is_null":
                clauses.append(f"{column} IS NULL")
            elif item.operator == "not_null":
                clauses.append(f"{column} IS NOT NULL")
            elif item.operator in {"contains", "starts_with"}:
                clauses.append(f"CAST({column} AS VARCHAR) ILIKE ? ESCAPE '\\'")
                escaped = str(item.value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                parameters.append(f"%{escaped}%" if item.operator == "contains" else f"{escaped}%")
            elif item.operator == "in":
                values = item.value if isinstance(item.value, list) else []
                clauses.append(f"{column} IN ({', '.join('?' for _ in values)})")
                parameters.extend(values)
            else:
                clauses.append(f"{column} {operators[item.operator]} ?")
                parameters.append(item.value)
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), parameters
