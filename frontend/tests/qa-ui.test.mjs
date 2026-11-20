import { test } from "node:test";
import assert from "node:assert/strict";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route, Outlet } from "react-router-dom";
import { JSDOM } from "jsdom";
import { createServer } from "vite";

const dataset = (id) => ({ id, name: id, row_count: 2, columns: [{ name: "amount", type: "number" }], source: "upload" });
const result = (id, amount) => ({ dataset_id: id, columns: ["amount"], rows: [{ amount }], offset: 0, limit: 25, total_rows: 1, grouped: false, chart: null });
const profile = (overrides = {}) => ({
  profile_version: "3.0",
  dataset_id: "test",
  row_count: 1,
  column_count: 1,
  quality: { completeness_percentage: 100, missing_cell_count: 0, duplicate_row_count: 0 },
  columns: [],
  numeric: [],
  categorical: [],
  correlation: { method: "pearson", columns: [], matrix: [], finite_pair_counts: [], minimum_finite_pairs: 3, sampled: false, source_row_count: 1, sample_row_count: 1, excluded_columns: [], excluded_count: 0, columns_truncated: false, exclusions_truncated: false, correlation_does_not_imply_causation: true },
  temporal: [],
  methodology: { quartiles: "linear_interpolation", standard_deviation: "sample_ddof_1", outliers: "tukey_iqr_1_5", minimum_recommended_outlier_sample: 20, histograms: "sturges_bounded_5_30", correlations: "pearson_pairwise_complete", correlation_note: "Correlation does not imply causation.", visualization_sample_limit: 50000, correlation_max_columns: 12, temporal_max_points: 60, category_top_limit: 10, category_label_max_characters: 160 },
  ...overrides,
});
async function harness(run) {
  const dom = new JSDOM("<div id='root'></div>", { url: "http://localhost/app/explorer" });
  const previous = { window: globalThis.window, document: globalThis.document, HTMLElement: globalThis.HTMLElement, IS_REACT_ACT_ENVIRONMENT: globalThis.IS_REACT_ACT_ENVIRONMENT };
  Object.assign(globalThis, { window: dom.window, document: dom.window.document, HTMLElement: dom.window.HTMLElement, IS_REACT_ACT_ENVIRONMENT: true });
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  const root = createRoot(document.getElementById("root"));
  try { await run({ server, root, container: document.getElementById("root") }); }
  finally { await act(async () => root.unmount()); await server.close(); dom.window.close(); Object.assign(globalThis, previous); }
}
function tree(Component, context) {
  return React.createElement(MemoryRouter, null, React.createElement(Routes, null,
    React.createElement(Route, { element: React.createElement(Outlet, { context }) },
      React.createElement(Route, { path: "*", element: React.createElement(Component) }))));
}

test("explorer isolates queries and ignores late responses across datasets", async () => {
  await harness(async ({ server, root, container }) => {
    const { default: Explorer } = await server.ssrLoadModule("/src/app/pages/DataExplorer.tsx");
    const { datasetsApi } = await server.ssrLoadModule("/src/app/api/datasetsApi.ts");
    const calls = [];
    let resolveOld;
    datasetsApi.query = (id, spec) => {
      calls.push({ id, columns: spec.columns });
      if (id === "first") return new Promise((resolve) => { resolveOld = resolve; });
      return Promise.resolve({ ...result(id, 999), columns: ["other"], rows: [{ other: 999 }] });
    };
    const first = dataset("first");
    const second = { ...dataset("second"), columns: [{ name: "other", type: "number" }] };
    const context = { uploadedDataset: first, uploadedDatasets: [first, second], selectDataset() {} };
    await act(async () => root.render(tree(Explorer, context)));
    await act(async () => root.render(tree(Explorer, { ...context, uploadedDataset: second })));
    assert.deepEqual(calls, [{ id: "first", columns: ["amount"] }, { id: "second", columns: ["other"] }]);
    await act(async () => resolveOld(result("first", 111)));
    assert.match(container.textContent, /999/);
    assert.doesNotMatch(container.textContent, /111/);
  });
});

test("assistant aborts and ignores an answer from a previously selected dataset", async () => {
  await harness(async ({ server, root, container }) => {
    const { default: Assistant } = await server.ssrLoadModule("/src/app/pages/Assistant.tsx");
    const { datasetsApi } = await server.ssrLoadModule("/src/app/api/datasetsApi.ts");
    let resolveAnswer;
    let signal;
    datasetsApi.ask = (_id, _question, nextSignal) => { signal = nextSignal; return new Promise((resolve) => { resolveAnswer = resolve; }); };
    const first = dataset("first"); const second = dataset("second");
    const context = { uploadedDataset: first, uploadedDatasets: [first, second], selectDataset() {} };
    await act(async () => root.render(tree(Assistant, context)));
    const suggestion = Array.from(container.querySelectorAll("button")).find((button) => button.textContent.includes("How many rows"));
    await act(async () => suggestion.click());
    await act(async () => container.querySelector("form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true })));
    assert.ok(resolveAnswer);
    await act(async () => root.render(tree(Assistant, { ...context, uploadedDataset: second })));
    assert.equal(signal.aborted, true);
    await act(async () => resolveAnswer({ status: "answer", answer: "OLD ANSWER MUST NOT APPEAR", warnings: [], query: null, results: null, chart: null }));
    assert.doesNotMatch(container.textContent, /OLD ANSWER MUST NOT APPEAR/);
  });
});

test("pie charts explain why negative measures cannot be plotted", async () => {
  const { renderToStaticMarkup } = await import("react-dom/server");
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  try {
    const { default: Chart } = await server.ssrLoadModule("/src/app/components/ExplorerChart.tsx");
    const html = renderToStaticMarkup(React.createElement(Chart, { type: "pie", chart: { dimension: "category", series: ["total"], rows: [{ category: "A", total: -5 }] } }));
    assert.match(html, /role="status"/);
    assert.match(html, /requires non-negative values/);
  } finally { await server.close(); }
});

test("uploaded overview renders factual profile metrics and distributions", async () => {
  await harness(async ({ server, root, container }) => {
    const { default: Overview } = await server.ssrLoadModule("/src/app/pages/Overview.tsx");
    const { datasetsApi } = await server.ssrLoadModule("/src/app/api/datasetsApi.ts");
    const uploadedDataset = {
      ...dataset("customer-orders"),
      name: "Customer orders",
      column_count: 2,
      columns: [
        { name: "amount", type: "number" },
        { name: "region", type: "text" },
      ],
    };
    datasetsApi.profile = async () => profile({
      dataset_id: uploadedDataset.id,
      row_count: 120,
      column_count: 2,
      quality: { completeness_percentage: 98.5, missing_cell_count: 4, duplicate_row_count: 2 },
      numeric: [{ column: "amount", count: 118, finite_count: 118, non_finite_count: 0, missing_count: 2, min: 5, max: 900, mean: 127.5, median: 88, std: 44.2, q1: 40, q3: 150, iqr: 110, lower_fence: -125, upper_fence: 315, lower_whisker: 5, upper_whisker: 300, outlier_count: 2, iqr_is_zero: false, warnings: [], histogram: { bins: [], source_count: 118, sample_count: 118, sampled: false } }],
      categorical: [{ column: "region", count: 118, missing_count: 2, unique_count: 3, top_values: [{ value: "North", count: 64, value_truncated: false }], other_count: 54 }],
    });
    await act(async () => root.render(tree(Overview, { dataset: null, uploadedDataset, selectDataset() {} })));
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 50)); });
    assert.match(container.textContent, /Customer orders/);
    assert.match(container.textContent, /98\.5%/);
    assert.match(container.textContent, /amount/);
    assert.match(container.textContent, /North/);
    assert.doesNotMatch(container.textContent, /Total Revenue/);
  });
});

test("advanced profile visualizations expose API values, interactions and methodology", async () => {
  await harness(async ({ server, root, container }) => {
    const { default: ProfileVisualizations } = await server.ssrLoadModule("/src/app/components/ProfileVisualizations.tsx");
    const completeProfile = profile({
      row_count: 60000,
      column_count: 5,
      numeric: [
        { column: "amount", count: 60000, finite_count: 59980, non_finite_count: 5, missing_count: 15, min: 0, max: 100, mean: 42, median: 40, std: 12, q1: 30, q3: 50, iqr: 20, lower_fence: 0, upper_fence: 80, lower_whisker: 0, upper_whisker: 79, outlier_count: 8, iqr_is_zero: false, warnings: [], histogram: { bins: [{ lower_bound: 0, upper_bound: 50, count: 25000 }, { lower_bound: 50, upper_bound: 100, count: 25000 }], source_count: 59980, sample_count: 50000, sampled: true } },
        { column: "score", count: 10, finite_count: 10, non_finite_count: 0, missing_count: 0, min: 7, max: 7, mean: 7, median: 7, std: 0, q1: 7, q3: 7, iqr: 0, lower_fence: 7, upper_fence: 7, lower_whisker: 7, upper_whisker: 7, outlier_count: 0, iqr_is_zero: true, warnings: ["small_sample", "zero_iqr"], histogram: { bins: [{ lower_bound: 7, upper_bound: 7, count: 10 }], source_count: 10, sample_count: 10, sampled: false } },
      ],
      categorical: [{ column: "region", count: 95, missing_count: 5, unique_count: 14, top_values: [{ value: "North", count: 40, value_truncated: false }, { value: "A very long label…#abc123", count: 20, value_truncated: true }], other_count: 35 }],
      correlation: { method: "pearson", columns: ["amount", "score"], matrix: [[1, null], [null, null]], finite_pair_counts: [[59980, 2], [2, 10]], minimum_finite_pairs: 3, sampled: true, source_row_count: 60000, sample_row_count: 50000, excluded_columns: [{ column: "active", reason: "boolean" }, { column: "region", reason: "non_numeric" }], excluded_count: 2, columns_truncated: false, exclusions_truncated: false, correlation_does_not_imply_causation: true },
      temporal: [{ column: "created_at", granularity: "month", bucket_size: 1, points: [{ period: "2026-01", count: 30 }, { period: "2026-02", count: 25 }], source_count: 55, missing_count: 5, coarsened: true, truncated: false }],
    });
    await act(async () => root.render(React.createElement(ProfileVisualizations, { profile: completeProfile })));
    assert.match(container.textContent, /Advanced Data Insights/i);
    assert.match(container.textContent, /deterministic sample of 50[.,]000 values/i);
    assert.match(container.textContent, /Correlation does not imply causation/i);
    assert.match(container.textContent, /not an inferred business measure/i);
    assert.match(container.textContent, /Other categories/i);
    assert.ok(container.querySelector('[aria-label="amount and score: not calculable, 2 finite pairs"]'));
    const numericSelector = container.querySelector('label.sa-viz-selector select');
    await act(async () => { numericSelector.value = "score"; numericSelector.dispatchEvent(new window.Event("change", { bubbles: true })); });
    assert.match(container.textContent, /Fewer than 20 finite values/i);
    assert.match(container.textContent, /interquartile range is zero/i);
    assert.equal(container.querySelectorAll(".sa-profile-chart").length, 3);
  });
});

test("advanced profile visualizations explain insufficient profile data", async () => {
  await harness(async ({ server, root, container }) => {
    const { default: ProfileVisualizations } = await server.ssrLoadModule("/src/app/components/ProfileVisualizations.tsx");
    await act(async () => root.render(React.createElement(ProfileVisualizations, { profile: profile() })));
    assert.match(container.textContent, /No numeric columns are available/i);
    assert.match(container.textContent, /No categorical columns are available/i);
    assert.match(container.textContent, /eligible numeric column is required/i);
    assert.match(container.textContent, /No datetime column was detected/i);
    assert.match(container.textContent, /Profile API 3\.0/i);
  });
});

test("dataset selection hides the previous preview while the next request loads", async () => {
  await harness(async ({ server, root, container }) => {
    const { default: Datasets } = await server.ssrLoadModule("/src/app/pages/Datasets.tsx");
    const { datasetsApi } = await server.ssrLoadModule("/src/app/api/datasetsApi.ts");
    const items = [dataset("first"), dataset("second")].map((item) => ({ ...item, file_type: "csv", column_count: 1, created_at: "2026-11-12T10:00:00Z" }));
    let resolveNext;
    datasetsApi.list = async () => items;
    datasetsApi.preview = (id) => id === "first" ? Promise.resolve({ ...result(id, 111), total_rows: 1, columns: items[0].columns }) : new Promise((resolve) => { resolveNext = resolve; });
    datasetsApi.profile = async () => profile();
    await act(async () => root.render(tree(Datasets, { refreshUploadedDatasets: async () => {}, selectDataset() {} })));
    assert.match(container.textContent, /111/);
    const second = Array.from(container.querySelectorAll("button")).find((button) => button.textContent.startsWith("second"));
    await act(async () => second.click());
    assert.doesNotMatch(container.textContent, /111/);
    assert.match(container.textContent, /Profiling dataset/);
    await act(async () => resolveNext({ ...result("second", 999), total_rows: 1, columns: items[1].columns }));
    assert.match(container.textContent, /999/);
  });
});

test("explorer replaces a result with loading, error and successful retry states", async () => {
  await harness(async ({ server, root, container }) => {
    const { default: Explorer } = await server.ssrLoadModule("/src/app/pages/DataExplorer.tsx");
    const { datasetsApi } = await server.ssrLoadModule("/src/app/api/datasetsApi.ts");
    let rejectPending;
    let calls = 0;
    datasetsApi.query = async () => {
      calls += 1;
      if (calls === 2) return new Promise((_resolve, reject) => { rejectPending = reject; });
      return result("first", calls === 1 ? 98765 : 55);
    };
    const first = dataset("first");
    await act(async () => root.render(tree(Explorer, { uploadedDataset: first, uploadedDatasets: [first], selectDataset() {} })));
    assert.match(container.textContent, /98765/);
    const run = Array.from(container.querySelectorAll("button")).find((button) => button.textContent.includes("Run analysis"));
    await act(async () => run.click());
    assert.match(container.textContent, /Running the validated query/);
    assert.doesNotMatch(container.textContent, /98765/);
    await act(async () => rejectPending(new Error("Test network failure")));
    assert.match(container.querySelector('[role="alert"]').textContent, /Test network failure/);
    await act(async () => container.querySelector('[role="alert"] button').click());
    assert.match(container.textContent, /55/);
    assert.equal(container.querySelector('[role="alert"]'), null);
  });
});

test("sidebar navigation closes its dialog and restores the menu state and focus", async () => {
  await harness(async ({ server, root, container }) => {
    window.scrollTo = () => {};
    window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
    window.HTMLDialogElement.prototype.close = function () {
      if (this.open) { this.open = false; this.dispatchEvent(new window.Event("close")); }
    };
    const { default: Layout } = await server.ssrLoadModule("/src/app/components/AppLayout.tsx");
    const { AuthContext } = await server.ssrLoadModule("/src/app/auth/authContext.ts");
    const AuthenticatedLayout = () => React.createElement(AuthContext.Provider, { value: { user: { id: "test-user", email: "test@example.com" }, status: "ready", error: "", logout: async () => {}, accept() {}, retry() {} } }, React.createElement(Layout));
    const { datasetsApi } = await server.ssrLoadModule("/src/app/api/datasetsApi.ts");
    datasetsApi.list = async () => [];
    await act(async () => root.render(React.createElement(MemoryRouter, { initialEntries: ["/app"] },
      React.createElement(Routes, null, React.createElement(Route, { path: "/app", element: React.createElement(AuthenticatedLayout) },
        React.createElement(Route, { index: true, element: React.createElement("p", null, "Overview test") }),
        React.createElement(Route, { path: "assistant", element: React.createElement("p", null, "Assistant test") }))))));
    const menu = container.querySelector('[aria-label="Open sidebar"]');
    await act(async () => menu.click());
    assert.equal(menu.getAttribute("aria-expanded"), "true");
    assert.equal(container.querySelector("dialog").open, true);
    await act(async () => container.querySelector('dialog a[href="/app/assistant"]').click());
    assert.equal(container.querySelector("dialog").open, false);
    assert.equal(menu.getAttribute("aria-expanded"), "false");
    assert.equal(document.activeElement, menu);
    assert.match(container.textContent, /Assistant test/);
  });
});
