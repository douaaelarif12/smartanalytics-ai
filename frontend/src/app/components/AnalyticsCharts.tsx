import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ReactNode } from "react";
import type { AnalyticsSnapshot } from "../types";
import { integer, money } from "../format";

const colors = ["#1f6b4f", "#4d8f70", "#87aa8d", "#d3a14a"];
const tooltipStyle = {
  borderRadius: 10,
  border: "1px solid #dfe5d7",
  fontSize: 12,
  boxShadow: "0 5px 20px #203c2c0a",
};
const compactMoney = (value: number) =>
  `$${value >= 1000 ? `${(value / 1000).toFixed(0)}k` : value}`;

function ChartCard({
  title,
  subtitle,
  className,
  children,
  table,
}: {
  title: string;
  subtitle: string;
  className: string;
  children: ReactNode;
  table: ReactNode;
}) {
  return (
    <section className={`sa-card sa-chart-card ${className}`}>
      <div className="sa-card-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span className="sa-chart-demo">DEMO</span>
      </div>
      {children}
      <details className="sa-chart-table">
        <summary>View chart data</summary>
        {table}
      </details>
    </section>
  );
}
export default function AnalyticsCharts({
  analytics,
}: {
  analytics: AnalyticsSnapshot;
}) {
  const { trend, categories, revenue } = analytics;
  const categoryTable = (
    <table>
      <caption>Sample revenue and order totals by category</caption>
      <thead>
        <tr>
          <th scope="col">Category</th>
          <th scope="col">Revenue</th>
          <th scope="col">Orders</th>
          <th scope="col">Share</th>
        </tr>
      </thead>
      <tbody>
        {categories.map((row) => (
          <tr key={row.name}>
            <th scope="row">{row.name}</th>
            <td>{money(row.revenue)}</td>
            <td>{integer(row.orders)}</td>
            <td>{row.share.toFixed(1)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
  return (
    <>
      <ChartCard
        title="Revenue over time"
        subtitle="Net sales after discounts · USD"
        className="sa-trend-card"
        table={
          <table>
            <caption>Sample revenue trend</caption>
            <thead>
              <tr>
                <th scope="col">Period</th>
                <th scope="col">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {trend.map((row) => (
                <tr key={row.date}>
                  <th scope="row">{row.date}</th>
                  <td>{money(row.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        }
      >
        <div className="sa-trend-total">
          <strong>{money(revenue)}</strong>
          <span>
            <i /> Revenue
          </span>
        </div>
        <div
          className="sa-trend-chart"
          aria-label="Revenue trend, with exact values in the chart data table"
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <AreaChart
              data={trend}
              margin={{ top: 10, right: 8, left: 0, bottom: 0 }}
              accessibilityLayer
            >
              <defs>
                <linearGradient id="sa-trend-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4d8f70" stopOpacity={0.34} />
                  <stop offset="100%" stopColor="#4d8f70" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                stroke="#edf0e7"
                strokeDasharray="4 4"
              />
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                minTickGap={34}
                tick={{ fill: "#858e7c", fontSize: 10 }}
                dy={9}
              />
              <YAxis
                tickFormatter={compactMoney}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#858e7c", fontSize: 10 }}
                width={47}
              />
              <Tooltip
                formatter={(value) => [money(Number(value)), "Revenue"]}
                contentStyle={tooltipStyle}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#1f6b4f"
                strokeWidth={2.5}
                fill="url(#sa-trend-fill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
      <ChartCard
        title="Category distribution"
        subtitle="Share of net sales revenue"
        className="sa-distribution-card"
        table={categoryTable}
      >
        <div
          className="sa-pie-wrap"
          aria-label="Category revenue distribution, with exact values in the chart data table"
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <PieChart accessibilityLayer>
              <Pie
                data={categories}
                dataKey="revenue"
                nameKey="name"
                innerRadius={64}
                outerRadius={86}
                paddingAngle={3}
                stroke="none"
                isAnimationActive={false}
              >
                {categories.map((row, index) => (
                  <Cell key={row.name} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => money(Number(value))}
                contentStyle={tooltipStyle}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="sa-pie-center">
            <strong>{categories.length}</strong>
            <span>categories</span>
          </div>
        </div>
        <ul className="sa-distribution-legend">
          {categories.map((row, index) => (
            <li key={row.name}>
              <i style={{ background: colors[index % colors.length] }} />
              <span>{row.name}</span>
              <strong>{row.share.toFixed(1)}%</strong>
            </li>
          ))}
        </ul>
      </ChartCard>
      <ChartCard
        title="Sales by category"
        subtitle="Where your sample revenue comes from · USD"
        className="sa-category-card"
        table={categoryTable}
      >
        <div
          className="sa-bar-chart"
          aria-label="Category sales bar chart, with exact values in the chart data table"
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart
              data={categories}
              layout="vertical"
              margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
              accessibilityLayer
            >
              <CartesianGrid
                horizontal={false}
                stroke="#edf0e7"
                strokeDasharray="4 4"
              />
              <XAxis
                type="number"
                tickFormatter={compactMoney}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#858e7c", fontSize: 10 }}
              />
              <YAxis
                dataKey="name"
                type="category"
                axisLine={false}
                tickLine={false}
                width={94}
                tick={{ fill: "#69775f", fontSize: 10 }}
              />
              <Tooltip
                formatter={(value) => [money(Number(value)), "Revenue"]}
                cursor={{ fill: "#f4f6ef" }}
                contentStyle={tooltipStyle}
              />
              <Bar
                dataKey="revenue"
                radius={[0, 5, 5, 0]}
                barSize={23}
                isAnimationActive={false}
              >
                {categories.map((row, index) => (
                  <Cell key={row.name} fill={colors[index % colors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </>
  );
}
