import type { UploadedDataset } from "./api/types";

export type DatasetPageState =
  | { status: "loading"; items: UploadedDataset[] }
  | { status: "ready"; items: UploadedDataset[] }
  | { status: "error"; items: UploadedDataset[]; message: string };

export type DatasetPageAction =
  | { type: "loading" }
  | { type: "loaded"; items: UploadedDataset[] }
  | { type: "failed"; message: string }
  | { type: "added"; item: UploadedDataset }
  | { type: "removed"; id: string };

export function datasetPageReducer(state: DatasetPageState, action: DatasetPageAction): DatasetPageState {
  switch (action.type) {
    case "loading":
      return { status: "loading", items: state.items };
    case "loaded":
      return { status: "ready", items: action.items };
    case "failed":
      return { status: "error", items: state.items, message: action.message };
    case "added":
      return { status: "ready", items: [action.item, ...state.items.filter((item) => item.id !== action.item.id)] };
    case "removed":
      return { status: "ready", items: state.items.filter((item) => item.id !== action.id) };
  }
}

