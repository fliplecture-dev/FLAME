import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Trash2, BookOpen, Check, Plus, Search, X } from "lucide-react";
import { getLearningLibrary } from "@/lib/api/student-learning";
import type { Curriculum } from "./types";
import { includesLearningPath } from "./merge-learning-path";
import { libraryItems, type LibraryTab } from "./library-items";

export function LearningLibrary({ learning, catalogue, onAdd, onRemoveCurriculum, onRemoveSubject, onClose, live = false }: {
  learning: Curriculum[];
  catalogue?: Curriculum[];
  onAdd: (path: Curriculum[], kind?: string) => Promise<void> | void;
  onRemoveCurriculum: (id: string, after?: () => void) => void;
  onRemoveSubject: (curriculumId: string, levelId: string, subjectId: string, after?: () => void) => void;
  onClose: () => void;
  live?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [catalog, setCatalog] = useState<Curriculum[]>(catalogue ?? []);
  const [loading, setLoading] = useState(!catalogue);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [tab, setTab] = useState<LibraryTab>("curriculum");
  const [query, setQuery] = useState("");
  const [curriculumFilter, setCurriculumFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [domainFilter, setDomainFilter] = useState("");
  const [notice, setNotice] = useState("");
  const id = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const el = dialog.current; el?.showModal();
    return () => { el?.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  useEffect(() => {
    if (catalogue) { setCatalog(catalogue); setLoading(false); setError(false); return; }
    let cancelled = false; setLoading(true); setError(false);
    getLearningLibrary(live).then(data => { if (!cancelled) setCatalog(data); }).catch(() => { if (!cancelled) setError(true); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [attempt, live, catalogue]);
  const visibleCurricula = catalog.filter(c => !curriculumFilter || c.id === curriculumFilter);
  const levels = visibleCurricula.flatMap(c => c.levels.map(l => ({
    value: l.id, label: curriculumFilter ? l.name : `${l.name} · ${c.name}`,
  })));
  const subjects = visibleCurricula.flatMap(c => c.levels
    .filter(l => !levelFilter || l.id === levelFilter)
    .flatMap(l => l.subjects.map(s => ({
      value: JSON.stringify([c.id, l.id, s.id]),
      label: levelFilter ? s.name : `${s.name} · ${l.name} · ${c.name}`,
    }))));
  const domains = visibleCurricula.flatMap(c => c.levels
    .filter(l => !levelFilter || l.id === levelFilter)
    .flatMap(l => l.subjects
      .filter(s => !subjectFilter || JSON.stringify([c.id, l.id, s.id]) === subjectFilter)
      .flatMap(s => s.domains.map(d => ({
        value: JSON.stringify([c.id, l.id, s.id, d.id]),
        label: `${d.name} · ${s.name} · ${l.name}`,
      })))));
  const items = useMemo(() => libraryItems(catalog, tab).filter(item => {
    if (curriculumFilter && item.curriculum.id !== curriculumFilter) return false;
    if (levelFilter && item.levelId && item.levelId !== levelFilter) return false;
    if (levelFilter && !item.levelId && !item.curriculum.levels.some(l => l.id === levelFilter)) return false;
    if (subjectFilter && JSON.stringify([item.curriculum.id, item.levelId, item.subjectId]) !== subjectFilter) return false;
    if (domainFilter && JSON.stringify([item.curriculum.id, item.levelId, item.subjectId, item.domainId]) !== domainFilter) return false;
    return `${item.title} ${item.subtitle}`.toLowerCase().includes(query.trim().toLowerCase());
  }), [catalog, tab, curriculumFilter, levelFilter, subjectFilter, domainFilter, query]);
  function changeTab(next: LibraryTab) { setTab(next); setQuery(""); setSubjectFilter(""); setDomainFilter(""); setNotice(""); }
  function clearFilters() { setQuery(""); setCurriculumFilter(""); setLevelFilter(""); setSubjectFilter(""); setDomainFilter(""); }
  const tabs: LibraryTab[] = ["curriculum", "subject", "topic"];
  return <dialog ref={dialog} className="library-dialog" aria-labelledby={`${id}-title`} onCancel={e => { e.preventDefault(); onClose(); }} onClick={e => { if (e.target === e.currentTarget) onClose(); }} onKeyDown={e => {
    if (e.key !== "Tab") return;
    const controls = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled):not([tabindex="-1"]), input, select, [tabindex="0"]')).filter(el => el.getClientRects().length);
    if (e.shiftKey && document.activeElement === controls[0]) { e.preventDefault(); controls.at(-1)?.focus(); }
    else if (!e.shiftKey && document.activeElement === controls.at(-1)) { e.preventDefault(); controls[0]?.focus(); }
  }}>
    <div className="library-surface">
      <header className="library-header"><div><h2 id={`${id}-title`}>Add from Library</h2><p>Build your learning space, one subject or subtopic at a time.</p></div><button className="icon-button" aria-label="Close library" onClick={onClose}><X size={20} /></button></header>
      <div className="library-tabs" role="tablist" aria-label="Library sections">{tabs.map((t, index) => <button key={t} id={`${id}-${t}`} role="tab" aria-selected={tab === t} aria-controls={`${id}-results`} tabIndex={tab === t ? 0 : -1} onClick={() => changeTab(t)} onKeyDown={e => { let next = index; if (e.key === "ArrowRight") next = (index + 1) % 3; else if (e.key === "ArrowLeft") next = (index + 2) % 3; else if (e.key === "Home") next = 0; else if (e.key === "End") next = 2; else return; e.preventDefault(); changeTab(tabs[next]); document.getElementById(`${id}-${tabs[next]}`)?.focus(); }}>{t === "curriculum" ? "Curriculum" : t === "subject" ? "Subject" : "Topic & Subtopic"}</button>)}</div>
      <div className="library-controls"><label className="library-search"><Search size={18} aria-hidden="true" /><span className="sr-only">Search library</span><input type="search" placeholder="Search curriculum, subject, topic or subtopic…" value={query} onChange={e => setQuery(e.target.value)} /></label>
      <div className="library-filters">
        <label>Curriculum<select aria-label="Curriculum" value={curriculumFilter} onChange={e => { setCurriculumFilter(e.target.value); setLevelFilter(""); setSubjectFilter(""); setDomainFilter(""); }}><option value="">All curricula</option>{catalog.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        <label>Level<select aria-label="Level" value={levelFilter} onChange={e => { setLevelFilter(e.target.value); setSubjectFilter(""); setDomainFilter(""); }}><option value="">All levels</option>{levels.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        {tab !== "curriculum" && <label>Subject<select aria-label="Subject" value={subjectFilter} onChange={e => { setSubjectFilter(e.target.value); setDomainFilter(""); }}><option value="">All subjects</option>{subjects.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>}
        {tab === "topic" && <label>Domain<select aria-label="Domain" value={domainFilter} onChange={e => setDomainFilter(e.target.value)}><option value="">All domains</option>{domains.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>}
      </div></div>
      <div className="library-results" role="tabpanel" id={`${id}-results`} aria-labelledby={`${id}-${tab}`} tabIndex={0} aria-busy={loading}>
        {loading ? <p role="status">Loading library…</p> : error ? <div className="library-empty"><p>The library couldn’t be loaded.</p><button onClick={() => setAttempt(n => n + 1)}>Try again</button></div> : items.length ? <ul>{items.map(item => {
          const added = includesLearningPath(learning, item.path);
          const current = learning.find(c => c.id === item.curriculum.id);
          const removable = tab === "curriculum" ? Boolean(current) : tab === "subject" && Boolean(current?.levels.some(l => l.id === item.levelId && l.subjects.some(s => s.id === item.subjectId)));
          return <li key={item.id}><BookOpen size={19} aria-hidden="true" /><div className="library-item-copy"><small>{item.kind}</small><h3>{item.title}</h3><p>{item.subtitle}</p></div><div className="library-item-actions"><button className="library-add" disabled={added} aria-label={added ? `${item.title} already added` : `Add ${item.title}`} onClick={async () => { try { await onAdd(item.path, item.kind); setNotice(`${item.title} added to My Learning.`); } catch (error) { setNotice(error instanceof Error ? error.message : "The addition could not be saved."); } }}>{added ? <Check size={16} aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}{added ? "Added" : "Add"}</button>{removable && <button className="library-remove" aria-label={`Remove ${item.title} from My Learning`} onClick={() => { const after = () => setNotice(`${item.title} removed. Add it again to restore progress in this tab.`); if (tab === "subject" && item.levelId && item.subjectId) onRemoveSubject(item.curriculum.id, item.levelId, item.subjectId, after); else onRemoveCurriculum(item.curriculum.id, after); }}><Trash2 size={15} aria-hidden="true" />Remove</button>}</div></li>;
        })}</ul> : <div className="library-empty"><p>No results match your search and filters.</p><button onClick={clearFilters}>Clear filters</button></div>}
      </div><footer className="library-footer"><span role="status">{notice || "Added items keep their curriculum and subject context."}</span><button onClick={onClose}>Done</button></footer>
    </div>
  </dialog>;
}
