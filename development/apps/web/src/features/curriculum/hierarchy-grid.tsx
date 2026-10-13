"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type Ref as ReactRef } from "react";

import { RowActionsMenu } from "./row-actions-menu";

type Node = { id: string; name: string; version: number; archived?: boolean; draft_status?: string;
  levels?: Node[]; subjects?: Node[]; domains?: Node[]; categories?: Node[];
  topics?: Node[]; subtopics?: Node[] };
type Field = "level" | "subject" | "domain" | "category" | "topic" | "subtopic";
type Values = Record<Field, string>;
type Ref = { id: string; version: number };
type Refs = Partial<Record<Field, Ref>>;
type Row = { key: string; values: Values; refs: Refs; sourceId?: string;
  incompleteKind?: Field; new?: boolean; draftStatus?: string; anchor?: string; placement?: "above" | "below" };
export type PathChange = { key: string; action: "upsert" | "delete";
  source_subtopic_id?: string; values?: Values };

const fields: Field[] = ["level", "subject", "domain", "category", "topic", "subtopic"];
const required: Field[] = ["level", "subject", "domain", "topic", "subtopic"];
const emptyValues = (): Values => ({ level: "", subject: "", domain: "", category: "", topic: "", subtopic: "" });
const clean = (value: string) => value.normalize("NFC").trim().replace(/\s+/g, " ").toLocaleLowerCase();
const pathKey = (values: Values) => fields.map(field => clean(values[field])).join("\u001f");

function tableRows(tree: Node): Row[] {
  const result: Row[] = [];
  const active = (items?: Node[]) => (items ?? []).filter(item => !item.archived);
  const add = (values: Values, refs: Refs, terminal: Field, draftStatus?: string) => {
    const ref = refs[terminal];
    result.push({ key: terminal + ":" + ref?.id, values: { ...values }, refs: { ...refs },
      sourceId: terminal === "subtopic" ? ref?.id : undefined,
      incompleteKind: terminal === "subtopic" ? undefined : terminal, draftStatus });
  };
  for (const level of active(tree.levels)) {
    const lv = { ...emptyValues(), level: level.name };
    const lr: Refs = { level: { id: level.id, version: level.version } };
    if (!active(level.subjects).length) { add(lv, lr, "level"); continue; }
    for (const subject of active(level.subjects)) {
      const sv = { ...lv, subject: subject.name };
      const sr: Refs = { ...lr, subject: { id: subject.id, version: subject.version } };
      if (!active(subject.domains).length) { add(sv, sr, "subject"); continue; }
      for (const domain of active(subject.domains)) {
        const dv = { ...sv, domain: domain.name };
        const dr: Refs = { ...sr, domain: { id: domain.id, version: domain.version } };
        let found = false;
        const topics = (items: Node[], values: Values, refs: Refs) => {
          for (const topic of items) {
            found = true;
            const tv = { ...values, topic: topic.name };
            const tr: Refs = { ...refs, topic: { id: topic.id, version: topic.version } };
            if (!active(topic.subtopics).length) { add(tv, tr, "topic"); continue; }
            for (const subtopic of active(topic.subtopics)) {
              add({ ...tv, subtopic: subtopic.name },
                { ...tr, subtopic: { id: subtopic.id, version: subtopic.version } }, "subtopic", subtopic.draft_status);
            }
          }
        };
        topics(active(domain.topics), dv, dr);
        for (const category of active(domain.categories)) {
          const cv = { ...dv, category: category.name };
          const cr: Refs = { ...dr, category: { id: category.id, version: category.version } };
          if (!active(category.topics).length) { found = true; add(cv, cr, "category"); }
          else topics(active(category.topics), cv, cr);
        }
        if (!found) add(dv, dr, "domain");
      }
    }
  }
  return result;
}

type Props = {
  tree: Node;
  curriculumState: string;
  onBatchSave: (changes: PathChange[]) => Promise<void>;
  onRename: (field: Field, ref: Ref, name: string) => Promise<void>;
  onDeleteIncomplete: (field: Field, ref: Ref) => Promise<void>;
  onDirtyChange: (dirty: boolean) => void;
  onMetricsChange?: (metrics: { unsaved: number; invalid: number; conflicts: number }) => void;
  onReload?: () => Promise<void>;
  saveButtonRef?: ReactRef<HTMLButtonElement>;
};

export function HierarchyGrid({ tree, curriculumState, onBatchSave, onRename,
  onDeleteIncomplete, onDirtyChange, onMetricsChange, onReload, saveButtonRef }: Props) {
  const base = useMemo(() => tableRows(tree), [tree]);
  const [drafts, setDrafts] = useState<Record<string, Values>>({});
  const [newRows, setNewRows] = useState<Row[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [activeKey, setActiveKey] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Partial<Record<Field, string>>>({});
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [errors, setErrors] = useState<Record<string, { field?: Field; message: string }>>({});
  const [shared, setShared] = useState<{ row: Row; field: Field; count: number } | null>(null);
  const [bulkField, setBulkField] = useState<Field>("level");
  const [bulkValue, setBulkValue] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  useEffect(() => {
    const closeOutside = (event: PointerEvent) => {
      const target = event.target as globalThis.Node | null;
      for (const menu of document.querySelectorAll<HTMLDetailsElement>(".admin-row-overflow[open]")) {
        if (!target || !menu.contains(target)) menu.open = false;
      }
    };
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      for (const menu of document.querySelectorAll<HTMLDetailsElement>(".admin-row-overflow[open]")) menu.open = false;
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  const rows = useMemo(() => {
    const result: Row[] = [];
    const before = (key: string) => newRows.filter(row => row.anchor === key && row.placement === "above");
    const after = (key: string) => newRows.filter(row => row.anchor === key && row.placement === "below");
    for (const row of base) result.push(...before(row.key), row, ...after(row.key));
    result.push(...newRows.filter(row => !row.anchor || !base.some(item => item.key === row.anchor)));
    return result;
  }, [base, newRows]);
  const current = (row: Row) => drafts[row.key] ?? row.values;
  const dirtyKeys = rows.filter(row => row.new || (drafts[row.key] && pathKey(drafts[row.key]) !== pathKey(row.values)))
    .map(row => row.key);
  const dirty = dirtyKeys.length > 0;
  useEffect(() => { onDirtyChange(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const choices = (field: Field, values: Values) => {
    const index = fields.indexOf(field);
    const seen = new Set<string>();
    return base.filter(row => fields.slice(0, index).every(previous =>
      !values[previous] || clean(row.values[previous]) === clean(values[previous])))
      .map(row => row.values[field]).filter(value => {
        const normalized = clean(value);
        if (!normalized || seen.has(normalized)) return false;
        seen.add(normalized); return true;
      }).sort((a, b) => a.localeCompare(b));
  };
  const filtered = rows.filter(row => {
    const values = current(row);
    const state = errors[row.key] ? "invalid" : (row.new || drafts[row.key] || row.draftStatus === "draft_change") ? "draft_change" : "unchanged";
    if (statusFilter && state !== statusFilter) return false;
    return fields.every(field => !filters[field] || clean(values[field]).includes(clean(filters[field]!))) &&
      (!query.trim() || fields.some(field => values[field].toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())));
  });
  const visible = filtered.slice(page * 50, (page + 1) * 50);
  const filterChoices = (field: Field) => {
    const preceding = fields.slice(0, fields.indexOf(field));
    return [...new Set(base.filter(row => preceding.every(previous =>
      !filters[previous] || clean(row.values[previous]).includes(clean(filters[previous]!))))
      .map(row => row.values[field]).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  };
  const serverConflictCount = Object.values(errors).filter(item => item.message === "Updated elsewhere").length;
  const validation = (row: Row) => {
    const values = current(row);
    const field = required.find(item => !values[item].trim());
    if (field) return { field, message: field[0].toUpperCase() + field.slice(1) + " is required." };
    if (fields.some(item => values[item].length > (item === "level" ? 80 : 255)))
      return { message: "A cell exceeds its length limit." };
    const duplicate = rows.find(other => other.key !== row.key && pathKey(current(other)) === pathKey(values) &&
      (!other.incompleteKind || other.new));
    if (duplicate) return { field: "subtopic" as Field, message: "This complete path already exists." };
    return null;
  };
  useEffect(() => {
    const invalid = rows.filter(row => {
      const editing = row.new || Boolean(drafts[row.key]);
      return editing && Boolean(errors[row.key] ?? validation(row));
    }).length;
    onMetricsChange?.({ unsaved: dirtyKeys.length, invalid, conflicts: serverConflictCount });
  }, [dirtyKeys.length, errors, onMetricsChange, rows]);
  const setValue = (row: Row, field: Field, value: string) => {
    if (row.new) setNewRows(previous => previous.map(item => item.key === row.key
      ? { ...item, values: { ...item.values, [field]: value } } : item));
    else setDrafts(previous => ({ ...previous,
      [row.key]: { ...(previous[row.key] ?? row.values), [field]: value } }));
    setErrors(previous => { const next = { ...previous }; delete next[row.key]; return next; });
  };
  const addRow = (anchor?: Row, placement: "above" | "below" = "below") => {
    const carried = anchor ? { ...current(anchor), subtopic: "" } : emptyValues();
    const row: Row = { key: "new:" + crypto.randomUUID(), values: carried, refs: {}, new: true,
      anchor: anchor?.key, placement };
    setNewRows(previous => [...previous, row]); setActiveKey(row.key);
    setPage(anchor ? Math.floor(Math.max(0, filtered.findIndex(item => item.key === anchor.key)) / 50) : Math.floor(rows.length / 50));
  };
  const duplicateRow = (source: Row) => {
    const row: Row = { key: "new:" + crypto.randomUUID(), values: { ...current(source) },
      refs: {}, new: true, anchor: source.key, placement: "below" };
    setNewRows(previous => [...previous, row]); setActiveKey(row.key);
    setPage(Math.floor(Math.max(0, filtered.findIndex(item => item.key === source.key)) / 50));
  };
  const discard = (row: Row) => {
    if (row.new) setNewRows(previous => previous.filter(item => item.key !== row.key));
    else setDrafts(previous => { const next = { ...previous }; delete next[row.key]; return next; });
    setErrors(previous => { const next = { ...previous }; delete next[row.key]; return next; });
    setActiveKey("");
  };
  const reportError = (error: unknown, fallbackKey: string) => {
    const detail = (error as { detail?: unknown })?.detail;
    const rowKey = typeof detail === "object" && detail !== null && "row_key" in detail
      ? String(detail.row_key) : fallbackKey;
    const field = typeof detail === "object" && detail !== null && "field" in detail
      ? String(detail.field) as Field : undefined;
    const rawCode = typeof detail === "object" && detail !== null && "code" in detail
      ? String(detail.code) : error instanceof Error ? error.message : "save_failed";
    const code = rawCode === "updated_elsewhere" || rawCode === "version_conflict" || rawCode === "source_path_changed"
      ? "Updated elsewhere" : rawCode.replaceAll("_", " ");
    setErrors(previous => ({ ...previous, [rowKey]: { field, message: code } }));
  };
  async function saveChanges(keys: string[]) {
    if (pending.current || busy) return;
    const targets = rows.filter(row => keys.includes(row.key) && (row.new ||
      (drafts[row.key] && pathKey(drafts[row.key]) !== pathKey(row.values))));
    if (!targets.length || curriculumState === "archived") return;
    for (const row of targets) {
      const issue = validation(row);
      if (issue) { setErrors(previous => ({ ...previous, [row.key]: issue })); return; }
    }
    const changes: PathChange[] = targets.map(row => ({ key: row.key, action: "upsert",
      source_subtopic_id: row.sourceId, values: current(row) }));
    pending.current = true; setBusy(true);
    try {
      await onBatchSave(changes);
      setDrafts(previous => { const next = { ...previous }; targets.forEach(row => delete next[row.key]); return next; });
      setNewRows(previous => previous.filter(row => !keys.includes(row.key)));
      setSelected(previous => previous.filter(key => !keys.includes(key)));
      setActiveKey(""); setErrors({});
    } catch (error) { reportError(error, targets[0].key); }
    finally { pending.current = false; setBusy(false); }
  }
  async function saveRow(row: Row) {
    const issue = validation(row);
    if (issue) { setErrors(previous => ({ ...previous, [row.key]: issue })); return; }
    if (curriculumState === "archived" || busy || pending.current) return;
    if (row.new || !drafts[row.key]) { await saveChanges([row.key]); return; }
    const changed = fields.filter(field => clean(drafts[row.key][field]) !== clean(row.values[field]));
    if (!changed.length) { discard(row); return; }
    if (changed.length === 1 && row.refs[changed[0]] && changed[0] !== "category") {
      const field = changed[0];
      const ref = row.refs[field]!;
      const affected = base.filter(item => item.refs[field]?.id === ref.id).length;
      if (affected > 1) { setShared({ row, field, count: affected }); return; }
      pending.current = true; setBusy(true);
      try {
        await onRename(field, ref, drafts[row.key][field].trim());
        discard(row);
      } catch (error) { reportError(error, row.key); }
      finally { pending.current = false; setBusy(false); }
      return;
    }
    const sharedField = changed.find(field => row.refs[field] &&
      base.filter(item => item.refs[field]?.id === row.refs[field]?.id).length > 1);
    if (sharedField) {
      setShared({ row, field: sharedField, count: base.filter(item =>
        item.refs[sharedField]?.id === row.refs[sharedField]?.id).length });
      return;
    }
    await saveChanges([row.key]);
  }
  async function removeRow(row: Row) {
    if (row.new) { discard(row); return; }
    if (!window.confirm("Delete this curriculum path? The node IDs and past activity will be retained as archived history.")) return;
    pending.current = true; setBusy(true);
    try {
      if (row.sourceId) await onBatchSave([{ key: row.key, action: "delete", source_subtopic_id: row.sourceId }]);
      else if (row.incompleteKind && row.refs[row.incompleteKind])
        await onDeleteIncomplete(row.incompleteKind, row.refs[row.incompleteKind]!);
      discard(row); setSelected(previous => previous.filter(key => key !== row.key));
    } catch (error) { reportError(error, row.key); }
    finally { pending.current = false; setBusy(false); }
  }
  async function bulkDelete() {
    const chosen = rows.filter(row => selected.includes(row.key));
    if (!chosen.length || !window.confirm("Delete " + chosen.length + " selected paths? This removes them from the active hierarchy.")) return;
    const saved = chosen.filter(row => row.sourceId);
    const incomplete = chosen.filter(row => row.incompleteKind && row.refs[row.incompleteKind]);
    const unsaved = chosen.filter(row => row.new);
    pending.current = true; setBusy(true);
    try {
      if (saved.length) await onBatchSave(saved.map(row => ({ key: row.key, action: "delete", source_subtopic_id: row.sourceId })));
      for (const row of incomplete) await onDeleteIncomplete(row.incompleteKind!, row.refs[row.incompleteKind!]!);
      setNewRows(previous => previous.filter(row => !unsaved.some(item => item.key === row.key)));
      setSelected([]);
    } catch (error) { reportError(error, saved[0]?.key ?? chosen[0].key); }
    finally { pending.current = false; setBusy(false); }
  }
  const applyBulkField = () => {
    if (!selected.length || !bulkValue.trim() || curriculumState === "archived") return;
    if (!window.confirm("Change " + bulkField + " in " + selected.length + " selected rows? Review each row before Bulk save.")) return;
    for (const row of rows.filter(item => selected.includes(item.key))) setValue(row, bulkField, bulkValue);
  };
  const cellKey = (event: KeyboardEvent<HTMLInputElement>, row: Row, field: Field, index: number) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void saveChanges(dirtyKeys); }
    else if (event.key === "Enter") { event.preventDefault(); void saveRow(row); }
    if (event.key === "Escape") { event.preventDefault(); discard(row); }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      const next = index + (event.key === "ArrowDown" ? 1 : -1);
      const target = document.querySelector<HTMLInputElement>(
        'input[data-grid-index="' + next + '"][data-grid-field="' + field + '"]');
      if (target) { event.preventDefault(); target.focus(); }
    }
  };
  return <div className="admin-grid">
    <div className="admin-grid-toolbar">
      <label>Search paths<input type="search" value={query} onChange={event => { setQuery(event.target.value); setPage(0); }}
        placeholder="Search any cell" /></label>
      <button className="admin-primary" disabled={curriculumState === "archived" || busy}
        onClick={() => addRow(rows.find(row => row.key === activeKey) ?? visible.at(-1))}>Add row</button>
      <button ref={saveButtonRef} disabled={!dirty || busy} onClick={() => void saveChanges(dirtyKeys)}>Save draft changes ({dirtyKeys.length})</button>
      <button disabled={!dirty || busy} onClick={() => {
        if (window.confirm("Discard all unsaved table changes?")) { setDrafts({}); setNewRows([]); setErrors({}); }
      }}>Discard changes</button>
      <span>{filtered.length} paths · {dirtyKeys.length} unsaved</span>
    </div>
    <p className="admin-help">Row Save saves one private draft path. Save draft changes saves all edited paths individually. Shared-parent changes require choosing rename everywhere or move only this path. Publish makes the saved draft available to members.</p>
    <div className="admin-grid-filters" aria-label="Path filters">
      {fields.map(field => <label key={field}>{field}
        <input type="search" list={"hierarchy-filter-" + field} aria-label={"Filter " + field} value={filters[field] ?? ""} onChange={event => {
          const next = { ...filters, [field]: event.target.value };
          for (const later of fields.slice(fields.indexOf(field) + 1)) next[later] = "";
          setFilters(next); setPage(0);
        }} placeholder="All" /><datalist id={"hierarchy-filter-" + field}>{filterChoices(field).map(value =>
          <option key={value} value={value} />)}</datalist></label>)}
      <label>Status<select aria-label="Filter status" value={statusFilter}
        onChange={event => { setStatusFilter(event.target.value); setPage(0); }}>
        <option value="">All</option><option value="draft_change">Draft change</option>
        <option value="invalid">Invalid</option><option value="unchanged">Unchanged</option>
      </select></label>
      <button disabled={!statusFilter && !query && !Object.values(filters).some(Boolean)}
        onClick={() => { setFilters({}); setStatusFilter(""); setQuery(""); setPage(0); }}>Clear filters</button>
    </div>
    {(statusFilter || query || Object.values(filters).some(Boolean)) && <div className="admin-filter-chips" aria-label="Active filters">
      {query && <button onClick={() => setQuery("")}>Search: {query} ×</button>}
      {Object.entries(filters).filter(([, value]) => value).map(([field, value]) =>
        <button key={field} onClick={() => setFilters(previous => ({ ...previous, [field]: "" }))}>{field}: {value} ×</button>)}
      {statusFilter && <button onClick={() => setStatusFilter("")}>Status: {statusFilter.replaceAll("_", " ")} ×</button>}
    </div>}
    {serverConflictCount > 0 && <div className="b4-notice b4-notice-error admin-conflict" role="alert">
      <strong>{serverConflictCount} row{serverConflictCount === 1 ? "" : "s"} updated elsewhere.</strong>
      <span>Your typed values are preserved.</span>
      <button onClick={() => void onReload?.()}>Review latest changes</button>
      <button onClick={() => setErrors(previous => Object.fromEntries(
        Object.entries(previous).filter(([, item]) => item.message !== "Updated elsewhere")))}>Keep my changes</button>
    </div>}
    <details className="admin-grid-options"><summary>Bulk actions{selected.length ? " (" + selected.length + " selected)" : ""}</summary><div className="admin-grid-bulk">
      <label><input type="checkbox" checked={visible.length > 0 && visible.every(row => selected.includes(row.key))}
        onChange={event => setSelected(previous => event.target.checked
          ? [...new Set([...previous, ...visible.map(row => row.key)])]
          : previous.filter(key => !visible.some(row => row.key === key)))} /> Select all visible</label>
      <strong>{selected.length} selected</strong>
      <button disabled={!selected.length || busy || curriculumState === "archived"} onClick={() => void saveChanges(selected)}>Bulk save</button>
      <button className="admin-danger" disabled={!selected.length || busy || curriculumState === "archived"} onClick={() => void bulkDelete()}>Bulk delete</button>
      <label>Bulk change<select value={bulkField} onChange={event => setBulkField(event.target.value as Field)}>
        {fields.slice(0, 5).map(field => <option key={field} value={field}>{field}</option>)}</select></label>
      <input aria-label="Bulk value" value={bulkValue} onChange={event => setBulkValue(event.target.value)} placeholder="New or existing value" />
      <button disabled={!selected.length || !bulkValue.trim() || curriculumState === "archived"} onClick={applyBulkField}>Apply to {selected.length}</button>
      <button disabled={!selected.length} onClick={() => setSelected([])}>Clear selection</button>
    </div></details>
    {!rows.length && <p className="admin-empty">No paths yet. Add a row with Level, Subject, Domain, Topic and Subtopic.</p>}
    {!!rows.length && !filtered.length && <p className="admin-empty">No paths match the current search and filters.</p>}
    {!!filtered.length && <div className="admin-grid-scroll" role="region" aria-label="Editable curriculum paths" tabIndex={0}>
      <table className="admin-grid-table admin-hierarchy-table"><thead><tr>
        <th scope="col" className="admin-grid-selection" aria-label="Selection" />
        {fields.map(field => <th key={field} scope="col">{field}</th>)}
        <th scope="col" className="admin-grid-actions">Actions</th>
      </tr></thead><tbody>{visible.map((row, index) => {
        const values = current(row);
        const editing = row.new || Boolean(drafts[row.key]);
        const issue = errors[row.key] ?? (editing ? validation(row) : null);
        const changed = row.new || (drafts[row.key] && pathKey(values) !== pathKey(row.values));
        return <tr key={row.key} className={issue ? "admin-grid-invalid" : changed ? "admin-grid-unsaved" : ""}
          onClick={() => setActiveKey(row.key)}>
          <td className="admin-grid-selection">
            <input type="checkbox" aria-label={"Select path " + (index + 1)} checked={selected.includes(row.key)} onChange={event => setSelected(previous => event.target.checked ? [...previous, row.key] : previous.filter(key => key !== row.key))} />
          </td>
          {fields.map(field => <td key={field} className={issue?.field === field ? "admin-grid-cell-error" : ""}>
            {editing ? <><input aria-label={field + " row " + (index + 1)}
              data-grid-index={index} data-grid-field={field}
              list={"grid-" + row.key + "-" + field} value={values[field]}
              onChange={event => setValue(row, field, event.target.value)}
              onKeyDown={event => cellKey(event, row, field, index)}
              aria-invalid={issue?.field === field || undefined} />
              <datalist id={"grid-" + row.key + "-" + field}>{choices(field, values).map(value =>
                <option key={value} value={value} />)}</datalist></>
              : <span className="admin-readable-cell" title={values[field]}>{values[field] || "—"}</span>}
          </td>)}
          <td className="admin-grid-actions"><div className="admin-row-actions">
            {editing ? <><button className="admin-primary" disabled={busy || Boolean(issue && issue.message !== "Updated elsewhere")}
              onClick={() => void saveRow(row)}>Save</button>
              <button onClick={() => discard(row)}>Cancel</button></>
              : <button disabled={curriculumState === "archived"} onClick={() => setDrafts(previous => ({ ...previous, [row.key]: { ...row.values } }))}>Edit</button>}
            <RowActionsMenu label={"More actions for path " + (index+1)} disabled={busy || curriculumState === "archived"}
              onInsert={placement => addRow(row, placement)} onDuplicate={() => duplicateRow(row)} onDelete={() => void removeRow(row)} />
          </div><span className={"admin-grid-status " + (issue ? "invalid" : changed ? "unsaved" : "")}>
            {issue ? "Invalid" : changed ? "Unsaved" : row.incompleteKind ? "Incomplete" : row.draftStatus === "draft_change" ? "Draft change" : "Unchanged"}</span>
            {issue && <small role="alert">{issue.message}</small>}
</td>
        </tr>;
      })}</tbody></table>
    </div>}
    {filtered.length > 50 && <nav className="admin-pagination" aria-label="Path pages">
      <button disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
      <span>{page * 50 + 1}–{Math.min(filtered.length, (page + 1) * 50)} of {filtered.length}</span>
      <button disabled={(page + 1) * 50 >= filtered.length} onClick={() => setPage(page + 1)}>Next</button>
    </nav>}
    <div className="admin-grid-bottom"><button className="admin-primary" disabled={curriculumState === "archived" || busy}
      onClick={() => addRow(visible.at(-1))}>Add row</button></div>
    {shared && <div className="admin-grid-dialog-backdrop"><div className="admin-grid-dialog" role="dialog"
      aria-modal="true" aria-labelledby="shared-edit-title">
      <h3 id="shared-edit-title">Shared {shared.field} used in {shared.count} paths</h3>
      <p>Choose how to apply this change. Renaming everywhere changes every path that uses this node.</p>
      <div className="admin-grid-dialog-actions">
        <button className="admin-primary" disabled={busy || fields.filter(field =>
          clean(current(shared.row)[field]) !== clean(shared.row.values[field])).length !== 1}
          onClick={() => {
            const ref = shared.row.refs[shared.field]!;
            setBusy(true);
            void onRename(shared.field, ref, current(shared.row)[shared.field].trim())
              .then(() => { discard(shared.row); setShared(null); })
              .catch(error => reportError(error, shared.row.key))
              .finally(() => setBusy(false));
          }}>Rename in all {shared.count} paths</button>
        <button disabled={busy} onClick={() => { const key = shared.row.key; setShared(null); void saveChanges([key]); }}>
          Change only this path</button>
        <button onClick={() => setShared(null)}>Cancel</button>
      </div>
      <p className="admin-help">To rename everywhere, save any other cell changes in this row separately first.</p>
    </div></div>}
  </div>;
}














