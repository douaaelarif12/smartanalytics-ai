export type SalesCategory =
  "Technology" | "Furniture" | "Office supplies" | "Accessories";

/** One row per order; money is stored in integer USD cents. */
export interface SalesOrder {
  orderId: string;
  date: string;
  category: SalesCategory;
  product: string;
  quantity: number;
  unitPriceCents: number;
  discountPercent: number;
  region: string | null;
}
export interface SalesDataset {
  id: string;
  name: string;
  description: string;
  currency: "USD";
  referenceDate: string;
  importedAt: string | null;
  columns: readonly (keyof SalesOrder)[];
  rows: readonly SalesOrder[];
}
export type PeriodMonths = 1 | 3 | 6;
export interface MetricComparison {
  revenue: number | null;
  orders: number | null;
  averageOrderValue: number | null;
}
export interface AnalyticsSnapshot {
  startDate: string;
  endDate: string;
  previousStartDate: string;
  previousEndDate: string;
  rows: readonly SalesOrder[];
  revenue: number;
  orders: number;
  averageOrderValue: number | null;
  growth: number | null;
  comparison: MetricComparison;
  trend: { date: string; label: string; revenue: number }[];
  categories: {
    name: SalesCategory;
    revenue: number;
    orders: number;
    share: number;
  }[];
}
export interface DatasetQuality {
  completeness: number | null;
  missingCells: number;
  duplicateOrderIds: number;
}
/** Replace this adapter with a FastAPI client later, without coupling UI to fetch. */
export interface AnalyticsService {
  listDatasets(): Promise<readonly SalesDataset[]>;
  getOverview(
    datasetId: string,
    months: PeriodMonths,
  ): Promise<AnalyticsSnapshot>;
}
