import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { CheckCircle2, ChevronLeft, ChevronRight, Database, FileSpreadsheet, LoaderCircle, Trash2, UploadCloud } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { datasetsApi, validateDatasetFile } from "../api/datasetsApi";
import type { DatasetPreviewResponse, DatasetProfileResponse, UploadedDataset } from "../api/types";
import DatasetProfileInsights, { ProfileSummary } from "../components/DatasetProfileInsights";
import { datasetPageReducer } from "../datasetsState";
import { displayDate } from "../format";
import { useWorkspace } from "../workspace";

const PAGE_SIZE = 25;
const messageOf = (error: unknown) => error instanceof Error ? error.message : "An unexpected dataset error occurred.";

export function DatasetList({ items, selectedId, onSelect }: { items: readonly UploadedDataset[]; selectedId: string | null; onSelect: (id: string) => void }) {
  if (!items.length) return <div className="sa-dataset-empty"><Database size={24} /><strong>No uploaded datasets yet</strong><p>Upload a CSV or Excel workbook to create your first profile.</p></div>;
  return <div className="sa-uploaded-list">{items.map((item) => <button type="button" key={item.id} className={`sa-uploaded-card${selectedId === item.id ? " is-selected" : ""}`} onClick={() => onSelect(item.id)}>
    <span className="sa-file-icon"><FileSpreadsheet size={19} /></span><span><strong>{item.name}</strong><small>{item.row_count.toLocaleString()} rows · {item.column_count} columns · {item.file_type.toUpperCase()}</small><small>Imported {displayDate(item.created_at)}</small></span>
  </button>)}</div>;
}

export default function Datasets() {
  const { refreshUploadedDatasets, selectDataset } = useWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("dataset");
  const [state, dispatch] = useReducer(datasetPageReducer, { status: "loading", items: [] });
  const [preview, setPreview] = useState<DatasetPreviewResponse | null>(null);
  const [profile, setProfile] = useState<DatasetProfileResponse | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [profileError, setProfileError] = useState("");
  const [settledPreviewKey, setSettledPreviewKey] = useState("");
  const [settledProfileId, setSettledProfileId] = useState("");
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [offset, setOffset] = useState(0);
  const detailKey = `${selectedId}:${offset}`;
  const detailLoading = !!selectedId && (settledPreviewKey !== detailKey || settledProfileId !== selectedId);
  const detailError = previewError || profileError;
  const [dragging, setDragging] = useState(false);
  const [upload, setUpload] = useState<{ status: "idle" | "uploading" | "success" | "error"; progress: number; message: string }>({ status: "idle", progress: 0, message: "" });
  const fileInput = useRef<HTMLInputElement>(null);
  const uploadInFlight = useRef(false);

  const loadDatasets = useCallback(async () => {
    dispatch({ type: "loading" });
    try {
      const items = await datasetsApi.list();
      dispatch({ type: "loaded", items });
      if (!selectedId && items[0]) setSearchParams({ dataset: items[0].id }, { replace: true });
    } catch (error) { dispatch({ type: "failed", message: messageOf(error) }); }
  }, [selectedId, setSearchParams]);

  useEffect(() => { void loadDatasets(); }, [loadDatasets]);
  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    datasetsApi.preview(selectedId, offset, PAGE_SIZE)
      .then((nextPreview) => { if (active) { setPreview(nextPreview); setPreviewError(""); setSettledPreviewKey(detailKey); } })
      .catch((error) => { if (active) { setPreviewError(messageOf(error)); setSettledPreviewKey(detailKey); } });
    return () => { active = false; };
  }, [selectedId, offset, detailKey, detailAttempt]);
  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    datasetsApi.profile(selectedId)
      .then((nextProfile) => { if (active) { setProfile(nextProfile); setProfileError(""); setSettledProfileId(selectedId); } })
      .catch((error) => { if (active) { setProfileError(messageOf(error)); setSettledProfileId(selectedId); } });
    return () => { active = false; };
  }, [selectedId, detailAttempt]);
  useEffect(() => {
    if (searchParams.get("upload") === "1") {
      setSearchParams({}, { replace: true });
      fileInput.current?.click();
    }
  }, [searchParams, setSearchParams]);

  async function processFile(file?: File) {
    if (!file || uploadInFlight.current) return;
    const validation = validateDatasetFile(file);
    if (validation) { setUpload({ status: "error", progress: 0, message: validation }); return; }
    uploadInFlight.current = true;
    setUpload({ status: "uploading", progress: 0, message: `Processing ${file.name}…` });
    try {
      const item = await datasetsApi.upload(file, (progress) => setUpload((current) => ({ ...current, progress })));
      dispatch({ type: "added", item });
      setUpload({ status: "success", progress: 100, message: `${item.name} was profiled successfully.` });
      setOffset(0); setSearchParams({ dataset: item.id }, { replace: true });
      selectDataset(`upload:${item.id}`);
      await refreshUploadedDatasets();
    } catch (error) { setUpload({ status: "error", progress: 0, message: messageOf(error) }); }
    finally { uploadInFlight.current = false; if (fileInput.current) fileInput.current.value = ""; }
  }

  async function deleteSelected() {
    const item = state.items.find((candidate) => candidate.id === selectedId);
    if (!item || !window.confirm(`Delete “${item.name}”? This permanently removes the local file and profile.`)) return;
    try {
      await datasetsApi.delete(item.id);
      dispatch({ type: "removed", id: item.id });
      const next = state.items.find((candidate) => candidate.id !== item.id);
      setOffset(0); setPreview(null); setProfile(null);
      setSearchParams(next ? { dataset: next.id } : {}, { replace: true });
      selectDataset("demo:northstar-sales");
      await refreshUploadedDatasets();
    } catch (error) { setPreviewError(messageOf(error)); }
  }

  return <>
    <section className="sa-datasets-heading"><div><span className="sa-overline">YOUR DATA LIBRARY</span><h1>Bring your data into focus.</h1><p>Upload a CSV or Excel file. The local service detects its schema, profiles quality and prepares a safe preview.</p></div></section>
    <section className="sa-upload-zone" data-dragging={dragging} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={(event) => { if (event.currentTarget === event.target) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); void processFile(event.dataTransfer.files[0]); }}>
      <input ref={fileInput} className="sr-only" type="file" accept=".csv,.xlsx" aria-label="Choose a CSV or Excel dataset" onChange={(event) => void processFile(event.target.files?.[0])} />
      {upload.status === "uploading" ? <><LoaderCircle className="sa-loader" /><strong>{upload.message}</strong><div className="sa-upload-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={upload.progress}><span style={{ width: `${upload.progress}%` }} /></div><small>{upload.progress}% uploaded · profiling begins immediately</small></> : <><span className="sa-upload-icon"><UploadCloud size={27} /></span><strong>Drop a dataset here</strong><p>CSV or XLSX · up to 20 MB</p><button className="sa-btn" type="button" onClick={() => fileInput.current?.click()}>Choose a file</button></>}
    </section>
    {upload.status === "success" && <div className="sa-inline-status is-success" role="status"><CheckCircle2 size={18} />{upload.message}</div>}
    {upload.status === "error" && <div className="sa-inline-status is-error" role="alert">{upload.message}</div>}
    <div className="sa-datasets-grid">
      <section className="sa-card sa-library-panel"><div className="sa-card-heading"><div><span className="sa-overline">UPLOADED</span><h2>Datasets</h2></div><span className="sa-badge">{state.items.length} LOCAL</span></div>
        {state.status === "loading" && !state.items.length ? <div className="sa-mini-loading"><LoaderCircle className="sa-loader" /> Loading datasets…</div> : state.status === "error" ? <div className="sa-inline-status is-error" role="alert"><span>{state.message}</span><button type="button" onClick={() => void loadDatasets()}>Retry</button></div> : <DatasetList items={state.items} selectedId={selectedId} onSelect={(id) => { setOffset(0); setSearchParams({ dataset: id }); }} />}
      </section>
      <section className="sa-card sa-preview-panel">
        {!selectedId ? <div className="sa-dataset-empty"><FileSpreadsheet size={25} /><strong>Select a dataset to preview</strong><p>Its columns, rows and quality profile will appear here.</p></div> : detailLoading ? <div className="sa-mini-loading"><LoaderCircle className="sa-loader" /> Profiling dataset…</div> : detailError ? <div className="sa-inline-status is-error" role="alert"><span>{detailError}</span><button type="button" onClick={() => setDetailAttempt((value) => value + 1)}>Retry</button></div> : preview && profile ? <>
          <div className="sa-card-heading"><div><span className="sa-overline">PROFILE & PREVIEW</span><h2>{state.items.find((item) => item.id === selectedId)?.name ?? "Dataset"}</h2></div><button className="sa-delete-button" type="button" onClick={() => void deleteSelected()}><Trash2 size={16} /> Delete</button></div>
          <ProfileSummary profile={profile} />
          <div className="sa-column-badges" aria-label="Detected column types">{preview.columns.map((column) => <span key={column.name}><strong>{column.name}</strong><small>{column.type}</small></span>)}</div>
          <DatasetProfileInsights profile={profile} />
          {preview.rows.length ? <div className="sa-table-scroll"><table><thead><tr>{preview.columns.map((column) => <th key={column.name}>{column.name}</th>)}</tr></thead><tbody>{preview.rows.map((row, index) => <tr key={offset + index}>{preview.columns.map((column) => <td key={column.name}>{row[column.name] == null ? <span className="sa-null">null</span> : String(row[column.name])}</td>)}</tr>)}</tbody></table></div> : <div className="sa-dataset-empty"><strong>No data rows</strong><p>The file contains headers but no rows to preview.</p></div>}
          <div className="sa-table-pagination"><span>{preview.total_rows ? `${preview.offset + 1}–${Math.min(preview.offset + preview.rows.length, preview.total_rows)} of ${preview.total_rows.toLocaleString()}` : "0 rows"}</span><div><button type="button" aria-label="Previous preview page" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}><ChevronLeft size={17} /></button><button type="button" aria-label="Next preview page" disabled={offset + preview.rows.length >= preview.total_rows} onClick={() => setOffset(offset + PAGE_SIZE)}><ChevronRight size={17} /></button></div></div>
        </> : null}
      </section>
    </div>
  </>;
}
