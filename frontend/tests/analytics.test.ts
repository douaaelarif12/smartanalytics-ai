import { test } from "node:test";
import assert from "node:assert/strict";
import {
  calculateOverview,
  inspectQuality,
  orderRevenueCents,
  percentageChange,
} from "../src/app/services/analytics.ts";
import { salesDemo, emptyDemo } from "../src/app/data/salesDemo.ts";
import { demoAnalyticsService } from "../src/app/services/demoAnalyticsService.ts";
import type { SalesDataset, SalesOrder } from "../src/app/types.ts";

const order = (
  orderId: string,
  date: string,
  price: number,
  quantity = 1,
  discount = 0,
): SalesOrder => ({
  orderId,
  date,
  category: "Technology",
  product: "Example",
  quantity,
  unitPriceCents: price,
  discountPercent: discount,
  region: "Europe",
});
const fixture: SalesDataset = {
  ...salesDemo,
  rows: [
    order("a", "2026-05-31", 10000),
    order("b", "2026-06-01", 10000, 2, 10),
    order("c", "2026-06-30", 5000),
    order("d", "2026-07-01", 90000),
  ],
};

test("KPI fixture: correct net revenue, order count, AOV, growth and inclusive month boundaries", () => {
  const result = calculateOverview(fixture, 1);
  assert.equal(result.revenue, 230);
  assert.equal(result.orders, 2);
  assert.equal(result.averageOrderValue, 115);
  assert.equal(result.growth, 130);
  assert.equal(result.comparison.orders, 100);
  assert.equal(result.comparison.averageOrderValue, 15);
  assert.equal(result.startDate, "2026-06-01");
  assert.equal(result.previousStartDate, "2026-05-01");
  assert.equal(result.previousEndDate, "2026-05-31");
  assert.equal(result.trend.length, 30);
  assert.equal(result.trend[0].revenue, 180);
  assert.equal(result.trend[29].revenue, 50);
});
test("order discounts use integer cents and round once per order", () => {
  assert.equal(orderRevenueCents(order("a", "2026-06-01", 999, 3, 10)), 2697);
});
test("zero baseline is unavailable rather than Infinity or a fabricated percentage", () => {
  assert.equal(percentageChange(100, 0), null);
  assert.equal(percentageChange(0, 100), -100);
  assert.equal(
    calculateOverview({ ...fixture, rows: [order("a", "2026-06-15", 100)] }, 1)
      .growth,
    null,
  );
});
test("empty datasets have safe metrics and an unavailable quality score", () => {
  const result = calculateOverview(emptyDemo, 6);
  assert.equal(result.revenue, 0);
  assert.equal(result.orders, 0);
  assert.equal(result.averageOrderValue, null);
  assert.equal(result.growth, null);
  assert.deepEqual(result.categories, []);
  assert.equal(inspectQuality(emptyDemo).completeness, null);
});
test("all periods reconcile: rows, trend, category totals and percentages share one source", () => {
  for (const months of [1, 3, 6] as const) {
    const result = calculateOverview(salesDemo, months);
    const cents = result.rows.reduce(
      (sum, row) => sum + orderRevenueCents(row),
      0,
    );
    assert.equal(result.revenue, cents / 100);
    assert.ok(
      Math.abs(
        result.trend.reduce((sum, row) => sum + row.revenue, 0) -
          result.revenue,
      ) < 0.001,
    );
    assert.ok(
      Math.abs(
        result.categories.reduce((sum, row) => sum + row.revenue, 0) -
          result.revenue,
      ) < 0.001,
    );
    assert.equal(
      result.categories.reduce((sum, row) => sum + row.orders, 0),
      result.orders,
    );
    assert.ok(
      Math.abs(
        result.categories.reduce((sum, row) => sum + row.share, 0) - 100,
      ) < 0.001,
    );
  }
});
test("period changes recalculate the sample KPIs and trend length", () => {
  const one = calculateOverview(salesDemo, 1),
    three = calculateOverview(salesDemo, 3),
    six = calculateOverview(salesDemo, 6);
  assert.ok(one.orders < three.orders && three.orders < six.orders);
  assert.ok(one.revenue < three.revenue && three.revenue < six.revenue);
  assert.equal(three.trend.length, 3);
  assert.equal(six.trend.length, 6);
  assert.equal(six.previousStartDate, "2025-07-01");
  assert.equal(six.previousEndDate, "2025-12-31");
});
test("quality checks derive missing cells and duplicate order IDs", () => {
  const a = { ...order("same", "2026-06-01", 100), region: null };
  const quality = inspectQuality({ ...salesDemo, rows: [a, a] });
  assert.equal(quality.missingCells, 2);
  assert.equal(quality.duplicateOrderIds, 1);
  assert.equal(quality.completeness, 87.5);
});
test("demo adapter lists datasets, resolves snapshots and rejects unknown datasets", async () => {
  const datasets = await demoAnalyticsService.listDatasets();
  assert.equal(datasets.length, 2);
  assert.deepEqual(
    await demoAnalyticsService.getOverview(salesDemo.id, 3),
    calculateOverview(salesDemo, 3),
  );
  await assert.rejects(
    demoAnalyticsService.getOverview("missing", 3),
    /unavailable/,
  );
});
