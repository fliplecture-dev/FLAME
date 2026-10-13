"use client";

import { useEffect, useRef, useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import styles from "./interactive-experience.module.css";

// Always isolate uploaded code; it receives no FLAME session or parent DOM access.
// Match the API policy: embedded Rive WASM can compile; JS eval and network remain blocked.
const policy = "default-src 'none'; script-src 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; img-src data:; media-src data:; font-src data:; connect-src 'none'; frame-src 'none'; worker-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
export function InteractiveExperience({ document: htmlDocument, title }: { document: string; title: string }) {
  const [attempt, setAttempt] = useState(0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const root = useRef<HTMLElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const expandedRef = useRef(false);
  const generation = useRef(0);

  function restore() {
    generation.current++;
    expandedRef.current = false;
    setExpanded(false);
    if (document.fullscreenElement === root.current) void document.exitFullscreen().catch(() => {});
    toggle.current?.focus({ preventScroll: true });
  }
  async function enterFullscreen() {
    const element = root.current;
    if (!element) return;
    const request = ++generation.current;
    expandedRef.current = true;
    setExpanded(true);
    // Keep the same iframe alive: resizing must preserve the running experiment.
    try {
      if (element.requestFullscreen) await element.requestFullscreen();
    } catch { /* Use the viewport-sized landscape fallback when native fullscreen is unavailable. */ }
    if (request !== generation.current) {
      if (document.fullscreenElement === element) void document.exitFullscreen().catch(() => {});
      return;
    }
  }
  useEffect(() => {
    const element = root.current;
    function fullscreenChanged() {
      if (document.fullscreenElement === element || !expandedRef.current) return;
      restore();
    }
    document.addEventListener("fullscreenchange", fullscreenChanged);
    return () => {
      generation.current++;
      expandedRef.current = false;
      document.removeEventListener("fullscreenchange", fullscreenChanged);
      if (document.fullscreenElement === element) void document.exitFullscreen().catch(() => {});
    };
  }, []);
  useEffect(() => {
    if (!expanded) return;
    const dialog = root.current?.closest("dialog");
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    toggle.current?.focus({ preventScroll: true });
    function cancel(event: Event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      restore();
    }
    function keyboard(event: KeyboardEvent) {
      if (event.key === "Escape") { cancel(event); return; }
      // Fallback fullscreen remains inside the existing modal; keep focus in its visible controls.
      if (event.key !== "Tab") return;
      const controls = root.current?.querySelectorAll<HTMLElement>("button, iframe");
      if (!controls?.length) return;
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    dialog?.addEventListener("cancel", cancel, true);
    document.addEventListener("keydown", keyboard, true);
    return () => {
      document.body.style.overflow = previousOverflow;
      dialog?.removeEventListener("cancel", cancel, true);
      document.removeEventListener("keydown", keyboard, true);
    };
  }, [expanded]);
  useEffect(() => {
    if (ready) return;
    const timer = setTimeout(() => setError(true), 20000);
    return () => clearTimeout(timer);
  }, [attempt, ready]);
  const source = `<meta http-equiv="Content-Security-Policy" content="${policy}">` + htmlDocument;
  return <section ref={root} aria-label={title} className={`${styles.viewer} ${expanded ? styles.expanded : ""}`} data-interactive-fullscreen={expanded}>
    <div className={styles.stage}>
    <header className={styles.toolbar}>
      <span className={styles.title}>{title}</span>
      <button ref={toggle} type="button" className={styles.toggle} aria-label={expanded ? "Restore compact interactive" : "Full screen interactive"} title={expanded ? "Restore compact view" : "Full screen (landscape)"} aria-pressed={expanded} onClick={() => expanded ? restore() : void enterFullscreen()}>
        {expanded ? <Minimize2 size={20} aria-hidden="true" /> : <Maximize2 size={20} aria-hidden="true" />}
      </button>
    </header>
    {!ready && !error && <p role="status">Loading interactive…</p>}
    <div className={styles.viewport}>
    {error ? <div role="alert"><p>This interactive could not load.</p><button onClick={() => { setReady(false); setError(false); setAttempt(value => value + 1); }}>Try again</button></div> :
      <iframe className={styles.frame} key={attempt} title={title} srcDoc={source} sandbox="allow-scripts" referrerPolicy="no-referrer" onLoad={() => setReady(true)} onError={() => setError(true)} />}
    </div>
    <button style={{ marginTop: 12, padding: "8px 12px", border: "1px solid #e6e8ed", borderRadius: 8, background: "#fff", color: "#111827", cursor: "pointer" }} onClick={() => { setReady(false); setError(false); setAttempt(value => value + 1); }}>Restart interactive</button>
    </div>
  </section>;
}
