"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { BulkTransfer } from "./bulk-transfer";
import { B9Admin } from "./b9-admin";
import { HierarchyGrid, type PathChange } from "./hierarchy-grid";
import { ImportReviewGrid, type ReviewChange } from "./import-review-grid";
import { UploadedWorkbookGrid } from "./uploaded-workbook-grid";
import { uploadPrivateFile, privateExport } from "@/lib/api/private-transfers";

type Node = { id: string; name: string; version: number; draft_revision?: number; published_revision?: number; base_revision?: number; has_draft?: boolean; description?: string | null; learning_outcome?: string | null; archived?: boolean; levels?: Node[]; subjects?: Node[]; domains?: Node[]; categories?: Node[]; topics?: Node[]; subtopics?: Node[] };
type CurriculumRow = { id: string; code: string; name: string; state: string; version: number; revision: number; published_revision?: number; draft_revision?: number; has_draft?: boolean; updated_at?: string; can_delete?: boolean };
type StudentRow = { id: string; display_name: string | null; email: string | null; status: string; created_at: string };
type LearningMembershipRow = { id: string; curriculum_id: string; level_id: string | null;
  subject_id: string | null; domain_id: string | null; topic_id: string | null;
  subtopic_id: string | null; visible: boolean; created_at: string };
type ActivitySummary = { visits: number; sessions: number; questions: number; resource_opens: number; last_activity_at: string | null };
type ImportPreviewRow = { sheet: string; row_number: number; normalized_path: string[] | null;
  operation: string; errors: { column: string; code: string }[] };
type ImportResult = { import_id: string; filename?: string; sheets?: string[]; preview_revision?: string; round_trip?: boolean; metadata?: Record<string, string>;
  counts?: Record<string, number>; rows?: ImportPreviewRow[]; status?: string; issue_count?: number; curriculum_version?: number; base_revision?: number; base_draft_revision?: number; published_revision?: number; dependency_warnings?: string[] };
type ImportHistoryRow = { import_id: string; filename?: string; draft_revision?: number; published_revision?: number; events?: { status: string; code?: string; at: string; draft_revision?: number; curriculum_revision?: number }[]; status: string; created_at: string; counts?: Record<string, number> };

async function get(path: string) {
  const response = await fetch("/api/b4/" + path, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data?.detail || data?.error?.message || "Request failed.");
  return data;
}
async function mutation(path: string, method: "POST" | "PATCH" | "DELETE", body: unknown, idempotencyKey?: string) {
  const csrf = await fetch("/api/auth/csrf", { cache: "no-store" }).then(r => r.json());
  const response = await fetch("/api/b4/" + path, {
    method, headers: { "content-type": "application/json", "x-flame-csrf": csrf.csrf,
      ...(idempotencyKey ? { "idempotency-key": idempotencyKey } : {}) },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = data?.detail ?? data?.error;
    const error = new Error(typeof detail === "string" ? detail : data?.error?.message || detail?.code || "The change could not be saved.");
    Object.assign(error, { detail, status: response.status, path });
    throw error;
  }
  return data;
}
async function upload(curriculumId: string, file: File) {
  const direct = await uploadPrivateFile<ImportResult>(file, { purpose: "curriculum", curriculum_id: curriculumId });
  if (direct) return direct;
  const csrf = await fetch("/api/auth/csrf", { cache: "no-store" }).then(r => r.json());
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/b4/admin/curriculum/imports?curriculum_id=" + curriculumId, {
    method: "POST", headers: { "x-flame-csrf": csrf.csrf }, body,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data?.detail || data?.error?.message || "Upload failed.");
  return data as ImportResult;
}

type Choice = { id: string; name: string; path: string; parentId?: string; lineage: string[]; version: number; kind: string; archived?: boolean; description?: string | null; learning_outcome?: string | null };
function flatten(tree: Node | null): Choice[] {
  if (!tree) return [];
  const result: Choice[] = [{ id: tree.id, name: tree.name, path: tree.name,
    version: tree.version, kind: "curriculum", lineage: [], description: tree.description }];
  function visit(node: Node, ancestor: string, lineage: string[]) {
    const groups: [string, keyof Node][] = [
      ["level", "levels"], ["subject", "subjects"], ["domain", "domains"],
      ["category", "categories"], ["topic", "topics"], ["subtopic", "subtopics"],
    ];
    for (const [childKind, key] of groups) {
      for (const child of (node[key] as Node[] | undefined) ?? []) {
        const path = ancestor + " / " + child.name;
        result.push({ id: child.id, name: child.name, path, parentId: node.id,
          version: child.version, kind: childKind, lineage: [...lineage, node.id], archived: child.archived,
          learning_outcome: child.learning_outcome });
        visit(child, path, [...lineage, node.id]);
      }
    }
  }
  visit(tree, tree.name, []);
  return result;
}
function positionOverflowMenu(menu: HTMLDetailsElement) {
  if (!menu.open) return;
  const trigger = menu.querySelector("summary");
  const panel = menu.querySelector<HTMLElement>(".admin-overflow-menu");
  if (!trigger || !panel) return;
  const rect = trigger.getBoundingClientRect();
  const height = panel.getBoundingClientRect().height;
  const width = panel.getBoundingClientRect().width;
  const top = window.innerHeight - rect.bottom >= height + 8
    ? rect.bottom + 4 : Math.max(8, rect.top - height - 4);
  const left = Math.max(8, Math.min(rect.left + rect.width / 2 - width / 2, window.innerWidth - width - 8));
  menu.style.setProperty("--menu-top", top + "px");
  menu.style.setProperty("--menu-left", left + "px");
}

export function AdminPanel() {
  const [tab, setTab] = useState<"curriculum" | "students" | "resources" | "teachers" | "kits">("curriculum");
  const [catalogueView, setCatalogueView] = useState<"list" | "create" | "workspace">("list");
  useEffect(() => {
    const closeOutside = (event: PointerEvent) => {
      const target = event.target as globalThis.Node | null;
      for (const menu of document.querySelectorAll<HTMLDetailsElement>(".b4-admin details.admin-overflow[open]")) {
        if (!target || !menu.contains(target)) menu.open = false;
      }
    };
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      for (const menu of document.querySelectorAll<HTMLDetailsElement>(".b4-admin details.admin-overflow[open]")) menu.open = false;
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  const [workspaceTab, setWorkspaceTab] = useState<"hierarchy" | "import" | "history" | "revisions">("hierarchy");
  const [createMode, setCreateMode] = useState<"manual" | "excel">("manual");
  const [catalogueSearch, setCatalogueSearch] = useState("");
  const [catalogueStatus, setCatalogueStatus] = useState("all");
  const [navIds, setNavIds] = useState<Record<string, string>>({});
  const [nodePage, setNodePage] = useState(0);
  const [addParentId, setAddParentId] = useState("");
  const [addKind, setAddKind] = useState("level");
  const [rows, setRows] = useState<CurriculumRow[]>([]);
  const [selected, setSelected] = useState("");
  const [loadedTree, setTree] = useState<Node | null>(null);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const [bulkStudentReload,setBulkStudentReload]=useState(0);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [student, setStudent] = useState<(StudentRow & { learning: LearningMembershipRow[] }) | null>(null);
  const [studentOffset, setStudentOffset] = useState(0);
  const [studentTotal, setStudentTotal] = useState(0);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [studentError, setStudentError] = useState("");
  const [studentActivity, setStudentActivity] = useState<ActivitySummary | null>(null);
  const [search, setSearch] = useState("");
  const [curriculumName, setCurriculumName] = useState("");
  const [childName, setChildName] = useState("");
  const [nodeSearch, setNodeSearch] = useState("");
  
  const [loadingCurricula, setLoadingCurricula] = useState(true);
  const [loadingTree, setLoadingTree] = useState(false);
  const [noticeError, setNoticeError] = useState(false);
  const [code, setCode] = useState("");
  const [subtopicName, setSubtopicName] = useState("");
  const [editId, setEditId] = useState("");
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editOutcome, setEditOutcome] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<ImportResult | null>(null);
  const batchRef = useRef(batch);
  batchRef.current = batch;
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<ImportResult | null>(null);
  const [history, setHistory] = useState<ImportHistoryRow[]>([]);
  const [restoringImport, setRestoringImport] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [workspaceHydrated, setWorkspaceHydrated] = useState(false);
  useEffect(() => {
    try {
      const value = JSON.parse(sessionStorage.getItem("flame:admin-workspace") ?? "null");
      if (value?.id && ["hierarchy", "import", "history", "revisions"].includes(value.tab)) {
        selectedRef.current = value.id; setSelected(value.id); setCatalogueView("workspace"); setWorkspaceTab(value.tab);
      }
    } catch {}
    setWorkspaceHydrated(true);
  }, []);
  useEffect(() => {
    if (workspaceHydrated) sessionStorage.setItem("flame:admin-workspace", JSON.stringify(
      catalogueView === "workspace" ? { id: selected, tab: workspaceTab } : null));
  }, [selected, workspaceTab, catalogueView, workspaceHydrated]);
  const [historyDetail, setHistoryDetail] = useState<unknown>(null);
  const [historyIssues, setHistoryIssues] = useState<{ items: { sheet: string; row_number: number; column: string; code: string }[]; total: number } | null>(null);
  const [revisions, setRevisions] = useState<unknown[]>([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const refreshSequence = useRef(0);
  const importSequence = useRef(0);
  const [importConflict, setImportConflict] = useState(false);
  const [recoveryRequired, setRecoveryRequired] = useState(false);
  const saveGridButton = useRef<HTMLButtonElement>(null);
  const [gridDirty, setGridDirty] = useState(false);
  const [importDirty, setImportDirty] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CurriculumRow | null>(null);
  const [deleteReview, setDeleteReview] = useState<{ counts: Record<string, number>; blockers: Record<string, number> } | null>(null);
  const [deleteTyped, setDeleteTyped] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [replaceConfirm, setReplaceConfirm] = useState("");
  const [exportBusy, setExportBusy] = useState(false);
  const [gridMetrics, setGridMetrics] = useState({ unsaved: 0, invalid: 0, conflicts: 0 });
  const tree = loadedTree?.id === selected ? loadedTree : null;
  const options = useMemo(() => flatten(tree), [tree]);
  const filteredCurricula = rows.filter(row => (catalogueStatus === "all" || row.state === catalogueStatus) &&
    (row.name + " " + row.code).toLowerCase().includes(catalogueSearch.trim().toLowerCase()));
  const focusedId = navIds.subtopic || navIds.topic || navIds.category || navIds.domain || navIds.subject || navIds.level;
  const filteredNodes = options.filter(option => option.kind !== "curriculum" &&
    (!focusedId || option.id === focusedId || option.lineage.includes(focusedId)) &&
    (!nodeSearch.trim() || option.path.toLowerCase().includes(nodeSearch.trim().toLowerCase())));
  const visibleNodes = filteredNodes.slice(nodePage * 40, (nodePage + 1) * 40);
  const navChoices = (kind: string) => options.filter(option => !option.archived && option.kind === kind &&
    (kind === "level" ? true : kind === "subject" ? option.parentId === navIds.level
      : kind === "domain" ? option.parentId === navIds.subject
      : kind === "category" ? option.parentId === navIds.domain
      : kind === "topic" ? option.lineage.includes(navIds.domain) && (!navIds.category || option.parentId === navIds.category)
      : option.parentId === navIds.topic));
  const levelSuggestions = (tree?.levels ?? []).filter(level => !level.archived).map(level => level.name);
  const selectedRow = rows.find(row => row.id === selected);
  const previewStale = Boolean(preview && tree && (preview.base_revision !== (tree as Node & { revision?: number }).revision ||
    preview.base_draft_revision !== tree.draft_revision || preview.curriculum_version !== tree.version ||
    preview.published_revision !== tree.published_revision));
  const importBlocked = previewStale || recoveryRequired || importConflict;
  const edit = options.find(option => option.id === editId);
  const hasPublishablePath = options.some(option => option.kind === "subtopic" && !option.archived);
  const recentChanges = (revisions as { change_kind?: string }[])
    .slice(0, Math.max(0, (revisions as { change_kind?: string }[]).findIndex(item => item.change_kind === "publish") < 0
      ? revisions.length : (revisions as { change_kind?: string }[]).findIndex(item => item.change_kind === "publish")))
    .slice(0, 5).map(item => item.change_kind?.replaceAll("_", " ") ?? "Curriculum change");
  const unsavedEdit = Boolean(edit && (editName !== edit.name ||
    (edit.kind === "curriculum" && editDescription !== (edit.description ?? "")) ||
    (edit.kind === "topic" && editOutcome !== (edit.learning_outcome ?? "")))) || Boolean(addParentId && childName.trim());
  const publicationBlocker = historyError ? "Pending-import status could not be verified. Review latest changes before publishing." : selectedRow?.state === "archived" ? "Restore this curriculum before publishing." : gridMetrics.invalid ? "Resolve invalid hierarchy rows before publishing." : restoringImport ? "Checking pending imports…" : batch ? "Complete or cancel the replacement import first." :
    gridDirty || unsavedEdit ? "Save or cancel your open draft edits before publishing." : !hasPublishablePath ? "Add a complete hierarchy path or import a workbook before publishing." : "";
  function chooseNav(kind: string, id: string) {
    const order = ["level", "subject", "domain", "category", "topic", "subtopic"];
    const next = { ...navIds, [kind]: id };
    for (const child of order.slice(order.indexOf(kind) + 1)) next[child] = "";
    setNavIds(next); setNodePage(0); setEditId(""); setAddParentId("");
  }

  function syncRevisions(result: Partial<CurriculumRow> & { base_revision?: number }) {
    const id = selectedRef.current;
    localStorage.setItem("flame:curriculum-updated", JSON.stringify({ id, nonce: crypto.randomUUID() }));
    const patch: Partial<CurriculumRow> = {};
    for (const field of ["draft_revision", "published_revision", "revision", "state"] as const) {
      if (result[field] !== undefined) Object.assign(patch, { [field]: result[field] });
    }
    if (result.id === id && result.version !== undefined) patch.version = result.version;
    setRows(current => current.map(row => row.id === id ? { ...row, ...patch } : row));
    setTree(current => current?.id === id ? { ...current, ...patch,
      ...(result.base_revision !== undefined ? { base_revision: result.base_revision } : {}) } : current);
  }
  async function refresh() {
    const request = ++refreshSequence.current;
    const curriculumId = selectedRef.current;
    const listing = await get("admin/curricula?limit=100");
    if (request !== refreshSequence.current) return;
    setRows(listing.items);
    if (curriculumId) {
      const [nextTree, nextRevisions, nextHistory] = await Promise.all([
        get("admin/curricula/" + curriculumId + "/tree"),
        get("admin/curricula/" + curriculumId + "/revisions"),
        get("admin/curriculum/imports?curriculum_id=" + curriculumId),
      ]);
      if (selectedRef.current === curriculumId && request === refreshSequence.current) {
        setTree(nextTree); setRevisions(nextRevisions.items); setHistory(nextHistory.items); setHistoryError("");
      }
    }
  }
  useEffect(() => {
    let active = true;
    get("admin/curricula?limit=100").then(data => {
      if (!active) return;
      setRows(data.items);
      setSelected(current => current || data.items.find((row: CurriculumRow) => row.state === "published")?.id || data.items[0]?.id || "");
    }).catch(error => { if (active) { setNotice(error.message); setNoticeError(true); } })
      .finally(() => { if (active) setLoadingCurricula(false); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!selected) { setTree(null); setRevisions([]); return; }
    let active = true;
    const request = ++refreshSequence.current;
    setTree(null); setRevisions([]); setHistory([]); setHistoryDetail(null); setHistoryIssues(null); setLoadingTree(true); setEditId(""); setAddParentId(""); setNavIds({}); setNodePage(0);
    Promise.all([get("admin/curricula/" + selected + "/tree"),
      get("admin/curricula/" + selected + "/revisions")]).then(([nextTree, nextRevisions]) => {
        if (active && request === refreshSequence.current) { setTree(nextTree); setRevisions(nextRevisions.items); }
      }).catch(error => { if (active) { setNotice(error.message); setNoticeError(true); } })
      .finally(() => { if (active) setLoadingTree(false); });
    return () => { active = false; };
  }, [selected]);
  useEffect(() => {
    if (tab !== "curriculum" || catalogueView !== "workspace" || !selected) return;
    let active = true;
    const sequence = importSequence.current;
    setRestoringImport(true); setHistoryLoading(true); setHistoryError("");
    get("admin/curriculum/imports?curriculum_id=" + selected).then(async data => {
      if (!active || selectedRef.current !== selected || sequence !== importSequence.current) return;
      setHistory(data.items);
      const latest = (data.items as ImportHistoryRow[]).find(item => item.status === "uploaded" || item.status === "previewed");
      if (!latest) return;
      const detail = await get("admin/curriculum/imports/" + latest.import_id);
      if (!active || selectedRef.current !== selected || batchRef.current || sequence !== importSequence.current) return;
      setBatch({ import_id: latest.import_id, status: detail.status, sheets: detail.sheets, round_trip: detail.round_trip, filename: detail.filename });
      setMapping(detail.sheet_levels ?? (detail.round_trip ? { Curriculum: "__ALL_LEVELS__" } : Object.fromEntries((detail.sheets ?? []).map((sheet: string) => [sheet, sheet]))));
      setPreview(detail.preview ?? null);
    }).catch(error => { if (active) setHistoryError("Could not restore server-recorded imports: " + error.message); })
      .finally(() => { if (active) { setRestoringImport(false); setHistoryLoading(false); } });
    return () => { active = false; };
  }, [tab, catalogueView, selected]);
  useEffect(() => {
    if (tab !== "students") return;
    let active = true;
    setLoadingStudents(true); setStudentError("");
    get("admin/students?q=" + encodeURIComponent(search) + "&offset=" + studentOffset + "&limit=30")
      .then(data => { if (active) { setStudents(data.items); setStudentTotal(data.total); } })
      .catch(error => { if (active) setStudentError(error.message); })
      .finally(() => { if (active) setLoadingStudents(false); });
    return () => { active = false; };
  }, [tab, search, studentOffset, bulkStudentReload]);
  useEffect(() => {
    if (tab !== "curriculum" || workspaceTab !== "history" || !selected) return;
    let active = true; setHistoryLoading(true); setHistoryError("");
    get("admin/curriculum/imports?curriculum_id=" + selected)
      .then(data => { if (active) setHistory(data.items); })
      .catch(error => { if (active) setHistoryError(error.message); })
      .finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [tab, workspaceTab, selected]);

  useEffect(() => {
    if (catalogueView !== "workspace" || !selected) return;
    const reloadLatest = () => { void refresh().catch(error => { setNotice(error.message); setNoticeError(true); }); };
    const otherTab = (event: StorageEvent) => { if (event.key === "flame:curriculum-updated") reloadLatest(); };
    window.addEventListener("focus", reloadLatest); window.addEventListener("storage", otherTab);
    return () => { window.removeEventListener("focus", reloadLatest); window.removeEventListener("storage", otherTab); };
  }, [selected, catalogueView]);
  useEffect(() => { if (previewStale || importDirty) setReplaceConfirm(""); }, [previewStale, importDirty]);

  async function act(run: () => Promise<void>, refreshAfter = true) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true); setNotice(""); setNoticeError(false);
    try {
      await run();
      if (refreshAfter) {
        try { await refresh(); }
        catch { setNotice(current => current + " The change completed, but latest status could not be loaded. Use Review latest changes."); }
      }
    }
    catch (error) {
      const message = error instanceof Error ? error.message : "Request failed.";
      const code = (error as { detail?: { code?: string } }).detail?.code;
      const revisionConflict = ["updated_elsewhere", "version_conflict", "stale_preview", "invalid_preview", "source_path_changed"].includes(code ?? "");
      setNotice(revisionConflict
        ? "This operation was not saved because its revision changed. Review latest changes, then retry. Your entered values are preserved."
        : code === "archived_path_conflict"
          ? "This path contains an archived hierarchy item. Nothing was published; your saved draft is preserved. Review the affected path before retrying."
          : message);
      if (batchRef.current && (code === "stale_preview" || code === "invalid_preview")) {
        setImportConflict(true); setRecoveryRequired(true);
        const operation = (error as { path?: string }).path?.endsWith("/commit") ? "Replacement hierarchy was not saved to draft" : "Replacement comparison was not regenerated";
        const mismatch = (error as { detail?: { revision_mismatch?: string } }).detail?.revision_mismatch;
        setNotice(operation + " because its preview is outdated" + (mismatch ? " (" + mismatch.replaceAll("_", " ") + ")" : "") + ". Your workbook and review edits are preserved. Retry comparison, review the latest changes, then confirm again.");
      }
      setNoticeError(true);
    } finally { busyRef.current = false; setBusy(false); }
  }
  async function cancelImport() {
    if (!batch || !canLeaveGrid()) return;
    await act(async () => {
      await mutation("admin/curriculum/imports/" + batch.import_id + "/cancel", "POST", {});
      importSequence.current++; setBatch(null); setPreview(null); setFile(null); setMapping({});
      setImportDirty(false); setImportConflict(false); setRecoveryRequired(false);
      setNotice("Replacement import cancelled. The saved draft and published curriculum are unchanged.");
    });
  }
  async function retryComparison() {
    const current = batchRef.current;
    if (!current) return;
    const sequence = ++importSequence.current;
    await act(async () => {
      await refresh();
      const result = await mutation("admin/curriculum/imports/" + current.import_id + "/preview", "POST",
        { sheet_levels: Object.fromEntries(Object.entries(mapping).filter(([, value]) => value.trim())) });
      if (sequence !== importSequence.current || batchRef.current?.import_id !== current.import_id) return;
      setPreview(result); setReplaceConfirm(""); setImportConflict(false); setRecoveryRequired(false);
      setNotice("Comparison updated against the latest draft. Review additions, changes, removals and warnings, save preserved corrections, then confirm again.");
      setHistory((await get("admin/curriculum/imports?curriculum_id=" + selected)).items);
    }, false);
  }
  function canLeaveGrid() {
    return !(gridDirty || importDirty) || window.confirm("Discard unsaved table changes?");
  }
  async function saveGrid(changes: PathChange[]) {
    const result = await mutation("admin/curricula/" + selected + "/paths/batch", "POST",
      { expected_revision: tree?.draft_revision ?? 1, changes });
    syncRevisions(result);
    await refresh();
    setNotice("Draft changes saved.");
    setNoticeError(false);
  }
  function openHierarchy() {
    setWorkspaceTab("hierarchy");
  }
  async function saveImportReview(changes: ReviewChange[]) {
    if (!batch || !preview?.preview_revision) throw new Error("Preview the workbook first.");
    if (busyRef.current) throw new Error("A request is already pending.");
    busyRef.current = true; setBusy(true);
    let result;
    try {
      result = await mutation("admin/curriculum/imports/" + batch.import_id + "/review", "POST",
        { preview_revision: preview.preview_revision, changes });
    } catch (error) {
      const code = (error as { detail?: { code?: string } }).detail?.code;
      if (code === "stale_preview" || code === "invalid_preview") {
        setImportConflict(true); setRecoveryRequired(true); setNoticeError(true);
        setNotice("Workbook corrections were not saved: the comparison is outdated. Retry comparison; your review edits are preserved for saving after review.");
      }
      throw error;
    } finally { busyRef.current = false; setBusy(false); }
    if (selectedRef.current !== selected || batchRef.current?.import_id !== batch.import_id) throw new Error("The active workbook changed. Open the original import to review its saved corrections.");
    setPreview(result); setReplaceConfirm(""); setImportConflict(false); setRecoveryRequired(false);
    setNotice(result.issue_count ? "Corrections saved. Review the remaining row issues." :
      "Workbook corrections saved and validated. Ready to import.");
    setNoticeError(false);
    void get("admin/curriculum/imports?curriculum_id=" + selected).then(data => {
      if (selectedRef.current === selected) setHistory(data.items);
    }).catch(error => setHistoryError(error.message));
    return result;
  }
  async function renameGrid(field: string, ref: { id: string; version: number }, name: string) {
    const result = await mutation("admin/curricula/" + selected + "/draft/rename", "POST",
      { expected_revision: tree?.draft_revision ?? 1, field, node_id: ref.id, name });
    syncRevisions(result);
    await refresh();
    setNotice("Draft changes saved.");
    setNoticeError(false);
  }
  async function deleteIncomplete(field: string, ref: { id: string; version: number }) {
    await mutation("admin/curriculum/" + field + "/" + ref.id, "DELETE",
      { expected_version: ref.version });
    await refresh();
    setNotice("Incomplete draft node deleted.");
    setNoticeError(false);
  }
  async function exportCurriculum(source: "draft" | "published" = "draft") {
    if (!selectedRow) return;
    setExportBusy(true); setNotice(""); setNoticeError(false);
    try {
      const direct = await privateExport({ purpose: "curriculum", curriculum_id: selectedRow.id, source });
      let blob: Blob;
      if (direct) blob = direct.blob;
      else {
        const response = await fetch("/api/b4/admin/curricula/" + selectedRow.id + "/export?source=" + source, { cache: "no-store" });
        if (!response.ok) throw new Error("Excel export could not be generated.");
        blob = await response.blob();
      }
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = selectedRow.code + "-" + source + ".xlsx";
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      URL.revokeObjectURL(url);
      setNotice("Complete " + source + " hierarchy exported. Screen filters were not applied.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Export failed."); setNoticeError(true);
    } finally { setExportBusy(false); }
  }
  async function reviewDelete(row: CurriculumRow) {
    if (!canLeaveGrid()) return;
    setDeleteTarget(row); setDeleteReview(null); setDeleteTyped(""); setDeleteError(""); setDeleteBusy(true);
    try { setDeleteReview(await get("admin/curricula/" + row.id + "/deletion-review")); }
    catch (error) { setDeleteError(error instanceof Error ? error.message : "Could not review dependencies."); }
    finally { setDeleteBusy(false); }
  }
  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleteBusy(true); setDeleteError("");
    try {
      await mutation("admin/curricula/" + deleteTarget.id + "/permanent", "POST",
        { expected_version: deleteTarget.version, expected_revision: deleteTarget.revision,
          confirm: deleteTyped.trim() });
      const listing = await get("admin/curricula?limit=100");
      setRows(listing.items);
      if (selected === deleteTarget.id) setSelected(listing.items[0]?.id ?? "");
      setCatalogueView("list"); setDeleteTarget(null); setDeleteReview(null); setDeleteTyped("");
      setNotice("Curriculum permanently deleted."); setNoticeError(false);
    } catch (error) { setDeleteError(error instanceof Error ? error.message : "Deletion failed."); }
    finally { setDeleteBusy(false); }
  }
  function openWorkspace(id: string, view: "hierarchy" | "import" | "history" | "revisions" = "hierarchy") {
    if (!canLeaveGrid()) return;
    setGridDirty(false); setImportDirty(false);
    importSequence.current++; selectedRef.current = id; setImportConflict(false); setRecoveryRequired(false); setSelected(id); setCatalogueView("workspace"); setWorkspaceTab(view);
    setEditId(""); setAddParentId(""); setNodeSearch(""); setNodePage(0);
    setBatch(null); setPreview(null); setFile(null); setMapping({}); setReplaceConfirm("");
  }
  function startAdd(parent: Choice, nextKind?: string) {
    setAddParentId(parent.id);
    setAddKind(nextKind ?? ({ curriculum: "level", level: "subject", subject: "domain",
      domain: "topic", category: "topic", topic: "subtopic" }[parent.kind] ?? "level"));
    setChildName(""); setSubtopicName(""); setEditId("");
  }
  function startEdit(option: Choice) {
    setEditId(option.id); setEditName(option.name);
    setEditDescription(option.description ?? ""); setEditOutcome(option.learning_outcome ?? "");
    setAddParentId("");
  }
  const selectedParent = options.find(option => option.id === addParentId);
  async function saveChild() {
    if (!selectedParent || !childName.trim()) return;
    await act(async () => {
      await mutation("admin/curriculum/" + addKind, "POST", { parent_id: selectedParent.id, name: childName.trim(),
        ...(addKind === "topic" ? { category_id: selectedParent.kind === "category" ? selectedParent.id : null,
          subtopic_name: subtopicName.trim() || null } : {}) });
      setAddParentId(""); setChildName(""); setSubtopicName(""); setNotice("Draft changes saved.");
    });
  }
  async function saveEdit() {
    if (!edit || !editName.trim()) return;
    await act(async () => {
      await mutation("admin/curriculum/" + edit.kind + "/" + edit.id, "PATCH",
        { expected_version: edit.version, name: editName.trim(),
          ...(edit.kind === "curriculum" ? { description: editDescription } : {}),
          ...(edit.kind === "topic" ? { learning_outcome: editOutcome } : {}) });
      setEditId(""); setNotice("Draft changes saved.");
    });
  }
  async function archiveChoice(option: Choice) {
    if (!window.confirm("Archive " + option.path + "? It will leave the member catalogue while its history remains.")) return;
    await act(async () => {
      await mutation("admin/curriculum/" + option.kind + "/" + option.id + "/archive", "POST",
        { expected_version: option.version });
      setEditId(""); setNotice("Archived. Historical IDs are retained.");
    });
  }
  const sections = [
    { id: "curriculum", label: "Curriculum Catalogue", hint: "Create and publish learning paths" },
    { id: "resources", label: "Resource Library", hint: "Manage approved learning media" },
    { id: "students", label: "Students", hint: "Profiles and measured activity" },
    { id: "teachers", label: "Teachers", hint: "Expertise and publication" },
    { id: "kits", label: "Activity Kits", hint: "Reusable topic-linked kits" },
  ] as const;
  const activeSection = sections.find(section => section.id === tab)!;
  return <div className={"b4-admin " + (tab === "resources" ? "admin-resource-mode" : tab === "curriculum" && catalogueView === "workspace" ? "admin-workspace-mode" : "")}>
    <nav className="admin-tabs" aria-label="Admin sections">
      {sections.map(section => <button key={section.id} type="button" aria-label={section.label}
        aria-current={tab === section.id ? "page" : undefined}
        onClick={() => { if (!canLeaveGrid()) return; setGridDirty(false); setImportDirty(false); setTab(section.id); setNotice(""); }}>
        <strong>{section.label}</strong><span>{section.hint}</span>
      </button>)}
    </nav>
    <div className="admin-section-heading"><div><p className="admin-eyebrow">ADMIN WORKSPACE</p>
      <h2>{activeSection.label}</h2><p>{activeSection.hint}</p></div></div>
    {notice && <p role={noticeError ? "alert" : "status"} className={`b4-notice ${noticeError ? "b4-notice-error" : ""}`}>{notice}<button type="button" aria-label="Dismiss notification" onClick={() => setNotice("")}>×</button></p>}
    {noticeError && <div className="admin-row-actions">
      <button disabled={busy} onClick={() => void act(async () => { await refresh(); setNotice("Latest draft and revision loaded. Your entered values are preserved. Review before retrying."); }, false)}>Review latest changes</button>
      {batch && <button disabled={busy} onClick={() => void retryComparison()}>Retry comparison</button>}
    </div>}
    {tab !== "students" && tab !== "curriculum" && tab !== "resources" && <section className="admin-context" aria-label="Selected curriculum">
      <div><strong>Working curriculum</strong><p>Choose where changes and new content belong.</p></div>
      <label><span className="sr-only">Curriculum</span><select aria-label="Curriculum" value={selected}
        disabled={loadingCurricula || busy} onChange={event => {
          setSelected(event.target.value); setBatch(null); setPreview(null); setHistory([]); setHistoryDetail(null); setHistoryIssues(null);
        }}>
        <option value="">{loadingCurricula ? "Loading curricula…" : "Choose a curriculum"}</option>
        {rows.map(row => <option key={row.id} value={row.id}>{row.name} ({row.code}, {row.state})</option>)}
      </select></label>
      {selectedRow && <span className={`admin-state admin-state-${selectedRow.state}`}>{selectedRow.state} · revision {selectedRow.revision}</span>}
    </section>}
    {tab !== "students" && tab !== "curriculum" && !loadingCurricula && !rows.length && <p className="admin-empty">No curriculum exists yet. Create one in Curriculum Catalogue before uploading or mapping content.</p>}
    {tab === "curriculum" && catalogueView === "list" && <section className="admin-card">
      <div className="admin-card-heading"><div><h3>Curricula</h3><p>Choose a curriculum to review its hierarchy, imports and publication.</p></div>
        <button className="admin-primary" onClick={() => { setCatalogueView("create"); setCode(""); setCurriculumName(""); setCreateMode("manual"); }}>Create curriculum</button></div>
      <div className="admin-list-filters">
        <label>Search curricula<input type="search" value={catalogueSearch} onChange={event => setCatalogueSearch(event.target.value)} placeholder="Name or code" /></label>
        <label>Status<select value={catalogueStatus} onChange={event => setCatalogueStatus(event.target.value)}>
          <option value="all">All statuses</option><option value="draft">Draft</option><option value="published">Published</option><option value="archived">Archived</option>
        </select></label>
      </div>
      <p className="admin-result-count" aria-live="polite">{filteredCurricula.length} curriculum{filteredCurricula.length === 1 ? "" : "s"} shown</p>
      {loadingCurricula && <p role="status">Loading curricula…</p>}
      {!loadingCurricula && !filteredCurricula.length && <p className="admin-empty">{rows.length ? "No curricula match these filters." : "No curricula yet. Create one to begin."}</p>}
      {!!filteredCurricula.length && <div className="admin-table-scroll admin-curricula-table"><table><thead><tr>
        <th>Name</th><th>Code</th><th>Status</th><th>Revision / version</th><th>Last updated</th><th>Actions</th>
      </tr></thead><tbody>{filteredCurricula.map(row => <tr key={row.id}>
        <td><button className="admin-name-link" onClick={() => openWorkspace(row.id)}>{row.name}</button></td><td>{row.code}</td><td><span className={"admin-state admin-state-" + row.state}>{row.state}</span></td>
        <td>{row.revision} / {row.version}</td><td>{row.updated_at ? new Date(row.updated_at).toLocaleDateString() : "—"}</td>
        <td><div className="admin-row-actions admin-catalogue-actions">
          <button className="admin-primary" onClick={() => openWorkspace(row.id)}>Edit</button>
          <details className="admin-overflow" onToggle={event => positionOverflowMenu(event.currentTarget)}><summary aria-label={"More actions for " + row.name}>•••</summary>
            <div className="admin-overflow-menu" onClick={event => { const menu = event.currentTarget.closest("details"); if (menu) menu.open = false; }}>
              {row.state !== "archived" ? <button disabled={busy}
                onClick={() => {
                  if (!window.confirm("Archive " + row.name + "? Its history will be retained.")) return;
                  void act(async () => {
                    await mutation("admin/curriculum/curriculum/" + row.id + "/archive", "POST", { expected_version: row.version });
                    setNotice("Curriculum archived.");
                  });
                }}>Archive</button> : <button disabled={busy} onClick={() => void act(async () => {
                  await mutation("admin/curricula/" + row.id + "/restore", "POST", { expected_version: row.version });
                  setNotice("Curriculum restored as draft.");
                })}>Restore</button>}
              <button className="admin-danger" disabled={busy}
                onClick={() => void reviewDelete(row)}>Permanently delete curriculum</button>
            </div>
          </details>
        </div></td>
      </tr>)}</tbody></table></div>}
      {rows.length === 100 && <p className="admin-help">Showing the newest 100 curricula. Search or archive older items through the API if needed.</p>}
    </section>}
    {tab === "curriculum" && catalogueView === "create" && <section className="admin-card">
      <div className="admin-card-heading"><div><h3>Create curriculum</h3><p>Every workbook import belongs to a curriculum code and name.</p></div>
        <button onClick={() => setCatalogueView("list")}>Back to curricula</button></div>
      <div className="admin-start-options" role="group" aria-label="Starting method">
        <button type="button" aria-pressed={createMode === "manual"} onClick={() => setCreateMode("manual")}>Create empty curriculum<span>Build the hierarchy manually.</span></button>
        <button type="button" aria-pressed={createMode === "excel"} onClick={() => setCreateMode("excel")}>Import from Excel<span>Create a draft, then upload a workbook.</span></button>
      </div>
      <div className="b4-fields">
        <label>Curriculum code<input value={code} maxLength={80} onChange={event => setCode(event.target.value)} /></label>
        <label>Curriculum name<input value={curriculumName} maxLength={255} onChange={event => setCurriculumName(event.target.value)} /></label>
        <button disabled={busy || !code.trim() || !curriculumName.trim()} onClick={() => void act(async () => {
          const row = await mutation("admin/curricula", "POST", { code: code.trim(), name: curriculumName.trim() });
          setRows(current => [row, ...current.filter(item => item.id !== row.id)]);
          setCode(""); setCurriculumName(""); openWorkspace(row.id, createMode === "excel" ? "import" : "hierarchy");
          setNotice("Curriculum created. Review the draft before publishing.");
        })}>Create draft</button>
      </div>
      <p className="admin-help">The curriculum remains Draft until you explicitly publish it.</p>
    </section>}
    {tab === "curriculum" && catalogueView === "workspace" && <>
      <section className="admin-card admin-workspace-header">
        <div className="admin-workspace-back"><button onClick={() => { if (!canLeaveGrid()) return; setCatalogueView("list"); setGridDirty(false); setImportDirty(false); setEditId(""); setAddParentId(""); }}>← All curricula</button></div>
        {selectedRow ? <><div className="admin-card-heading admin-workspace-title"><div><h3>{selectedRow.name}</h3>
          <p>Code {selectedRow.code} · Last updated {selectedRow.updated_at ? new Date(selectedRow.updated_at).toLocaleString() : "—"}</p></div>
          <div className="admin-workspace-actions">
            <button disabled={busy || selectedRow.state === "archived" || !options.length} onClick={() => startEdit(options[0])}>Edit details</button>
            <details className="admin-overflow" onToggle={event => positionOverflowMenu(event.currentTarget)}><summary>Export Excel</summary>
              <div className="admin-overflow-menu"><button disabled={exportBusy} onClick={() => void exportCurriculum("draft")}>Export complete draft</button>
                <button disabled={exportBusy || !tree?.published_revision} onClick={() => void exportCurriculum("published")}>Export published curriculum</button></div></details>
            <button disabled={busy} onClick={() => setWorkspaceTab("import")}>Import replacement</button>
            <details className="admin-overflow" onToggle={event => positionOverflowMenu(event.currentTarget)}><summary aria-label="More curriculum actions">•••</summary>
              <div className="admin-overflow-menu" onClick={event => { const menu = event.currentTarget.closest("details"); if (menu) menu.open = false; }}>
                {selectedRow.state !== "archived" ? <button disabled={busy || gridDirty}
                  onClick={() => {
                    if (!window.confirm("Archive " + selectedRow.name + "? Its history will be retained.")) return;
                    void act(async () => {
                      await mutation("admin/curriculum/curriculum/" + selectedRow.id + "/archive", "POST",
                        { expected_version: selectedRow.version });
                      setNotice("Curriculum archived.");
                    });
                  }}>Archive</button> : <button disabled={busy} onClick={() => void act(async () => {
                    await mutation("admin/curricula/" + selectedRow.id + "/restore", "POST",
                      { expected_version: selectedRow.version });
                    setNotice("Curriculum restored as draft.");
                  })}>Restore</button>}
                <button className="admin-danger" disabled={busy}
                  onClick={() => void reviewDelete(selectedRow)}>Permanently delete curriculum</button>
              </div>
            </details>
          </div></div>
          <div className="admin-workspace-metrics" aria-label="Curriculum status">
            <div><span>Status</span><strong className={"admin-state admin-state-" + selectedRow.state}>{selectedRow.state}</strong></div>
            <div><span>Published revision</span><strong>{tree?.published_revision ?? selectedRow.published_revision ?? 0}</strong></div>
            <div><span>Draft revision</span><strong>{tree?.draft_revision ?? selectedRow.draft_revision ?? 0}</strong></div>
            <div><span>Unsaved changes</span><strong>{gridMetrics.unsaved + (importDirty ? 1 : 0)}</strong></div>
            <div><span>Validation errors</span><strong>{gridMetrics.invalid + (preview?.issue_count ?? 0)}</strong></div>
            <div><span>Conflicts</span><strong>{gridMetrics.conflicts + (importBlocked ? 1 : 0)}</strong></div>
          </div>
          {selectedRow.state === "published" && <p className="b4-notice" role="status">
            Saved changes remain in the private draft. Members continue seeing published revision {tree?.published_revision ?? selectedRow.revision} until Publish changes completes.
          </p>}          {editId === selected && <div className="admin-inline-form"><h4>Edit curriculum details</h4>
            <label>Name<input value={editName} maxLength={255} onChange={event => setEditName(event.target.value)} /></label>
            <label>Description<textarea value={editDescription} maxLength={2000} onChange={event => setEditDescription(event.target.value)} /></label>
            <div className="admin-row-actions"><button className="admin-primary" disabled={busy || !editName.trim()} onClick={() => void saveEdit()}>Save</button>
              <button onClick={() => setEditId("")}>Cancel</button></div>
          </div>}
          <div className="admin-publish-row"><div><strong>{publicationBlocker ? "Publication blocked" : "Ready to publish?"}</strong>{publicationBlocker && <p>{publicationBlocker}</p>}
            <p>{options.filter(o => o.kind === "level" && !o.archived).length} levels · {options.filter(o => o.kind === "topic" && !o.archived).length} topics · {options.filter(o => o.kind === "subtopic" && !o.archived).length} subtopics.
              Review edits and validation before publishing.</p>
            {recentChanges.length > 0 && <p className="admin-change-summary">Recent changes since publication: {recentChanges.join(", ")}{revisions.length > 5 ? "…" : ""}.</p>}
            {!hasPublishablePath && <p className="admin-help">No saved hierarchy is ready. If you uploaded a workbook, finish mapping, preview, and Create replacement draft in Excel Import before publishing.</p>}
            {Boolean(preview?.issue_count) && <p className="admin-help">Fix {preview?.issue_count} import issues before publishing.</p>}
            {batch && <p className="admin-help">Complete or cancel the replacement import first.</p>}
            {(unsavedEdit || gridDirty) && <p className="admin-help">Save or discard open edits before publishing.</p>}
          </div><button className="admin-primary" disabled={busy || restoringImport || Boolean(historyError) || Boolean(batch) || selectedRow.state === "archived" || !hasPublishablePath || Boolean(preview?.issue_count) || unsavedEdit || gridDirty || importDirty}
            onClick={() => {
              if (!window.confirm("Publish all saved draft changes for " + selectedRow.name + "? Members will move to the new immutable revision.")) return;
              void act(async () => {
                const result = await mutation("admin/curriculum/curriculum/" + selected + "/publish", "POST", { expected_version: tree?.version ?? selectedRow.version, expected_draft_revision: tree?.draft_revision ?? 0 });
                syncRevisions(result);
                setGridDirty(false); setImportDirty(false); setGridMetrics({ unsaved: 0, invalid: 0, conflicts: 0 });
                setNotice((Boolean(tree?.published_revision) || revisions.some(item => (item as { change_kind?: string }).change_kind === "publish") ? "Curriculum update published successfully" : "Curriculum published successfully") + " — revision " + result.revision + ".");
              });
            }}>Publish changes</button></div>
        </> : <p role="status">Loading curriculum…</p>}
        <div className="admin-subtabs admin-workspace-tabs" role="tablist" aria-label="Curriculum workspace">
          {([["hierarchy", "Hierarchy"], ["import", "Excel Import"], ["history", "Import History"], ["revisions", "Revision History"]] as const).map(([view, label]) =>
            <button key={view} type="button" role="tab" aria-selected={workspaceTab === view} onClick={() => { if (view === "hierarchy") { openHierarchy(); return; } setWorkspaceTab(view); }}>{label}</button>)}
        </div>
      </section>
      {loadingTree && <p role="status">Loading curriculum hierarchy…</p>}
      {restoringImport && <p role="status">Restoring pending workbook and import history…</p>}
      {!restoringImport && batch && <div className="admin-pending-import" role="status">
        <span><strong>Pending replacement</strong> · {batch.filename ?? "Server-recorded workbook"} · {preview ? importBlocked ? "Comparison outdated — revalidate" : importDirty ? "Unsaved workbook corrections" : "Validated; not saved to draft" : "Uploaded; mapping and validation required"}</span>
        <button disabled={busy} onClick={() => setWorkspaceTab("import")}>Continue import</button>
        <button disabled={busy} onClick={() => void cancelImport()}>Cancel import</button>
      </div>}
      {tree && selectedRow && <section className="admin-card" hidden={workspaceTab !== "hierarchy"} key={selected}>
        <div className="admin-card-heading"><div><h3>Hierarchy Table</h3>
          <p>Edit complete paths in rows. Category is optional; all other columns are required for a saved path.</p></div></div>
        <HierarchyGrid tree={tree} curriculumState={selectedRow.state} onBatchSave={saveGrid}
          onRename={renameGrid} onDeleteIncomplete={deleteIncomplete} onDirtyChange={setGridDirty}
          onMetricsChange={setGridMetrics} onReload={refresh} saveButtonRef={saveGridButton} />
      </section>}
      {selected && <section className="admin-card admin-imports" hidden={workspaceTab !== "import"}>
        <div className="admin-card-heading"><div><h3>Import complete replacement</h3>
          <button disabled={busy} onClick={openHierarchy}>Back to saved hierarchy</button>
          <p className="admin-active-stage"><strong>Active stage: {preview ? importBlocked ? "Revalidate comparison" : importDirty ? "Save workbook corrections" : "Review and create replacement draft" : batch ? "Map sheets and validate" : "Upload workbook"}</strong></p>
          <p>Upload a complete workbook, review additions and removals, then create a private replacement draft.</p>{batch && !preview && <button disabled={busy} onClick={() => void cancelImport()}>Cancel replacement import</button>}</div></div>
        {selectedRow?.state === "published" && <p className="b4-notice" role="status">Published revision {tree?.published_revision ?? selectedRow.revision} remains active for members until the replacement draft is explicitly published.</p>}
        <ol className="admin-import-progress" aria-label="Import stages"><li>1 Upload</li><li>2 Map sheets</li><li>3 Validate and review</li><li>4 Create draft</li><li>5 Review and publish</li></ol>
        <div className="admin-import-flow">
          <div className="admin-step" hidden={Boolean(batch)}><span className="admin-step-number">1</span><div><h4>Upload workbook</h4>
            <p>Select an .xlsx workbook whose Curriculum Code matches {selectedRow?.code}.</p>
            <div className="admin-upload-row"><input aria-label="Excel workbook" type="file" accept=".xlsx"
              disabled={busy} onChange={event => { if (busy) return; setFile(event.target.files?.[0] ?? null); }} />
              <button disabled={busy || !file} onClick={() => void act(async () => {
                if (importDirty && !window.confirm("Discard unsaved workbook corrections and upload a different workbook?")) return;
                const sequence = ++importSequence.current; const result = await upload(selected, file!); if (sequence !== importSequence.current || selectedRef.current !== selected) return; setImportConflict(false); setRecoveryRequired(false); setImportDirty(false); setBatch({ ...result, filename: file!.name }); setPreview(null); setReplaceConfirm("");
                setMapping(result.round_trip ? { Curriculum: "__ALL_LEVELS__" } :
                  Object.fromEntries((result.sheets ?? []).map(sheet => [sheet, sheet])));
                setNotice("Workbook uploaded. Map its sheets to levels."); await refresh();
              }, false)}>Upload workbook</button></div>
            {batch?.filename && !file && <p className="admin-help">Current uploaded workbook: {batch.filename}. Continue this import without uploading again.</p>}
            {file && <p className="admin-help">Selected: {file.name} · {(file.size / 1048576).toFixed(1)} MiB</p>}
          </div></div>
          <div className="admin-step" hidden={!batch || Boolean(preview)}><span className="admin-step-number">2</span><div><h4>Map sheets to levels</h4>
            {!batch ? <p>Upload a workbook to see its sheets.</p> : <>
              {batch.round_trip ? <p>Workbook identity and schema verified. The Curriculum sheet contains the complete hierarchy.</p> :
                <p>Enter the Level name for each sheet to import. Leave unrelated sheets blank.</p>}
              <datalist id="admin-level-options">{levelSuggestions.map(level => <option key={level} value={level} />)}</datalist>
              <div className="admin-sheet-map">{(batch.sheets ?? []).filter(sheet => !batch.round_trip || sheet === "Curriculum").map(sheet => <label key={sheet}>
                <span>{sheet}</span><input list="admin-level-options" value={mapping[sheet] === "__ALL_LEVELS__" ? "Complete hierarchy" : mapping[sheet] ?? ""} disabled={batch.round_trip || busy || importDirty}
                  placeholder="Level name, or leave out" onChange={event => { if (busy || importDirty) return; setReplaceConfirm(""); setMapping(previous => ({ ...previous, [sheet]: event.target.value })); setPreview(null); }} /></label>)}</div>
              <button disabled={busy || !Object.values(mapping).some(value => value.trim())} onClick={() => void act(async () => {
                const sheet_levels = Object.fromEntries(Object.entries(mapping).filter(([, value]) => value.trim()).map(([sheet, value]) => [sheet, value.trim()]));
                const result = await mutation("admin/curriculum/imports/" + batch.import_id + "/preview", "POST", { sheet_levels });
                if (selectedRef.current !== selected || batchRef.current?.import_id !== batch.import_id) return;
                setPreview(result); setImportConflict(false); setRecoveryRequired(false); setReplaceConfirm(""); setNotice(result.issue_count ? "Preview found row issues. Correct them in the table below." : "Preview ready. Review the changes below."); await refresh();
              }, false)}>Validate and preview</button>
            </>}
          </div></div>
          <div className="admin-step" hidden={!preview}><span className="admin-step-number">3</span><div><h4>Review changes and import</h4>
            {!preview ? <p>Preview the mapped workbook to see changes and row issues.</p> : <>
              <div className="admin-import-summary" aria-label="Import preview summary">
                {(["reused", "created", "updated", "removed", "duplicates", "invalid"] as const).map(key =>
                  <div key={key}><strong>{preview.counts?.[key] ?? 0}</strong><span>{{reused:"Unchanged",created:"To add",updated:"To update",removed:"To remove",duplicates:"Duplicates",invalid:"Invalid"}[key]}</span></div>)}
              </div>
              {importBlocked && <div className="b4-notice b4-notice-error" role="alert">This comparison is outdated. The current published/draft revisions differ from its base. Your workbook corrections are preserved.
                <button disabled={busy} onClick={() => void retryComparison()}>Revalidate comparison</button></div>}
              <p className="admin-help">Unchanged paths are retained. Duplicate rows are skipped; invalid rows block replacement. Removals refer to saved draft paths, not uploaded rows.</p>
              <p className="admin-help">Comparison base · Published revision {preview.published_revision ?? preview.base_revision} · Draft revision {preview.base_draft_revision} · Preview {preview.preview_revision?.slice(0, 8)}</p>
              {preview.dependency_warnings?.map(warning => <p key={warning} className="admin-help">{warning}</p>)}
              {(preview.counts?.duplicates ?? 0) > 0 && <p className="admin-help">{preview.counts?.duplicates} duplicate row(s) will be skipped.</p>}
              {preview.issue_count ? <p className="b4-notice b4-notice-error" role="alert">{preview.issue_count} row issue{preview.issue_count === 1 ? "" : "s"} block this import.</p>
                : <p className="admin-ready">No blocking row issues. The curriculum will remain in its current publication state.</p>}
              <div className="admin-row-actions"><button disabled={busy || importDirty} onClick={() => setPreview(null)}>Back to mapping</button>
                <button disabled={busy} onClick={() => void cancelImport()}>Cancel replacement import</button></div>
              <div className="admin-replacement-warning">
                <strong>This workbook will replace the entire draft hierarchy.</strong>
                <p>Paths missing from the workbook are removed from the replacement draft. Linked records remain protected, and the published curriculum stays active until Publish changes.</p>
                <label><span>Type <code>REPLACE {selectedRow?.code}</code> to confirm</span>
                  <input value={replaceConfirm} onChange={event => setReplaceConfirm(event.target.value)}
                    autoComplete="off" />
                </label>
              </div>
              {(gridDirty || unsavedEdit) && <p className="admin-help">Save or cancel your pending hierarchy edits before replacing the draft. <button onClick={openHierarchy}>Review hierarchy edits</button></p>}
              <button className="admin-danger admin-confirm-replacement" disabled={busy || restoringImport || !tree || importBlocked || gridDirty || unsavedEdit || importDirty || !preview.preview_revision ||
                Boolean(preview.issue_count) || replaceConfirm.trim() !== "REPLACE " + selectedRow?.code} onClick={() => {
                const changed = (preview.counts?.created ?? 0) + (preview.counts?.updated ?? 0);
                void act(async () => {
                  const latest = await get("admin/curricula/" + selected + "/tree");
                  if (selectedRef.current !== selected || batchRef.current?.import_id !== batch?.import_id) return;
                  setTree(latest);
                  if (preview.base_revision !== latest.revision || preview.base_draft_revision !== latest.draft_revision ||
                    preview.curriculum_version !== latest.version || preview.published_revision !== latest.published_revision) {
                    const error = new Error("The comparison changed before replacement. No draft changes were saved.");
                    Object.assign(error, { detail: { code: "stale_preview" }, path: "/commit" });
                    throw error;
                  }
                  if (!window.confirm("Replace the entire saved draft with this workbook? " + changed + " paths to add or update; " + (preview.counts?.removed ?? 0) + " paths to remove. Members keep the published curriculum until publication.")) return;
                  const result = await mutation("admin/curriculum/imports/" + batch?.import_id + "/commit", "POST",
                    { preview_revision: preview.preview_revision, confirm: replaceConfirm }, crypto.randomUUID());
                  syncRevisions(result);
                  setBatch(null); setPreview(null); setFile(null); setMapping({}); setReplaceConfirm("");
                  setWorkspaceTab("hierarchy"); setImportDirty(false); setGridDirty(false); setImportConflict(false); setRecoveryRequired(false);
                  setGridMetrics({ unsaved: 0, invalid: 0, conflicts: 0 });
                  setNotice("Replacement draft created. Review and publish when ready.");
                });
              }}>Create replacement draft</button>
            </>}
          </div></div>
          <div className="admin-step" hidden={Boolean(batch)}><span className="admin-step-number">4</span><div><h4>Review, edit and publish</h4>
            <p>After import, the hierarchy opens for review. Save any inline edits and select Publish explicitly.</p>
            <button disabled={busy} onClick={openHierarchy}>Open hierarchy</button>
          </div></div>
        </div>
        {batch && preview?.preview_revision && <div className="admin-import-table" key={batch.import_id}>
          <h3>Workbook comparison</h3><p>Row Save updates and revalidates this workbook only. Create replacement draft applies the complete reviewed workbook.</p>
          <ImportReviewGrid importId={batch.import_id}
            sheetLevels={Object.fromEntries(Object.entries(mapping).filter(([, level]) => level.trim()))}
            previewRevision={preview.preview_revision} busy={busy || importBlocked}
            onSave={saveImportReview} onDirtyChange={setImportDirty} />
        </div>}
        {batch && !preview && <UploadedWorkbookGrid key={batch.import_id} importId={batch.import_id} />}
      </section>}
      {workspaceTab === "history" && <section className="admin-card admin-import-history">
        <div className="admin-card-heading"><div><h3>Import History</h3><p>Uploads, previews, failed attempts and committed results for {selectedRow?.name}.</p></div>
          <button disabled={busy} onClick={() => void act(async () => {
            setHistory((await get("admin/curriculum/imports?curriculum_id=" + selected)).items);
          }, false)}>Refresh history</button></div>
        {historyLoading && <p role="status">Loading server-recorded import history…</p>}
        {historyError && <p role="alert" className="b4-notice b4-notice-error">{historyError}</p>}
        {!historyLoading && !historyError && !history.length && <p className="admin-empty">No server-recorded imports. A selected local file appears here only after Upload succeeds.</p>}
        <ul className="admin-history-list">{history.map(item => <li key={item.import_id}>
          <button onClick={() => void act(async () => {
            const [detail, issues] = await Promise.all([get("admin/curriculum/imports/" + item.import_id),
              get("admin/curriculum/imports/" + item.import_id + "/issues")]);
            setHistoryDetail(detail); setHistoryIssues(issues);
          }, false)}><strong>{item.filename ?? "Workbook"} · {item.status.replaceAll("_", " ")}</strong><span>{new Date(item.created_at).toLocaleString()}</span>
            <span>Published {item.published_revision ?? "—"} · Draft {item.draft_revision ?? "—"}</span>
            <small>{item.import_id.slice(0, 8)}</small></button>
          {item.events && <ol className="admin-import-events">{item.events.map((event, index) => <li key={index}>{event.status.replaceAll("_", " ")}{event.code ? ": " + event.code.replaceAll("_", " ") : ""} · {new Date(event.at).toLocaleString()}{event.draft_revision !== undefined ? " · draft " + event.draft_revision : ""}</li>)}</ol>}
          {item.counts && <span className="admin-history-counts">{Object.entries(item.counts).map(([key, value]) => value + " " + key).join(" · ")}</span>}
        </li>)}</ul>
        {historyDetail !== null && <div className="admin-history-detail"><h4>Import detail</h4>
          <dl>{Object.entries(historyDetail as Record<string, unknown>)
            .filter(([key]) => ["filename", "status", "curriculum_id", "payload_expires_at"].includes(key))
            .map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(value)}</dd></div>)}</dl>
          {(() => { const detail = historyDetail as { sheet_levels?: Record<string, string>;
            committed_result?: { counts?: Record<string, number> }; preview?: { counts?: Record<string, number> } };
            const counts = detail.committed_result?.counts ?? detail.preview?.counts;
            return <>{detail.sheet_levels && <div><h4>Sheet mapping</h4><ul>{Object.entries(detail.sheet_levels)
              .map(([sheet, level]) => <li key={sheet}>{sheet} → {level}</li>)}</ul></div>}
              {counts && <div className="admin-import-summary">{Object.entries(counts).map(([key, value]) =>
                <div key={key}><strong>{value}</strong><span>{key}</span></div>)}</div>}</>;
          })()}
          <h4>Row issues ({historyIssues?.total ?? 0})</h4>
          {historyIssues?.items.length ? <ul>{historyIssues.items.map((issue, index) =>
            <li key={index}>{issue.sheet}, row {issue.row_number}, {issue.column}: {issue.code}</li>)}</ul>
            : <p>No row issues recorded.</p>}
        </div>}
      </section>}
      {workspaceTab === "revisions" && <section className="admin-card"><h3>Revision History</h3>
        {revisions.length ? <ul className="admin-revisions">{revisions.map((revision, index) => {
          const item = revision as { number?: number; change_kind?: string; created_at?: string; details?: unknown };
          return <li key={index}><strong>Revision {item.number ?? index + 1}</strong>
            <span>{item.change_kind?.replaceAll("_", " ") ?? "Change"} · {item.created_at ? new Date(item.created_at).toLocaleString() : ""}</span>
            <details><summary>Details</summary><pre>{JSON.stringify(item.details ?? item, null, 2)}</pre></details></li>;
        })}</ul> : <p className="admin-empty">No revisions recorded yet.</p>}
      </section>}
    </>}


    {deleteTarget && <div className="admin-grid-dialog-backdrop"><div className="admin-grid-dialog admin-delete-dialog"
      role="dialog" aria-modal="true" aria-labelledby="delete-curriculum-title">
      <h3 id="delete-curriculum-title">Delete {deleteTarget.name} permanently?</h3>
      <p>Code {deleteTarget.code}. This action cannot be undone.</p>
      {deleteBusy && !deleteReview && <p role="status">Checking dependencies…</p>}
      {deleteReview && <><h4>Affected data</h4><dl className="admin-delete-counts">
        {Object.entries(deleteReview.counts).map(([key, count]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{count}</dd></div>)}
      </dl>
      {Object.keys(deleteReview.blockers).length > 0 && <div className="b4-notice b4-notice-error" role="alert">
        <strong>Deletion blocked</strong><ul>{Object.entries(deleteReview.blockers).map(([blocker, count]) => <li key={blocker}>{count} {blocker.replaceAll("_", " ")}</li>)}</ul>
      </div>}</>}
      {deleteError && <p className="b4-notice b4-notice-error" role="alert">{deleteError}</p>}
      <label>Type {deleteTarget.name} or {deleteTarget.code} to confirm
        <input value={deleteTyped} onChange={event => setDeleteTyped(event.target.value)} autoFocus /></label>
      <div className="admin-grid-dialog-actions">
        <button onClick={() => { setDeleteTarget(null); setDeleteReview(null); }}>Cancel</button>
        <button className="admin-danger" disabled={deleteBusy || !deleteReview || Object.keys(deleteReview.blockers).length > 0 ||
          ![deleteTarget.name, deleteTarget.code].includes(deleteTyped.trim())}
          onClick={() => void confirmDelete()}>Permanently delete curriculum</button>
      </div>
    </div></div>}
    {(tab === "resources" || tab === "teachers" || tab === "kits") && <B9Admin section={tab} tree={tree} />}
    {tab === "students" && <section className="admin-card"><div className="admin-card-heading"><div>
      <h3>Student directory</h3><p>Search individual profiles and measured activity. Learning activity is not a mastery score.</p></div></div>
      <BulkTransfer kind="students" onImported={()=>setBulkStudentReload(n=>n+1)} />
      <label>Search by name, email or ID<input type="search" value={search}
        onChange={event => { setSearch(event.target.value); setStudentOffset(0); setStudent(null); }} /></label>
      {loadingStudents && <p role="status">Loading students…</p>}
      {studentError && <p role="alert" className="b4-notice b4-notice-error">{studentError}</p>}
      {!loadingStudents && !students.length && !studentError && <p className="admin-empty">No students match this search.</p>}
      <ul className="admin-student-list">{students.map(row => <li key={row.id}>
        <button onClick={() => void act(async () => {
          const [profile, activity] = await Promise.all([get("admin/students/" + row.id),
            get("admin/students/" + row.id + "/activity")]);
          setStudent(profile); setStudentActivity(activity);
        }, false)}><strong>{row.display_name || row.email || "Student"}</strong>
          <span>{row.email || row.id}</span></button>
        <span className="admin-state">{row.status}</span>
        <small>Joined {new Date(row.created_at).toLocaleDateString()}</small>
      </li>)}</ul>
      {studentTotal > 30 && <nav className="admin-pagination" aria-label="Student pages">
        <button disabled={loadingStudents || studentOffset === 0}
          onClick={() => setStudentOffset(Math.max(0, studentOffset - 30))}>Previous</button>
        <span>{studentOffset + 1}–{Math.min(studentTotal, studentOffset + 30)} of {studentTotal}</span>
        <button disabled={loadingStudents || studentOffset + 30 >= studentTotal}
          onClick={() => setStudentOffset(studentOffset + 30)}>Next</button>
      </nav>}
      {student && <div className="admin-student-detail"><div className="admin-card-heading"><div>
        <h3>{student.display_name || student.email || "Student"}</h3>
        <p>{student.email || student.id} · {student.status}</p></div></div>
        <h4>Measured activity</h4>
        {studentActivity && <div className="admin-import-summary">
          {[["Visits", studentActivity.visits], ["Sessions", studentActivity.sessions],
            ["Questions", studentActivity.questions], ["Resource opens", studentActivity.resource_opens]].map(([label, value]) =>
            <div key={label}><strong>{value}</strong><span>{label}</span></div>)}
        </div>}
        <p className="admin-help">Last activity: {studentActivity?.last_activity_at
          ? new Date(studentActivity.last_activity_at).toLocaleString() : "None recorded"}</p>
        <h4>My Learning</h4>
        {!student.learning.length && <p>No selected learning paths.</p>}
        <ul className="admin-learning-list">{student.learning.map(item => {
          const curriculum = rows.find(row => row.id === item.curriculum_id);
          const deepest = item.subtopic_id || item.topic_id || item.domain_id || item.subject_id || item.level_id;
          const path = options.find(option => option.id === deepest)?.path;
          return <li key={item.id}><strong>{path || curriculum?.name || "Curriculum path"}</strong>
            <span className="admin-state">{item.visible ? "Visible" : "Hidden"}</span>
            <small>{curriculum?.name || item.curriculum_id} · selected {new Date(item.created_at).toLocaleDateString()}</small>
          </li>;
        })}</ul>
      </div>}
    </section>}
  </div>;
}










