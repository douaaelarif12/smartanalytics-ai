import { test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("dataset list renders metadata and its empty state", async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  try {
    const { DatasetList } = await server.ssrLoadModule("/src/app/pages/Datasets.tsx");
    const item = { id: "a", name: "Orders", original_filename: "orders.csv", file_type: "csv", file_size_bytes: 20, row_count: 125, column_count: 4, missing_cell_count: 2, created_at: "2026-11-12T10:00:00Z", columns: [], source: "upload" };
    const list = renderToStaticMarkup(React.createElement(DatasetList, { items: [item], selectedId: "a", onSelect() {} }));
    assert.match(list, /Orders/);
    assert.match(list, /125 rows/);
    const empty = renderToStaticMarkup(React.createElement(DatasetList, { items: [], selectedId: null, onSelect() {} }));
    assert.match(empty, /No uploaded datasets yet/);
  } finally { await server.close(); }
});
