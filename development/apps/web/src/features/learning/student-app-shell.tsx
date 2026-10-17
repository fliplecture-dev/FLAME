"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { BookOpen, Library, Lightbulb, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { StudentProfile } from "./student-profile";
import { ModeSwitcher, type LearningMode } from "./mode-switcher";
import { DesktopPaneResizer } from "./desktop-pane-resizer";
import { ThemeToggle } from "./theme-toggle";
import Link from "next/link";
import { FliplectureLogo } from "@/components/ui/fliplecture-logo";

const layoutPreferenceKey = "flame.sidebar.collapsed";
export function StudentAppShell({ navigation, breadcrumb, children, mode, onModeChange, headerAction, explorePanel, accountAllowance, guest = false }: {
  accountAllowance?: ReactNode; guest?: boolean; navigation: ReactNode; breadcrumb: ReactNode; children: ReactNode; mode: LearningMode; onModeChange: (mode: LearningMode) => void; headerAction?: ReactNode; explorePanel?: ReactNode;
}) {
  const app = useRef<HTMLDivElement>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [device, setDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const railTrigger = useRef<HTMLButtonElement>(null);
  const collapseTrigger = useRef<HTMLButtonElement>(null);
  const focusLearning = useRef(false);
  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;
    const resize = () => { if (app.current && viewport.scale === 1) app.current.style.height = `${viewport.height}px`; };
    resize(); viewport.addEventListener("resize", resize);
    return () => viewport.removeEventListener("resize", resize);
  }, []);
  useEffect(() => {
    const phone = window.matchMedia("(max-width: 767px)");
    const compact = window.matchMedia("(max-width: 1099px)");
    const sync = () => {
      dialog.current?.close(); setOpen(false);
      // Resizing into tablet layout must not open navigation over active content.
      if (compact.matches && !phone.matches) setCollapsed(true);
      setDevice(phone.matches ? "mobile" : compact.matches ? "tablet" : "desktop");
    };
    sync();
    try { const saved = localStorage.getItem(layoutPreferenceKey); setCollapsed(saved === null ? compact.matches : saved === "true"); }
    catch { setCollapsed(compact.matches); }
    setReady(true);
    phone.addEventListener("change", sync); compact.addEventListener("change", sync);
    return () => { phone.removeEventListener("change", sync); compact.removeEventListener("change", sync); };
  }, []);
  useEffect(() => {
    if (!ready || device !== "tablet") return;
    if (!collapsed) { dialog.current?.showModal(); setOpen(true); }
    else { dialog.current?.close(); setOpen(false); }
  }, [ready, device, collapsed]);
  function rememberCollapse(value: boolean) {
    setCollapsed(value);
    try { localStorage.setItem(layoutPreferenceKey, String(value)); } catch { /* Layout still works when browser storage is unavailable. */ }
  }
  function close() {
    dialog.current?.close(); setOpen(false);
    if (device === "tablet") rememberCollapse(true);
    (device === "mobile" ? trigger : railTrigger).current?.focus();
  }
  function expand() {
    rememberCollapse(false);
    if (device === "desktop") requestAnimationFrame(() => collapseTrigger.current?.focus());
  }
  function showLearning() {
    focusLearning.current = true;
    onModeChange("study");
    rememberCollapse(false);
  }
  useEffect(() => {
    if (!focusLearning.current || collapsed || mode !== "study") return;
    const surface = device === "tablet" ? dialog.current : app.current?.querySelector(".desktop-sidebar");
    const heading = surface?.querySelector<HTMLElement>(".curriculum-heading h2");
    if (!heading || !heading.getClientRects().length) return;
    focusLearning.current = false;
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
    heading.scrollIntoView({ block: "nearest" });
  }, [collapsed, mode, device, open]);
  const switcher = <ModeSwitcher mode={mode} onChange={onModeChange} studyLocked={guest} />;
  const brandSwitcher = <div className="workspace-brand"><Link className="workspace-product-link" href="/" aria-label="Fliplecture home"><FliplectureLogo /></Link><ModeSwitcher mode={mode} onChange={onModeChange} studyLocked={guest} variant="brand" /></div>;
  return <div ref={app} className={`student-app ${collapsed ? "sidebar-hidden" : ""}`}>
    <header className="flame-topbar"><button ref={trigger} className="icon-button navigation-toggle" aria-label="Open navigation" aria-expanded={open} onClick={() => { dialog.current?.showModal(); setOpen(true); }}><PanelLeftOpen size={20} /></button><div className="workspace-modes">{switcher}</div><ThemeToggle /></header>
    <a className="skip-link" href="#learning-workspace">Skip to learning workspace</a>
    <aside className="desktop-sidebar" aria-label="Learning navigation">
      <div className="sidebar-brand">{brandSwitcher}<button ref={collapseTrigger} className="icon-button" title="Collapse sidebar" aria-label="Collapse sidebar" onClick={() => { rememberCollapse(true); requestAnimationFrame(() => railTrigger.current?.focus()); }}><PanelLeftClose size={18} /></button></div>
      <div className="sidebar-scroll">{navigation}</div>
      <div className="sidebar-account">{device === "desktop" && !collapsed && <StudentProfile guest={guest} allowance={accountAllowance} />}</div>
      <DesktopPaneResizer pane="sidebar" />
    </aside>
    <aside className="sidebar-rail" aria-label="Compact learning navigation">
      {brandSwitcher}
      <button ref={railTrigger} className="rail-button" aria-label="Expand sidebar" aria-expanded={device === "tablet" ? open : !collapsed} data-tooltip="Expand sidebar" onClick={expand}><PanelLeftOpen size={20} aria-hidden="true" /></button>
      <nav aria-label="Quick learning actions">
        <button className="rail-button" aria-label="Study" aria-pressed={mode === "study"} data-tooltip="Study" onClick={() => onModeChange("study")}><BookOpen size={20} aria-hidden="true" /></button>
        <button className="rail-button" aria-label="Curiosity" aria-pressed={mode === "curiosity"} data-tooltip="Curiosity" onClick={() => onModeChange("curiosity")}><Lightbulb size={20} aria-hidden="true" /></button>
        <button className="rail-button" aria-label="My Learning" data-tooltip="My Learning" onClick={showLearning}><Library size={20} aria-hidden="true" /></button>
      </nav>
      <div className="sidebar-account">{device !== "mobile" && (collapsed || device === "tablet") && <StudentProfile compact guest={guest} allowance={accountAllowance} />}</div>
    </aside>
    <dialog ref={dialog} className="curriculum-drawer" aria-label="Learning navigation" onClose={() => setOpen(false)} onCancel={event => { event.preventDefault(); close(); }} onClick={e => { if (e.target === e.currentTarget) close(); }} onKeyDown={e => {
      if (e.key !== "Tab") return;
      const items = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), input, summary, a[href]')).filter(el => el.getClientRects().length);
      const first = items[0], last = items.at(-1);
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    }}>
      <div className="drawer-inner"><div className="sidebar-brand">{brandSwitcher}<button className="icon-button" aria-label="Close navigation" onClick={close}><X size={20} /></button></div>
      <div className="drawer-navigation" onClick={e => { if ((e.target as HTMLElement).closest('.topic-button, .topic-open, .shortcut-link')) close(); }}>{navigation}</div><div className="sidebar-account">{open && <StudentProfile guest={guest} allowance={accountAllowance} />}</div></div>
    </dialog>
    <main id="learning-workspace" className="workspace" tabIndex={-1}>
      <header className="workspace-header"><div className="workspace-breadcrumb">{breadcrumb}</div><span className="workspace-motto">A calmer way to learn</span>{headerAction}</header>
      <div className="learning-columns"><div className="learning-column">{children}</div>{explorePanel}</div>
    </main>
  </div>;
}
