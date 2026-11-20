import { test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("explorer feedback renders backend errors and honest empty states", async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  try {
    const { ExplorerFeedback } = await server.ssrLoadModule("/src/app/pages/DataExplorer.tsx");
    const error = renderToStaticMarkup(React.createElement(ExplorerFeedback, { loading: false, error: "Invalid column", result: null, onRetry() {} }));
    assert.match(error, /Invalid column/);
    assert.match(error, /role="alert"/);
    const emptyResult = { dataset_id: "a", columns: ["name"], rows: [], offset: 0, limit: 25, total_rows: 0, grouped: false, chart: null };
    const empty = renderToStaticMarkup(React.createElement(ExplorerFeedback, { loading: false, error: "", result: emptyResult, onRetry() {} }));
    assert.match(empty, /No rows match this query/);
    assert.match(empty, /No analytical values were generated/);
  } finally { await server.close(); }
});
