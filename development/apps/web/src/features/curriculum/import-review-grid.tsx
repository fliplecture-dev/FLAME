"use client";

import { useEffect, useRef, useState } from "react";
import { RowActionsMenu } from "./row-actions-menu";

type Row = { sheet: string; row_number: number; values: string[]; operation: string;
  errors: { column: string; code: string }[]; localKey?: string; insert_before?: number; anchor?: string; placement?: "above" | "below" };
export type ReviewChange = { sheet: string; row_number?: number; insert_before?: number;
  action: "upsert" | "delete" | "add"; values?: string[] };
type Draft = { row: Row; values: string[] };
type Props = { importId: string; sheetLevels: Record<string, string>; previewRevision: string;
  busy: boolean; onSave: (changes: ReviewChange[]) => Promise<{ row_remap?: Record<string, number | null> }>;
  onDirtyChange: (dirty: boolean) => void };
const fields = ["Level", "Subject", "Domain", "Category", "Topic", "Subtopic"];
const key = (row: Row) => row.localKey ?? row.sheet + ":" + row.row_number;
const operationLabels: Record<string, string> = { reused: "Unchanged", created: "To add", updated: "To update", removed: "To remove", duplicate: "Duplicate", invalid: "Invalid", new: "Unsaved new row" };

export function ImportReviewGrid({ importId, sheetLevels, previewRevision, busy, onSave, onDirtyChange }: Props) {
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [uploadedTotal, setUploadedTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [added, setAdded] = useState<Row[]>([]);
  const [removed, setRemoved] = useState<Record<string, Row>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(false);
  const [operation, setOperation] = useState("");
  const [query, setQuery] = useState("");
  const [localSaving, setLocalSaving] = useState(false);
  const saving = useRef(false);
  const changeCount = new Set([...Object.keys(drafts), ...added.map(key), ...Object.keys(removed)]).size;
  const dirty = changeCount > 0;
  const blocked = busy || localSaving;
  useEffect(() => { onDirtyChange(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => { setErrors({}); }, [previewRevision]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    let live = true; setLoading(true); setLoadError("");
    const params = new URLSearchParams({ offset: String(offset), limit: "50", operation, q: query });
    fetch("/api/b4/admin/curriculum/imports/" + importId + "/review-rows?" + params, { cache: "no-store" }).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data?.error?.message || "Could not load workbook rows.");
      if (live) { setRows(data.items); setTotal(data.total); setUploadedTotal(data.uploaded_total ?? data.total); }
    }).catch(cause => { if (live) setLoadError(cause instanceof Error ? cause.message : "Could not load rows."); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [importId, previewRevision, offset, operation, query]);
  const display: Row[] = [];
  for (const row of rows) {
    display.push(...added.filter(item => item.anchor === key(row) && item.placement === "above"), row,
      ...added.filter(item => item.anchor === key(row) && item.placement === "below"));
  }
  display.push(...added.filter(item => !rows.some(row => key(row) === item.anchor)));
  const current = (row: Row) => drafts[key(row)]?.values ?? row.values;
  const cancel = (row: Row) => {
    const id = key(row);
    if (row.localKey) setAdded(previous => previous.filter(item => key(item) !== id));
    setDrafts(previous => { const next = { ...previous }; delete next[id]; return next; });
    setRemoved(previous => { const next = { ...previous }; delete next[id]; return next; });
    setErrors(previous => { const next = { ...previous }; delete next[id]; return next; });
  };
  function edit(row: Row) { setDrafts(previous => ({ ...previous, [key(row)]: { row, values: [...row.values] } })); }
  function update(row: Row, field: number, value: string) {
    if (row.localKey) setAdded(previous => previous.map(item => key(item) === key(row) ? { ...item, values: item.values.map((cell, index) => index === field ? value : cell) } : item));
    else setDrafts(previous => ({ ...previous, [key(row)]: { row, values: (previous[key(row)]?.values ?? row.values).map((cell, index) => index === field ? value : cell) } }));
    setErrors(previous => { const next = { ...previous }; delete next[key(row)]; return next; });
  }
  function addRow(anchor?: Row, placement: "above" | "below" = "below", duplicate = false) {
    const sheet = anchor?.sheet ?? Object.keys(sheetLevels)[0];
    if (!sheet || operation === "removed") return;
    const values = anchor ? [...current(anchor)] : [sheetLevels[sheet] === "__ALL_LEVELS__" ? "" : sheetLevels[sheet], "", "", "", "", ""];
    if (!duplicate) values[5] = "";
    setAdded(previous => [...previous, { localKey: crypto.randomUUID(), sheet, row_number: 0, values, operation: "new", errors: [],
      anchor: anchor ? key(anchor) : undefined, placement, insert_before: anchor && !anchor.localKey ? anchor.row_number + (placement === "below" ? 1 : 0) : undefined }]);
  }
  async function save(only?: Row) {
    if (saving.current || blocked) return;
    const id = only ? key(only) : null;
    const changes: ReviewChange[] = [];
    const targets = new Set<string>();
    for (const [rowKey, row] of Object.entries(removed)) if (!id || rowKey === id) { changes.push({ sheet: row.sheet, row_number: row.row_number, action: "delete" }); targets.add(rowKey); }
    for (const [rowKey, draft] of Object.entries(drafts)) if ((!id || rowKey === id) && !removed[rowKey]) {
      changes.push({ sheet: draft.row.sheet, row_number: draft.row.row_number, action: "upsert", values: draft.values }); targets.add(rowKey);
    }
    for (const row of added) if (!id || key(row) === id) { changes.push({ sheet: row.sheet, action: "add", insert_before: row.insert_before, values: row.values }); targets.add(key(row)); }
    if (!changes.length) return;
    if (changes.length > 100) { setLoadError("Save up to 100 corrections at a time using row Save. Your other edits are preserved."); return; }
    const invalid = changes.find(change => change.action !== "delete" && [0,1,2,4,5].some(index => !change.values?.[index]?.trim()));
    if (invalid) { setErrors(previous => ({ ...previous, [id ?? [...targets][0]]: "Level, Subject, Domain, Topic and Subtopic are required." })); return; }
    saving.current = true; setLocalSaving(true);
    try {
      const result = await onSave(changes);
      const remap = (row: Row): Row | null => {
        const next = result.row_remap?.[row.sheet + ":" + row.row_number];
        return next === null ? null : { ...row, row_number: next ?? row.row_number };
      };
      setDrafts(previous => Object.fromEntries(Object.entries(previous).filter(([rowKey]) => !targets.has(rowKey)).flatMap(([, draft]) => {
        const row = remap(draft.row); return row ? [[key(row), { ...draft, row }]] : [];
      })));
      setRemoved(previous => Object.fromEntries(Object.entries(previous).filter(([rowKey]) => !targets.has(rowKey)).flatMap(([, old]) => { const row = remap(old); return row ? [[key(row),row]] : []; })));
      setAdded(previous => previous.filter(row => !targets.has(key(row))).map(row => {
        const next = row.insert_before !== undefined ? result.row_remap?.[row.sheet + ":" + row.insert_before] : undefined;
        return { ...row, insert_before: next ?? row.insert_before };
      }));
      setErrors({});
    } catch (cause) { setErrors(previous => ({ ...previous, [id ?? [...targets][0]]: cause instanceof Error ? cause.message : "Corrections could not be saved. Your values are preserved." })); }
    finally { saving.current = false; setLocalSaving(false); }
  }
  function deleteRow(row: Row) {
    if (row.localKey) { cancel(row); return; }
    if (!window.confirm("Remove this row from the pending workbook? This does not change the saved draft.")) return;
    setRemoved(previous => ({ ...previous, [key(row)]: row }));
  }
  return <div className="admin-grid admin-import-review">
    <div className="admin-grid-toolbar">
      <strong>Workbook rows ({uploadedTotal})</strong>
      <label>Search workbook<input type="search" value={query} onChange={event => { setQuery(event.target.value); setOffset(0); }} /></label>
      <label>Comparison filter<select aria-label="Comparison filter" value={operation} onChange={event => { setOperation(event.target.value); setOffset(0); }}>
        <option value="">All uploaded rows</option><option value="changed">Changed rows</option><option value="reused">Unchanged</option><option value="created">To add</option><option value="updated">To update</option><option value="removed">To remove</option><option value="duplicate">Duplicates</option><option value="invalid">Errors</option>
      </select></label>
      <button disabled={!operation && !query} onClick={() => { setOperation(""); setQuery(""); setOffset(0); }}>Clear filters</button>
      <button onClick={() => addRow(display.at(-1))} disabled={blocked || operation === "removed"}>Add row</button>
      <button className="admin-primary" onClick={() => void save()} disabled={blocked || !dirty}>Save workbook corrections ({changeCount})</button>
      <span>{total} matching rows · {changeCount} unsaved</span>
    </div>
    <p className="admin-help">Row Save saves one workbook correction and revalidates the comparison. Save workbook corrections saves all pending corrections across pages. Neither changes the saved draft.</p>
    {loading && <p role="status">Loading workbook rows…</p>}
    {loadError && <p className="b4-notice b4-notice-error" role="alert">{loadError}</p>}
    {Object.entries(errors).filter(([rowKey]) => !display.some(row => key(row) === rowKey)).map(([rowKey, message]) => <p key={rowKey} role="alert">{message}</p>)}
    <div className="admin-grid-scroll" role="region" aria-label="Workbook comparison rows" tabIndex={0}>
      <table className="admin-grid-table"><thead><tr><th>Sheet</th><th>Excel row</th>{fields.map(field => <th key={field}>{field}</th>)}<th>Comparison</th><th>Actions</th></tr></thead>
        <tbody>{display.map((row,index) => {
          const id = key(row), values = current(row), editing = Boolean(drafts[id] || row.localKey || removed[id]);
          const readOnly = row.operation === "removed";
          return <tr key={id} className={errors[id] || row.errors.length ? "admin-grid-invalid" : editing ? "admin-grid-unsaved" : ""}>
            <td>{row.sheet}</td><td>{row.localKey ? "New" : readOnly ? "—" : row.row_number}</td>
            {fields.map((field,fieldIndex) => <td key={field}>{editing && !readOnly ? <>
              <input aria-label={field + " import row " + (index+1)} value={values[fieldIndex] ?? ""} list={"import-choice-" + fieldIndex}
                onChange={event => update(row,fieldIndex,event.target.value)} disabled={blocked || Boolean(removed[id])}
                onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); void save(row); } if (event.key === "Escape") cancel(row); }} />
              </> : <span className="admin-readable-cell" title={values[fieldIndex]}>{values[fieldIndex] || "—"}</span>}</td>)}
            <td>{removed[id] ? "Pending removal" : editing ? "Unsaved correction" : operationLabels[row.operation] ?? row.operation}
              {row.errors.map((issue,i) => <small key={i}>{issue.column}: {issue.code.replaceAll("_"," ")}</small>)}</td>
            <td className="admin-import-actions"><div className="admin-row-actions">
              {!readOnly && (editing ? <><button className="admin-primary" disabled={blocked} onClick={() => void save(row)}>Save</button><button disabled={blocked} onClick={() => cancel(row)}>Cancel</button></> : <button disabled={blocked} onClick={() => edit(row)}>Edit</button>)}
              {!readOnly && <RowActionsMenu label={"More actions for import row " + (index+1)} disabled={blocked}
                onInsert={placement => addRow(row,placement)} onDuplicate={() => addRow(row,"below",true)} onDelete={() => deleteRow(row)} />}
            </div>{errors[id] && <small role="alert">{errors[id]}</small>}</td>
          </tr>;
        })}</tbody>
      </table>
    </div>
    {fields.map((field,index) => <datalist key={field} id={"import-choice-" + index}>{[...new Set(rows.map(row => row.values[index]).filter(Boolean))].map(value => <option key={value} value={value} />)}</datalist>)}
    <nav className="admin-pagination" aria-label="Import row pages">
      <button disabled={offset===0 || loading} onClick={() => setOffset(Math.max(0,offset-50))}>Previous</button>
      <span>{total ? offset+1 : 0}–{Math.min(total,offset+50)} of {total} · {uploadedTotal} total uploaded rows</span>
      <button disabled={offset+50>=total || loading} onClick={() => setOffset(offset+50)}>Next</button>
    </nav>
  </div>;
}
