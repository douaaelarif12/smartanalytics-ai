import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalyticsResult } from "../api/types";

const COLORS = ["#1f6b4f", "#4d8f70", "#87aa8d", "#d3a14a", "#42665a"];
export default function ExplorerChart({ chart, type }: { chart: NonNullable<AnalyticsResult["chart"]>; type: "bar" | "line" | "pie" }) {
  const data = chart.rows.map((row) => ({ ...row, [chart.dimension]: row[chart.dimension] == null ? "Missing" : String(row[chart.dimension]) }));
  if (type === "pie") {
    const series = chart.series[0];
    if (!series || !data.some((row) => typeof row[series] === "number" && Number(row[series]) > 0) || data.some((row) => typeof row[series] === "number" && Number(row[series]) < 0)) {
      return <p role="status" className="sa-chart-note">A pie chart requires non-negative values and a positive total. Choose a bar or line chart to inspect these results.</p>;
    }
    return <div className="sa-explorer-chart-canvas"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey={series} nameKey={chart.dimension} innerRadius={55} outerRadius={95} paddingAngle={2}>{data.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer></div>;
  }
  const common = <><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e3e8dc" /><XAxis dataKey={chart.dimension} tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} /><Tooltip /><Legend /></>;
  return <div className="sa-explorer-chart-canvas"><ResponsiveContainer width="100%" height="100%">{type === "line" ? <LineChart data={data}>{common}{chart.series.map((series, index) => <Line key={series} dataKey={series} stroke={COLORS[index % COLORS.length]} strokeWidth={2} dot={false} />)}</LineChart> : <BarChart data={data}>{common}{chart.series.map((series, index) => <Bar key={series} dataKey={series} fill={COLORS[index % COLORS.length]} radius={[6, 6, 0, 0]} />)}</BarChart>}</ResponsiveContainer></div>;
}
