"use client";
import { Component, lazy, memo, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import { changeMathParameter, isMathVisualBlock, mathState, mathTemplates, type MathParameters, type MathTemplate, type MathVisualBlock } from "./math-spec";

export type MathEngineProps = { template: MathTemplate; parameters: MathParameters; width: number; height: number; onChange: (key: string, value: number | string) => void };
const engines = {
  konva: lazy(() => import("./math-konva")),
  jsxgraph: lazy(() => import("./math-geometry")),
  mafs: lazy(() => import("./math-functions")),
};
class ActivityBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <p role="status">The drawing is unavailable. Use the controls and mathematical description below.</p> : this.props.children; }
}

export const MathActivity = memo(function MathActivity({ block }: { block: MathVisualBlock }) {
  // Only canonical saved initial parameters are persisted; controls never mutate the block.
  const [parameters, setParameters] = useState<MathParameters>({ ...block.parameters });
  const [expanded, setExpanded] = useState(false), [reset, setReset] = useState(0), [width, setWidth] = useState(0);
  const frame = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(0, Math.floor(entry.contentRect.width))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  if (!isMathVisualBlock(block)) return <p role="status">This mathematical activity could not be displayed.</p>;
  const spec = mathTemplates[block.template], Engine = engines[spec.engine];
  const change = (key: string, value: number | string) => setParameters(current => changeMathParameter(block.template, current, key, value));
  return <figure className={`math-activity${expanded ? " math-activity-expanded" : ""}`} data-template={block.template} data-engine={spec.engine}>
    <figcaption><strong>{block.title}</strong><p>{block.description}</p></figcaption>
    <div className="math-activity-toolbar"><button type="button" onClick={() => { setParameters({ ...block.parameters }); setReset(value => value + 1); }}>Reset activity</button><button type="button" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? "Restore activity" : "Expand activity"}</button></div>
    <div className="math-activity-drawing" ref={frame} role="group" aria-label={`${block.title} drawing`} style={{ height: expanded ? 440 : 300 }}>
      {width > 0 && <ActivityBoundary key={`${block.id}-${reset}`}><Suspense fallback={<p role="status">Loading activity. Its controls and description are available below.</p>}><Engine template={block.template} parameters={parameters} width={width} height={expanded ? 440 : 300} onChange={change} /></Suspense></ActivityBoundary>}
    </div>
    <div className="math-activity-controls">{Object.entries(spec.parameters).filter(([key]) => !(block.template === "shape_explorer" && parameters.shape === "circle" && key === "height")).map(([key, field]) => <div key={key}><label>{field.label}
      {field.options ? <select aria-label={field.label} value={String(parameters[key])} onChange={event => change(key, event.target.value)}>{field.options.map(option => <option key={option}>{option}</option>)}</select> :
        <input aria-label={field.label} type="number" inputMode="decimal" min={field.min} max={field.max} step={field.step} value={parameters[key]} onChange={event => { if (event.target.value !== "") change(key, Number(event.target.value)); }} />}
    </label>{block.template.endsWith("function") && key !== "x" && !field.options && <input type="range" aria-label={`${field.label} slider`} min={field.min} max={field.max} step={field.step} value={parameters[key]} onChange={event => change(key, Number(event.target.value))} />}</div>)}</div>
    <p className="math-activity-state" role="status" aria-live="polite" aria-atomic="true">{mathState(block.template, parameters)}</p>
    <small>Use the controls or move the highlighted objects. Changes stay in this activity; Reset restores the original example.</small>
  </figure>;
});
