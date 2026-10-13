import { Trash2, BookOpen, ChevronRight, FileText, Search, Plus, Folder, GraduationCap, ListFilter, ChevronDown, X } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { ProficiencyIndicator } from "@/features/progress/proficiency-indicator";
import type { Curriculum, TopicContext } from "./types";
import { allBranchKeys, contextKey, filterCurricula, nodeKey, type ProgressFilter } from "./learning-tree";

export interface TreeViewState { query: string; filter: ProgressFilter; expanded: string[] }
function SubtopicSearch({ id, query, inputRef, onSearch, onClose }: {
  id: string; query: string; inputRef: RefObject<HTMLInputElement | null>;
  onSearch: (query: string) => void; onClose: () => void;
}) {
  const [draft, setDraft] = useState(query);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestSearch = useRef(onSearch);
  latestSearch.current = onSearch;
  useEffect(() => {
    if (document.activeElement !== inputRef.current) setDraft(query);
  }, [query, inputRef]);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  function change(next: string) {
    setDraft(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => { timer.current = null; latestSearch.current(next); }, 180);
  }
  return <div id={id} className="curriculum-search" onKeyDown={e => {
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onClose(); }
  }}><label className="sr-only" htmlFor={`${id}-input`}>Find a subtopic</label><Search size={16} aria-hidden="true" />
    <input ref={inputRef} id={`${id}-input`} type="search" value={draft} onChange={e => change(e.target.value)} placeholder="Find a subtopic" />
    <button className="icon-button" aria-label="Close search" title="Close search" onClick={onClose}><X size={15} /></button>
  </div>;
}

function Progress({ value }: { value: number | null }) { return <span className="tree-progress" aria-label={value === null ? "Progress unavailable" : `${value}% progress`}>{value === null ? "—" : `${value}%`}</span>; }
function Branch({ label, icon, progress, expanded, onToggle, onOpen, selected, onRemove, children }: { label: string; icon: ReactNode; progress?: number | null; expanded: boolean; onToggle: () => void; onOpen?: () => void; selected?: boolean; onRemove?: () => void; children: ReactNode }) {
  const id = useId();
  return <li className="learning-branch"><div className="branch-row">{onOpen ? <>
    <button className="branch-expand" aria-expanded={expanded} aria-controls={id} aria-label={`${expanded ? "Collapse" : "Expand"} subtopics for ${label}`} onClick={onToggle}><ChevronRight size={14} aria-hidden="true" /></button>
    <button className={`branch-button topic-open ${selected ? "selected" : ""}`} aria-current={selected ? "page" : undefined} onClick={onOpen} title={`Ask about ${label}`}>{icon}<span className="tree-label">{label}</span></button>
  </> : <button className="branch-button" aria-expanded={expanded} aria-controls={id} onClick={onToggle} title={label}><ChevronRight className="branch-chevron" size={14} aria-hidden="true" />{icon}<span className="tree-label">{label}</span>{progress !== undefined && <Progress value={progress} />}</button>}{onRemove && <button className="curriculum-remove" aria-label={`Remove ${label} from My Learning`} title={`Remove ${label}`} onClick={onRemove}><Trash2 size={14} aria-hidden="true" /></button>}</div><ul id={id} hidden={!expanded}>{children}</ul></li>;
}
export function CurriculumNavigator({ curricula, selectedId, onSelect, view, onViewChange, onOpenLibrary, onRemoveCurriculum, onRemoveSubject, sectionExpanded, onSectionExpandedChange, live = false }: {
  sectionExpanded: boolean; onSectionExpandedChange: (expanded: boolean) => void;
  curricula: Curriculum[]; live?: boolean; selectedId?: string; onSelect: (context: TopicContext) => void; view: TreeViewState; onViewChange: (view: TreeViewState) => void; onOpenLibrary: () => void; onRemoveCurriculum: (id: string) => void; onRemoveSubject: (curriculumId: string, levelId: string, subjectId: string) => void;
}) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const searchButton = useRef<HTMLButtonElement>(null);
  const filterButton = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const filterSelect = useRef<HTMLSelectElement>(null);
  const sectionId = useId();
  const searchId = useId();
  const filterId = useId();
  const showSearch = searchOpen || Boolean(view.query);
  function closeSearch() { setSearchOpen(false); filterView("", view.filter); searchButton.current?.focus(); }
  function closeFilter() { setFilterOpen(false); filterButton.current?.focus(); }
  const filtered = useMemo(() => filterCurricula(curricula, view.query, view.filter), [curricula, view.query, view.filter]);
  const expandedKeys = useMemo(() => new Set(view.expanded), [view.expanded]);
  function toggle(key: string) { onViewChange({ ...view, expanded: view.expanded.includes(key) ? view.expanded.filter(id => id !== key) : [...view.expanded, key] }); }
  function filterView(query: string, filter: ProgressFilter) { onViewChange({ query, filter, expanded: allBranchKeys(filterCurricula(curricula, query, filter)) }); }
  const count = filtered.reduce((total, c) => total + c.levels.reduce((n, l) => n + l.subjects.reduce((m, s) => m + s.domains.reduce((k, d) => k + d.topics.reduce((j, t) => j + t.subtopics.length, 0), 0), 0), 0), 0);
  return <nav aria-label="Curriculum" className="curriculum-navigation">
    <div className="curriculum-heading"><h2><button className="shortcut-toggle" aria-expanded={sectionExpanded} aria-controls={sectionId} onClick={() => onSectionExpandedChange(!sectionExpanded)}><span>My Learning</span><ChevronDown size={14} className={sectionExpanded ? "" : "collapsed"} aria-hidden="true" /></button></h2>{sectionExpanded && <div className="learning-toolbar">
      <button className="icon-button" title="Add from Library" aria-label="Add from Library" onClick={onOpenLibrary}><Plus size={17} /></button>
      <button ref={searchButton} className="icon-button" title="Find a subtopic" aria-label="Find a subtopic" aria-expanded={showSearch} aria-controls={searchId} onClick={() => { if (showSearch) closeSearch(); else { setSearchOpen(true); requestAnimationFrame(() => searchInput.current?.focus()); } }}><Search size={17} /></button>
      {!live && <button ref={filterButton} className={`icon-button filter-toggle ${view.filter !== "all" ? "filter-active" : ""}`} title={view.filter === "all" ? "Filter learning" : `Filter learning: ${view.filter}`} aria-label={view.filter === "all" ? "Filter learning" : "Filter learning (active)"} aria-expanded={filterOpen} aria-controls={filterId} onClick={() => { if (filterOpen) closeFilter(); else { setFilterOpen(true); requestAnimationFrame(() => filterSelect.current?.focus()); } }}><ListFilter size={17} />{view.filter !== "all" && <span className="filter-dot" aria-hidden="true" />}</button>}
    </div>}</div>
    <div id={sectionId} hidden={!sectionExpanded}>{sectionExpanded && <>
    {showSearch && <SubtopicSearch id={searchId} query={view.query} inputRef={searchInput} onSearch={query => filterView(query, view.filter)} onClose={closeSearch} />}
    {!live && filterOpen && <div id={filterId} className="learning-filter" onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeFilter(); } }}><label className="sr-only" htmlFor={`${filterId}-select`}>Filter My Learning</label><select ref={filterSelect} id={`${filterId}-select`} value={view.filter} onChange={e => { filterView(view.query, e.target.value as ProgressFilter); closeFilter(); }}><option value="all">All learning</option><option value="in-progress">In Progress</option><option value="mastered">Mastered</option><option value="not-started">Not Started</option></select><button className="icon-button" aria-label="Close filter" title="Close filter" onClick={closeFilter}><X size={15} /></button></div>}
    {(view.query || view.filter !== "all") && <p className="search-count" role="status">{count} matching subtopic{count === 1 ? "" : "s"}</p>}
    {!filtered.length && <div className="navigation-empty"><p>{curricula.length ? "No subtopics match these filters." : "Your learning space is empty."}</p>{!curricula.length && <button className="clear-filters" onClick={onOpenLibrary}>Add from Library</button>}{curricula.length > 0 && <button className="clear-filters" onClick={() => filterView("", "all")}>Clear filters</button>}</div>}
    <ul className="learning-tree">{filtered.map(c => <Branch key={c.id} label={c.name} icon={<GraduationCap size={16} aria-hidden="true" />} progress={c.progress} expanded={expandedKeys.has(nodeKey(c.id))} onToggle={() => toggle(nodeKey(c.id))} onRemove={() => onRemoveCurriculum(c.id)}>
      {expandedKeys.has(nodeKey(c.id)) && c.levels.map(l => <Branch key={l.id} label={l.name} icon={<Folder size={16} aria-hidden="true" />} progress={l.progress} expanded={expandedKeys.has(nodeKey(c.id, l.id))} onToggle={() => toggle(nodeKey(c.id, l.id))}>
        {expandedKeys.has(nodeKey(c.id, l.id)) && l.subjects.map(s => <Branch key={s.id} label={s.name} icon={<BookOpen size={16} aria-hidden="true" />} progress={s.progress} expanded={expandedKeys.has(nodeKey(c.id, l.id, s.id))} onToggle={() => toggle(nodeKey(c.id, l.id, s.id))} onRemove={() => onRemoveSubject(c.id, l.id, s.id)}>
          {expandedKeys.has(nodeKey(c.id, l.id, s.id)) && s.domains.map(d => <Branch key={d.id} label={d.name} icon={<Folder size={16} aria-hidden="true" />} progress={d.progress} expanded={expandedKeys.has(nodeKey(c.id, l.id, s.id, d.id))} onToggle={() => toggle(nodeKey(c.id, l.id, s.id, d.id))}>
            {expandedKeys.has(nodeKey(c.id, l.id, s.id, d.id)) && d.topics.map(t => <Branch key={`${t.categoryId ?? "none"}:${t.id}`} label={t.name} icon={<FileText size={16} aria-hidden="true" />} expanded={expandedKeys.has(nodeKey(c.id, l.id, s.id, d.id, t.categoryId, t.id))} onToggle={() => toggle(nodeKey(c.id, l.id, s.id, d.id, t.categoryId, t.id))} onOpen={() => onSelect({ curriculum: c, level: l, subject: s, domain: d, topic: t })} selected={selectedId === contextKey({ curriculum: c, level: l, subject: s, domain: d, topic: t })}>
              {expandedKeys.has(nodeKey(c.id, l.id, s.id, d.id, t.categoryId, t.id)) && t.subtopics.map(st => {
                const context: TopicContext = { curriculum: c, level: l, subject: s, domain: d, topic: t, subtopic: st };
                const selected = selectedId === contextKey(context);
                return <li key={st.id}><button className={`topic-button ${selected ? "selected" : ""}`} aria-current={selected ? "page" : undefined} title={st.locked ? `${st.name}: ${st.lockReason ?? "Complete prerequisites first"}` : st.name} disabled={st.locked} onClick={() => onSelect(context)}><FileText size={15} aria-hidden="true" /><span className="topic-name">{st.name}</span><ProficiencyIndicator value={st.proficiency} /></button></li>;
              })}
            </Branch>)}
          </Branch>)}
        </Branch>)}
      </Branch>)}
    </Branch>)}</ul>
    {!live && <details className="proficiency-guide"><summary>Understanding proficiency <Plus size={14} aria-hidden="true" /></summary><dl>{[["0", "Not started"], ["1–2", "Initial exposure"], ["3–4", "Developing"], ["5–6", "Basic understanding"], ["7–8", "Strong understanding"], ["9", "Near mastery"], ["10", "Mastered"]].map(([score, label]) => <div key={score}><dt>{score}</dt><dd>{label}</dd></div>)}</dl></details>}
    </>}</div>
  </nav>;
}
