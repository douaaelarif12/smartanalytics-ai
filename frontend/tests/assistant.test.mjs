import { test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("assistant renders real results, clarification and escaped content", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  });
  try {
    const { AssistantAnswer } = await server.ssrLoadModule(
      "/src/app/pages/Assistant.tsx",
    );
    const response = {
      status: "answer",
      answer: "Computed total is 35.",
      warnings: ["Subset only"],
      chart: null,
      query: {
        aggregations: [{ function: "sum", column: "amount", alias: "total" }],
      },
      results: { total_rows: 1, columns: ["total"], rows: [{ total: 35 }] },
    };
    const html = renderToStaticMarkup(
      React.createElement(AssistantAnswer, { response }),
    );
    assert.match(html, /Computed total is 35/);
    assert.match(html, /<td>35<\/td>/);
    assert.match(html, /Analytical details/);
    assert.match(html, /Subset only/);
    const clarification = renderToStaticMarkup(
      React.createElement(AssistantAnswer, {
        response: {
          status: "clarification",
          answer: "Which <script> column?",
          warnings: [],
          query: null,
          results: null,
          chart: null,
        },
      }),
    );
    assert.match(clarification, /Clarification needed/);
    assert.doesNotMatch(clarification, /<script>/);
    assert.doesNotMatch(clarification, /Computed results/);
  } finally {
    await server.close();
  }
});

test("assistant API posts only question and propagates structured errors", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  });
  const original = globalThis.fetch;
  try {
    const { datasetsApi } = await server.ssrLoadModule(
      "/src/app/api/datasetsApi.ts",
    );
    const { setCsrfToken } = await server.ssrLoadModule("/src/app/api/http.ts");
    setCsrfToken("test-csrf");
    globalThis.fetch = async (url, init) => {
      assert.match(url, /\/api\/datasets\/abc\/ai\/ask$/);
      assert.deepEqual(JSON.parse(init.body), { question: "Count rows" });
      return new Response(
        JSON.stringify({
          error: { code: "ai_rate_limited", message: "Retry later" },
        }),
        { status: 429 },
      );
    };
    await assert.rejects(datasetsApi.ask("abc", "Count rows"), /Retry later/);
  } finally {
    globalThis.fetch = original;
    await server.close();
  }
});
