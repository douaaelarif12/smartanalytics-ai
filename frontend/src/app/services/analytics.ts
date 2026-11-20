import type {
  AnalyticsSnapshot,
  DatasetQuality,
  PeriodMonths,
  SalesDataset,
  SalesOrder,
} from "../types.ts";

export const orderRevenueCents = (row: SalesOrder): number =>
  Math.round(
    (row.quantity * row.unitPriceCents * (100 - row.discountPercent)) / 100,
  );

export function percentageChange(
  current: number,
  previous: number,
): number | null {
  return previous === 0 ? null : ((current - previous) / previous) * 100;
}

const iso = (date: Date) => date.toISOString().slice(0, 10);
const sumCents = (rows: readonly SalesOrder[]) =>
  rows.reduce((sum, row) => sum + orderRevenueCents(row), 0);

/** Complete calendar periods anchored to dataset metadata, independent of today's date/timezone. */
export function calculateOverview(
  dataset: SalesDataset,
  months: PeriodMonths,
): AnalyticsSnapshot {
  const end = new Date(`${dataset.referenceDate}T00:00:00Z`);
  const start = new Date(
    Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - months + 1, 1),
  );
  const previousStart = new Date(
    Date.UTC(start.getUTCFullYear(), start.getUTCMonth() - months, 1),
  );
  const previousEnd = new Date(start.getTime() - 86400000);
  const startDate = iso(start),
    endDate = iso(end);
  const previousStartDate = iso(previousStart),
    previousEndDate = iso(previousEnd);
  const rows = dataset.rows.filter(
    (row) => row.date >= startDate && row.date <= endDate,
  );
  const previous = dataset.rows.filter(
    (row) => row.date >= previousStartDate && row.date <= previousEndDate,
  );
  const revenue = sumCents(rows) / 100;
  const previousRevenue = sumCents(previous) / 100;
  const averageOrderValue = rows.length ? revenue / rows.length : null;
  const previousAov = previous.length ? previousRevenue / previous.length : 0;
  const growth = percentageChange(revenue, previousRevenue);

  // Include zero-revenue days/months so gaps do not distort the trend.
  const trend: AnalyticsSnapshot["trend"] = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    const date = months === 1 ? iso(cursor) : iso(cursor).slice(0, 7);
    const matching = rows.filter((row) =>
      months === 1 ? row.date === date : row.date.startsWith(date),
    );
    trend.push({
      date,
      label: new Intl.DateTimeFormat("en-US", {
        timeZone: "UTC",
        ...(months === 1
          ? { month: "short", day: "numeric" }
          : { month: "short" }),
      }).format(cursor),
      revenue: sumCents(matching) / 100,
    });
    if (months === 1) cursor.setUTCDate(cursor.getUTCDate() + 1);
    else cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  const categories: AnalyticsSnapshot["categories"] = [
    ...new Set(rows.map((row) => row.category)),
  ]
    .map((name) => {
      const matching = rows.filter((row) => row.category === name);
      const categoryRevenue = sumCents(matching) / 100;
      return {
        name,
        revenue: categoryRevenue,
        orders: matching.length,
        share: revenue ? (categoryRevenue / revenue) * 100 : 0,
      };
    })
    .sort((a, b) => b.revenue - a.revenue);
  return {
    startDate,
    endDate,
    previousStartDate,
    previousEndDate,
    rows,
    revenue,
    orders: rows.length,
    averageOrderValue,
    growth,
    comparison: {
      revenue: growth,
      orders: percentageChange(rows.length, previous.length),
      averageOrderValue:
        averageOrderValue === null
          ? null
          : percentageChange(averageOrderValue, previousAov),
    },
    trend,
    categories,
  };
}

export function inspectQuality(dataset: SalesDataset): DatasetQuality {
  const totalCells = dataset.rows.length * dataset.columns.length;
  const missingCells = dataset.rows.reduce(
    (sum, row) =>
      sum +
      dataset.columns.filter(
        (column) =>
          row[column] === null ||
          row[column] === undefined ||
          row[column] === "",
      ).length,
    0,
  );
  return {
    completeness: totalCells
      ? ((totalCells - missingCells) / totalCells) * 100
      : null,
    missingCells,
    duplicateOrderIds:
      dataset.rows.length -
      new Set(dataset.rows.map((row) => row.orderId)).size,
  };
}
