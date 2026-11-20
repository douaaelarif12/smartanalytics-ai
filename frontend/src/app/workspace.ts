import { useOutletContext } from "react-router-dom";
import type { UploadedDataset } from "./api/types";
import type { SalesDataset } from "./types";

export interface WorkspaceContext {
  dataset: SalesDataset | null;
  uploadedDataset: UploadedDataset | null;
  uploadedDatasets: readonly UploadedDataset[];
  refreshUploadedDatasets: () => Promise<void>;
  openUpload: () => void;
  selectDataset: (id: string) => void;
}
export const useWorkspace = () => useOutletContext<WorkspaceContext>();

