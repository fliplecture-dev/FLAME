"use client";
import Link from "next/link";
import { FliplectureLogo } from "@/components/ui/fliplecture-logo";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, Boxes, GraduationCap, Users, Search, SlidersHorizontal, X, ArrowRight, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ThemeToggle } from "@/features/learning/theme-toggle";
import { catalogues, catalogueKind, filterLabels, searchHref, type CatalogueItem, type CatalogueResults } from "./catalogue";
import { preferredResponseLanguage, saveQuestionIntent } from "./question-intent";

export function CatalogueSearch() {
  const router = useRouter(), params = useSearchParams();
  const kind = catalogueKind(params.get("kind")), query = params.get("q") ?? "";
  const [draft, setDraft] = useState(query), [filtersOpen, setFiltersOpen] = useState(false);
  const [results, setResults] = useState<CatalogueResults | null>(null), [error, setError] = useState("");
  const [loading, setLoading] = useState(true), [attempt, setAttempt] = useState(0);
  const [detail, setDetail] = useState<CatalogueItem | null>(null), [detailError, setDetailError] = useState("");
  const [detailLoading, setDetailLoading] = useState(false), [question, setQuestion] = useState("");
  const dialog = useRef<HTMLDialogElement>(null), returnFocus = useRef<HTMLElement | null>(null);
  const icons = { books: BookOpen, kits: Boxes, teachers: Users, classes: GraduationCap }, Icon = icons[kind];
  const label = catalogues.find(item => item.id === kind)!.label;
  const requestParams = new URLSearchParams(params.toString()); requestParams.delete("item"); requestParams.set("kind", kind);
  const key = requestParams.toString(), itemId = params.get("item");
  useEffect(() => { setDraft(query); }, [query]);
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true); setError(""); setResults(null);
    const request = new URLSearchParams(key); request.delete("item"); request.set("kind", kind);
    fetch(`/api/catalogue?${request}`, { signal: abort.signal, cache: "no-store" }).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? "Catalogue search is unavailable. Please try again.");
      if (!abort.signal.aborted) setResults(data);
    }).catch(cause => { if (!abort.signal.aborted) setError(cause.message); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [key, kind, attempt]);
  useEffect(() => {
    setDetail(null); setDetailError(""); setQuestion("");
    if (!itemId) { dialog.current?.close(); return; }
    returnFocus.current = document.activeElement as HTMLElement;
    dialog.current?.showModal(); setDetailLoading(true);
    const abort = new AbortController();
    fetch(`/api/catalogue/${kind}/${encodeURIComponent(itemId)}`, { signal: abort.signal, cache: "no-store" }).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(response.status === 404 ? "This listing is no longer available." : "This listing could not be loaded. Please try again.");
      if (!abort.signal.aborted) setDetail(data);
    }).catch(cause => { if (!abort.signal.aborted) setDetailError(cause.message); }).finally(() => { if (!abort.signal.aborted) setDetailLoading(false); });
    return () => { abort.abort(); dialog.current?.close(); if (returnFocus.current?.isConnected) returnFocus.current.focus({ preventScroll: true }); };
  }, [itemId, kind]);
  function update(values: Record<string, string | null>) {
    const next = new URLSearchParams(params.toString()); next.delete("item");
    if (!("offset" in values)) next.delete("offset");
    Object.entries(values).forEach(([name, value]) => { if (value) next.set(name, value); else next.delete(name); });
    router.push(`/search?${next}`, { scroll: false });
  }
  function clearFilters() { const next = new URLSearchParams({ kind }); if (query) next.set("q", query); router.push(`/search?${next}`, { scroll: false }); }
  function ask(text: string, item?: CatalogueItem) {
    try { saveQuestionIntent(item ? `About “${item.title}”: ${text}` : text, preferredResponseLanguage(), item ? { kind: item.kind, id: item.id, version: item.version } : undefined); router.push("/flame"); }
    catch { setDetailError("Your browser could not keep this question. Enable session storage and try again."); }
  }
  const selected = Object.keys(filterLabels).filter(name => params.has(name));
  return <main className="discovery results-page">
    <header className="results-header"><Link href="/" className="fliplecture-wordmark compact" aria-label="Fliplecture home"><FliplectureLogo /></Link>
      <form className="catalogue-search-form" onSubmit={event => { event.preventDefault(); update({ q: draft.trim() }); }}><label className="sr-only" htmlFor="catalogue-query">Search {label.toLowerCase()}</label><input id="catalogue-query" value={draft} maxLength={200} placeholder={`Search ${label.toLowerCase()}…`} onChange={event => setDraft(event.target.value)} />{draft && <button type="button" aria-label="Clear search" onClick={() => { setDraft(""); update({ q: null }); }}><X size={18} /></button>}<button type="submit" aria-label={`Search ${label.toLowerCase()}`}><Search size={20} /></button></form>
      <div className="results-account"><ThemeToggle /><Link href="/flame" className="account-link">My learning</Link></div>
    </header>
    <nav className="catalogue-tabs" aria-label="Search catalogues"><button className="ask-flame-tab" onClick={() => query ? ask(query) : router.push("/")}><Sparkles size={16} aria-hidden="true" />Ask FLAME</button>{catalogues.map(item => <Link key={item.id} aria-current={kind === item.id ? "page" : undefined} href={searchHref(item.id, query)}>{item.label}</Link>)}</nav>
    <section className="catalogue-body" aria-label={`${label} search results`}>
      <div className="catalogue-chips"><button className="filter-trigger" aria-expanded={filtersOpen} aria-controls="catalogue-filters" onClick={() => setFiltersOpen(value => !value)}><SlidersHorizontal size={16} aria-hidden="true" />Filters{selected.length ? ` (${selected.length})` : ""}</button>{(results?.facets.category ?? []).map(category => <button key={category} aria-pressed={params.get("category") === category} onClick={() => update({ category: params.get("category") === category ? null : category })}>{category}</button>)}</div>
      <div id="catalogue-filters" className="catalogue-filters" hidden={!filtersOpen}><div className="filter-heading"><h2>Filter {label.toLowerCase()}</h2><button type="button" onClick={() => setFiltersOpen(false)} aria-label="Close filters"><X size={18} /></button></div><div className="catalogue-filter-grid">{Object.entries(results?.facets ?? {}).filter(([name, values]) => name !== "category" && values.length).map(([name, values]) => <label key={name}>{filterLabels[name]}<select aria-label={filterLabels[name]} value={params.get(name) ?? ""} onChange={event => update({ [name]: event.target.value })}><option value="">All</option>{values.map(value => <option key={value} value={value}>{value}</option>)}</select></label>)}<label>Sort by<select value={params.get("sort") ?? "title"} onChange={event => update({ sort: event.target.value })}><option value="title">Title A–Z</option><option value="newest">Recently added</option></select></label></div>{!Object.values(results?.facets ?? {}).some(values => values.length) && <p>More filters will appear as listings are added.</p>}</div>
      {selected.length > 0 && <div className="selected-filters" aria-label="Selected filters">{selected.map(name => <button key={name} onClick={() => update({ [name]: null })}>{filterLabels[name]}: {params.get(name)}<X size={14} aria-hidden="true" /><span className="sr-only">Remove filter</span></button>)}<button onClick={clearFilters}>Clear filters</button></div>}
      <div className="catalogue-summary"><div><p className="discovery-eyebrow">THE FLIPLECTURE COLLECTION</p><h1>{query ? `${label} for “${query}”` : `Discover ${label.toLowerCase()}`}</h1></div>{!loading && results && <p role="status">{results.total} {results.total === 1 ? "result" : "results"}</p>}</div>
      {loading ? <p role="status" className="catalogue-loading">Searching {label.toLowerCase()}…</p> : error ? <div className="catalogue-empty" role="alert"><Icon size={35} aria-hidden="true" /><h2>Search is taking a break</h2><p>{error}</p><button className="account-link" onClick={() => setAttempt(value => value + 1)}>Try again</button></div> : results && !results.items.length ? <div className="catalogue-empty"><Icon size={40} strokeWidth={1.2} aria-hidden="true" /><h2>{results.inventory_total === 0 ? `No ${label.toLowerCase()} listed yet` : `No matching ${label.toLowerCase()}`}</h2><p>{results.inventory_total === 0 ? "This collection is getting started. You can still ask FLAME for help with a question." : "Try another search or remove a filter to explore more."}</p>{results.inventory_total > 0 && <button onClick={clearFilters}>Clear filters</button>}<button className="ask-empty" onClick={() => query ? ask(query) : router.push("/")}>Ask FLAME instead <ArrowRight size={16} aria-hidden="true" /></button></div> : <>
        <div className="catalogue-grid">{results?.items.map(item => <article key={item.id} className="catalogue-card"><button onClick={() => { const next = new URLSearchParams(params.toString()); next.set("item", item.id); router.push(`/search?${next}`, { scroll: false }); }} aria-label={`View ${item.title}`}><span className="catalogue-art"><Icon size={46} strokeWidth={1.1} aria-hidden="true" /></span><small>{item.category ?? label}</small><h2>{item.title}</h2>{item.author && <p>{item.author}</p>}{item.description && <p className="card-description">{item.description}</p>}<div className="catalogue-meta">{[item.level, item.languages?.join(", ") || item.language, item.format].filter(Boolean).join(" · ")}</div>{item.price !== null && <strong>{item.currency} {item.price}</strong>}<span className="card-action">View details <ArrowRight size={15} aria-hidden="true" /></span></button></article>)}</div>
        {results && results.total > results.limit && <nav className="catalogue-pagination" aria-label="Results pages"><button disabled={results.offset === 0} onClick={() => update({ offset: String(Math.max(0, results.offset - results.limit)) })}>Previous</button><span>{results.offset + 1}–{Math.min(results.offset + results.limit, results.total)} of {results.total}</span><button disabled={results.offset + results.limit >= results.total} onClick={() => update({ offset: String(results.offset + results.limit) })}>Next</button></nav>}
      </>}
    </section>
    <dialog ref={dialog} className="catalogue-detail" aria-label="Listing details" onCancel={event => { event.preventDefault(); update({ item: null, offset: params.get("offset") }); }}><button className="detail-close" aria-label="Close details" onClick={() => update({ item: null, offset: params.get("offset") })}><X size={20} /></button>{detailLoading ? <p role="status">Loading listing…</p> : detail ? <><p className="discovery-eyebrow">{label}</p><h2>{detail.title}</h2><p>{detail.description}</p><dl>{Object.entries({ Author: detail.author, Category: detail.category, Subject: detail.subject, Level: detail.level, Language: detail.languages?.join(", ") || detail.language, Format: detail.format, Location: detail.location, Schedule: detail.schedule, Availability: detail.availability, Price: detail.price !== null ? `${detail.currency} ${detail.price}` : null }).filter(([, value]) => value).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl><form onSubmit={event => { event.preventDefault(); if (question.trim()) ask(question, detail); }}><label htmlFor="item-question">Ask FLAME about this {kind === "classes" ? "class" : kind === "teachers" ? "teacher" : kind === "books" ? "book" : "kit"}</label><textarea id="item-question" required maxLength={3500} value={question} onChange={event => setQuestion(event.target.value)} placeholder="Would this suit my learning level?" /><button className="account-link" type="submit">Ask FLAME <ArrowRight size={16} aria-hidden="true" /></button></form></> : null}{detailError && <p role="alert">{detailError}</p>}</dialog>
  </main>;
}
