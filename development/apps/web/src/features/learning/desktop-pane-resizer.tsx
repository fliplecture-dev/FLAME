"use client";
import { useEffect, useRef, useState } from "react";

export function DesktopPaneResizer({ pane }: { pane: "sidebar" | "explore" }) {
  const handle = useRef<HTMLDivElement>(null);
  const drag = useRef<{ root:HTMLElement; x:number; width:number } | null>(null);
  const minimum = pane === "sidebar" ? 220 : 300;
  const defaultWidth = pane === "sidebar" ? 280 : 440;
  const [width, setWidth] = useState(defaultWidth);
  const property = `--flame-${pane}-width`, key = `flame.layout.${pane}.width`;
  function root() { return handle.current?.closest<HTMLElement>(".student-app") ?? null; }
  function actual(container:HTMLElement) {
    return container.querySelector<HTMLElement>(pane === "sidebar" ? ".desktop-sidebar" : ".explore-panel")?.getBoundingClientRect().width ?? defaultWidth;
  }
  function maximum(container:HTMLElement) {
    const other = container.querySelector<HTMLElement>(pane === "sidebar" ? ".explore-panel[open]" : container.classList.contains("sidebar-hidden") ? ".sidebar-rail" : ".desktop-sidebar");
    const occupied = other?.getBoundingClientRect().width ?? 0;
    return Math.max(minimum, Math.min(pane === "sidebar" ? 520 : 760, container.clientWidth - (pane === "sidebar" ? Math.max(300, occupied) : occupied) - 400));
  }
  function apply(container:HTMLElement, value:number) {
    const next = Math.round(Math.min(maximum(container), Math.max(minimum, value)));
    container.style.setProperty(property, `${next}px`); setWidth(next); return next;
  }
  function save(value:number) { try { localStorage.setItem(key, String(value)); } catch { /* Resizing works without storage. */ } }
  function finish() {
    if (!drag.current) return;
    const { root:container, width:start } = drag.current; drag.current = null;
    const current = actual(container);
    container.classList.remove("pane-resizing"); save(Math.round(current >= minimum ? current : Number.parseFloat(container.style.getPropertyValue(property)) || start));
  }
  useEffect(() => {
    const container = root(); if (!container) return;
    try { const saved = Number(localStorage.getItem(key)); if (Number.isFinite(saved) && saved >= minimum && saved <= (pane === "sidebar" ? 520 : 760)) { container.style.setProperty(property, `${saved}px`); setWidth(saved); } } catch { /* Default layout remains available. */ }
    const sync = () => { finish(); setWidth(Math.round(actual(container))); };
    const observer = new ResizeObserver(() => { const value = Math.round(actual(container)); if (value >= minimum) setWidth(previous => previous === value ? previous : value); });
    const target = container.querySelector(pane === "sidebar" ? ".desktop-sidebar" : ".explore-panel");
    if (target) observer.observe(target);
    window.addEventListener("resize", sync);
    return () => { observer.disconnect(); window.removeEventListener("resize", sync); container.classList.remove("pane-resizing"); };
  }, [pane]);
  return <div ref={handle} className={`desktop-pane-resizer resize-${pane}`} role="separator" tabIndex={0}
    aria-label={pane === "sidebar" ? "Resize navigation sidebar" : "Resize Explore panel"} aria-orientation="vertical"
    aria-valuemin={minimum} aria-valuemax={root() ? maximum(root()!) : pane === "sidebar" ? 520 : 760} aria-valuenow={width}
    title="Drag to resize. Arrow keys adjust width. Double-click to reset."
    onPointerDown={event => {
      if (event.button !== 0 || !matchMedia(pane === "sidebar" ? "(min-width:1100px)" : "(min-width:1280px)").matches) return;
      const container = root(); if (!container) return;
      event.preventDefault(); event.currentTarget.focus(); event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = { root:container, x:event.clientX, width:actual(container) }; container.classList.add("pane-resizing");
    }} onPointerMove={event => { if (drag.current) apply(drag.current.root, drag.current.width + (event.clientX - drag.current.x) * (pane === "sidebar" ? 1 : -1)); }}
    onPointerUp={finish} onPointerCancel={finish} onLostPointerCapture={finish}
    onDoubleClick={() => { const container = root(); if (container) save(apply(container, defaultWidth)); }}
    onKeyDown={event => {
      if (!["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
      const container = root(); if (!container) return;
      event.preventDefault(); const step = event.shiftKey ? 48 : 16;
      save(apply(container, event.key === "Home" ? minimum : event.key === "End" ? maximum(container) : actual(container) + (event.key === "ArrowRight" ? step : -step) * (pane === "sidebar" ? 1 : -1)));
    }} />;
}
