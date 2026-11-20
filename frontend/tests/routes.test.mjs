import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "vite";
import { matchRoutes } from "react-router-dom";

test("actual route configuration preserves landing and resolves overview, planned pages and unknown paths", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  });
  try {
    const { routes } = await server.ssrLoadModule("/src/routes.tsx");
    assert.equal(matchRoutes(routes, "/").at(-1).route.path, "/");
    assert.equal(matchRoutes(routes, "/app").at(-1).route.index, true);
    assert.equal(matchRoutes(routes, "/app/").at(-1).route.index, true);
    for (const page of [
      "datasets",
      "explorer",
      "dashboards",
      "assistant",
      "settings",
    ]) {
      assert.equal(matchRoutes(routes, `/app/${page}`).at(-1).route.path, page);
    }
    assert.equal(matchRoutes(routes, "/app/missing").at(-1).route.path, "*");
    assert.equal(matchRoutes(routes, "/missing").at(-1).route.path, "*");
    const landing = await readFile(
      new URL("../src/Landing.tsx", import.meta.url),
      "utf8",
    );
    assert.match(landing, /<LinkButton href="\/app">\s*Start Analyzing/);
  } finally {
    await server.close();
  }
});
