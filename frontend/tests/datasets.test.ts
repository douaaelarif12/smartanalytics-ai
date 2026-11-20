import { test } from "node:test";
import assert from "node:assert/strict";
import { validateDatasetFile } from "../src/app/api/datasetsApi.ts";
import { datasetPageReducer } from "../src/app/datasetsState.ts";
import type { UploadedDataset } from "../src/app/api/types.ts";

const item: UploadedDataset = {
  id: "3ce82b4d-811e-40eb-84e0-9cedf7fc52bb",
  name: "Sales",
  original_filename: "sales.csv",
  file_type: "csv",
  file_size_bytes: 42,
  row_count: 2,
  column_count: 2,
  missing_cell_count: 0,
  created_at: "2026-11-12T10:00:00Z",
  columns: [],
  source: "upload",
};

test("dataset file validation accepts CSV/XLSX and rejects unsupported or empty files", () => {
  assert.equal(validateDatasetFile({ name: "orders.csv", size: 10 }), null);
  assert.equal(validateDatasetFile({ name: "orders.XLSX", size: 10 }), null);
  assert.match(validateDatasetFile({ name: "orders.txt", size: 10 }) ?? "", /csv or \.xlsx/i);
  assert.match(validateDatasetFile({ name: "empty.csv", size: 0 }) ?? "", /empty/i);
});

test("dataset reducer represents list, loading, error and deletion states", () => {
  const loaded = datasetPageReducer({ status: "loading", items: [] }, { type: "loaded", items: [item] });
  assert.equal(loaded.status, "ready");
  assert.equal(loaded.items[0]?.name, "Sales");
  const failed = datasetPageReducer(loaded, { type: "failed", message: "API offline" });
  assert.equal(failed.status, "error");
  assert.deepEqual(failed.items, [item]);
  const removed = datasetPageReducer(failed, { type: "removed", id: item.id });
  assert.deepEqual(removed.items, []);
});
