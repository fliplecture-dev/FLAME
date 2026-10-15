"use client";
import { useEffect, useRef, useState } from "react";
import { simulationDocument, type SimulationBundle } from "@/lib/simulations/document";
import type { SimulationSpec } from "@/lib/simulations/spec";
import { SimulationProgress } from "./simulation-progress";

export function SimulationPlayer({ spec }: { spec: SimulationSpec }) {
  const [attempt, setAttempt] = useState(0), [html, setHtml] = useState(""), [state, setState] = useState("compiling");
  const [expanded, setExpanded] = useState(false), [closed, setClosed] = useState(false);
  const frame = useRef<HTMLIFrameElement>(null), root = useRef<HTMLElement>(null);
  useEffect(() => {
    if (closed) return;
    const abort = new AbortController(), nonce = crypto.randomUUID();
    let active = true, timer: ReturnType<typeof setTimeout>;
    setHtml(""); setState("compiling");
    function message(event: MessageEvent) {
      if (event.source !== frame.current?.contentWindow || event.data?.channel !== "flame-simulation" || event.data?.nonce !== nonce) return;
      if (event.data.type === "ready") { clearTimeout(timer); setState("ready"); }
      if (event.data.type === "error") { clearTimeout(timer); setState("error"); }
    }
    const dispose = () => frame.current?.contentWindow?.postMessage({ nonce, type: "dispose" }, "*");
    const visibility = () => frame.current?.contentWindow?.postMessage({ nonce, type: "visibility", hidden: document.hidden }, "*");
    window.addEventListener("message", message); document.addEventListener("visibilitychange", visibility);
    void (async () => {
      try {
        const auth = await fetch("/api/auth/csrf", { cache: "no-store", signal: abort.signal });
        if (!auth.ok) throw Error();
        const { csrf } = await auth.json();
        const response = await fetch("/api/simulations/compile", { method: "POST", cache: "no-store", signal: abort.signal,
          headers: { "content-type": "application/json", "x-flame-csrf": csrf }, body: JSON.stringify(spec) });
        if (!response.ok) throw Error();
        const bundle = await response.json() as SimulationBundle;
        if (active) { setHtml(simulationDocument(bundle, spec.engine, nonce, document.hidden || window.matchMedia("(prefers-reduced-motion: reduce)").matches)); setState("starting"); timer = setTimeout(() => { dispose(); setHtml(""); setState("error"); }, 15000); }
      } catch { if (active) setState("error"); }
    })();
    return () => { active = false; abort.abort(); clearTimeout(timer); dispose(); window.removeEventListener("message", message); document.removeEventListener("visibilitychange", visibility); };
  }, [spec, attempt, closed]);
  useEffect(() => {
    if (!expanded) return;
    const overflow = document.body.style.overflow; document.body.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setExpanded(false); };
    document.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = overflow; document.removeEventListener("keydown", onKey); };
  }, [expanded]);
  return <section ref={root} className={`simulation-player${expanded ? " simulation-expanded" : ""}`} aria-label={spec.title} data-simulation-engine={spec.engine} data-simulation-state={closed ? "closed" : state}>
    <header><strong>{spec.title}</strong><span><button onClick={() => setExpanded(v => !v)} aria-expanded={expanded}>{expanded ? "Compact view" : "Expand"}</button><button onClick={() => { setClosed(v => !v); setExpanded(false); }}>{closed ? "Open" : "Close"}</button></span></header>
    <p>{spec.description}</p>
    {!closed && <>{(state === "compiling" || state === "starting" || state === "ready") && <SimulationProgress key={attempt} stage={state} />}
      {state === "error" ? <p role="alert">This simulation could not run. Your explanation is still available.</p> : html && <iframe ref={frame} title={spec.title} srcDoc={html} sandbox="allow-scripts" allow="camera 'none'; microphone 'none'; geolocation 'none'; payment 'none'; clipboard-read 'none'; clipboard-write 'none'" referrerPolicy="no-referrer" />}
      <button onClick={() => setAttempt(v => v + 1)}>Reset simulation</button></>}
  </section>;
}
