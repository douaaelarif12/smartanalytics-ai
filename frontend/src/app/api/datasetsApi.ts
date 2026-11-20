import type {
  ApiErrorBody,
  AssistantResponse,
  DatasetPreviewResponse,
  DatasetProfileResponse,
  UploadedDataset,
  AnalyticsQuerySpec,
  AnalyticsResult,
} from "./types";

import {
  API_BASE_URL,
  DatasetApiError,
  ensureCsrf,
  request,
  sessionExpired,
} from "./http.ts";
export { DatasetApiError } from "./http.ts";

export const datasetsApi = {
  ask(id: string, question: string, signal?: AbortSignal) {
    return request<AssistantResponse>(
      `/api/datasets/${encodeURIComponent(id)}/ai/ask`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal,
      },
    );
  },
  async list(): Promise<UploadedDataset[]> {
    const response = await request<{ items: UploadedDataset[] }>(
      "/api/datasets",
    );
    return response.items;
  },
  get(id: string) {
    return request<UploadedDataset>(`/api/datasets/${encodeURIComponent(id)}`);
  },
  preview(id: string, offset = 0, limit = 25) {
    return request<DatasetPreviewResponse>(
      `/api/datasets/${encodeURIComponent(id)}/preview?offset=${offset}&limit=${limit}`,
    );
  },
  profile(id: string) {
    return request<DatasetProfileResponse>(
      `/api/datasets/${encodeURIComponent(id)}/profile`,
    );
  },
  query(id: string, specification: AnalyticsQuerySpec) {
    return request<AnalyticsResult>(
      `/api/datasets/${encodeURIComponent(id)}/query`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(specification),
      },
    );
  },
  export(id: string, specification: AnalyticsQuerySpec, signal?: AbortSignal) {
    return request<Blob>(
      `/api/datasets/${encodeURIComponent(id)}/export`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(specification),
        signal,
      },
      "blob",
    );
  },
  delete(id: string) {
    return request<void>(`/api/datasets/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  },
  upload(
    file: File,
    onProgress: (progress: number) => void,
  ): Promise<UploadedDataset> {
    return ensureCsrf().then(
      (csrf) =>
        new Promise<UploadedDataset>((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.open("POST", `${API_BASE_URL}/api/datasets`);
          xhr.responseType = "json";
          xhr.withCredentials = true;
          xhr.timeout = 90_000;
          xhr.addEventListener("timeout", () =>
            reject(
              new DatasetApiError(
                "The upload timed out. Check your dataset list before retrying.",
              ),
            ),
          );
          xhr.setRequestHeader("X-CSRF-Token", csrf);
          xhr.upload.addEventListener("progress", (event) => {
            if (event.lengthComputable)
              onProgress(Math.round((event.loaded / event.total) * 100));
          });
          xhr.addEventListener("load", () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              onProgress(100);
              resolve(xhr.response as UploadedDataset);
              return;
            }
            if (xhr.status === 401) sessionExpired();
            const body = (xhr.response || {}) as ApiErrorBody;
            reject(
              new DatasetApiError(
                body.error?.message || `The upload failed (${xhr.status}).`,
                xhr.status,
                body.error?.code,
              ),
            );
          });
          xhr.addEventListener("error", () =>
            reject(
              new DatasetApiError(
                "The dataset service is unavailable. Start the FastAPI backend and try again.",
              ),
            ),
          );
          xhr.addEventListener("abort", () =>
            reject(new DatasetApiError("The upload was cancelled.")),
          );
          const form = new FormData();
          form.append("file", file);
          xhr.send(form);
        }),
    );
  },
};

export function validateDatasetFile(
  file: Pick<File, "name" | "size">,
): string | null {
  const extension = file.name.toLowerCase().split(".").pop();
  if (extension !== "csv" && extension !== "xlsx")
    return "Choose a .csv or .xlsx file.";
  if (file.size === 0) return "The selected file is empty.";
  return null;
}
