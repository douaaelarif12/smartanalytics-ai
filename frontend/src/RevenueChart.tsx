import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
export default function RevenueChart({
  data,
}: {
  data: { month: string; revenue: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 10, right: 5, bottom: 0, left: 5 }}>
        <defs>
          <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#a3bb92" stopOpacity={0.45} />
            <stop offset="100%" stopColor="#a3bb92" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="#eceee8" />
        <XAxis
          dataKey="month"
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 10, fill: "#7b8278" }}
          dy={8}
        />
        <Tooltip
          formatter={(value) => [
            `$${Number(value).toLocaleString()}`,
            "Demo revenue",
          ]}
          contentStyle={{
            borderRadius: 10,
            border: "1px solid #e3e7dc",
            fontSize: 12,
          }}
        />
        <Area
          type="monotone"
          dataKey="revenue"
          stroke="#56794c"
          strokeWidth={2.5}
          fill="url(#revenueFill)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
