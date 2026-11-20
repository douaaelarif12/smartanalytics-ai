from __future__ import annotations

import math
import hashlib
from bisect import bisect_right
from zipfile import BadZipFile, ZipFile
from xml.etree.ElementTree import ParseError
from datetime import date, datetime
from pathlib import Path
from typing import Any

from defusedxml.common import DefusedXmlException

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_numeric_dtype,
)

from .errors import ApiError
from .models import (
    CategoricalStatistics,
    CategoryValue,
    ColumnQuality,
    ColumnKind,
    ColumnMetadata,
    DatasetProfile,
    DatasetQuality,
    CorrelationExclusion,
    CorrelationMatrix,
    HistogramBin,
    NumericHistogram,
    NumericStatistics,
    TemporalPoint,
    TemporalSeries,
)


MINIMUM_RECOMMENDED_OUTLIER_SAMPLE = 20
MAX_VISUALIZATION_SAMPLE = 50_000
MIN_HISTOGRAM_BINS = 5
MAX_HISTOGRAM_BINS = 30
MAX_CATEGORY_VALUES = 10
MAX_CATEGORY_LABEL_CHARS = 160
MAX_CATEGORY_LABEL_BYTES = 256
MAX_CORRELATION_COLUMNS = 12
MAX_CORRELATION_EXCLUSIONS = 100
MIN_CORRELATION_PAIRS = 3
MAX_TEMPORAL_POINTS = 60


def read_dataframe(path: Path, extension: str) -> pd.DataFrame:
    try:
        if extension == "csv":
            frame = pd.read_csv(path, encoding="utf-8-sig")
        else:
            with ZipFile(path) as archive:
                members = archive.infolist()
                if len(members) > 2000 or sum(item.file_size for item in members) > 100 * 1024 * 1024:
                    raise ApiError(413, "workbook_too_large", "The expanded workbook exceeds the safe parsing limit.")
            frame = pd.read_excel(path, engine="openpyxl")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError, OSError, ImportError, BadZipFile, ParseError, KeyError, EOFError, DefusedXmlException) as exc:
        raise ApiError(422, "invalid_dataset_file", "The file could not be read as a valid CSV or Excel workbook.") from exc
    if len(frame.columns) == 0:
        raise ApiError(422, "empty_dataset", "The file must contain at least one column header.")
    frame.columns = _unique_column_names(frame.columns)
    for name in frame.columns:
        series = frame[name]
        if series.dtype == "object":
            clean = series.dropna().astype(str).str.strip()
            if len(clean) and clean.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T].*)?$").mean() >= 0.9:
                converted = pd.to_datetime(series, errors="coerce", utc=False)
                if converted.notna().sum() == series.notna().sum():
                    frame[name] = converted
    return frame


def _unique_column_names(columns: Any) -> list[str]:
    # DuckDB identifiers are case insensitive. Reserve original names so generated
    # suffixes cannot steal a later source header (e.g. x, x, x_2).
    bases = [str(raw).strip() or f"column_{index + 1}" for index, raw in enumerate(columns)]
    reserved = {base.casefold() for base in bases}
    used: set[str] = set()
    result: list[str] = []
    for base in bases:
        candidate = base
        suffix = 2
        if candidate.casefold() in used:
            while True:
                candidate = f"{base}_{suffix}"
                suffix += 1
                if candidate.casefold() not in used | reserved:
                    break
        used.add(candidate.casefold())
        result.append(candidate)
    return result


def infer_kind(series: pd.Series) -> ColumnKind:
    if is_bool_dtype(series.dtype):
        return "boolean"
    if is_integer_dtype(series.dtype):
        return "integer"
    if is_float_dtype(series.dtype) or is_numeric_dtype(series.dtype):
        return "number"
    if is_datetime64_any_dtype(series.dtype):
        return "datetime"
    return "text"


def column_metadata(frame: pd.DataFrame) -> list[ColumnMetadata]:
    row_count = len(frame)
    return [
        ColumnMetadata(
            name=str(name),
            type=infer_kind(frame[name]),
            pandas_dtype=str(frame[name].dtype),
            missing_count=int(frame[name].isna().sum()),
            missing_percentage=round(float(frame[name].isna().mean() * 100), 2) if row_count else 0.0,
        )
        for name in frame.columns
    ]


def json_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def preview_rows(frame: pd.DataFrame, offset: int, limit: int) -> list[dict[str, Any]]:
    subset = frame.iloc[offset : offset + limit]
    return [{str(key): json_value(value) for key, value in row.items()} for row in subset.to_dict(orient="records")]


def profile_dataframe(frame: pd.DataFrame, dataset_id: str) -> DatasetProfile:
    numeric: list[NumericStatistics] = []
    categorical: list[CategoricalStatistics] = []
    columns: list[ColumnQuality] = []
    for name in frame.columns:
        series = frame[name]
        missing = int(series.isna().sum())
        non_null = series.dropna()
        non_null_count = int(non_null.count())
        unique_count = int(non_null.nunique())
        columns.append(
            ColumnQuality(
                column=str(name),
                type=infer_kind(series),
                non_null_count=non_null_count,
                missing_count=missing,
                missing_percentage=round(float(series.isna().mean() * 100), 2) if len(series) else 0.0,
                unique_count=unique_count,
                cardinality_percentage=round(unique_count / non_null_count * 100, 2) if non_null_count else None,
                constant=non_null_count > 0 and unique_count == 1,
            )
        )
        if is_numeric_dtype(series.dtype) and not is_bool_dtype(series.dtype):
            numeric.append(_numeric_statistics(str(name), series, missing))
        else:
            clean = non_null.astype(str)
            counts = clean.value_counts()
            top_counts = counts.head(MAX_CATEGORY_VALUES)
            categorical.append(
                CategoricalStatistics(
                    column=str(name), count=int(clean.count()), missing_count=missing,
                    unique_count=int(clean.nunique()),
                    top_values=[
                        CategoryValue(value=label, count=int(count), value_truncated=truncated)
                        for value, count in top_counts.items()
                        for label, truncated in [_bounded_category_label(value)]
                    ],
                    other_count=int(clean.count()) - int(top_counts.sum()),
                )
            )
    total_cells = len(frame) * len(frame.columns)
    missing_cells = int(frame.isna().sum().sum())
    return DatasetProfile(
        dataset_id=dataset_id, row_count=len(frame), column_count=len(frame.columns),
        quality=DatasetQuality(
            completeness_percentage=round((total_cells - missing_cells) / total_cells * 100, 2) if total_cells else None,
            missing_cell_count=missing_cells,
            duplicate_row_count=int(frame.duplicated().sum()),
        ),
        columns=columns, numeric=numeric, categorical=categorical,
        correlation=_correlation_matrix(frame),
        temporal=_temporal_series(frame),
    )


def _numeric_statistics(column: str, series: pd.Series, missing_count: int) -> NumericStatistics:
    """Return exact finite-value statistics for one numeric, non-boolean column.

    Pandas' linear interpolation defines Q1/Q3. Standard deviation is the
    sample statistic (ddof=1). Tukey fences use 1.5 * IQR; an observation
    outside those fences is unusual, not automatically erroneous.
    """
    non_null = series.dropna()
    finite_mask = non_null.map(lambda value: math.isfinite(float(value)))
    finite = non_null[finite_mask].astype(float)
    finite_count = len(finite)
    warnings: list[str] = []
    if finite_count == 0:
        warnings.extend(("no_finite_values", "small_sample"))
        return NumericStatistics(
            column=column,
            count=int(non_null.count()),
            finite_count=0,
            non_finite_count=int(non_null.count()),
            missing_count=missing_count,
            warnings=warnings,
            histogram=NumericHistogram(bins=[], source_count=0, sample_count=0, sampled=False),
        )

    if finite_count < MINIMUM_RECOMMENDED_OUTLIER_SAMPLE:
        warnings.append("small_sample")

    q1 = float(finite.quantile(0.25, interpolation="linear"))
    q3 = float(finite.quantile(0.75, interpolation="linear"))
    iqr = q3 - q1
    iqr_is_zero = iqr == 0.0
    if iqr_is_zero:
        warnings.append("zero_iqr")
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    inside = finite[(finite >= lower_fence) & (finite <= upper_fence)]
    outlier_count = int(((finite < lower_fence) | (finite > upper_fence)).sum())

    return NumericStatistics(
        column=column,
        count=int(non_null.count()),
        finite_count=finite_count,
        non_finite_count=int(non_null.count()) - finite_count,
        missing_count=missing_count,
        min=_finite_stat(finite.min()),
        max=_finite_stat(finite.max()),
        mean=_finite_stat(finite.mean()),
        median=_finite_stat(finite.median()),
        std=_finite_stat(finite.std(ddof=1)) if finite_count > 1 else None,
        q1=_finite_stat(q1),
        q3=_finite_stat(q3),
        iqr=_finite_stat(iqr),
        lower_fence=_finite_stat(lower_fence),
        upper_fence=_finite_stat(upper_fence),
        lower_whisker=_finite_stat(inside.min()) if len(inside) else None,
        upper_whisker=_finite_stat(inside.max()) if len(inside) else None,
        outlier_count=outlier_count,
        iqr_is_zero=iqr_is_zero,
        warnings=warnings,
        histogram=_numeric_histogram(finite),
    )


def _deterministic_sample(series_or_frame: Any, limit: int = MAX_VISUALIZATION_SAMPLE) -> Any:
    length = len(series_or_frame)
    if length <= limit:
        return series_or_frame
    positions = [(index * (length - 1)) // (limit - 1) for index in range(limit)]
    return series_or_frame.iloc[positions]


def _numeric_histogram(finite: pd.Series) -> NumericHistogram:
    source_count = len(finite)
    if source_count == 0:
        return NumericHistogram(bins=[], source_count=0, sample_count=0, sampled=False)
    sample = _deterministic_sample(finite)
    sample_count = len(sample)
    sampled = sample_count < source_count
    minimum = float(finite.min())
    maximum = float(finite.max())
    if minimum == maximum:
        return NumericHistogram(
            bins=[HistogramBin(lower_bound=minimum, upper_bound=maximum, count=sample_count)],
            source_count=source_count,
            sample_count=sample_count,
            sampled=sampled,
        )

    bin_count = max(MIN_HISTOGRAM_BINS, min(MAX_HISTOGRAM_BINS, math.ceil(math.log2(sample_count) + 1)))
    edges = [minimum * (1 - index / bin_count) + maximum * (index / bin_count) for index in range(bin_count + 1)]
    counts = [0] * bin_count
    for value in sample:
        position = min(bin_count - 1, max(0, bisect_right(edges, float(value)) - 1))
        counts[position] += 1
    return NumericHistogram(
        bins=[
            HistogramBin(lower_bound=edges[index], upper_bound=edges[index + 1], count=counts[index])
            for index in range(bin_count)
        ],
        source_count=source_count,
        sample_count=sample_count,
        sampled=sampled,
    )


def _bounded_category_label(value: Any) -> tuple[str, bool]:
    label = str(value)
    if len(label) <= MAX_CATEGORY_LABEL_CHARS and len(label.encode("utf-8")) <= MAX_CATEGORY_LABEL_BYTES:
        return label, False
    suffix = f"…#{hashlib.sha256(label.encode('utf-8')).hexdigest()[:12]}"
    prefix = label[: MAX_CATEGORY_LABEL_CHARS - len(suffix)]
    byte_budget = MAX_CATEGORY_LABEL_BYTES - len(suffix.encode("utf-8"))
    prefix = prefix.encode("utf-8")[:byte_budget].decode("utf-8", errors="ignore")
    return prefix + suffix, True


def _correlation_matrix(frame: pd.DataFrame) -> CorrelationMatrix:
    selected: list[str] = []
    exclusions: list[CorrelationExclusion] = []
    excluded_count = 0
    columns_truncated = False
    for raw_name in frame.columns:
        name = str(raw_name)
        series = frame[raw_name]
        reason: str | None = None
        if is_bool_dtype(series.dtype):
            reason = "boolean"
        elif not is_numeric_dtype(series.dtype):
            reason = "non_numeric"
        elif len(selected) >= MAX_CORRELATION_COLUMNS:
            reason = "column_limit"
            columns_truncated = True
        else:
            selected.append(name)
        if reason is not None:
            excluded_count += 1
            if len(exclusions) < MAX_CORRELATION_EXCLUSIONS:
                exclusions.append(CorrelationExclusion(column=name, reason=reason))

    sampled_frame = _deterministic_sample(frame)
    sampled = len(sampled_frame) < len(frame)
    if not selected:
        return CorrelationMatrix(
            columns=[], matrix=[], finite_pair_counts=[], sampled=sampled,
            source_row_count=len(frame), sample_row_count=len(sampled_frame),
            excluded_columns=exclusions, excluded_count=excluded_count,
            columns_truncated=columns_truncated,
            exclusions_truncated=excluded_count > len(exclusions),
        )

    numeric = sampled_frame[selected].astype(float).replace([float("inf"), float("-inf")], float("nan"))
    matrix: list[list[float | None]] = []
    pair_counts: list[list[int]] = []
    for left in selected:
        coefficient_row: list[float | None] = []
        count_row: list[int] = []
        for right in selected:
            valid = numeric[left].notna() & numeric[right].notna()
            pair_count = int(valid.sum())
            count_row.append(pair_count)
            if pair_count < MIN_CORRELATION_PAIRS:
                coefficient_row.append(None)
                continue
            left_values = numeric.loc[valid, left]
            right_values = numeric.loc[valid, right]
            if left_values.nunique() <= 1 or right_values.nunique() <= 1:
                coefficient_row.append(None)
                continue
            coefficient = float(left_values.corr(right_values, method="pearson"))
            coefficient_row.append(round(coefficient, 8) if math.isfinite(coefficient) else None)
        matrix.append(coefficient_row)
        pair_counts.append(count_row)
    return CorrelationMatrix(
        columns=selected, matrix=matrix, finite_pair_counts=pair_counts,
        sampled=sampled, source_row_count=len(frame), sample_row_count=len(sampled_frame),
        excluded_columns=exclusions, excluded_count=excluded_count,
        columns_truncated=columns_truncated,
        exclusions_truncated=excluded_count > len(exclusions),
    )


def _temporal_series(frame: pd.DataFrame) -> list[TemporalSeries]:
    result: list[TemporalSeries] = []
    for raw_name in frame.columns:
        series = frame[raw_name]
        if not is_datetime64_any_dtype(series.dtype):
            continue
        clean = series.dropna()
        missing_count = int(series.isna().sum())
        if len(clean) == 0:
            result.append(TemporalSeries(
                column=str(raw_name), granularity="day", points=[], source_count=0,
                missing_count=missing_count, coarsened=False, truncated=False,
            ))
            continue

        day_counts = clean.dt.strftime("%Y-%m-%d").value_counts().sort_index()
        if len(day_counts) <= MAX_TEMPORAL_POINTS:
            granularity = "day"
            bucket_size = 1
            counts = day_counts
            coarsened = False
        else:
            month_counts = clean.dt.to_period("M").astype(str).value_counts().sort_index()
            if len(month_counts) <= MAX_TEMPORAL_POINTS:
                granularity = "month"
                bucket_size = 1
                counts = month_counts
                coarsened = True
            else:
                years = clean.dt.year.astype(int)
                minimum_year = int(years.min())
                maximum_year = int(years.max())
                bucket_size = max(1, math.ceil((maximum_year - minimum_year + 1) / MAX_TEMPORAL_POINTS))
                starts = minimum_year + ((years - minimum_year) // bucket_size) * bucket_size
                raw_counts = starts.value_counts().sort_index()
                labels = [
                    str(int(start)) if bucket_size == 1 else f"{int(start)}–{min(int(start) + bucket_size - 1, maximum_year)}"
                    for start in raw_counts.index
                ]
                counts = pd.Series(raw_counts.to_list(), index=labels)
                granularity = "year"
                coarsened = True
        points = [TemporalPoint(period=str(period), count=int(count)) for period, count in counts.items()]
        result.append(TemporalSeries(
            column=str(raw_name), granularity=granularity, bucket_size=bucket_size,
            points=points, source_count=len(clean), missing_count=missing_count,
            coarsened=coarsened, truncated=len(points) > MAX_TEMPORAL_POINTS,
        ))
    return result


def _finite_stat(value: Any) -> float | None:
    result = float(value)
    return result if math.isfinite(result) else None

