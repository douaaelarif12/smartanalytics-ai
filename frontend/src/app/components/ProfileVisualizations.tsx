import { useState } from "react";
import type { ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, Beaker, Info, ScanSearch } from "lucide-react";
import type { DatasetProfileResponse } from "../api/types";

type NumericProfile = DatasetProfileResponse["numeric"][number];
type CategoryProfile = DatasetProfileResponse["categorical"][number];
type TemporalProfile = DatasetProfileResponse["temporal"][number];
type CorrelationProfile = DatasetProfileResponse["correlation"];

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #d7e0d5",
  background: "#fffefb",
  fontSize: 12,
  boxShadow: "0 12px 32px rgba(21, 61, 46, .12)",
};

const number = (value: number | null, maximumFractionDigits = 3) =>
  value === null
    ? "Unavailable"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits }).format(value);

const compact = (value: number) =>
  new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);

const shorten = (value: string, limit = 18) =>
  value.length > limit ? `${value.slice(0, limit - 1)}…` : value;

function EmptyVisualization({ children }: { children: string }) {
  return <div className="sa-viz-empty" role="status"><ScanSearch size={21} />{children}</div>;
}

function Notice({ tone = "info", children }: { tone?: "info" | "warning"; children: ReactNode }) {
  return <div className={`sa-viz-notice is-${tone}`} role="note">{tone === "warning" ? <AlertTriangle size={15} /> : <Info size={15} />}<span>{children}</span></div>;
}

function Selector({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
}) {
  return <label className="sa-viz-selector"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>;
}

function ChartData({ summary, children }: { summary: string; children: ReactNode }) {
  return <details className="sa-chart-table sa-profile-chart-data"><summary>{summary}</summary>{children}</details>;
}

function NumericVisualization({ items }: { items: readonly NumericProfile[] }) {
  const [selection, setSelection] = useState(items[0]?.column ?? "");
  const statistic = items.find((item) => item.column === selection) ?? items[0];
  if (!statistic) return <EmptyVisualization>No numeric columns are available for a histogram.</EmptyVisualization>;

  const bins = statistic.histogram.bins.map((bin, index) => ({
    ...bin,
    index: index + 1,
    range: `${number(bin.lower_bound)} – ${number(bin.upper_bound)}`,
  }));

  return <section className="sa-profile-viz-card" aria-labelledby="histogram-title">
    <div className="sa-viz-card-heading"><div><span className="sa-overline">NUMERIC DISTRIBUTION</span><h4 id="histogram-title">Histogram & statistical markers</h4><p>Finite values only. Bin boundaries and counts come directly from the profile API.</p></div><Selector label="Numeric column" value={statistic.column} options={items.map((item) => item.column)} onChange={setSelection} /></div>
    <div className="sa-stat-strip" aria-label={`Statistical indicators for ${statistic.column}`}>
      <div><span>Mean</span><strong>{number(statistic.mean)}</strong></div>
      <div><span>Median</span><strong>{number(statistic.median)}</strong></div>
      <div><span>Q1 / Q3</span><strong>{number(statistic.q1)} / {number(statistic.q3)}</strong></div>
      <div><span>IQR</span><strong>{number(statistic.iqr)}</strong></div>
      <div><span>Std. deviation</span><strong>{number(statistic.std)}</strong></div>
      <div><span>Potential outliers</span><strong>{statistic.outlier_count.toLocaleString()}</strong></div>
    </div>
    <div className="sa-viz-meta">
      <span>{statistic.finite_count.toLocaleString()} finite</span>
      <span>{statistic.missing_count.toLocaleString()} missing</span>
      <span>{statistic.non_finite_count.toLocaleString()} non-finite</span>
      <span>Whiskers {number(statistic.lower_whisker)} to {number(statistic.upper_whisker)}</span>
    </div>
    {statistic.histogram.sampled && <Notice tone="warning">Histogram based on a deterministic sample of {statistic.histogram.sample_count.toLocaleString()} values from {statistic.histogram.source_count.toLocaleString()} finite values.</Notice>}
    {statistic.warnings.includes("small_sample") && <Notice tone="warning">Fewer than 20 finite values are available. Interpret the distribution and outlier count with caution.</Notice>}
    {statistic.warnings.includes("zero_iqr") && <Notice>The interquartile range is zero. Repeated values can make Tukey fences very narrow; flagged values are not automatically errors.</Notice>}
    {bins.length ? <>
      <div className="sa-profile-chart" aria-label={`Histogram of ${statistic.column}. Exact bin values follow in a data table.` }>
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart data={bins} margin={{ top: 10, right: 12, left: 0, bottom: 4 }} accessibilityLayer>
            <CartesianGrid vertical={false} stroke="#e7ece5" strokeDasharray="4 4" />
            <XAxis dataKey="index" axisLine={false} tickLine={false} tick={{ fill: "#788578", fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis allowDecimals={false} tickFormatter={compact} axisLine={false} tickLine={false} tick={{ fill: "#788578", fontSize: 10 }} width={44} />
            <Tooltip labelFormatter={(_, payload) => payload[0]?.payload.range ?? "Bin"} formatter={(value) => [Number(value).toLocaleString(), "Values"]} contentStyle={tooltipStyle} cursor={{ fill: "#edf3ec" }} />
            <Bar dataKey="count" name="Values" fill="#2f7658" radius={[5, 5, 1, 1]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ChartData summary="View histogram data"><table><caption>Histogram bins for {statistic.column}</caption><thead><tr><th scope="col">Bin</th><th scope="col">Lower bound</th><th scope="col">Upper bound</th><th scope="col">Count</th></tr></thead><tbody>{bins.map((bin) => <tr key={bin.index}><th scope="row">{bin.index}</th><td>{number(bin.lower_bound)}</td><td>{number(bin.upper_bound)}</td><td>{bin.count.toLocaleString()}</td></tr>)}</tbody></table></ChartData>
    </> : <EmptyVisualization>This column has no finite values to plot.</EmptyVisualization>}
  </section>;
}

function CategoryVisualization({ items }: { items: readonly CategoryProfile[] }) {
  const [selection, setSelection] = useState(items[0]?.column ?? "");
  const statistic = items.find((item) => item.column === selection) ?? items[0];
  if (!statistic) return <EmptyVisualization>No categorical columns are available for a distribution chart.</EmptyVisualization>;
  const values = [
    ...statistic.top_values.map((item) => ({ label: item.value || "(empty string)", count: item.count, truncated: item.value_truncated, other: false })),
    ...(statistic.other_count ? [{ label: "Other categories", count: statistic.other_count, truncated: false, other: true }] : []),
  ];

  return <section className="sa-profile-viz-card" aria-labelledby="category-distribution-title">
    <div className="sa-viz-card-heading"><div><span className="sa-overline">CATEGORICAL DISTRIBUTION</span><h4 id="category-distribution-title">Most frequent categories</h4><p>Top values and the aggregated remainder are supplied by the profile API.</p></div><Selector label="Categorical column" value={statistic.column} options={items.map((item) => item.column)} onChange={setSelection} /></div>
    <div className="sa-viz-meta"><span>{statistic.count.toLocaleString()} populated</span><span>{statistic.unique_count.toLocaleString()} unique</span><span>{statistic.other_count.toLocaleString()} grouped as other</span><span>{statistic.missing_count.toLocaleString()} missing</span></div>
    {statistic.top_values.some((item) => item.value_truncated) && <Notice>Some source labels were shortened by the API to keep the response safe and bounded. Their hash suffix preserves distinction.</Notice>}
    {values.length ? <>
      <div className="sa-profile-chart is-category" aria-label={`Category distribution for ${statistic.column}. Exact values follow in a data table.`}>
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart data={values} layout="vertical" margin={{ top: 6, right: 18, left: 8, bottom: 4 }} accessibilityLayer>
            <CartesianGrid horizontal={false} stroke="#e7ece5" strokeDasharray="4 4" />
            <XAxis type="number" allowDecimals={false} tickFormatter={compact} axisLine={false} tickLine={false} tick={{ fill: "#788578", fontSize: 10 }} />
            <YAxis type="category" dataKey="label" tickFormatter={(value) => shorten(String(value))} width={122} axisLine={false} tickLine={false} tick={{ fill: "#617064", fontSize: 10 }} />
            <Tooltip formatter={(value) => [Number(value).toLocaleString(), "Rows"]} contentStyle={tooltipStyle} cursor={{ fill: "#edf3ec" }} />
            <Bar dataKey="count" name="Rows" radius={[0, 5, 5, 0]} barSize={22} isAnimationActive={false}>{values.map((item) => <Cell key={item.label} fill={item.other ? "#a9b4a7" : "#3f8062"} />)}</Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ChartData summary="View category data"><table><caption>Category counts for {statistic.column}</caption><thead><tr><th scope="col">Category</th><th scope="col">Count</th><th scope="col">Status</th></tr></thead><tbody>{values.map((item) => <tr key={item.label}><th scope="row">{item.label}</th><td>{item.count.toLocaleString()}</td><td>{item.other ? "Aggregated remainder" : item.truncated ? "Label shortened by API" : "Top category"}</td></tr>)}<tr><th scope="row">Missing</th><td>{statistic.missing_count.toLocaleString()}</td><td>Not included in bars</td></tr></tbody></table></ChartData>
    </> : <EmptyVisualization>This column contains no populated categories.</EmptyVisualization>}
  </section>;
}

function correlationColor(value: number | null) {
  if (value === null) return { background: "#eef0ec", color: "#68736c" };
  const strength = Math.abs(value);
  if (value >= 0) return { background: `rgba(31, 107, 79, ${0.13 + strength * 0.75})`, color: strength > 0.58 ? "#fff" : "#173c2e" };
  return { background: `rgba(176, 83, 62, ${0.13 + strength * 0.72})`, color: strength > 0.58 ? "#fff" : "#703b2e" };
}

function CorrelationHeatmap({ correlation }: { correlation: CorrelationProfile }) {
  if (!correlation.columns.length) return <section className="sa-profile-viz-card"><div className="sa-viz-card-heading"><div><span className="sa-overline">RELATIONSHIPS</span><h4>Pearson correlation heatmap</h4></div></div><EmptyVisualization>At least one eligible numeric column is required for a correlation matrix.</EmptyVisualization></section>;
  const exclusionPreview = correlation.excluded_columns.slice(0, 8);
  return <section className="sa-profile-viz-card sa-correlation-card" aria-labelledby="correlation-title">
    <div className="sa-viz-card-heading"><div><span className="sa-overline">RELATIONSHIPS</span><h4 id="correlation-title">Pearson correlation heatmap</h4><p>Pairwise-complete coefficients from −1 to +1. Correlation does not imply causation.</p></div><div className="sa-heat-legend" aria-label="Correlation color scale"><span>−1</span><i /><span>0</span><i /><span>+1</span></div></div>
    {correlation.sampled && <Notice tone="warning">Coefficients use a deterministic sample of {correlation.sample_row_count.toLocaleString()} rows from {correlation.source_row_count.toLocaleString()}.</Notice>}
    {correlation.columns_truncated && <Notice tone="warning">Only the first {correlation.columns.length} eligible numeric columns are shown. Additional numeric columns were excluded by the API limit.</Notice>}
    <div className="sa-heatmap-scroll" role="region" aria-label="Scrollable Pearson correlation matrix" tabIndex={0}>
      <table className="sa-heatmap"><caption className="sr-only">Pearson correlation coefficients and finite pair counts</caption><thead><tr><th scope="col">Column</th>{correlation.columns.map((column) => <th scope="col" key={column} title={column}>{shorten(column, 12)}</th>)}</tr></thead><tbody>{correlation.columns.map((row, rowIndex) => <tr key={row}><th scope="row" title={row}>{row}</th>{correlation.columns.map((column, columnIndex) => { const value = correlation.matrix[rowIndex]?.[columnIndex] ?? null; const pairs = correlation.finite_pair_counts[rowIndex]?.[columnIndex] ?? 0; const text = value === null ? "N/A" : value.toFixed(2); return <td key={column}><span className={value === null ? "is-unavailable" : ""} style={correlationColor(value)} title={`${row} and ${column}: ${value === null ? "not calculable" : value.toFixed(4)} from ${pairs.toLocaleString()} finite pairs`} aria-label={`${row} and ${column}: ${value === null ? "not calculable" : value.toFixed(4)}, ${pairs.toLocaleString()} finite pairs`}>{text}</span></td>; })}</tr>)}</tbody></table>
    </div>
    <div className="sa-correlation-foot"><span><i className="is-negative" /> Negative</span><span><i className="is-neutral" /> Unavailable / insufficient</span><span><i className="is-positive" /> Positive</span></div>
    {correlation.excluded_count > 0 && <details className="sa-method-details"><summary>{correlation.excluded_count.toLocaleString()} excluded column{correlation.excluded_count === 1 ? "" : "s"}</summary><ul>{exclusionPreview.map((item) => <li key={`${item.column}:${item.reason}`}><strong>{item.column}</strong><span>{item.reason === "boolean" ? "Boolean values are not numeric measures." : item.reason === "column_limit" ? "Beyond the 12-column matrix limit." : "Not a numeric column."}</span></li>)}</ul>{(correlation.excluded_count > exclusionPreview.length || correlation.exclusions_truncated) && <p>The complete exclusion list is intentionally bounded in the API response.</p>}</details>}
  </section>;
}

function TemporalVisualization({ items }: { items: readonly TemporalProfile[] }) {
  const [selection, setSelection] = useState(items[0]?.column ?? "");
  const series = items.find((item) => item.column === selection) ?? items[0];
  if (!series) return <section className="sa-profile-viz-card"><div className="sa-viz-card-heading"><div><span className="sa-overline">TIME</span><h4>Temporal evolution</h4><p>Available only for columns detected as datetime.</p></div></div><EmptyVisualization>No datetime column was detected, so no temporal chart was generated.</EmptyVisualization></section>;
  return <section className="sa-profile-viz-card sa-temporal-card" aria-labelledby="temporal-title">
    <div className="sa-viz-card-heading"><div><span className="sa-overline">TIME</span><h4 id="temporal-title">Temporal evolution</h4><p>Row frequency by {series.granularity}; this is not an inferred business measure.</p></div><Selector label="Datetime column" value={series.column} options={items.map((item) => item.column)} onChange={setSelection} /></div>
    <div className="sa-viz-meta"><span>{series.source_count.toLocaleString()} dated rows</span><span>{series.missing_count.toLocaleString()} missing dates</span><span>{series.points.length.toLocaleString()} points</span><span>{series.bucket_size > 1 ? `${series.bucket_size}-year buckets` : `Grouped by ${series.granularity}`}</span></div>
    {series.coarsened && <Notice>Granularity was widened by the API to keep the series within 60 points.</Notice>}
    {series.truncated && <Notice tone="warning">The API truncated this series to its configured point limit.</Notice>}
    {series.points.length ? <>
      <div className="sa-profile-chart is-temporal" aria-label={`Temporal row frequency for ${series.column}. Exact values follow in a data table.`}>
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <AreaChart data={series.points} margin={{ top: 12, right: 14, left: 0, bottom: 4 }} accessibilityLayer>
            <defs><linearGradient id="sa-profile-temporal-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4d8f70" stopOpacity={0.36} /><stop offset="100%" stopColor="#4d8f70" stopOpacity={0.02} /></linearGradient></defs>
            <CartesianGrid vertical={false} stroke="#e7ece5" strokeDasharray="4 4" />
            <XAxis dataKey="period" axisLine={false} tickLine={false} minTickGap={32} tick={{ fill: "#788578", fontSize: 10 }} />
            <YAxis allowDecimals={false} tickFormatter={compact} axisLine={false} tickLine={false} tick={{ fill: "#788578", fontSize: 10 }} width={44} />
            <Tooltip formatter={(value) => [Number(value).toLocaleString(), "Rows"]} contentStyle={tooltipStyle} />
            <Area type="monotone" dataKey="count" name="Rows" stroke="#1f6b4f" strokeWidth={2.5} fill="url(#sa-profile-temporal-fill)" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <ChartData summary="View temporal data"><table><caption>Row frequency for {series.column}</caption><thead><tr><th scope="col">Period</th><th scope="col">Rows</th></tr></thead><tbody>{series.points.map((point) => <tr key={point.period}><th scope="row">{point.period}</th><td>{point.count.toLocaleString()}</td></tr>)}</tbody></table></ChartData>
    </> : <EmptyVisualization>No valid dates are available for this column.</EmptyVisualization>}
  </section>;
}

function Methodology({ profile }: { profile: DatasetProfileResponse }) {
  const method = profile.methodology;
  return <details className="sa-methodology"><summary><span><Beaker size={17} />Methodology & interpretation</span><small>Profile API {profile.profile_version}</small></summary><div className="sa-method-grid">
    <div><strong>Quartiles</strong><span>Linear interpolation</span><p>Q1 and Q3 are calculated by the API, not in the browser.</p></div>
    <div><strong>Dispersion</strong><span>Sample standard deviation</span><p>Uses ddof=1. Tukey fences use 1.5 × IQR.</p></div>
    <div><strong>Histograms</strong><span>Sturges, 5–30 bins</span><p>Up to {method.visualization_sample_limit.toLocaleString()} deterministic finite values.</p></div>
    <div><strong>Correlation</strong><span>Pearson, pairwise complete</span><p>At least 3 finite pairs and at most {method.correlation_max_columns} columns.</p></div>
    <div><strong>Temporal</strong><span>Frequency, not a KPI</span><p>Adaptive day, month or year grouping; at most {method.temporal_max_points} points.</p></div>
    <div><strong>Categories</strong><span>Top {method.category_top_limit} + other</span><p>Missing values remain separate from the distribution.</p></div>
  </div><Notice tone="warning">Potential outliers are observations outside Tukey fences. They may be valid and should not be treated as data errors without domain review.</Notice></details>;
}

export default function ProfileVisualizations({ profile }: { profile: DatasetProfileResponse }) {
  return <div className="sa-profile-visualizations">
    <div className="sa-profile-viz-intro"><div><span className="sa-overline">ADVANCED DATA INSIGHTS</span><h3>Explore shape, relationships and time.</h3><p>Interactive views use the bounded, owner-authorized profile. No raw data or statistic is recomputed in your browser.</p></div><span className="sa-badge">PROFILE {profile.profile_version}</span></div>
    <div className="sa-profile-viz-grid"><NumericVisualization items={profile.numeric} /><CategoryVisualization items={profile.categorical} /><CorrelationHeatmap correlation={profile.correlation} /><TemporalVisualization items={profile.temporal} /></div>
    <Methodology profile={profile} />
  </div>;
}
