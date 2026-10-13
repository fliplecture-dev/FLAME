"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { B9Error, b9Get, b9Mutation, b9Upload } from "@/lib/api/b9-client";
import { HtmlSourceEditor } from "./html-source-editor";
import { BulkTransfer } from "./bulk-transfer";
import { GoogleSheetsSync } from "./google-sheets-sync";
import { ResourceMappingDialog, ResourceDeleteDialog } from "./resource-mapping-dialog";
import { ResourceBulkDialog, type ResourceBulkAction } from "./resource-bulk-dialog";
import { LibraryHierarchy, hierarchy, mediaFormat, MediaPreview, ResourceMenu, ResourcePreviewDialog, MappingsDialog } from "./resource-library-ui";
import { ListPages, useCatalogue } from "./b9-catalogue";
import { ExternalVideoInfo, ExternalVideoSummary, resourceTypes, resourceTypeLabel, resourceFamily } from "@/components/ui/external-video-info";

import { LearningMetadataEditor, LearningMetadata, metadataForm, metadataValue } from "./learning-metadata-editor";

type Path = { topic_id: string; subtopic_id: string | null };
type Choice = Path & { label: string; curriculum_id?: string; curriculum?: string; level_id?: string; subject_id?: string; domain_id?: string; category_id?: string | null; level?: string; subject?: string;
  domain?: string; category?: string; topic?: string; subtopic?: string; valid?: boolean; available_for_publication?: boolean };
const defaults = { type: "image", title: "", description: "", external_url: "", alt_text: "",
  caption_or_transcript: "", accessibility_note: "", rights_basis: "owned", rights_holder: "",
  rights_reference: "", attribution: "", distribution_scope: "members", availability: "available" };
type Form = typeof defaults;
type Resource = Omit<Form, "external_url"> & { id: string; source: string; external_url: string | null;
  learning_metadata?: LearningMetadata; external_video?:ExternalVideoInfo|null; has_thumbnail?:boolean; thumbnail_upload_id?:string|null; upload_id?: string | null; mime_type?: string | null; byte_size?: number | null; file_name?: string | null; updated_at?: string; version: number; published: boolean; paths: Path[]; path_details?: Choice[] };
type Upload = Awaited<ReturnType<typeof b9Upload>>;
const pathKey = (path: Path) => path.topic_id + ":" + (path.subtopic_id ?? "");
function resourceForm(row: Resource | null): Form {
  return Object.fromEntries(Object.entries(defaults).map(([field, fallback]) =>
    [field, field === "type" ? resourceFamily(row?.type ?? "image") : row?.[field as keyof Form] ?? fallback])) as Form;
}
const signature = (form: Form, paths: Path[]) => JSON.stringify([form, paths.map(pathKey).sort()]);
export function ResourcePanel({ curriculumId }: { curriculumId: string }) {
  const listing = useCatalogue<Resource>("admin/resources",true);
  const [bulkSelected,setBulkSelected] = useState<Map<string,Resource>>(new Map());
  const [bulkAction,setBulkAction] = useState<ResourceBulkAction|null>(null);
  const pageSelection = useRef<HTMLInputElement>(null);
  const selectedOnPage = listing.rows.filter(row=>bulkSelected.has(row.id)).length;
  useEffect(()=>{if(pageSelection.current)pageSelection.current.indeterminate=selectedOnPage>0&&selectedOnPage<listing.rows.length;},[selectedOnPage,listing.rows]);
  function selectPage(checked:boolean){setBulkSelected(previous=>{const next=new Map(previous);listing.rows.forEach(row=>checked?next.set(row.id,row):next.delete(row.id));return next;});}
  function selectResource(row:Resource,checked:boolean){setBulkSelected(previous=>{const next=new Map(previous);if(checked)next.set(row.id,row);else next.delete(row.id);return next;});}
  async function bulkApplied(ids:string[],summary:string,failed:boolean){
    setBulkSelected(previous=>{const next=new Map(previous);ids.forEach(id=>next.delete(id));return next;});
    setNotice(summary);setNoticeError(failed);setSavedHidden(null);
    await listing.refresh();
    if(bulkAction==="delete"&&listing.offset>0&&listing.rows.every(row=>ids.includes(row.id)))listing.setOffset(Math.max(0,listing.offset-listing.limit));
  }
  const [editing, setEditing] = useState(false);
  const [curriculumFiltersOpen, setCurriculumFiltersOpen] = useState(false);
  const [sourceMode, setSourceMode] = useState("upload"); const [replacing, setReplacing] = useState(false);
  const [highlight, setHighlight] = useState(""); const [savedHidden, setSavedHidden] = useState<Resource | null>(null);
  const [mappingEditor, setMappingEditor] = useState<Resource | null>(null); const [deleteRow, setDeleteRow] = useState<Resource | null>(null);
  const [previewRow, setPreviewRow] = useState<Resource | null>(null); const [mappingRow, setMappingRow] = useState<Resource | null>(null);
  const [localUrl, setLocalUrl] = useState(""); const [localHtml,setLocalHtml]=useState(""); const [previewHtml,setPreviewHtml]=useState(""); const libraryScroll = useRef(0);
  const [selected, setSelected] = useState<Resource | null>(null);
  const [form, setForm] = useState<Form>({ ...defaults });
  const [education, setEducation] = useState(metadataForm());
  const [thumbnailFile,setThumbnailFile]=useState<File|null>(null); const [thumbnailUrl,setThumbnailUrl]=useState(""); const [removeThumbnail,setRemoveThumbnail]=useState(false); const thumbnailUploadRef=useRef<Upload|null>(null);
  const [inspected,setInspected]=useState<ExternalVideoInfo|null>(null);
  const [file, setFile] = useState<File | null>(null); const [upload, setUpload] = useState<Upload | null>(null);
  const uploadRef = useRef<Upload | null>(null); const creationId = useRef(""); const busyRef = useRef(false);
  const [htmlReading,setHtmlReading]=useState(false);
  const [htmlLoadAttempt,setHtmlLoadAttempt]=useState(0), [htmlLoading,setHtmlLoading]=useState(false), [htmlError,setHtmlError]=useState("");
  const [fileInputKey, setFileInputKey] = useState(0);
  const [options, setOptions] = useState<Choice[]>([]); const [pathsLoading, setPathsLoading] = useState(false);
  const [pathsError, setPathsError] = useState(""); const pathsSequence = useRef(0);
  const [invalid, setInvalid] = useState<string[]>([]); const [fields, setFields] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState(""); const [noticeError, setNoticeError] = useState(false);
  const [busy, setBusy] = useState(false); const [stage, setStage] = useState(""); const [preview, setPreview] = useState("");
  const dirty = Boolean(file || upload || thumbnailFile || removeThumbnail) || signature(form, []) !== signature(resourceForm(selected), []) || JSON.stringify(education) !== JSON.stringify(metadataForm(selected?.learning_metadata));
  useEffect(() => { if (!editing || !dirty) return; const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [editing, dirty]);
  useEffect(() => {
    if(!editing || !dirty)return;
    const leave = (event: MouseEvent) => {
      const target=event.target as HTMLElement;
      if(target.closest(".b9-resource-panel") || !target.closest("button,a"))return;
      if(!window.confirm("Discard unsaved resource changes?")){event.preventDefault();event.stopPropagation();}
    };
    document.addEventListener("click",leave,true);return()=>document.removeEventListener("click",leave,true);
  },[editing,dirty]);
  useEffect(()=>{let active=true;setHtmlError("");setHtmlLoading(Boolean(selected&&editing&&selected.type==="interactive"&&selected.source==="upload"));if(selected && editing)b9Get<{url:string;html_document?:string;launch_mode?:string}>("admin/resources/"+selected.id+"/preview").then(result=>{if(active){setPreview(result.url);setPreviewHtml(result.html_document||"");if(selected.type==="interactive"&&selected.source==="upload"&&!result.html_document&&result.launch_mode!=="interactive_pending")setHtmlError("Saved HTML was not returned. Retry before editing the source.");}}).catch(cause=>{if(active)setHtmlError("Saved HTML could not load: "+(cause instanceof Error?cause.message:"Retry."));}).finally(()=>{if(active)setHtmlLoading(false);});return()=>{active=false;};},[selected?.id,selected?.version,editing,htmlLoadAttempt]);
  useEffect(() => { if (!file) { setLocalUrl(""); return; } const url=URL.createObjectURL(file);setLocalUrl(url);return()=>URL.revokeObjectURL(url); }, [file]);
  useEffect(()=>{let active=true;setLocalHtml("");if(file && form.type==="interactive" && file.size<=2*1024*1024)file.text().then(text=>{if(active)setLocalHtml(text);});return()=>{active=false;};},[file,form.type]);
  useEffect(()=>{let active=true;setThumbnailUrl("");if(thumbnailFile){const url=URL.createObjectURL(thumbnailFile);setThumbnailUrl(url);return()=>URL.revokeObjectURL(url);}if(selected?.has_thumbnail&&!removeThumbnail)b9Get<{url:string}>("admin/resources/"+selected.id+"/preview?thumbnail=true").then(data=>{if(active)setThumbnailUrl(data.url);}).catch(()=>{});return()=>{active=false;};},[thumbnailFile,removeThumbnail,selected?.id,selected?.version,selected?.has_thumbnail]);
  function back(force = false) {
    if(busyRef.current)return;
    if(!force && dirty && !window.confirm("Discard unsaved resource changes?"))return;
    setEditing(false);setPreview("");requestAnimationFrame(()=>window.scrollTo(0,libraryScroll.current));
  }
  function libraryHierarchy(key:string, value:string) {
    const index=hierarchy.findIndex(field=>field+"_id"===key);
    listing.setFilter(key,value);hierarchy.slice(index+1).forEach(field=>listing.setFilter(field+"_id",""));
  }
  function clearFilters(){listing.setSearch("");Object.keys(listing.filters).forEach(key=>listing.setFilter(key,""));}
  function savedFeedback(row:Resource, added:boolean){
    setHighlight(row.id);setSavedHidden(row);setNotice(added?"Resource added successfully":"Resource changes saved");setEditing(false);setPreview("");
    requestAnimationFrame(()=>window.scrollTo(0,libraryScroll.current));
  }
  async function refreshPaths() {
    const request = ++pathsSequence.current;
    setPathsLoading(true); setPathsError("");
    try {
      const result = await b9Get<{ items: Choice[] }>("admin/resources/paths");
      if (request === pathsSequence.current) { setOptions(result.items); setInvalid(current => current.filter(key => !result.items.some(item => pathKey(item) === key))); }
    } catch (error) { if (request === pathsSequence.current) setPathsError(error instanceof Error ? error.message : "Paths unavailable."); }
    finally { if (request === pathsSequence.current) setPathsLoading(false); }
  }
  useEffect(() => { void refreshPaths(); return () => { pathsSequence.current++; }; }, [curriculumId]);
  function choose(row: Resource | null) {
    if (busyRef.current) return;
    if(editing && dirty && !window.confirm("Discard unsaved resource changes?"))return;
    libraryScroll.current = window.scrollY;setEditing(true);setSourceMode(row?.type==="interactive"?"html":row?.source ?? "upload");setReplacing(false);setSavedHidden(null);
    setPreviewHtml("");setSelected(row); setForm(resourceForm(row)); setEducation(metadataForm(row?.learning_metadata)); setFile(null);setInspected(row?.external_video??null);setThumbnailFile(null);setRemoveThumbnail(false);thumbnailUploadRef.current=null;
    uploadRef.current = null; setUpload(null); creationId.current = crypto.randomUUID();
    setFileInputKey(key => key + 1); setPreview(""); setNotice(""); setNoticeError(false); setFields({}); setInvalid([]);
    requestAnimationFrame(()=>document.getElementById("resource-editor-title")?.focus());
  }
  function accept(row: Resource) {
    setSelected(row); setForm(resourceForm(row)); setEducation(metadataForm(row?.learning_metadata)); setFile(null);setInspected(row.external_video??null);setThumbnailFile(null);setRemoveThumbnail(false);thumbnailUploadRef.current=null;
    uploadRef.current = null; setUpload(null); setFileInputKey(key => key + 1); setFields({}); setInvalid([]);
  }
  function field(name: keyof Form, value: string) {
    if(name==="external_url"||name==="type")setInspected(null);
    setForm(previous => ({ ...previous, [name]: value })); setFields(previous => ({ ...previous, [name]: "" }));
  }
  function mediaType(value:string){setThumbnailFile(null);thumbnailUploadRef.current=null;setRemoveThumbnail(false);field("type",value);setFile(null);setLocalHtml("");setPreviewHtml("");uploadRef.current=null;setUpload(null);if(selected&&value!==resourceFamily(selected.type))setReplacing(true);if(value==="interactive"){setSourceMode("html");field("external_url","");}}

  async function inspectVideo(){await act("Inspect video",async()=>{const data=await b9Mutation<ExternalVideoInfo>("admin/resources/external-video/inspect","POST",{url:form.external_url});setInspected(data);setForm(old=>({...old,title:old.title||data.title,description:old.description||data.description||""}));setNotice("Video metadata verified. Preview the video and review its rights and accessibility details.");});}
  async function act(operation: string, task: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true); setStage(operation); setNotice(""); setNoticeError(false); setFields({});
    try { await task(); await listing.refresh(); }
    catch (cause) {
      const error = cause instanceof B9Error ? cause : null;
      const detail = cause instanceof Error ? cause.message : "The request failed.";
      const prefix = error?.code === "stale_version" ? "Resource changed elsewhere: review the latest version."
        : operation === "Upload" || (cause as { uploadFailed?: boolean })?.uploadFailed ? "Upload failed."
        : operation === "Publish" ? "Publication blocked:"
        : operation === "Unpublish" ? "Resource could not be unpublished:"
        : operation === "Preview" ? "Preview failed."
        : operation === "Inspect video" ? "Video URL validation failed."
        : error?.field === "paths" || error?.fields.includes("paths") ? "Topic associations could not be saved."
        : "Resource could not be saved.";
      const partial = operation === "Save draft" && uploadRef.current
        ? error && error.status < 500 ? " Media uploaded successfully. The draft was not saved; retry will reuse this upload."
          : " Media uploaded successfully. Draft saving could not be confirmed; retry will reuse the upload and creation reference."
        : "";
      setNotice(prefix + " " + detail + (operation === "Publish" ? " Open Edit to review requirements, save the draft, then retry Publish." : "") + partial + (error?.reference ? " Reference: " + error.reference : "")); setNoticeError(true);
      setFields(Object.fromEntries((error?.fields ?? []).map(name => [name, detail])));
      if (error?.invalidPaths.length) { setInvalid(error.invalidPaths.map(pathKey)); await refreshPaths(); }
      if (error?.code === "upload_not_found") { uploadRef.current = null; setUpload(null); }
    } finally { busyRef.current = false; setBusy(false); setStage(""); }
  }
  async function save() {
    if(htmlReading)return;
    if(form.type==="interactive"&&sourceMode==="html"&&(!selected&&!file || file&&(file.size>2*1024*1024||!(await file.text()).trim()))){setFields({file:"Paste a non-empty HTML document up to 2 MiB."});setNotice("Resource could not be saved. Paste a non-empty HTML document up to 2 MiB.");setNoticeError(true);return;}

    if (!form.title.trim() || (form.type==="video" && sourceMode==="external"?!form.external_url:!selected && !file && !upload && !form.external_url)) {
      setFields({ ...(!form.title.trim() ? { title: "Enter a title." } : {}), 
        ...(!form.external_url&&form.type==="video" && sourceMode==="external"?{external_url:"Enter a supported Video URL."}:!selected && !file && !upload && !form.external_url ? { file: "Choose a file or approved HTTPS URL." } : {}) });
      setNotice("Resource could not be saved. Complete the highlighted fields."); setNoticeError(true); return;
    }
    if(selected?.published){setNotice("Unpublish this resource before saving edits. Publish explicitly when the changes are ready.");setNoticeError(true);return;}
    await act("Save draft", async () => {
      const learning_metadata = metadataValue(education);
      if (file && !uploadRef.current) {
        setStage("Upload");
        try { const result = await b9Upload(file); uploadRef.current = result; setUpload(result); }
        catch (cause) { throw Object.assign(cause instanceof Error ? cause : new Error("Upload failed."), { uploadFailed: true }); }
        finally { setStage("Save draft"); }
      }
      if(thumbnailFile && !thumbnailUploadRef.current) thumbnailUploadRef.current=await b9Upload(thumbnailFile);
      const thumbnail= form.type==="video" && thumbnailUploadRef.current ? {thumbnail_upload_id:thumbnailUploadRef.current.upload_id} : removeThumbnail ? {thumbnail_upload_id:null} : {};
      const source = uploadRef.current ? { upload_id: uploadRef.current.upload_id } :
        form.external_url && (!selected || selected.source === "external" || form.external_url !== selected.external_url) ? { external_url: form.external_url } : {};
      const { external_url: _url, ...metadata } = form;
      if (!creationId.current) creationId.current = crypto.randomUUID();
      try {
        const saved = await b9Mutation<Resource>(selected ? "admin/resources/" + selected.id : "admin/resources", selected ? "PATCH" : "POST",
          { ...metadata, learning_metadata, ...source, ...thumbnail, ...(!selected ? {paths: []} : {}), ...(selected ? { expected_version: selected.version } : { creation_id: creationId.current }) });
        const added = !selected; accept(saved); savedFeedback(saved, added);
      } catch (cause) {
        // Recover a confirmed creation after a lost response; never create a second draft.
        if (!selected && cause instanceof B9Error && cause.code === "resource_creation_exists") {
          const saved = await b9Get<Resource>("admin/resources/" + creationId.current);
          if (!(sourceMode==="html"&&uploadRef.current&&saved.upload_id!==uploadRef.current.upload_id) && signature(form, []) === signature(resourceForm(saved), []) && JSON.stringify(metadataValue(education)) === JSON.stringify(metadataValue(metadataForm(saved.learning_metadata)))) {
            accept(saved); savedFeedback(saved, true);
          } else {
            setSelected(saved); if(sourceMode!=="html"){setFile(null); uploadRef.current = null; setUpload(null); setFileInputKey(key => key + 1);}
            setNotice("Resource creation already completed. Latest saved version loaded; your entered details are preserved. Review them before saving or publishing.");
          }
        } else { throw cause; }
      }
    });
  }
  const requirements = [
    ...(form.type==="interactive"&&selected&&!selected.mime_type&&!selected.external_url&&!file?["Paste or upload HTML5 before previewing or publishing."]:[]),
    ...(form.type==="video"&&sourceMode==="upload"&&(file?.type||selected?.mime_type)!=="image/gif"&&(!selected?.has_thumbnail||removeThumbnail)&&!thumbnailFile?["Video thumbnail"]:[]),
    ...(form.type === "interactive" && sourceMode !== "external" && !form.accessibility_note.trim() ? ["Enter keyboard instructions and an accessibility note for this interactive."] : []),
    ...(!form.rights_basis || !form.rights_holder.trim() || !form.distribution_scope.trim() ? ["Enter rights basis, rights holder and distribution scope."] : []),
    ...(form.rights_basis !== "owned" && !form.rights_reference.trim() ? ["Enter the licence or permission reference."] : []),
    ...((["image", "diagram"].includes(form.type) || form.type === "video" && (file?.type ?? upload?.mime_type ?? selected?.mime_type) === "image/gif") && (!form.alt_text.trim() || /^(gif|png|jpe?g|webp|image|animation|picture|file|diagram|photo)$/i.test(form.alt_text.trim())) ? ["Enter an image description."] : []),
    ...(["audio", "video", "animation", "external_video"].includes(form.type) && !(form.type === "video" && (file?.type ?? upload?.mime_type ?? selected?.mime_type) === "image/gif") && !form.caption_or_transcript.trim() && !form.accessibility_note.trim() ? ["Enter captions, transcript or an accessibility note."] : []),
    ...(form.availability !== "available" ? ["Set availability to Available."] : []),
  ];
  const input = (name: keyof Form, label: string, maxLength: number, multiline = false) => <label>{label}
    {multiline ? <textarea value={form[name]} maxLength={maxLength} aria-invalid={Boolean(fields[name])} onChange={event => field(name, event.target.value)} />
      : <input value={form[name]} maxLength={maxLength} aria-invalid={Boolean(fields[name])} onChange={event => field(name, event.target.value)} />}
    {fields[name] && <small role="alert">{fields[name]}</small>}</label>;
  async function publication(row:Resource, preserveEdits=false) {
    const operation=row.published?"Unpublish":"Publish";
    if(row.published && !window.confirm("Unpublish ‘"+row.title+"’? Members will no longer see it. Media and mappings will be preserved."))return;
    await act(operation,async()=>{
      const result=await b9Mutation<Resource>("admin/resources/"+row.id+"/"+operation.toLowerCase(),"POST",{expected_version:row.version});
      if(preserveEdits)setSelected(result);else if(editing)accept(result);
      setHighlight(result.id);if(!editing)setSavedHidden(result);setNotice(row.published?"Resource unpublished successfully.":"Resource published successfully.");
    });
  }
  const currentMime=file?.type || upload?.mime_type || selected?.mime_type;
  const hasHiddenSaved=savedHidden && !listing.loading && !listing.rows.some(row=>row.id===savedHidden.id);
  return <section className="b9-admin-section b9-resource-panel">
    <header className="resource-library-header"><div><h3>Resource Library</h3><p>{editing?"Media and details → Save draft → Preview → Publish":"Browse and manage media for your learning paths."}</p></div>
      {!editing && <button className="resource-primary" disabled={busy} onClick={()=>choose(null)}>+ Add resource</button>}
      {editing && <button disabled={busy} onClick={()=>back()}>Back to library</button>}</header>
    {notice && <div className={"b4-notice"+(noticeError?" b4-notice-error":"")} role={noticeError?"alert":"status"}><span>{notice}</span>{noticeError&&!editing&&<button disabled={busy} onClick={()=>{setNotice("");void listing.refresh();}}>Refresh latest resources</button>}<button aria-label="Dismiss resource message" onClick={()=>setNotice("")}>×</button></div>}
    {!editing && <>
      <BulkTransfer kind="resources" onImported={listing.refresh} />
      <GoogleSheetsSync onImported={listing.refresh} />
      <div className="resource-bulk-toolbar" aria-label="Bulk resource actions"><strong>{bulkSelected.size} selected across pages</strong><button disabled={!bulkSelected.size} onClick={()=>setBulkSelected(new Map())}>Clear selection</button>{(["map","publish","unpublish","delete"] as ResourceBulkAction[]).map(action=><button key={action} className={action==="delete"?"resource-delete-action":""} disabled={!bulkSelected.size||busy} onClick={()=>setBulkAction(action)}>{action==="map"?"Map selected topics":action.charAt(0).toUpperCase()+action.slice(1)+" selected"}</button>)}<small>Page selection includes only displayed rows. Selections are preserved across filters and pages.</small></div>
      <div className="resource-library-filters"><label>Search resources<input type="search" value={listing.search} onChange={e=>listing.setSearch(e.target.value)} placeholder="Title or description"/></label>
        <label>Topic label<input type="search" aria-label="Filter resources by topic label" placeholder="e.g. Gravity" value={listing.filters.topic_label??""} onChange={event=>listing.setFilter("topic_label",event.target.value)}/></label>
        <label>Media type<select aria-label="Media type" value={listing.filters.type??""} onChange={e=>listing.setFilter("type",e.target.value)}><option value="">All types</option>{resourceTypes.map(type=><option key={type} value={type}>{resourceTypeLabel(type)}</option>)}</select></label>
        <label>File format<select aria-label="File format" value={listing.filters.format??""} onChange={e=>listing.setFilter("format",e.target.value)}><option value="">All formats</option>{["PNG","JPEG","WEBP","GIF","MP4","WEBM","HTML5"].map(format=><option key={format}>{format}</option>)}<option value="URL">Approved URL</option></select></label>
        <label>Publication status<select aria-label="Publication status" value={listing.filters.published??""} onChange={e=>listing.setFilter("published",e.target.value)}><option value="">All statuses</option><option value="true">Published</option><option value="false">Draft</option></select></label>
        <label>Availability<select aria-label="Availability" value={listing.filters.availability??""} onChange={e=>listing.setFilter("availability",e.target.value)}><option value="">All</option><option value="available">Available</option><option value="unavailable">Unavailable</option></select></label>
      </div>
      <button type="button" className="resource-curriculum-toggle" aria-label="Filter by curriculum" aria-expanded={curriculumFiltersOpen} aria-controls="resource-library-curriculum-filters" data-active={hierarchy.some(key=>Boolean(listing.filters[key+"_id"]))} onClick={()=>setCurriculumFiltersOpen(open=>!open)}>{curriculumFiltersOpen?<ChevronDown size={16} aria-hidden="true"/>:<ChevronRight size={16} aria-hidden="true"/>}<span><strong>Filter by curriculum</strong><small>Narrow resources by curriculum, level, subject, topic or subtopic.</small></span>{hierarchy.some(key=>Boolean(listing.filters[key+"_id"]))&&<span className="resource-curriculum-active">Filters active</span>}</button>
      <div id="resource-library-curriculum-filters" className="resource-filter-details" hidden={!curriculumFiltersOpen}><fieldset disabled={pathsLoading} aria-label="Library hierarchy filters"><legend>Filter by curriculum hierarchy</legend><LibraryHierarchy options={options} values={listing.filters} onChange={libraryHierarchy}/></fieldset></div>
      <div className="resource-library-toolbar"><strong>{listing.loading?"Loading resources…":`${listing.total} matching resources`}</strong><button onClick={clearFilters}>Clear filters</button>
        <label>Sort by<select aria-label="Sort by" value={listing.filters.sort||"updated"} onChange={e=>listing.setFilter("sort",e.target.value)}><option value="updated">Last updated</option><option value="title">Title</option><option value="type">Media type</option><option value="status">Publication status</option></select></label>
        <label>Order<select aria-label="Order" value={listing.filters.direction||"desc"} onChange={e=>listing.setFilter("direction",e.target.value)}><option value="desc">Descending</option><option value="asc">Ascending</option></select></label></div>
      {pathsLoading&&<p role="status">Loading hierarchy filters…</p>}{pathsError&&<p role="alert">Hierarchy filters unavailable: {pathsError} <button onClick={()=>void refreshPaths()}>Retry hierarchy</button></p>}
      {hasHiddenSaved&&<div className="b4-notice" role="status">Saved resource ‘{savedHidden.title}’ is outside this filtered page. <button onClick={()=>{clearFilters();listing.setSearch(savedHidden.title);listing.setOffset(0);}}>View saved resource</button></div>}
      {listing.loading&&<p role="status">Loading resources…</p>}{listing.error&&<p role="alert">Library could not load: {listing.error} <button onClick={()=>void listing.refresh()}>Retry library</button></p>}
      {!listing.loading&&!listing.error&&!listing.rows.length&&<div className="resource-empty"><h4>No matching resources</h4><p>Clear filters or add media and map it to a learning path.</p></div>}
      <div className="resource-table-scroll"><table className="resource-library-table"><caption className="sr-only">Saved learning resources</caption><thead><tr><th scope="col" className="resource-selection-cell"><input ref={pageSelection} type="checkbox" aria-label="Select resources on this page" disabled={listing.loading||!listing.rows.length} checked={Boolean(listing.rows.length)&&selectedOnPage===listing.rows.length} onChange={event=>selectPage(event.target.checked)}/></th>{["Resource","Topic","Media type","File format","Mapped topics","Mapped subtopics","Publication / availability","Last updated","Actions"].map(label=><th key={label} scope="col">{label}</th>)}</tr></thead><tbody>{listing.rows.map(row=>{
        const topics=[...new Map((row.path_details??[]).map(p=>[p.topic_id,p.topic||"Unavailable topic"])).values()];
        const subtopics=(row.path_details??[]).filter(p=>p.subtopic_id);const wide=row.paths.filter(p=>!p.subtopic_id).length;
        return <tr key={row.id} className={(highlight===row.id?"resource-row-saved ":"")+(bulkSelected.has(row.id)?"resource-row-selected":"")}><td className="resource-selection-cell"><input type="checkbox" aria-label={"Select resource: "+row.title} disabled={listing.loading} checked={bulkSelected.has(row.id)} onChange={event=>selectResource(row,event.target.checked)}/></td><th scope="row"><span className="resource-title-icon" aria-hidden="true">{row.type==="audio"?"♫":row.type==="video"||row.type==="animation"?"▷":row.type==="interactive"?"↗":"▧"}</span><span title={row.title}>{row.title}</span><small>v{row.version}</small></th>
          <td className="resource-topic-label">{row.learning_metadata?.topic_labels?.join(", ")||"Not specified"}</td><td className="resource-type">{resourceTypeLabel(row.type)}</td><td>{row.type==="interactive"&&!row.mime_type&&!row.external_url?"HTML pending":row.external_video?<span>Source: {row.external_video.provider_name}</span>:mediaFormat(row.mime_type,row.source)}</td>
          <td>{!row.paths.length&&<strong>Not mapped</strong>}<span title={topics.join(", ")}>{topics.slice(0,2).join(", ")||(row.paths.length?"Unavailable topics":"")}{topics.length>2?" +"+(topics.length-2):""}</span><small>{topics.length} topics</small><button onClick={()=>{setNotice("");setNoticeError(false);setMappingEditor(row);}} disabled={busy}>{row.paths.length?"Manage mappings":"Map topics"}</button><button aria-label={"View all mappings for "+row.title} onClick={()=>setMappingRow(row)}>View all mappings</button></td>
          <td>{subtopics.length} direct links{wide>0&&<small>All subtopics of {wide} topic-wide {wide===1?"link":"links"}</small>}</td>
          <td><span className={"resource-status-badge "+(row.published?"published":"draft")}>{row.published?"Published":"Draft"}</span><small>{row.availability}</small>{Boolean(row.external_video)&&<small>In-app video player</small>}</td>
          <td>{row.updated_at?new Date(row.updated_at).toLocaleString():"Not recorded"}</td>
          <td><div className="resource-row-actions"><button disabled={busy} onClick={()=>setPreviewRow(row)}>Preview</button><ResourceMenu title={row.title} busy={busy} published={row.published} onEdit={()=>choose(row)} onPublication={()=>void publication(row)} onDelete={()=>{setNotice("");setNoticeError(false);setDeleteRow(row);}}/></div></td></tr>;
      })}</tbody></table></div><ListPages listing={listing}/>
      <p className="resource-library-hint">Topic-wide mappings cover the topic and its subtopics. Direct subtopic mappings cover only that subtopic.</p>
    </>}
    {editing && <div className="b9-editor resource-details-editor">
      <h3 id="resource-editor-title" tabIndex={-1}>{selected?"Edit resource":"Add resource"}{selected&&<small> · {selected.published?"Published":"Draft"} · v{selected.version}</small>}</h3>
      <div className="b9-resource-actions"><button className="resource-primary" disabled={busy||htmlReading||selected?.published} onClick={()=>void save()}>Save draft</button>
        <button disabled={busy||!selected||dirty} onClick={()=>setPreviewRow(selected)}>Preview</button>
        <button disabled={busy||!selected||selected.published||dirty||Boolean(requirements.length)} onClick={()=>selected&&void publication(selected)}>Publish</button>
        <button disabled={busy} onClick={()=>back()}>Cancel</button>
        {selected&&<button disabled={busy} onClick={()=>void act("Review latest",async()=>{const latest=await b9Get<Resource>("admin/resources/"+selected.id);setSelected(latest);if(uploadRef.current&&latest.upload_id===uploadRef.current.upload_id){uploadRef.current=null;setUpload(null);setFile(null);}await refreshPaths();setNotice("Latest version loaded. Your entered details are preserved; review before saving.");})}>Review latest version</button>}
        {busy&&<span role="status">{stage}…</span>}
      <details className="b9-publication-requirements resource-toolbar-requirements" open={Boolean(requirements.length)}><summary>Media publication requirements{requirements.length?" · "+requirements.length+" to complete":" · complete"}</summary>
        {requirements.length?<ul className="resource-requirement-content">{requirements.map(item=><li key={item}>{item}</li>)}</ul>:<p className="resource-requirement-content">{form.type==="video" && sourceMode==="external"?"Save and preview the video, then publish explicitly. No API key is needed. Published videos appear through valid curriculum mappings.":"Save and preview, then publish explicitly. Unmapped resources can be published; learners see them only through valid mappings in published curricula."}</p>}
      </details>
      </div>
      {selected?.published&&<div className="b9-publication-requirements"><p>This library stores one version of each resource. Unpublish before saving edits; this removes it from learner visibility. Save as a draft, then publish explicitly when ready. Your entered values are preserved.</p><button disabled={busy} onClick={()=>void publication(selected,true)}>Unpublish to edit as draft</button></div>}
      {!selected?.published&&<p className="resource-library-hint">{!selected||dirty?"Save draft before Preview or Publish. Saving does not publish your changes.":requirements.length?"Publish is blocked until the requirements in the action bar are complete.":"Saved draft ready to preview and publish."}</p>}
      {upload&&<p role="status">Media uploaded and retained for retry; no additional upload is needed.</p>}
      <fieldset disabled={busy} className="b9-resource-details"><legend>A. Media and details</legend><label>Media type<select aria-label="Media type" value={form.type} onChange={e=>mediaType(e.target.value)}>{resourceTypes.map(type=><option key={type} value={type}>{resourceTypeLabel(type)}</option>)}</select>{fields.type&&<small role="alert">{fields.type}</small>}</label>
          {form.type!=="interactive"&&<div className="resource-source-choice"><label>Media source<select aria-label="Media source" value={sourceMode} onChange={e=>{setSourceMode(e.target.value);setFileInputKey(key=>key+1);setFile(null);uploadRef.current=null;setUpload(null);field("external_url","");setInspected(null);setReplacing(true);}}><option value="upload">Upload file</option><option value="external">{form.type==="video"?"YouTube / Vimeo URL":"Approved HTTPS URL"}</option></select></label></div>}
        {form.type==="video" && sourceMode==="external"?<><label>Video URL<input aria-label="Video URL" type="url" value={form.external_url} maxLength={2048} aria-invalid={Boolean(fields.external_url)} onChange={e=>field("external_url",e.target.value)}/>{fields.external_url&&<small role="alert">{fields.external_url}</small>}</label><button disabled={!form.external_url.trim()} onClick={()=>void inspectVideo()}>Validate video URL</button><ExternalVideoSummary info={inspected} description={form.alt_text||form.title}/></>:form.type==="interactive"?<><HtmlSourceEditor key={(selected?.id||"new")+":"+fileInputKey} document={file?localHtml:previewHtml} onReading={setHtmlReading} loading={htmlLoading} error={htmlError} disabled={busy||Boolean(selected?.published)} title={form.title} onRetry={()=>setHtmlLoadAttempt(value=>value+1)} onChange={next=>{setFile(next);setReplacing(true);uploadRef.current=null;setUpload(null);setFields(previous=>({...previous,file:""}));}}/>{fields.file&&<small role="alert">{fields.file}</small>}</>:selected&&!replacing?<div className="resource-current-media"><strong>{selected.file_name|| (selected.source==="external"?"Approved URL":"Stored media")}</strong> · {mediaFormat(selected.mime_type,selected.source)}{selected.byte_size?" · "+(selected.byte_size/1024).toFixed(1)+" KiB":""}<button onClick={()=>setPreviewRow(selected)}>Preview saved media</button><button onClick={()=>setReplacing(true)}>Replace file</button><small>Metadata-only edits retain this media.</small></div>:<>

          {replacing&&<button onClick={()=>{setReplacing(false);setFile(null);uploadRef.current=null;setUpload(null);field("external_url",selected?.external_url??"");field("type",selected?.type??"image");}}>Keep existing media</button>}
          {sourceMode==="upload"?<label>File<input key={fileInputKey} type="file" accept={form.type==="image"?".jpg,.jpeg,.png,.webp":form.type==="video"?".gif,.mp4,.webm":form.type==="interactive"?".html,.htm,text/html":""} aria-invalid={Boolean(fields.file)} onChange={e=>{const next=e.target.files?.[0]??null;setFile(next);uploadRef.current=null;setUpload(null);if(next){field("external_url","");if(next.type==="text/html"||/\.html?$/i.test(next.name))setSourceMode("html");field("type",next.type==="text/html" || /\.html?$/i.test(next.name)?"interactive":next.type==="image/gif"?"video":next.type.startsWith("image/")?"image":next.type.startsWith("video/")?"video":form.type);}}}/>{fields.file&&<small role="alert">{fields.file}</small>}</label>:input("external_url","Approved HTTPS URL",2048)}
          <small>{form.type==="interactive"?"HTML5: up to 2 MiB. Use one UTF-8 .html or .htm file with inline CSS/JavaScript and embedded assets. External libraries, network requests and nested frames are blocked.":<>Images: up to 10 MiB · GIF animations (Video): up to 10 MiB · video: 100 MiB. GIFs retain their original animation. URL hosts must be approved.</>}</small>
        </>}
        {form.type==="video"&&<fieldset><legend>Video thumbnail</legend><p>{sourceMode==="external"?"YouTube / Vimeo thumbnail loads automatically. Upload an image to override it.":"Upload a PNG, JPEG or WebP thumbnail before publishing this video (GIF previews use their own image)."}</p><label>Thumbnail image<input key={fileInputKey+"-thumbnail"} type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" onChange={e=>{setThumbnailFile(e.target.files?.[0]??null);thumbnailUploadRef.current=null;setRemoveThumbnail(false);}}/></label>{(thumbnailUrl||(!removeThumbnail&&inspected?.thumbnail_url))&&<img src={thumbnailUrl||inspected?.thumbnail_url||""} alt="Video thumbnail preview" style={{maxWidth:"100%",width:280,aspectRatio:"16/9",objectFit:"cover"}}/>}{(selected?.has_thumbnail||thumbnailFile)&&<button type="button" onClick={()=>{setThumbnailFile(null);thumbnailUploadRef.current=null;setRemoveThumbnail(true);}}>Remove thumbnail</button>}</fieldset>}
        {sourceMode!=="html"&&!file&&selected&&(preview||previewHtml)&&<MediaPreview htmlDocument={previewHtml} url={preview} type={selected.type} mime={selected.mime_type} description={selected.alt_text||selected.title} caption={selected.caption_or_transcript}/>}
        {file&&<p>{file.name} · {mediaFormat(file.type)} · {(file.size/1024).toFixed(1)} KiB</p>}
        {localUrl&&form.type!=="interactive"&&<MediaPreview url={localUrl} type={form.type} mime={file?.type} description={form.alt_text||form.title||"Uploaded media preview"} caption={form.caption_or_transcript}/>}
        {sourceMode!=="html"&&localHtml&&form.type==="interactive"&&<MediaPreview url="" type="interactive" htmlDocument={localHtml} description={form.title||"Interactive preview"}/>}
        <div className="b4-fields">{input("title","Title",255)}<label>Topic labels (for library filtering)<input aria-label="Topic labels (for library filtering)" value={education.topicLabels} onChange={event=>setEducation(previous=>({...previous,topicLabels:event.target.value}))} placeholder="Gravity | Force"/><small>Labels help group resources for mapping; they do not create curriculum associations.</small></label>
          {input("description","Description",2000,true)}{input("alt_text","Image description",1000)}{input("caption_or_transcript","Caption or transcript (optional for GIF)",10000,true)}{input("accessibility_note","Accessibility note",1000,true)}
          <label>Rights basis<select value={form.rights_basis} onChange={e=>field("rights_basis",e.target.value)}><option value="owned">Owned</option><option value="licensed">Licensed</option><option value="permission">Permission</option></select></label>
          {input("rights_holder","Rights holder",255)}{input("rights_reference","Rights reference",2048)}{input("attribution","Attribution",2000)}{input("distribution_scope","Distribution scope",255)}
          <label>Availability<select aria-label="Availability" value={form.availability} onChange={e=>field("availability",e.target.value)}><option value="available">Available</option><option value="unavailable">Unavailable</option></select></label></div>
      </fieldset>
      <LearningMetadataEditor value={education} onChange={setEducation} disabled={busy} />

    </div>}
    {mappingEditor&&<ResourceMappingDialog resource={mappingEditor} onClose={()=>setMappingEditor(null)} onSaved={async id=>{setHighlight(id);setNoticeError(false);setNotice("Resource mappings updated successfully.");await listing.refresh();}}/>}
    {deleteRow&&<ResourceDeleteDialog resource={deleteRow} onClose={()=>setDeleteRow(null)} onDeleted={async()=>{selectResource(deleteRow,false);setNoticeError(false);setNotice("Resource deleted successfully.");setSavedHidden(null);await listing.refresh();}}/>}
    {bulkAction&&<ResourceBulkDialog action={bulkAction} resources={[...bulkSelected.values()]} onApplied={bulkApplied} onClose={()=>setBulkAction(null)}/>}
    {previewRow&&<ResourcePreviewDialog resource={previewRow} onClose={()=>setPreviewRow(null)}/>}
    {mappingRow&&<MappingsDialog title={mappingRow.title} paths={mappingRow.path_details??mappingRow.paths.map(p=>({...p,label:"Unavailable path",valid:false}))} onClose={()=>setMappingRow(null)}/>}
  </section>;
}



