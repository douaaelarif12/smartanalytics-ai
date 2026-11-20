import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("nginx keeps security headers on the SPA entry point", async () => {
  const source = await readFile(new URL("../nginx.conf", import.meta.url), "utf8");
  const indexLocation = source.match(/location = \/index\.html\s*\{([\s\S]*?)\}/)?.[1] ?? "";

  assert.match(indexLocation, /add_header Cache-Control no-store always;/);
  assert.match(indexLocation, /add_header X-Content-Type-Options nosniff always;/);
  assert.match(indexLocation, /add_header X-Frame-Options DENY always;/);
  assert.match(indexLocation, /add_header Referrer-Policy no-referrer always;/);
});
