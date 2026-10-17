"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { b4Mutation } from "@/lib/api/student-learning";
import { type CatalogueSimulation, type SimulationSpec } from "@/lib/simulations/spec";
import { requestSimulation } from "@/lib/simulations/request";
import { SimulationProgress } from "./simulation-progress";
import { InteractiveExperience } from "@/components/ui/interactive-experience";
const SimulationPlayer = dynamic(() => import("./simulation-player").then(module => module.SimulationPlayer), { ssr: false, loading: () => <SimulationProgress stage="compiling" /> });
// Tab-memory only. Reloading history never automatically requests a new paid generation.
type SimulationJob = { promise: ReturnType<typeof requestSimulation>; preparing: boolean; listeners: Set<() => void> };
const generated = new Map<string, SimulationJob>();
export function ResponseSimulation({ sessionId, messageId, fresh = false, guest = false }: { sessionId: string; messageId: string; fresh?: boolean; guest?: boolean }) {
  const [spec, setSpec] = useState<SimulationSpec | null>(null), [state, setState] = useState("loading");
  const [resource, setResource] = useState<CatalogueSimulation | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setSpec(null); setResource(null); setState("loading");
    const key = `${sessionId}/${messageId}`;
    let pending = generated.get(key);
    if (!pending) {
      const entry: SimulationJob = {
        preparing: false, listeners: new Set(),
        promise: requestSimulation(async (start, signal) => {
          const value = await b4Mutation(`sessions/${sessionId}/simulation`, "POST", { message_id: messageId, start }, undefined, signal, guest);
          // Eligibility checks run for all answers. Only confirmed simulation
          // work may display progress; ordinary text/F12 answers stay untouched.
          if (value?.status === "pending") {
            entry.preparing = true;
            entry.listeners.forEach(listener => listener());
          }
          return value;
        }, fresh && attempt === 0),
      };
      pending = entry;
      generated.set(key, pending);
      const job = pending;
      void job.promise.catch(() => { if (generated.get(key) === job) generated.delete(key); });
      // Catalogue documents must pass current authorization on every mount.
      void job.promise.then(value => { if (value.status === "resource" && generated.get(key) === job) generated.delete(key); }, () => {});
      if (generated.size > 64) generated.delete(generated.keys().next().value!);
    }
    const preparing = () => { if (active) setState("pending"); };
    pending.listeners.add(preparing);
    if (pending.preparing) preparing();
    void pending.promise.then(value => { if (!active) return; if (value.status === "ready") setSpec(value.spec); if (value.status === "resource") setResource(value.resource); setState(value.status); }, () => { if (active) setState("interrupted"); });
    return () => { active = false; pending.listeners.delete(preparing); };
  }, [sessionId, messageId, fresh, attempt, guest]);
  if (spec) return <SimulationPlayer spec={spec} />;
  if (resource) return <div className="catalogue-simulation" data-simulation-source="catalogue"><InteractiveExperience inline key={`${resource.resourceId}/${resource.version}`} title={resource.title} document={resource.document} /></div>;
  if (state === "loading" || state === "ineligible") return null;
  if (state === "expired") return <p role="status">This temporary simulation is no longer available. Your saved explanation is preserved.</p>;
  if (state === "interrupted") return <div><p role="status">The simulation is taking longer than expected or the connection was interrupted. Your explanation is still available.</p><button type="button" onClick={() => setAttempt(value => value + 1)}>Check simulation</button></div>;
  if (state === "limited") return <p role="status">The simulation generation limit has been reached. Your explanation is still available.</p>;
  if (state === "pending") return <SimulationProgress key={`${sessionId}/${messageId}/${attempt}`} stage="generating" />;
  return <p role="status">The interactive simulation is unavailable. Your explanation is still available.</p>;
}
