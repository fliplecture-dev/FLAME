import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, FileText, Pin, Lightbulb, Trash2, MoreHorizontal } from "lucide-react";
import type { LearningMode } from "./mode-switcher";
import type { TopicContext } from "@/features/curriculum/types";
export interface LearningShortcut { id: string; title: string; mode: LearningMode; context?: TopicContext; pinned?: boolean; groupIds?: string[]; recentAt?: string | null }
export function LearningShortcuts({ title, items, activeId, expanded, onExpandedChange, onSelect, onPin, onDelete, onSectionAction, busy = false }: {
  title: "Pinned" | "Recent"; items: LearningShortcut[]; activeId: string; expanded: boolean;
  onExpandedChange: (expanded: boolean) => void; onSelect: (item: LearningShortcut) => void;
  onPin: (item: LearningShortcut) => void; onDelete: (item: LearningShortcut) => void;
  onSectionAction: () => void; busy?: boolean;
}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const action = title === "Pinned" ? "Unpin all" : "Clear recent history";
  function closeMenu(focus = false) { setPosition(null); if (focus) trigger.current?.focus(); }
  function openMenu() {
    if (position) { closeMenu(); return; }
    const rect = trigger.current?.getBoundingClientRect();
    if (!rect) return;
    setPosition({ left: Math.max(8, Math.min(rect.right - 190, window.innerWidth - 198)),
      top: rect.bottom + 54 > window.innerHeight ? Math.max(8, rect.top - 50) : rect.bottom + 4 });
  }
  useEffect(() => {
    if (!position) return;
    menu.current?.querySelector<HTMLButtonElement>("button")?.focus();
    function outside(event: PointerEvent) {
      if (!menu.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) closeMenu();
    }
    function escape(event: KeyboardEvent) { if (event.key === "Escape") { event.preventDefault(); closeMenu(true); } }
    function dismiss() { closeMenu(); }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    window.addEventListener("resize", dismiss);
    window.addEventListener("scroll", dismiss, true);
    return () => {
      document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape);
      window.removeEventListener("resize", dismiss); window.removeEventListener("scroll", dismiss, true);
    };
  }, [position]);
  return <section className="shortcut-section" aria-labelledby={`${id}-label`}>
    <div className="shortcut-header">
      <button className="shortcut-toggle" id={`${id}-label`} aria-expanded={expanded} aria-controls={`${id}-items`} onClick={() => onExpandedChange(!expanded)}>
        <span>{title}</span><ChevronDown size={14} className={expanded ? "" : "collapsed"} aria-hidden="true" />
      </button>
      <button ref={trigger} className="icon-button shortcut-overflow" aria-label={`${title} options`} title={`${title} options`} aria-haspopup="menu" aria-expanded={Boolean(position)} aria-controls={position ? `${id}-menu` : undefined} onClick={event => { event.stopPropagation(); openMenu(); }} onKeyDown={event => { if (event.key === "ArrowDown") { event.preventDefault(); if (!position) openMenu(); } }}><MoreHorizontal size={16} aria-hidden="true" /></button>
    </div>
    <div id={`${id}-items`} hidden={!expanded}>
      {items.length ? <ul>{items.map(item => <li key={item.id}>
        <button className={`shortcut-link ${activeId === item.id ? "active" : ""}`} title={item.title} onClick={() => onSelect(item)}>{item.mode === "study" ? <FileText size={15} aria-hidden="true" /> : <Lightbulb size={15} aria-hidden="true" />}<span>{item.title}</span><span className="sr-only">({item.mode})</span></button>
        <button className={`icon-button shortcut-action ${item.pinned ? "is-pinned" : ""}`} disabled={busy} aria-pressed={Boolean(item.pinned)} title={item.pinned ? "Unpin conversation" : "Pin conversation"} aria-label={`${item.pinned ? "Unpin" : "Pin"} conversation: ${item.title}`} onClick={event => { event.stopPropagation(); onPin(item); }}><Pin size={14} fill={item.pinned ? "currentColor" : "none"} aria-hidden="true" /></button>
        <button className="icon-button shortcut-action" disabled={busy} title={`Delete ${item.title}`} aria-label={`Delete ${item.title}`} onClick={event => { event.stopPropagation(); onDelete(item); }}><Trash2 size={14} aria-hidden="true" /></button>
      </li>)}</ul> : <p className="shortcut-empty">{title === "Pinned" ? "No pinned conversations yet." : "No recent conversations."}</p>}
    </div>
    {position && createPortal(<div ref={menu} id={`${id}-menu`} className="shortcut-menu" role="menu" aria-label={`${title} options`} style={position} onKeyDown={event => { if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) { event.preventDefault(); menu.current?.querySelector<HTMLButtonElement>("button")?.focus(); } if (event.key === "Tab") closeMenu(); }}>
      <button role="menuitem" disabled={busy || !items.length} onClick={event => { event.stopPropagation(); closeMenu(true); onSectionAction(); }}>{action}</button>
    </div>, trigger.current?.closest("dialog") ?? document.body)}
  </section>;
}
