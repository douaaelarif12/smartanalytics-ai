from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.errors import ApiError
from app.models import CorrelationMatrix, DatasetProfile, DatasetQuality
from app.profile_cache import PROFILE_VERSION, ProfileCache, ProfileCacheKey
from app.profiling import profile_dataframe
from app.service import DatasetService
from app.config import Settings
from app.main import create_app
from helpers import sign_in


def test_advanced_numeric_statistics_exclude_null_and_non_finite_values():
    frame = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 100.0, None, float("inf"), float("-inf")]})

    profile = profile_dataframe(frame, "dataset")
    statistic = profile.numeric[0]

    assert statistic.count == 7
    assert statistic.finite_count == 5
    assert statistic.non_finite_count == 2
    assert statistic.missing_count == 1
    assert statistic.q1 == pytest.approx(2.0)
    assert statistic.q3 == pytest.approx(4.0)
    assert statistic.iqr == pytest.approx(2.0)
    assert statistic.lower_fence == pytest.approx(-1.0)
    assert statistic.upper_fence == pytest.approx(7.0)
    assert statistic.lower_whisker == pytest.approx(1.0)
    assert statistic.upper_whisker == pytest.approx(4.0)
    assert statistic.outlier_count == 1
    assert statistic.std == pytest.approx(pd.Series([1.0, 2.0, 3.0, 4.0, 100.0]).std(ddof=1))
    assert statistic.warnings == ["small_sample"]


def test_profile_documents_linear_quartiles_sample_std_and_tukey_method():
    profile = profile_dataframe(pd.DataFrame({"value": [1, 2, 3, 4]}), "dataset")

    assert profile.profile_version == "3.0"
    assert profile.methodology.quartiles == "linear_interpolation"
    assert profile.methodology.standard_deviation == "sample_ddof_1"
    assert profile.methodology.outliers == "tukey_iqr_1_5"
    assert profile.methodology.minimum_recommended_outlier_sample == 20
    assert profile.methodology.histograms == "sturges_bounded_5_30"
    assert profile.methodology.correlations == "pearson_pairwise_complete"
    assert "does not imply causation" in profile.methodology.correlation_note
    assert profile.methodology.visualization_sample_limit == 50_000
    assert profile.methodology.correlation_max_columns == 12
    assert profile.methodology.temporal_max_points == 60
    assert profile.methodology.category_top_limit == 10


def test_zero_iqr_is_explicit_and_does_not_label_constant_values_as_outliers():
    profile = profile_dataframe(pd.DataFrame({"constant": [5.0] * 20}), "dataset")
    statistic = profile.numeric[0]

    assert statistic.iqr == 0
    assert statistic.iqr_is_zero is True
    assert statistic.lower_fence == 5
    assert statistic.upper_fence == 5
    assert statistic.lower_whisker == 5
    assert statistic.upper_whisker == 5
    assert statistic.outlier_count == 0
    assert statistic.warnings == ["zero_iqr"]


def test_empty_numeric_column_and_boolean_column_are_handled_explicitly():
    frame = pd.DataFrame({
        "empty": pd.Series([None, None], dtype="float64"),
        "flag": pd.Series([True, False], dtype="bool"),
    })
    profile = profile_dataframe(frame, "dataset")

    assert [item.column for item in profile.numeric] == ["empty"]
    assert profile.numeric[0].finite_count == 0
    assert profile.numeric[0].warnings == ["no_finite_values", "small_sample"]
    assert any(item.column == "flag" for item in profile.categorical)
    assert profile.columns[0].cardinality_percentage is None
    assert profile.columns[1].type == "boolean"


def test_column_quality_reports_completeness_cardinality_and_constants():
    frame = pd.DataFrame({
        "category": ["A", "A", None, "B"],
        "constant": [7, 7, 7, 7],
    })
    profile = profile_dataframe(frame, "dataset")
    quality = {item.column: item for item in profile.columns}

    assert quality["category"].non_null_count == 3
    assert quality["category"].missing_count == 1
    assert quality["category"].missing_percentage == 25
    assert quality["category"].unique_count == 2
    assert quality["category"].cardinality_percentage == pytest.approx(66.67)
    assert quality["category"].constant is False
    assert quality["constant"].constant is True


def test_high_cardinality_text_profile_remains_bounded():
    values = [f"category-{index}" for index in range(20_000)]
    profile = profile_dataframe(pd.DataFrame({"label": values}), "dataset")

    assert profile.columns[0].unique_count == 20_000
    assert profile.columns[0].cardinality_percentage == 100
    assert len(profile.categorical[0].top_values) == 10
    assert profile.categorical[0].other_count == 19_990
    assert len(profile.model_dump_json()) < 15_000


def test_large_high_cardinality_upload_keeps_profile_response_bounded(tmp_path: Path):
    rows = 60_000
    content = "value,label\n" + "".join(f"{index},category-{index}\n" for index in range(rows))
    settings = Settings(
        cookie_secure=False,
        data_dir=tmp_path / "large-profile-data",
        max_upload_bytes=5 * 1024 * 1024,
        profile_cache_max_bytes=512 * 1024,
    )
    with TestClient(create_app(settings)) as client:
        sign_in(client)
        upload = client.post(
            "/api/datasets",
            files={"file": ("large.csv", content.encode("utf-8"), "text/csv")},
        )
        assert upload.status_code == 201
        response = client.get(f"/api/datasets/{upload.json()['id']}/profile")

    assert response.status_code == 200
    profile = response.json()
    assert profile["row_count"] == rows
    assert profile["columns"][1]["unique_count"] == rows
    assert len(profile["categorical"][0]["top_values"]) == 10
    assert profile["categorical"][0]["other_count"] == rows - 10
    assert len(response.content) < 25_000


def test_histogram_conserves_finite_sample_counts_and_bounds_bins():
    values = list(range(1, 101)) + [None, float("nan"), float("inf"), float("-inf")]
    histogram = profile_dataframe(pd.DataFrame({"value": values}), "dataset").numeric[0].histogram

    assert 5 <= len(histogram.bins) <= 30
    assert histogram.source_count == 100
    assert histogram.sample_count == 100
    assert histogram.sampled is False
    assert sum(item.count for item in histogram.bins) == histogram.sample_count
    assert histogram.bins[0].lower_bound == pytest.approx(1)
    assert histogram.bins[-1].upper_bound == pytest.approx(100)


def test_histogram_sampling_is_deterministic_and_limited_to_fifty_thousand():
    frame = pd.DataFrame({"value": range(60_000)})
    first = profile_dataframe(frame, "first").numeric[0].histogram
    second = profile_dataframe(frame, "second").numeric[0].histogram

    assert first == second
    assert first.source_count == 60_000
    assert first.sample_count == 50_000
    assert first.sampled is True
    assert sum(item.count for item in first.bins) == 50_000
    assert len(first.bins) == 17


def test_histogram_handles_constant_and_empty_numeric_columns():
    profile = profile_dataframe(pd.DataFrame({
        "constant": pd.Series([7.0] * 25),
        "empty": pd.Series([None] * 25, dtype="float64"),
    }), "dataset")
    by_column = {item.column: item.histogram for item in profile.numeric}

    assert len(by_column["constant"].bins) == 1
    assert by_column["constant"].bins[0].lower_bound == 7
    assert by_column["constant"].bins[0].upper_bound == 7
    assert by_column["constant"].bins[0].count == 25
    assert by_column["empty"].bins == []
    assert by_column["empty"].sample_count == 0


def test_categorical_distribution_conserves_counts_and_bounds_long_labels():
    long_label = "é" * 1_000
    values = [f"category-{index}" for index in range(20)] + [long_label] * 5 + [None, None]
    statistic = profile_dataframe(pd.DataFrame({"label": values}), "dataset").categorical[0]

    assert len(statistic.top_values) == 10
    assert sum(item.count for item in statistic.top_values) + statistic.other_count == statistic.count
    assert statistic.missing_count == 2
    bounded = next(item for item in statistic.top_values if item.count == 5)
    assert bounded.value_truncated is True
    assert len(bounded.value) <= 160
    assert len(bounded.value.encode("utf-8")) <= 256


def test_pearson_correlations_cover_positive_negative_constant_and_exclusions():
    frame = pd.DataFrame({
        "x": range(1, 11),
        "positive": [value * 2 for value in range(1, 11)],
        "negative": [-value for value in range(1, 11)],
        "constant": [5] * 10,
        "flag": [True, False] * 5,
        "label": list("abcdefghij"),
    })
    correlation = profile_dataframe(frame, "dataset").correlation
    positions = {name: index for index, name in enumerate(correlation.columns)}

    assert correlation.method == "pearson"
    assert correlation.matrix[positions["x"]][positions["positive"]] == pytest.approx(1)
    assert correlation.matrix[positions["x"]][positions["negative"]] == pytest.approx(-1)
    assert correlation.matrix[positions["x"]][positions["constant"]] is None
    assert correlation.finite_pair_counts[positions["x"]][positions["positive"]] == 10
    assert {item.reason for item in correlation.excluded_columns} == {"boolean", "non_numeric"}
    assert correlation.correlation_does_not_imply_causation is True


def test_correlation_requires_three_finite_pairs_and_limits_numeric_columns():
    data = {f"numeric_{index}": [1.0, 2.0, float("nan"), float("inf")] for index in range(14)}
    data["flag"] = [True, False, True, False]
    correlation = profile_dataframe(pd.DataFrame(data), "dataset").correlation

    assert len(correlation.columns) == 12
    assert correlation.matrix[0][1] is None
    assert correlation.finite_pair_counts[0][1] == 2
    assert sum(item.reason == "column_limit" for item in correlation.excluded_columns) == 2
    assert any(item.reason == "boolean" for item in correlation.excluded_columns)
    assert correlation.columns_truncated is True


def test_correlation_sampling_is_deterministic_and_bounded():
    frame = pd.DataFrame({"x": range(50_100), "y": [value * 3 for value in range(50_100)]})
    first = profile_dataframe(frame, "first").correlation
    second = profile_dataframe(frame, "second").correlation

    assert first == second
    assert first.sampled is True
    assert first.source_row_count == 50_100
    assert first.sample_row_count == 50_000
    assert first.matrix[0][1] == pytest.approx(1)


def test_correlation_exclusion_payload_is_bounded_for_very_wide_datasets():
    data = {f"numeric_{index}": [1, 2, 3] for index in range(13)}
    data.update({f"text_{index}": ["a", "b", "c"] for index in range(150)})
    data["flag"] = [True, False, True]

    correlation = profile_dataframe(pd.DataFrame(data), "dataset").correlation

    assert len(correlation.columns) == 12
    assert correlation.columns_truncated is True
    assert correlation.excluded_count == 152
    assert len(correlation.excluded_columns) == 100
    assert correlation.exclusions_truncated is True
    assert len(correlation.model_dump_json()) < 20_000


def test_temporal_series_selects_day_month_and_multiyear_granularities():
    daily = pd.date_range("2026-01-01", periods=10, freq="D").to_series(index=range(10))
    monthly = pd.date_range("2026-01-01", periods=90, freq="D").to_series(index=range(90))
    long_years = pd.Series(pd.to_datetime([f"{year}-01-01" for year in range(1900, 2021)]))
    frame = pd.DataFrame({
        "daily": daily.reindex(range(121)),
        "monthly": monthly.reindex(range(121)),
        "long_years": long_years,
        "date_text": ["2026-01-01"] * 121,
    })
    temporal = {item.column: item for item in profile_dataframe(frame, "dataset").temporal}

    assert set(temporal) == {"daily", "monthly", "long_years"}
    assert temporal["daily"].granularity == "day"
    assert temporal["monthly"].granularity == "month"
    assert temporal["monthly"].coarsened is True
    assert temporal["long_years"].granularity == "year"
    assert temporal["long_years"].bucket_size == 3
    assert len(temporal["long_years"].points) <= 60
    for series in temporal.values():
        assert sum(point.count for point in series.points) == series.source_count
        assert series.truncated is False


def test_empty_datetime_series_is_explicit_and_does_not_create_business_measures():
    frame = pd.DataFrame({"when": pd.Series([pd.NaT, pd.NaT], dtype="datetime64[ns]")})
    temporal = profile_dataframe(frame, "dataset").temporal[0]

    assert temporal.column == "when"
    assert temporal.points == []
    assert temporal.source_count == 0
    assert temporal.missing_count == 2


def _profile(dataset_id: str) -> DatasetProfile:
    return DatasetProfile(
        dataset_id=dataset_id,
        row_count=1,
        column_count=1,
        quality=DatasetQuality(completeness_percentage=100, missing_cell_count=0, duplicate_row_count=0),
        numeric=[],
        categorical=[],
        correlation=CorrelationMatrix(
            columns=[], matrix=[], finite_pair_counts=[], sampled=False,
            source_row_count=1, sample_row_count=1, excluded_columns=[],
            excluded_count=0, columns_truncated=False, exclusions_truncated=False,
        ),
    )


def _key(owner: str, dataset_id: str, suffix: int = 0) -> ProfileCacheKey:
    return ProfileCacheKey(owner, dataset_id, PROFILE_VERSION, 100 + suffix, 200 + suffix)


def test_profile_cache_enforces_memory_budget_and_lru_eviction():
    first_id, second_id = str(uuid4()), str(uuid4())
    probe = ProfileCache(600, 8, 1_000_000)
    probe.put(_key("owner", first_id), _profile(first_id))
    one_entry_size = probe.current_bytes
    cache = ProfileCache(600, 8, one_entry_size + 64)

    cache.put(_key("owner", first_id), _profile(first_id))
    cache.put(_key("owner", second_id, 1), _profile(second_id))

    assert cache.current_bytes <= cache.max_bytes
    assert cache.entry_count == 1
    assert cache.get(_key("owner", first_id)) is None
    assert cache.get(_key("owner", second_id, 1)) is not None


def test_profile_cache_ttl_file_identity_owner_and_version_are_part_of_key():
    dataset_id = str(uuid4())
    cache = ProfileCache(10, 8, 1_000_000)
    original = _key("owner-a", dataset_id)
    with patch("app.profile_cache.time.monotonic", side_effect=[100.0, 105.0, 111.0]):
        cache.put(original, _profile(dataset_id))
        assert cache.get(original) is not None
        assert cache.get(original) is None

    cache.put(original, _profile(dataset_id))
    assert cache.get(_key("owner-b", dataset_id)) is None
    assert cache.get(ProfileCacheKey("owner-a", dataset_id, "old", 100, 200)) is None
    assert cache.get(_key("owner-a", dataset_id, 1)) is None


def test_service_authorizes_before_cache_and_reuses_serialized_profile(tmp_path: Path, monkeypatch):
    dataset_id = str(uuid4())
    path = tmp_path / f"{dataset_id}.csv"
    path.write_text("value\n1\n2\n", encoding="utf-8")
    metadata = SimpleNamespace(id=dataset_id, file_type="csv")
    repository = Mock()

    def owned_path(_dataset_id, owner_id):
        if owner_id != "owner-a":
            raise ApiError(404, "dataset_not_found", "The requested dataset does not exist.")
        return metadata, path

    repository.get_path.side_effect = owned_path
    service = object.__new__(DatasetService)
    service.repository = repository
    service.profile_cache = ProfileCache(600, 8, 1_000_000)
    reader = Mock(return_value=pd.DataFrame({"value": [1, 2]}))
    monkeypatch.setattr("app.service.read_dataframe", reader)

    assert service.profile(dataset_id, "owner-a").row_count == 2
    assert service.profile(dataset_id, "owner-a").row_count == 2
    assert reader.call_count == 1
    before = service.profile_cache.entry_count
    with pytest.raises(ApiError) as error:
        service.profile(dataset_id, "owner-b")
    assert error.value.status_code == 404
    assert service.profile_cache.entry_count == before


def test_service_delete_invalidates_cached_profile():
    dataset_id = str(uuid4())
    cache = ProfileCache(600, 8, 1_000_000)
    key = _key("owner", dataset_id)
    cache.put(key, _profile(dataset_id))
    service = object.__new__(DatasetService)
    service.repository = Mock()
    service.profile_cache = cache

    service.delete(dataset_id, "owner")

    service.repository.delete.assert_called_once_with(dataset_id, "owner")
    assert cache.get(key) is None
