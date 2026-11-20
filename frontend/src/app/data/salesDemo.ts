import type { SalesDataset, SalesOrder } from "../types.ts";

const catalog = [
  { category: "Technology", product: "Wireless monitor", price: 24900 },
  { category: "Furniture", product: "Ergonomic chair", price: 18900 },
  { category: "Office supplies", product: "Desk essentials kit", price: 3900 },
  { category: "Accessories", product: "Laptop sleeve", price: 4900 },
] as const;
const columns = [
  "orderId",
  "date",
  "category",
  "product",
  "quantity",
  "unitPriceCents",
  "discountPercent",
  "region",
] as const;

// Deterministic, fictional order history: Jul 2025–Jun 2026. No random or live data.
const rows: SalesOrder[] = Array.from({ length: 12 }, (_, monthIndex) => {
  const date = new Date(Date.UTC(2025, 6 + monthIndex, 1));
  return Array.from({ length: 28 + monthIndex * 4 }, (_, index) => {
    const item = catalog[(index * 3 + monthIndex) % catalog.length];
    const day = String(1 + ((index * 11 + monthIndex * 3) % 28)).padStart(
      2,
      "0",
    );
    return {
      orderId: `NS-${String(monthIndex + 1).padStart(2, "0")}-${String(index + 1).padStart(3, "0")}`,
      date: `${date.toISOString().slice(0, 7)}-${day}`,
      category: item.category,
      product: item.product,
      quantity: 1 + ((index + monthIndex) % 4),
      unitPriceCents: item.price,
      discountPercent: index % 6 === 0 ? 10 : 0,
      region:
        index % 23 === 0
          ? null
          : ["North America", "Europe", "Asia Pacific"][index % 3],
    };
  });
})
  .flat()
  .sort(
    (a, b) =>
      a.date.localeCompare(b.date) || a.orderId.localeCompare(b.orderId),
  );

export const salesDemo: SalesDataset = {
  id: "northstar-sales",
  name: "Northstar Sales",
  description: "Fictional retail orders · Jul 2025–Jun 2026",
  currency: "USD",
  referenceDate: "2026-06-30",
  importedAt: "2026-07-01T09:00:00Z", // Fictional import metadata, not a real upload.
  columns,
  rows,
};
export const emptyDemo: SalesDataset = {
  ...salesDemo,
  id: "empty-sample",
  name: "Empty sample",
  description: "An empty dataset to explore the initial state",
  importedAt: null,
  rows: [],
};
export const demoDatasets: readonly SalesDataset[] = [salesDemo, emptyDemo];
