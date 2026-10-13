"use client";
import { useEffect, useMemo, useRef, useState, type ReactNode, type ComponentProps, type CSSProperties } from "react";
import { Compass, ChevronLeft, ChevronRight, Play, Image as ImageIcon, BookOpen, UserRound, Search, SlidersHorizontal } from "lucide-react";
import type { Curriculum, TopicContext } from "@/features/curriculum/types";
import { getLearningLibrary } from "@/lib/api/student-learning";
import { B9Error } from "@/lib/api/b9-client";
import { CatalogueViewer, LearningSupportViewer, type ResourceCard } from "./catalogue-recommendations";
import { ExploreThumbnail } from "./explore-thumbnail";
import { ExploreContext, type ExploreKind } from "./explore-context";
import type { ConversationTurn } from "./conversation-types";
import { DesktopPaneResizer } from "./desktop-pane-resizer";

type Path = { curriculum_id: string; level_id: string; subject_id: string; domain_id?: string; topic_id: string; subtopic_id: string | null; curriculum_revision: number };
type ContextResult = { context: Path | null; candidates?: (Path & { label: string })[] };
type Item = { thumbnail_url?: string | null; has_thumbnail?: boolean; browse_path?: Path; mime_type?: string | null; alt_text?: string | null; id: string; version: number; kind: ExploreKind; type: string; title: string; description: string | null; availability_state: string; coverage: string; languages: string[]; grade_min: number | null; grade_max: number | null };
type Results = { items: Item[]; total: number; offset: number; limit: number };
type Support = Omit<ComponentProps<typeof LearningSupportViewer>, "onClose">;
type Filter = "curriculum" | "level" | "subject" | "domain" | "topic" | "subtopic";
const fields: Filter[] = ["curriculum", "level", "subject", "domain", "topic", "subtopic"];
const emptyFilters = { curriculum: "", level: "", subject: "", domain: "", topic: "", subtopic: "" };
const tabs: { kind: ExploreKind; label: string }[] = [{ kind: "resource", label: "Media" }, { kind: "tutor", label: "Teachers" }, { kind: "kit", label: "Activity Kits" }];
function fromStudy(context: TopicContext | null): Path | null {
  return context ? { curriculum_id: context.curriculum.id, level_id: context.level.id, subject_id: context.subject.id,
    domain_id: context.domain.id, topic_id: context.topic.id, subtopic_id: context.subtopic?.id ?? null, curriculum_revision: context.curriculum.revision ?? 1 } : null;
}
async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch("/api/b9/" + path, { cache: "no-store", signal });
  const data = await response.json();
  if (!response.ok) throw new B9Error(data, response.status);
  return data;
}
function parametersFor(item: Item, fallback: string): string {
  const path = item.browse_path;
  if (!path) return fallback;
  const value = new URLSearchParams({ topic_id: path.topic_id, curriculum_revision: String(path.curriculum_revision) });
  if (path.subtopic_id) value.set("subtopic_id", path.subtopic_id);
  return value.toString();
}

export function ExploreWorkspace({ catalogue, context, curiosity = false, curiosityTurn = null, live, children }: {
  catalogue: Curriculum[]; context: TopicContext | null; live: boolean;
  curiosity?: boolean; curiosityTurn?: ConversationTurn | null;
  children: (trigger: ReactNode, panel: ReactNode) => ReactNode;
}) {
  const [open, setOpen] = useState(false), [narrow, setNarrow] = useState(false);
  const [closing, setClosing] = useState(false);
  const [anchor, setAnchor] = useState({ top:70, offset:-42 });
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (closeTimer.current) clearTimeout(closeTimer.current); }, []);
  const [trees, setTrees] = useState(catalogue);
  const [filters, setFilters] = useState(emptyFilters), [revision, setRevision] = useState<number | null>(null);
  const [kind, setKind] = useState<ExploreKind>("resource"), [query, setQuery] = useState(""), [debounced, setDebounced] = useState("");
  const [pathSearch, setPathSearch] = useState(""), [mediaType, setMediaType] = useState("");
  const [offset, setOffset] = useState(0), [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(false), [opening, setOpening] = useState(false), [error, setError] = useState("");
  const [notice, setNotice] = useState(""), [highlight, setHighlight] = useState("");
  const [resource, setResource] = useState<{ item: ResourceCard; deliveryPath: string } | null>(null), [support, setSupport] = useState<Support | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [curiosityScope, setCuriosityScope] = useState<{ sessionId: string; messageId: string } | null>(null);
  const lastCuriosity = useRef("");
  const curiosityKey = curiosity ? `${curiosityTurn?.id ?? "empty"}:${curiosityTurn?.status ?? "empty"}:${curiosityTurn?.sessionId ?? ""}:${curiosityTurn?.messageId ?? ""}` : "";
  const refreshLock = useRef(false);
  const dialog = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLButtonElement>(null), returnFocus = useRef<HTMLElement | null>(null);
  const wasOpen = useRef(false);
  const generation = useRef(0), openRequest = useRef(false), answerRequest = useRef(0), initialized = useRef(false);
  const scroll = useRef<HTMLDivElement>(null), rememberedScroll = useRef(0);
  // This cache is component/member scoped, holds no delivery URLs and expires quickly.
  const cache = useRef(new Map<string, { at: number; value: Results }>());
  const displayed = useRef<{ params:string; attempt:number; value:Results } | null>(null);
  function measureAnchor() {
    const header = document.querySelector<HTMLElement>(".workspace-header");
    const columns = document.querySelector<HTMLElement>(".learning-columns");
    if (!header || !columns) return;
    const bounds = header.getBoundingClientRect();
    const top = header.contains(trigger.current) ? trigger.current!.getBoundingClientRect().top : bounds.top + (bounds.height - 36) / 2;
    setAnchor({ top, offset:top - columns.getBoundingClientRect().top });
  }
  useEffect(() => {
    measureAnchor();
    const header = document.querySelector(".workspace-header");
    const observer = new ResizeObserver(measureAnchor);
    if (header) observer.observe(header);
    window.addEventListener("resize", measureAnchor);
    return () => { observer.disconnect(); window.removeEventListener("resize", measureAnchor); };
  }, []);
  const current = fromStudy(context);
  const currentKey = current ? JSON.stringify(current) : "";
  useEffect(() => { setTrees(catalogue); cache.current.clear(); displayed.current = null; }, [catalogue]);
  useEffect(() => {
    const mq = matchMedia("(max-width: 1279px)");
    const sync = () => setNarrow(mq.matches); sync(); mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  useEffect(() => {
    const element = dialog.current; if (!element) return;
    element.close();
    if (open) { wasOpen.current = true; narrow ? element.showModal() : element.show(); requestAnimationFrame(() => { scroll.current && (scroll.current.scrollTop = rememberedScroll.current); }); }
    else if (wasOpen.current) { wasOpen.current = false; requestAnimationFrame(() => (returnFocus.current?.isConnected ? returnFocus.current : trigger.current)?.focus({ preventScroll: true })); }
    return () => element.close();
  }, [open, narrow]);
  useEffect(() => {
    const timer = setTimeout(() => { setDebounced(query); setOffset(0); }, 250);
    return () => clearTimeout(timer);
  }, [query]);
  function applyPath(path: Path | null, available = trees) {
    setCuriosityScope(null);
    setFiltersOpen(!path);
    setOffset(0); setHighlight(""); setResults(null);
    if (!path) { setFilters(emptyFilters); setRevision(null); return; }
    const tree = available.find(c => c.id === path.curriculum_id);
    const domain = tree?.levels.find(l => l.id === path.level_id)?.subjects.find(s => s.id === path.subject_id)?.domains.find(d => d.topics.some(t => t.id === path.topic_id));
    setFilters({ curriculum: path.curriculum_id, level: path.level_id, subject: path.subject_id,
      domain: path.domain_id ?? domain?.id ?? "", topic: path.topic_id, subtopic: path.subtopic_id ?? "" });
    setRevision(path.curriculum_revision); setOffset(0); setHighlight(""); setResults(null);
  }
  function show() {
    measureAnchor();
    cancelClose();
    returnFocus.current = document.activeElement as HTMLElement;
    if (!initialized.current || currentKey !== previousStudy.current) { applyPath(current); setNotice(""); initialized.current = true; previousStudy.current = currentKey; }
    setOpen(true);
    if (error) { displayed.current = null; cache.current.clear(); setAttempt(value => value + 1); void refreshPaths(); }
  }
  const previousStudy = useRef("");
  useEffect(() => {
    if (!open || !initialized.current || currentKey === previousStudy.current) return;
    // Follow navigation in My Learning, while allowing independent browsing
    // until the student actually changes their learning topic or subtopic.
    previousStudy.current = currentKey;
    answerRequest.current++; generation.current++;
    openRequest.current = false;
    cache.current.clear();
    applyPath(current);
    setQuery(""); setDebounced(""); setPathSearch("");
    setError(""); setNotice(""); setOpening(false);
    setResource(null); setSupport(null);
    rememberedScroll.current = 0;
    if (scroll.current) scroll.current.scrollTop = 0;
    setAttempt(value => value + 1);
  }, [currentKey, open]);
  function close() {
    if (closeTimer.current) return;
    answerRequest.current++; generation.current++; rememberedScroll.current = scroll.current?.scrollTop ?? 0;
    setClosing(true); setResource(null); setSupport(null);
    const finish = () => {
      closeTimer.current = null; setOpen(false); setClosing(false);
    };
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) finish();
    else closeTimer.current = setTimeout(finish, 220);
  }
  function cancelClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = null; setClosing(false);
  }
  async function fromAnswer(sessionId: string, messageId: string, nextKind: ExploreKind = "resource", id = "") {
    measureAnchor();
    cancelClose();
    const request = ++answerRequest.current;
    // Opening a saved answer is deliberate; only subsequent learning
    // navigation should replace its requested path.
    previousStudy.current = currentKey;
    lastCuriosity.current = curiosityKey;
    returnFocus.current = document.activeElement as HTMLElement;
    setOpen(true); setError(""); setCuriosityScope(null); setNotice("Loading this answer’s learning path…"); setFilters(emptyFilters); setResults(null);
    try {
      const data = await get<ContextResult>(`explore/context?session_id=${encodeURIComponent(sessionId)}&message_id=${encodeURIComponent(messageId)}`);
      if (request !== answerRequest.current) return;
      applyPath(data.context); setKind(nextKind); setHighlight(id); setQuery(""); setDebounced(""); setMediaType("");
      if (data.candidates?.length) { setCuriosityScope({ sessionId, messageId }); setFiltersOpen(false); }
      setNotice(data.context || data.candidates?.length ? "" : "No published learning path matches this question.");
      initialized.current = true; previousStudy.current = currentKey;
    } catch (cause) { if (request === answerRequest.current) { setNotice(""); setError(cause instanceof Error ? cause.message : "This answer’s path could not be loaded."); } }
  }
  useEffect(() => {
    if (!curiosity) { lastCuriosity.current = ""; setCuriosityScope(null); return; }
    if (!open || lastCuriosity.current === curiosityKey) return;
    lastCuriosity.current = curiosityKey;
    const request = ++answerRequest.current;
    generation.current++; cache.current.clear(); openRequest.current = false;
    applyPath(null); setFiltersOpen(!curiosityTurn); setError(""); setOpening(false);
    setResource(null); setSupport(null); setQuery(""); setDebounced(""); setPathSearch("");
    rememberedScroll.current = 0;
    if (scroll.current) scroll.current.scrollTop = 0;
    if (!curiosityTurn?.sessionId || !curiosityTurn.messageId || curiosityTurn.status !== "complete") {
      setNotice(curiosityTurn?.status === "pending" ? "Matching the latest question after its answer is ready…" : "");
      return;
    }
    setNotice("Finding published learning paths for this question…");
    const controller = new AbortController();
    let finished = false;
    void get<ContextResult>(`explore/context?session_id=${encodeURIComponent(curiosityTurn.sessionId)}&message_id=${encodeURIComponent(curiosityTurn.messageId)}`, controller.signal)
      .then(data => {
        if (request !== answerRequest.current || controller.signal.aborted) return;
        finished = true;
        applyPath(data.context);
        if (data.candidates?.length) setCuriosityScope({ sessionId: curiosityTurn.sessionId!, messageId: curiosityTurn.messageId! });
        if (!data.context) setFiltersOpen(false);
        setNotice(data.context || data.candidates?.length ? "" : "No published learning path matches this question.");
        setAttempt(value => value + 1);
      }).catch(cause => {
        if (request === answerRequest.current && !controller.signal.aborted) { setNotice(""); setError(cause instanceof Error ? cause.message : "The question’s learning path could not be matched."); lastCuriosity.current = ""; }
      });
    return () => { controller.abort(); if (request === answerRequest.current) { answerRequest.current++; if (!finished) lastCuriosity.current = ""; } };
  }, [open, curiosity, curiosityKey]);
  const curriculum = trees.find(c => c.id === filters.curriculum), level = curriculum?.levels.find(l => l.id === filters.level);
  const subject = level?.subjects.find(s => s.id === filters.subject), domain = subject?.domains.find(d => d.id === filters.domain);
  const topic = domain?.topics.find(t => t.id === filters.topic), subtopic = topic?.subtopics.find(s => s.id === filters.subtopic);
  const options = { curriculum: trees, level: curriculum?.levels ?? [], subject: level?.subjects ?? [], domain: subject?.domains ?? [], topic: domain?.topics ?? [], subtopic: topic?.subtopics ?? [] };
  const params = useMemo(() => {
    if (!curiosityScope && (!topic || filters.subtopic && !subtopic)) return null;
    const value = new URLSearchParams({ kind, offset: String(offset), limit: "24" });
    if (curiosityScope) { value.set("session_id", curiosityScope.sessionId); value.set("message_id", curiosityScope.messageId); }
    else { value.set("topic_id", topic!.id); if (subtopic) value.set("subtopic_id", subtopic.id); if (revision) value.set("curriculum_revision", String(revision)); }
    if (debounced) value.set("search", debounced);
    if (highlight && offset === 0) value.set("focus_id", highlight);
    if (mediaType && kind === "resource") value.set("media_type", mediaType);
    return value.toString();
  }, [topic, subtopic, filters.subtopic, revision, kind, offset, debounced, mediaType, highlight, curiosityScope]);
  useEffect(() => {
    const request = ++generation.current, controller = new AbortController();
    setOpening(false); openRequest.current = false; setResource(null); setSupport(null);
    if (!open || !params || !live) { setLoading(false); return; }
    // Closing a drawer is presentation only. Keep the last successful page
    // until its path/query/revision changes or explicit recovery invalidates it.
    if (displayed.current?.params === params && displayed.current.attempt === attempt) {
      setResults(displayed.current.value); setLoading(false); return;
    }
    setError(""); setLoading(true); setResults(null);
    const stored = cache.current.get(params);
    const load = stored && Date.now() - stored.at < 15000 ? Promise.resolve(stored.value) : get<Results>((curiosityScope ? "explore/curiosity?" : "explore?") + params, controller.signal);
    load.then(value => { if (request === generation.current) { displayed.current = { params, attempt, value }; setResults(value); cache.current.set(params, { at: Date.now(), value }); if (cache.current.size > 20) cache.current.delete(cache.current.keys().next().value!); } })
      .catch(cause => { if (request === generation.current && !controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Explore could not be loaded."); })
      .finally(() => { if (request === generation.current) setLoading(false); });
    return () => { controller.abort(); if (request === generation.current) generation.current++; };
  }, [open, params, attempt, live]);
  useEffect(() => {
    if (!open || !results || !highlight) return;
    const timer = requestAnimationFrame(() => dialog.current?.querySelector<HTMLElement>(".explore-highlight")?.scrollIntoView({ block: "nearest" }));
    return () => cancelAnimationFrame(timer);
  }, [open, results, highlight]);
  async function refreshPaths() {
    if (refreshLock.current) return;
    refreshLock.current = true;
    const request = ++answerRequest.current; setError(""); setNotice("Refreshing published paths…"); cache.current.clear();
    try {
      const latest = await getLearningLibrary(live); if (request !== answerRequest.current) return;
      setTrees(latest); setRevision(latest.find(c => c.id === filters.curriculum)?.revision ?? null); setAttempt(value => value + 1);
      setNotice("Paths refreshed. Review the selected topic before opening an item.");
    } catch (cause) { if (request === answerRequest.current) setError(cause instanceof Error ? cause.message : "Paths could not be refreshed."); }
    finally { refreshLock.current = false; }
  }
  async function openItem(item: Item) {
    if (openRequest.current || !params) return;
    openRequest.current = true; setOpening(true); setError(""); const request = generation.current;
    const selection = new URLSearchParams(parametersFor(item, params)); selection.delete("offset"); selection.delete("limit"); selection.delete("search"); selection.delete("media_type"); selection.delete("kind"); selection.delete("focus_id"); selection.set("version", String(item.version));
    try {
      const data = await get<{ item: ResourceCard & Support["item"]; availability_state: string }>(`explore/${item.kind}/${item.id}?${selection}`);
      if (request !== generation.current) return;
      if (item.kind === "resource") setResource({ item: data.item, deliveryPath: `resources/${item.id}/delivery?${selection}` });
      else setSupport({ item: data.item, kind: item.kind, availabilityState: data.availability_state });
    } catch (cause) { if (request === generation.current) setError(cause instanceof Error ? cause.message : "This item could not be opened."); }
    finally { if (request === generation.current) { openRequest.current = false; setOpening(false); } }
  }
  function changeFilter(field: Filter, value: string) {
    setCuriosityScope(null);
    answerRequest.current++; const index = fields.indexOf(field);
    setFilters(previous => Object.fromEntries(fields.map((name, i) => [name, i > index ? "" : name === field ? value : previous[name]])) as typeof emptyFilters);
    if (field === "curriculum") setRevision(trees.find(c => c.id === value)?.revision ?? null);
    setOffset(0); setNotice("Browsing independently. Your learning topic is unchanged."); setHighlight("");
  }
  const matches = pathSearch.trim() ? trees.flatMap(c => c.levels.flatMap(l => l.subjects.flatMap(s => s.domains.flatMap(d => d.topics.flatMap(t => [{ c, l, s, d, t, leaf: "", label: [c.name, l.name, s.name, d.name, t.name].join(" / ") }, ...t.subtopics.map(leaf => ({ c, l, s, d, t, leaf: leaf.id, label: [c.name, l.name, s.name, d.name, t.name, leaf.name].join(" / ") }))]))))).filter(p => p.label.toLowerCase().includes(pathSearch.toLowerCase())).slice(0, 30) : [];
  const toggle = <button ref={trigger} autoFocus={open} className="explore-trigger" aria-label="Explore" title={open ? "Close Explore" : "Explore resources"} aria-expanded={open} aria-controls="learning-explore" onClick={() => open ? close() : show()}>{open ? <ChevronRight size={20} aria-hidden="true" /> : <ChevronLeft size={20} aria-hidden="true" />}<span className="sr-only">Explore</span></button>;
  const panel = <dialog ref={dialog} id="learning-explore" style={{ "--explore-anchor-top": `${anchor.top}px`, "--explore-anchor-offset": `${anchor.offset}px` } as CSSProperties} className={`explore-panel ${closing ? "explore-closing" : ""}`} aria-label="Explore" onCancel={event => { if (event.target !== event.currentTarget) return; event.preventDefault(); close(); }} onKeyDown={event => { if ((event.target as HTMLElement).closest("dialog") !== event.currentTarget) return; if (narrow && event.key === "Tab") { const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), summary, a[href]')).filter(element => element.getClientRects().length && element.closest("dialog") === event.currentTarget && element.tabIndex !== -1); if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1)?.focus(); } else if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0]?.focus(); } } if (!narrow && event.key === "Escape" && (event.target as HTMLElement).closest("dialog") === event.currentTarget) { event.preventDefault(); close(); } }}>
    <header className="explore-header"><div><h2 id="explore-title"><Compass size={20} aria-hidden="true" />{kind === "resource" ? "Browse Media" : kind === "tutor" ? "Browse Teachers" : "Browse Activity Kits"}</h2><p>Explore resources for your learning topic</p></div>{open && toggle}</header>
    <div className="explore-tabs" role="tablist" aria-label="Explore catalogues">{tabs.map((tab, index) => <button key={tab.kind} id={`explore-tab-${tab.kind}`} role="tab" tabIndex={kind === tab.kind ? 0 : -1} aria-selected={kind === tab.kind} aria-controls="explore-results" onClick={() => { setKind(tab.kind); setOffset(0); }} onKeyDown={event => { const next = event.key === "ArrowRight" ? (index + 1) % 3 : event.key === "ArrowLeft" ? (index + 2) % 3 : event.key === "Home" ? 0 : event.key === "End" ? 2 : -1; if (next >= 0) { event.preventDefault(); setKind(tabs[next].kind); setOffset(0); document.getElementById(`explore-tab-${tabs[next].kind}`)?.focus(); } }}>{tab.label}</button>)}</div>
    <div ref={scroll} className="explore-scroll">
      <div className="explore-search-toolbar">
        <label className="explore-search"><Search size={16} aria-hidden="true" /><span className="sr-only">Search Explore resources</span><input type="search" placeholder={`Search ${tabs.find(tab => tab.kind === kind)?.label.toLowerCase()}…`} value={query} onChange={event => setQuery(event.target.value)} /></label>
        <button className="explore-filter-toggle" aria-label="Learning path filters" title="Learning path filters" aria-expanded={filtersOpen} aria-controls="explore-path-filters" onClick={() => setFiltersOpen(value => !value)}><SlidersHorizontal size={18} aria-hidden="true" /></button>
      </div>
      {kind === "resource" && <div className="explore-category-toolbar"><div className="explore-media-chips" aria-label="Media categories">{[{value:"",label:"All"},{value:"image",label:"Image"},{value:"video",label:"Video"},{value:"interactive",label:"Interactive"}].map(option => <button key={option.label} aria-pressed={mediaType===option.value} onClick={()=>{setMediaType(option.value);setOffset(0);}}>{option.label}</button>)}</div></div>}
      <div id="explore-path-filters" className="explore-filters" hidden={!filtersOpen}><h3 className="sr-only">Learning path filters</h3>
        <label>Find a learning path<input type="search" value={pathSearch} onChange={event => setPathSearch(event.target.value)} placeholder="Search curriculum, grade or topic" /></label>
        {matches.length > 0 && <ul className="explore-path-matches">{matches.map(p => <li key={p.t.id + p.leaf}><button title={p.label} onClick={() => { applyPath({ curriculum_id: p.c.id, level_id: p.l.id, subject_id: p.s.id, domain_id: p.d.id, topic_id: p.t.id, subtopic_id: p.leaf || null, curriculum_revision: p.c.revision ?? 1 }); setPathSearch(""); }}>{p.label}</button></li>)}</ul>}
        <div className="explore-filter-grid">{fields.map(field => <label key={field}>{field === "level" ? "Level / Grade" : field[0].toUpperCase() + field.slice(1)}<select aria-label={`Explore ${field}`} value={filters[field]} onChange={event => changeFilter(field, event.target.value)}><option value="">{field === "subtopic" ? "Topic-wide coverage" : `Choose ${field}`}</option>{options[field].map(option => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label>)}</div>
      </div>

      {notice && <p role="status" className="explore-notice">{notice}</p>}
      {error && <p id="explore-error-message" role="alert" className="explore-error">{error} <span>Close and reopen Explore to retry with the latest paths.</span></p>}
      <section id="explore-results" role="tabpanel" aria-labelledby={`explore-tab-${kind}`} aria-busy={loading || opening}>
        {!live ? <p>Explore uses the signed-in published catalogue.</p> : !topic && !curiosityScope ? null : loading ? <p role="status">Loading {tabs.find(tab => tab.kind === kind)?.label.toLowerCase()}…</p> : results && <><p role="status" className="explore-count">{results.total} matching {kind === "resource" ? "resources" : kind === "tutor" ? "teachers" : "kits"}</p>{!results.items.length && <p>No eligible items match this topic and your filters.</p>}<div className="explore-items">{results.items.map(item => { const Icon = item.kind === "tutor" ? UserRound : item.kind === "kit" ? BookOpen : ["video", "external_video", "animation"].includes(item.type) ? Play : ImageIcon; return <article key={item.id} className={`explore-item ${highlight === item.id ? "explore-highlight" : ""}`}>{item.kind === "resource" ? <button className="explore-thumbnail-button" disabled={opening} onClick={() => void openItem(item)} aria-label={`Open thumbnail for ${item.title}`}>{params && (["image/png", "image/jpeg", "image/webp"].includes(item.mime_type ?? "") || item.has_thumbnail || item.thumbnail_url) ? <ExploreThumbnail id={item.id} version={item.version} title={item.title} description={item.alt_text || item.description} parameters={parametersFor(item, params)} thumbnailUrl={item.has_thumbnail ? null : item.thumbnail_url} video={item.type === "video" || item.type === "external_video"} /> : <span className="explore-item-icon"><Icon size={20} aria-hidden="true" /></span>}</button> : <span className="explore-item-icon"><Icon size={20} aria-hidden="true" /></span>}<div><h3 title={item.title}>{item.title}</h3><small>{item.type.replaceAll("_", " ")} · {item.kind === "tutor" ? item.availability_state === "unknown" ? "Availability unknown" : "Listed: " + item.availability_state : item.coverage === "subtopic" ? "Specific subtopic" : "Topic-wide coverage"}</small>{item.description && <p>{item.description}</p>}<button disabled={opening} onClick={() => void openItem(item)} aria-label={`Open ${item.title}`}>{item.kind === "tutor" ? "View teacher" : item.kind === "kit" ? "View kit" : "Open media"}</button></div></article>; })}</div><nav className="explore-pagination" aria-label="Explore pages"><button disabled={results.offset === 0 || loading} onClick={() => { setHighlight(""); setOffset(Math.max(0, results.offset - 24)); }}>Previous</button><span>{results.total ? `${results.offset + 1}–${Math.min(results.offset + results.items.length, results.total)} of ${results.total}` : "0 results"}</span><button disabled={results.offset + 24 >= results.total || loading} onClick={() => { setHighlight(""); setOffset(results.offset + 24); }}>Next</button></nav></>}
      </section>
    </div>
    {resource && <CatalogueViewer deliveryPath={resource.deliveryPath} resource={resource.item} onClose={() => setResource(null)} />}
    {support && <LearningSupportViewer {...support} onClose={() => setSupport(null)} />}
    <DesktopPaneResizer pane="explore" />
  </dialog>;
  return <ExploreContext.Provider value={{ fromAnswer }}>{children(open ? null : toggle, panel)}</ExploreContext.Provider>;
}
