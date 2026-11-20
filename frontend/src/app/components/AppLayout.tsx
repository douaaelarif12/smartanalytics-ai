import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowUpRight, BarChart3, Database, Menu, ShieldCheck, X } from "lucide-react";
import { appNavigation } from "../navigation";
import { demoAnalyticsService } from "../services/demoAnalyticsService";
import { datasetsApi } from "../api/datasetsApi";
import type { UploadedDataset } from "../api/types";
import type { SalesDataset } from "../types";
import AccountMenu from "../auth/AccountMenu";
import { ErrorState, LoadingState } from "./States";
import type { WorkspaceContext } from "../workspace";
import "../dashboard.css";

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<readonly SalesDataset[]>([]);
  const [uploadedDatasets, setUploadedDatasets] = useState<readonly UploadedDataset[]>([]);
  const [datasetId, setDatasetId] = useState("demo:northstar-sales");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [uploadedError, setUploadedError] = useState("");
  const mobileNav = useRef<HTMLDialogElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const [navOpenPath, setNavOpenPath] = useState<string | null>(null);
  const navOpen = navOpenPath === location.pathname;
  const page = appNavigation.find((item) => item.path === location.pathname.replace(/\/$/, ""));
  const dataset = datasetId.startsWith("demo:") ? datasets.find((item) => `demo:${item.id}` === datasetId) ?? null : null;
  const uploadedDataset = datasetId.startsWith("upload:") ? uploadedDatasets.find((item) => `upload:${item.id}` === datasetId) ?? null : null;

  async function refreshUploadedDatasets() {
    return datasetsApi.list().then((items) => {
      setUploadedDatasets(items); setUploadedError("");
      setDatasetId((current) => current.startsWith("upload:") && !items.some((item) => `upload:${item.id}` === current) ? "demo:northstar-sales" : current);
    }).catch(() => {
      setUploadedError("Uploaded datasets could not be refreshed. Check the local API and retry.");
    });
  }

  useEffect(() => {
    let active = true;
    demoAnalyticsService.listDatasets().then((result) => { if (active) setDatasets(result); }).catch(() => { if (active) setError("The local sample could not be loaded."); });
    return () => { active = false; };
  }, [attempt]);
  useEffect(() => { void refreshUploadedDatasets(); }, []);
  useEffect(() => {
    document.title = `${page?.title ?? "Page not found"} — SmartAnalytics AI`;
    mobileNav.current?.close();
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname, page?.title]);

  function navigation(mobile = false) {
    return <>
      <Link to="/" className="sa-brand" aria-label="SmartAnalytics AI landing page"><span className="brand-mark"><BarChart3 size={21} /></span><span>SmartAnalytics <small>AI</small></span></Link>
      <div className="sa-workspace"><span>SA</span><div><strong>Personal workspace</strong><small>Account-isolated data</small></div></div>
      <span className="sa-nav-label">WORKSPACE</span>
      <nav aria-label={mobile ? "Mobile application navigation" : "Application navigation"}>
        {appNavigation.map(({ path, title, icon: Icon }) => <NavLink key={path} end={path === "/app"} to={path} className={({ isActive }) => `sa-nav-item${isActive ? " sa-active" : ""}`}><Icon size={18} /><span>{title}</span>{path !== "/app" && path !== "/app/datasets" && path !== "/app/explorer" && path !== "/app/assistant" && <small>Planned</small>}</NavLink>)}
      </nav>
      <div className="sa-sidebar-bottom"><div className="sa-sidebar-note"><ShieldCheck size={20} /><strong>Private by design.</strong><p>Demo data stays labelled. Every upload is scoped to your authenticated account.</p><Link to="/">Back to the website <ArrowUpRight size={14} /></Link></div><span className="sa-local-status"><i /> Secure workspace</span></div>
    </>;
  }

  return <div className="sa-app">
    <a className="skip-link" href="#app-main">Skip to dashboard content</a>
    <aside className="sa-sidebar">{navigation()}</aside>
    <dialog ref={mobileNav} className="sa-mobile-nav" aria-label="Application sidebar" onClose={() => { setNavOpenPath(null); menuButton.current?.focus(); }} onClick={(event) => { if (event.target === event.currentTarget) mobileNav.current?.close(); }}><div className="sa-mobile-nav-inner"><button className="sa-icon-button sa-close-nav" aria-label="Close sidebar" onClick={() => mobileNav.current?.close()}><X size={20} /></button>{navigation(true)}</div></dialog>
    <div className="sa-app-body">
      <header className="sa-header"><div className="sa-header-title"><button ref={menuButton} className="sa-icon-button sa-menu-button" aria-label="Open sidebar" aria-expanded={navOpen} onClick={() => { mobileNav.current?.showModal(); setNavOpenPath(location.pathname); }}><Menu size={21} /></button><span>Workspace <span>/</span> <strong>{page?.title ?? "Not found"}</strong></span></div><div className="sa-header-controls">
        <label className="sa-dataset-selector"><Database size={16} /><span className="sr-only">Active dataset</span><select value={datasetId} disabled={!datasets.length} onChange={(event) => setDatasetId(event.target.value)}>{datasets.length ? <><optgroup label="Demo datasets">{datasets.map((item) => <option key={item.id} value={`demo:${item.id}`}>{item.name} (demo)</option>)}</optgroup>{uploadedDatasets.length > 0 && <optgroup label="Uploaded datasets">{uploadedDatasets.map((item) => <option key={item.id} value={`upload:${item.id}`}>{item.name}</option>)}</optgroup>}</> : <option value="demo:northstar-sales">Loading datasets…</option>}</select></label>
        <AccountMenu />
      </div></header>
      <main id="app-main" className="sa-main"><div className="sa-demo-banner"><span><i /> {uploadedDataset ? "UPLOADED DATASET" : "DEMO ANALYTICS"}</span><p>{uploadedDataset ? "This file is stored by your local API. Sales KPIs are not inferred without an explicit schema mapping." : "Overview uses fictional sales orders. Real analysis and AI require an uploaded dataset."}</p></div>
        {uploadedError && <div className="sa-inline-status is-error" role="alert"><span>{uploadedError}</span><button type="button" onClick={() => void refreshUploadedDatasets()}>Retry</button></div>}
        {error ? <ErrorState message={error} onRetry={() => { setError(""); setAttempt((value) => value + 1); }} /> : !dataset && !uploadedDataset ? <LoadingState /> : <Outlet context={{ dataset, uploadedDataset, uploadedDatasets, refreshUploadedDatasets, openUpload: () => navigate("/app/datasets?upload=1"), selectDataset: setDatasetId } satisfies WorkspaceContext} />}
        <footer className="sa-app-footer"><span>SmartAnalytics AI · A little more clarity.</span><Link to="/"><ArrowLeft size={13} /> Back to landing page</Link></footer>
      </main>
    </div>
  </div>;
}
