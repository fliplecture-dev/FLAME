"use client";
import { useEffect, useRef, useState } from "react";
import type { CatalogueItem } from "./catalogue";
type Entry = CatalogueItem & { published: boolean };
const fields = { title: "Title", description: "Description", category: "Category", subject: "Subject", level: "Grade / Age", language: "Language", format: "Format", author: "Author / Instructor", location: "Location", schedule: "Schedule (include date, time and timezone)", availability: "Availability", price: "Price", currency: "Currency (e.g. INR)" };

export function CatalogueAdmin({ kind }: { kind: "books" | "classes" }) {
  const [rows, setRows] = useState<Entry[]>([]), [selected, setSelected] = useState<Entry | null>(null);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState(""), [busy, setBusy] = useState(false), [attempt, setAttempt] = useState(0), [offset, setOffset] = useState(0);
  const form = useRef<HTMLFormElement>(null);
  const limit = 24;
  useEffect(() => { setDirty(false); }, [selected]);
  useEffect(() => {
    const abort = new AbortController();
    fetch(`/api/catalogue/admin/${kind}?offset=${offset}&limit=${limit}`, { signal: abort.signal, cache: "no-store" }).then(async response => {
      const data = await response.json(); if (!response.ok) throw new Error(data.error?.message ?? "Catalogue could not be loaded. Check the API migration and try again.");
      if (!abort.signal.aborted) setRows(data.items);
    }).catch(error => { if (!abort.signal.aborted) setNotice(error.message); });
    return () => abort.abort();
  }, [kind, attempt, offset]);
  async function mutate(path: string, method: "POST" | "PATCH", body: object) {
    const auth = await fetch("/api/auth/csrf", { cache: "no-store" });
    if (!auth.ok) throw new Error("Could not authorize this change.");
    const { csrf } = await auth.json();
    const response = await fetch(`/api/catalogue/admin/${kind}${path}`, { method, headers: { "content-type": "application/json", "x-flame-csrf": csrf }, body: JSON.stringify(body) });
    const data = await response.json();
    if (!response.ok) throw new Error(response.status === 409 ? "This listing changed. Reload and review the latest version before saving." : typeof data.detail === "string" ? data.detail : data.error?.message ?? "This change could not be saved. Check the entered values.");
    return data as Entry;
  }
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const values = new FormData(event.currentTarget);
    const body = Object.fromEntries(Object.keys(fields).map(name => [name, String(values.get(name) ?? "").trim() || null]));
    setBusy(true); setNotice("");
    try {
      const changed = await mutate(selected ? `/${selected.id}` : "", selected ? "PATCH" : "POST", { ...body, ...(selected ? { expected_version: selected.version } : {}) });
      setSelected(changed); setAttempt(value => value + 1);
      setNotice("Draft saved. Review it before publishing; editing a published listing withdraws it until you publish again.");
    } catch (error) { setNotice((error as Error).message); } finally { setBusy(false); }
  }
  return <section className="catalogue-admin"><p>Create and review {kind}. New records start as private drafts. Existing Teachers and Kits remain in their own management screens.</p>
    <div className="b4-fields"><button disabled={busy} onClick={() => { setSelected(null); form.current?.reset(); }}>New {kind === "books" ? "book" : "class"}</button><button disabled={busy} onClick={() => setAttempt(value => value + 1)}>Reload listings</button></div>
    <ul>{rows.map(row => <li key={row.id}><button disabled={busy} onClick={() => setSelected(row)}>{row.title} · {row.published ? "Published" : "Draft"}</button></li>)}</ul>
    {!rows.length && <p>No listings on this page.</p>}<div className="b4-fields"><button disabled={busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - limit))}>Previous</button><button disabled={busy || rows.length < limit} onClick={() => setOffset(value => value + limit)}>Next</button></div>
    <form key={selected ? `${selected.id}:${selected.version}` : "new"} ref={form} onSubmit={save} onChange={() => setDirty(true)}><h3>{selected ? `Edit ${selected.title}` : `New ${kind === "books" ? "book" : "class"}`}</h3><div className="b4-fields">{Object.entries(fields).map(([name, label]) => <label key={name}>{label}{name === "description" ? <textarea name={name} maxLength={4000} defaultValue={selected?.description ?? ""} /> : <input name={name} required={name === "title"} maxLength={name === "title" ? 255 : name === "currency" ? 3 : ["category", "level", "language", "format"].includes(name) ? 80 : name === "subject" ? 120 : 255} type={name === "price" ? "number" : "text"} min={name === "price" ? 0 : undefined} step={name === "price" ? "0.01" : undefined} defaultValue={selected?.[name as keyof CatalogueItem]?.toString() ?? ""} />}</label>)}</div><button disabled={busy} type="submit">{busy ? "Saving…" : "Save draft"}</button></form>
    {dirty && selected && <p role="status">Save your changes before publishing.</p>}
    {selected && <button disabled={busy || dirty} onClick={async () => { if (busy) return; setBusy(true); try { const changed = await mutate(`/${selected.id}/publication`, "POST", { expected_version: selected.version, published: !selected.published }); setSelected(changed); setAttempt(value => value + 1); setNotice(changed.published ? "Listing published." : "Listing withdrawn."); } catch (error) { setNotice((error as Error).message); } finally { setBusy(false); } }}>{selected.published ? "Withdraw listing" : "Publish listing"}</button>}
    {notice && <p role="status" className="b4-notice">{notice}</p>}
  </section>;
}
