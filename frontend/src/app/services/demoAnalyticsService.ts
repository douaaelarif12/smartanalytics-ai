import { demoDatasets } from "../data/salesDemo.ts";
import { calculateOverview } from "./analytics.ts";
import type { AnalyticsService } from "../types.ts";

// Async adapter contract only. There are deliberately no HTTP requests or fake latency.
export const demoAnalyticsService: AnalyticsService = {
  async listDatasets() {
    return demoDatasets;
  },
  async getOverview(datasetId, months) {
    const dataset = demoDatasets.find((item) => item.id === datasetId);
    if (!dataset)
      throw new Error(
        "This demo dataset is unavailable. Please choose another dataset.",
      );
    return calculateOverview(dataset, months);
  },
};
