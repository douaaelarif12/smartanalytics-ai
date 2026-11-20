import { test } from "node:test";
import assert from "node:assert/strict";
import { addExplorerFilter, enableAggregation, initialExplorerQuery, normalizeExplorerQuery, safeAlias, uploadedDatasetKey } from "../src/app/explorerState.ts";
import type { UploadedDataset } from "../src/app/api/types.ts";

const dataset: UploadedDataset = {
  id: "dataset-id", name: "Orders", original_filename: "orders.csv", file_type: "csv",
  file_size_bytes: 100, row_count: 3, column_count: 3, missing_cell_count: 0,
  created_at: "2026-11-12T10:00:00Z", source: "upload",
  columns: [
    { name: "category", type: "text", pandas_dtype: "object", missing_count: 0, missing_percentage: 0 },
    { name: "amount", type: "number", pandas_dtype: "float64", missing_count: 0, missing_percentage: 0 },
    { name: "date", type: "datetime", pandas_dtype: "datetime64[ns]", missing_count: 0, missing_percentage: 0 },
  ],
};

test("uploaded dataset selection uses the global selector key", () => {
  assert.equal(uploadedDatasetKey(dataset.id), "upload:dataset-id");
  assert.deepEqual(initialExplorerQuery(dataset).columns, ["category", "amount", "date"]);
});

test("filter interactions add a type-aware filter and normalize values", () => {
  const filters = addExplorerFilter([], dataset);
  assert.deepEqual(filters[0], { column: "category", operator: "contains", value: "" });
  const normalized = normalizeExplorerQuery({ ...initialExplorerQuery(dataset), filters: [{ column: "amount", operator: "in", value: "10, 20" }] }, dataset);
  assert.deepEqual(normalized.filters[0]?.value, [10, 20]);
});

test("aggregation configuration selects a real dimension and measure", () => {
  const configuration = enableAggregation(dataset);
  assert.deepEqual(configuration.group_by, ["category"]);
  assert.deepEqual(configuration.aggregations, [{ function: "sum", column: "amount", alias: "sum_amount" }]);
  assert.deepEqual(configuration.columns, []);
});


test("wide dataset starts with a valid bounded selection and bounded generated aliases", () => {
  const wide = { ...dataset, columns: Array.from({ length: 40 }, (_, i) => ({ ...dataset.columns[0]!, name: `column_${i}` })) };
  assert.equal(initialExplorerQuery(wide).columns.length, 30);
  assert.ok(`sum_${safeAlias("a".repeat(200))}`.length <= 64);
});
