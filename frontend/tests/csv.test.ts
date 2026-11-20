import { test } from "node:test";
import assert from "node:assert/strict";
import { escapeCsvCell } from "../src/app/csv.ts";

test("CSV exports quote data and neutralize spreadsheet formulas in imported text", () => {
  assert.equal(escapeCsvCell('=HYPERLINK("https://invalid.example")'), '"\'=HYPERLINK(""https://invalid.example"")"');
  assert.equal(escapeCsvCell("  @SUM(A1)"), '"\'  @SUM(A1)"');
  assert.equal(escapeCsvCell(-42), '"-42"');
  assert.equal(escapeCsvCell(null), '""');
  assert.equal(escapeCsvCell('a,"b"\nc'), '"a,""b""\nc"');
});
