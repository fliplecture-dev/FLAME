"use client";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartBlock } from "./rich-blocks";
const colors = ["#345c9c", "#a0461b", "#2f7960", "#8155a2"];
export default function ChartPlot({ block }: { block: ChartBlock }) {
  const axes = <><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey={block.xKey} label={block.xLabel ? { value: block.xLabel, position: "insideBottom", offset: -10 } : undefined} /><YAxis width={60} label={block.yLabel ? { value: block.yLabel, angle: -90, position: "insideLeft" } : undefined} /><Tooltip /><Legend /></>;
  return <ResponsiveContainer width="100%" height={300} minWidth={0}>
    {block.chartType === "pie" ? <PieChart accessibilityLayer aria-label={block.title}><Tooltip /><Legend /><Pie data={block.data} dataKey={block.series[0].key} nameKey={block.xKey} isAnimationActive={false}>{block.data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}</Pie></PieChart> :
      block.chartType === "bar" ? <BarChart data={block.data} accessibilityLayer aria-label={block.title} margin={{ bottom: 20, right: 16 }}>{axes}{block.series.map((item, i) => <Bar key={item.key} dataKey={item.key} name={item.label} fill={colors[i]} isAnimationActive={false} />)}</BarChart> :
        <LineChart data={block.data} accessibilityLayer aria-label={block.title} margin={{ bottom: 20, right: 16 }}>{axes}{block.series.map((item, i) => <Line key={item.key} dataKey={item.key} name={item.label} stroke={colors[i]} strokeWidth={2} isAnimationActive={false} />)}</LineChart>}
  </ResponsiveContainer>;
}
