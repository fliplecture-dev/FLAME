"use client";
import { useEffect, useState } from "react";

type Stage = "generating" | "compiling" | "starting" | "ready";
const stages = {
  generating: { min: 0, max: 69, label: "Preparing interactive simulation…" },
  compiling: { min: 70, max: 89, label: "Preparing simulation…" },
  starting: { min: 90, max: 99, label: "Starting simulation…" },
  ready: { min: 100, max: 100, label: "Interactive simulation ready" },
};

/** Stage milestones are real; progress within an unfinished stage is estimated. */
export function SimulationProgress({ stage }: { stage: Stage }) {
  const { min, max, label } = stages[stage];
  const [progress, setProgress] = useState(min);
  const [finished, setFinished] = useState(false);
  const value = Math.max(min, Math.min(max, progress));
  useEffect(() => {
    setProgress(min);
    setFinished(false);
    if (min === max) {
      const timer = setTimeout(() => setFinished(true), 1000);
      return () => clearTimeout(timer);
    }
    const timer = setInterval(() => setProgress(previous => Math.min(max, previous + Math.max(1, Math.ceil((max - previous) * .08)))), 1000);
    return () => clearInterval(timer);
  }, [min, max]);
  if (stage === "ready" && finished) return null;
  return <div className="simulation-progress" data-progress-stage={stage}>
    <div className="simulation-progress-label"><p role="status">{label}</p><span aria-hidden="true">{value}%</span></div>
    <div className="simulation-progress-track" role="progressbar" aria-label="Interactive simulation preparation"
      aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}
      aria-valuetext={`${value}%${stage === "ready" ? " — ready" : " — estimated"}`}>
      <span style={{ width: `${value}%` }} />
    </div>
    {stage !== "ready" && <small>Estimated progress</small>}
  </div>;
}
