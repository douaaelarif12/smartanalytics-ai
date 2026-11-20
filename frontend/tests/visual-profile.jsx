import React from "react";
import { createRoot } from "react-dom/client";
import ProfileVisualizations from "/src/app/components/ProfileVisualizations.tsx";

const profile = {
  profile_version: "3.0",
  dataset_id: "visual-fixture",
  row_count: 60000,
  column_count: 7,
  quality: { completeness_percentage: 98.7, missing_cell_count: 5460, duplicate_row_count: 18 },
  columns: [],
  numeric: [
    {
      column: "order_amount", count: 59980, finite_count: 59975, non_finite_count: 5,
      missing_count: 20, min: 4.5, max: 980, mean: 184.72, median: 142.5, std: 126.8,
      q1: 86, q3: 238, iqr: 152, lower_fence: -142, upper_fence: 466,
      lower_whisker: 4.5, upper_whisker: 465, outlier_count: 234, iqr_is_zero: false,
      warnings: [], histogram: {
        bins: [
          { lower_bound: 4.5, upper_bound: 102.05, count: 14200 },
          { lower_bound: 102.05, upper_bound: 199.6, count: 16800 },
          { lower_bound: 199.6, upper_bound: 297.15, count: 10400 },
          { lower_bound: 297.15, upper_bound: 394.7, count: 5200 },
          { lower_bound: 394.7, upper_bound: 492.25, count: 2100 },
          { lower_bound: 492.25, upper_bound: 589.8, count: 850 },
          { lower_bound: 589.8, upper_bound: 687.35, count: 320 },
          { lower_bound: 687.35, upper_bound: 784.9, count: 90 },
          { lower_bound: 784.9, upper_bound: 882.45, count: 32 },
          { lower_bound: 882.45, upper_bound: 980, count: 8 },
        ], source_count: 59975, sample_count: 50000, sampled: true,
      },
    },
    {
      column: "satisfaction_score", count: 12, finite_count: 12, non_finite_count: 0,
      missing_count: 59988, min: 7, max: 7, mean: 7, median: 7, std: 0,
      q1: 7, q3: 7, iqr: 0, lower_fence: 7, upper_fence: 7,
      lower_whisker: 7, upper_whisker: 7, outlier_count: 0, iqr_is_zero: true,
      warnings: ["small_sample", "zero_iqr"],
      histogram: { bins: [{ lower_bound: 7, upper_bound: 7, count: 12 }], source_count: 12, sample_count: 12, sampled: false },
    },
  ],
  categorical: [{
    column: "region", count: 59960, missing_count: 40, unique_count: 16,
    top_values: [
      { value: "Casablanca-Settat", count: 14200, value_truncated: false },
      { value: "Rabat-Salé-Kénitra", count: 11850, value_truncated: false },
      { value: "Marrakech-Safi", count: 8900, value_truncated: false },
      { value: "Fès-Meknès", count: 7200, value_truncated: false },
      { value: "Tanger-Tétouan-Al Hoceïma", count: 6100, value_truncated: false },
    ], other_count: 11710,
  }],
  correlation: {
    method: "pearson", columns: ["order_amount", "discount", "units", "margin"],
    matrix: [[1, -0.62, 0.78, 0.41], [-0.62, 1, -0.31, -0.73], [0.78, -0.31, 1, 0.55], [0.41, -0.73, 0.55, 1]],
    finite_pair_counts: [[59975, 59920, 59975, 59960], [59920, 59940, 59920, 59910], [59975, 59920, 60000, 59960], [59960, 59910, 59960, 59960]],
    minimum_finite_pairs: 3, sampled: true, source_row_count: 60000, sample_row_count: 50000,
    excluded_columns: [{ column: "is_priority", reason: "boolean" }, { column: "region", reason: "non_numeric" }],
    excluded_count: 2, columns_truncated: false, exclusions_truncated: false,
    correlation_does_not_imply_causation: true,
  },
  temporal: [{
    column: "order_date", granularity: "month", bucket_size: 1, source_count: 59940,
    missing_count: 60, coarsened: true, truncated: false,
    points: [
      { period: "2026-01", count: 4100 }, { period: "2026-02", count: 4380 },
      { period: "2026-03", count: 4620 }, { period: "2026-04", count: 4510 },
      { period: "2026-05", count: 4890 }, { period: "2026-06", count: 5070 },
      { period: "2026-07", count: 5250 }, { period: "2026-08", count: 5180 },
      { period: "2026-09", count: 5390 }, { period: "2026-10", count: 5570 },
      { period: "2026-11", count: 5440 }, { period: "2026-12", count: 5540 },
    ],
  }],
  methodology: {
    quartiles: "linear_interpolation", standard_deviation: "sample_ddof_1", outliers: "tukey_iqr_1_5",
    minimum_recommended_outlier_sample: 20, histograms: "sturges_bounded_5_30",
    correlations: "pearson_pairwise_complete", correlation_note: "Correlation does not imply causation.",
    visualization_sample_limit: 50000, correlation_max_columns: 12, temporal_max_points: 60,
    category_top_limit: 10, category_label_max_characters: 160,
  },
};

createRoot(document.getElementById("root")).render(<ProfileVisualizations profile={profile} />);
