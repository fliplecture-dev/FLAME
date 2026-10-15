"use client";
import { Component, lazy, memo, Suspense, type ReactNode } from "react";
import { isChartBlock, type ChartBlock as ChartData } from "./rich-blocks";
const ChartPlot = lazy(() => import("./chart-plot"));
class PlotBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <p>Chart unavailable. The data is shown below.</p> : this.props.children; }
}
export const ChartBlock = memo(function ChartBlock({ block }: { block: ChartData }) {
  if (!isChartBlock(block)) return <p role="status">This chart could not be displayed.</p>;
  return <figure className="response-chart">
    <figcaption><strong>{block.title}</strong><p>{block.description}</p>{block.illustrative && <span className="response-chart-example">Illustrative example data</span>}</figcaption>
    <div className="response-chart-plot" role="group" aria-label={block.title}><PlotBoundary><Suspense fallback={<p>Loading chart. Data is available below.</p>}><ChartPlot block={block} /></Suspense></PlotBoundary></div>
    <details><summary>View chart data</summary><div className="content-table" role="region" aria-label={`${block.title} data`} tabIndex={0}><table>
      <caption>{block.title}</caption><thead><tr><th scope="col">{block.xLabel || block.xKey}</th>{block.series.map(item => <th scope="col" key={item.key}>{item.label}{block.yLabel ? ` (${block.yLabel})` : ""}</th>)}</tr></thead>
      <tbody>{block.data.map((row, i) => <tr key={i}><th scope="row">{row[block.xKey]}</th>{block.series.map(item => <td key={item.key}>{row[item.key]}</td>)}</tr>)}</tbody>
    </table></div></details>
  </figure>;
});
