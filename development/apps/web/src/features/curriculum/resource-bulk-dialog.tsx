"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { B9Error, b9Get, b9Mutation } from "@/lib/api/b9-client";
import { hierarchy, LibraryHierarchy, type LearningPath } from "./resource-library-ui";
import type { MappableResource, ResourceMapping } from "./resource-mapping-dialog";

export type ResourceBulkAction = "map" | "publish" | "unpublish" | "delete";
type Impact = { resource:MappableResource; dependencies?:Record<string,number> };
type Result = { id:string; title:string; state:"completed" | "unchanged" | "failed"; message:string };
const pathKey = (path:ResourceMapping) => path.topic_id + ":" + (path.subtopic_id ?? "");
function MappingCheckbox({checked,mixed,onChange,label}:{checked:boolean; mixed:boolean; onChange:(checked:boolean)=>void; label:string}) {
  const ref=useRef<HTMLInputElement>(null);
  useEffect(()=>{if(ref.current)ref.current.indeterminate=mixed;},[mixed]);
  return <input ref={ref} type="checkbox" aria-label={label} checked={checked} onChange={event=>onChange(event.target.checked)}/>;
}
const labels = { map:"Map topics", publish:"Publish", unpublish:"Unpublish", delete:"Delete" };

export function ResourceBulkDialog({ action, resources, onApplied, onClose }: {
  action:ResourceBulkAction; resources:MappableResource[];
  onApplied:(ids:string[], summary:string, failed:boolean)=>Promise<void>; onClose:()=>void;
}) {
  const dialog = useRef<HTMLDialogElement>(null), guard = useRef(false), mounted = useRef(true);
  const initial = useRef(resources), completed = useRef(new Set<string>());
  const [rows,setRows] = useState<Impact[]>(resources.map(resource=>({resource}))), [options,setOptions] = useState<LearningPath[]>([]);
  const [removed,setRemoved] = useState<ResourceMapping[]>([]);
  const [pathsLoading,setPathsLoading] = useState(action === "map"), [pathsError,setPathsError] = useState("");
  const [selected,setSelected] = useState<ResourceMapping[]>([]), [filters,setFilters] = useState<Record<string,string>>({});
  const [mappingStatus,setMappingStatus]=useState("all"), [pathType,setPathType]=useState("all"), [changeStatus,setChangeStatus]=useState("all");
  const [search,setSearch] = useState(""), [page,setPage] = useState(0), [attempt,setAttempt] = useState(0);
  const [loading,setLoading] = useState(true), [busy,setBusy] = useState(false), [reviewed,setReviewed] = useState(false);
  const [confirmed,setConfirmed] = useState(false), [error,setError] = useState(""), [results,setResults] = useState<Result[]>([]);
  const [progress,setProgress] = useState("");
  useEffect(() => { mounted.current = true; dialog.current?.showModal(); return () => { mounted.current = false; dialog.current?.close(); }; }, []);
  useEffect(() => {
    let active = true; setLoading(true); setReviewed(false); setConfirmed(false); setError("");
    // Start hierarchy retrieval immediately, independently of resource version review.
    if(action === "map") {
      setPathsLoading(true);setPathsError("");
      void b9Get<{items:LearningPath[]}>("admin/resources/paths").then(paths=>{if(active)setOptions(paths.items);})
        .catch(cause=>{if(active)setPathsError("Learning paths could not load: "+(cause instanceof Error?cause.message:"Retry."));})
        .finally(()=>{if(active)setPathsLoading(false);});
    }
    void (async () => {
      const pending=initial.current.filter(resource=>!completed.current.has(resource.id));
      const loaded:Impact[]=new Array(pending.length);let cursor=0;
      // Bound parallel reads to four; mutations remain sequential and version checked.
      await Promise.all(Array.from({length:Math.min(4,pending.length)},async()=>{
        while(active && cursor<pending.length){
          const index=cursor++,resource=pending[index];
          try { loaded[index]=action === "delete" ? await b9Get<Impact>(`admin/resources/${resource.id}/delete-preview`)
            : {resource:await b9Get<MappableResource>(`admin/resources/${resource.id}`)}; }
          catch(cause){throw new Error(`Could not review ‘${resource.title}’: ${cause instanceof Error?cause.message:"Retry."}`);}
        }
      }));
      if(active){setRows(loaded);setReviewed(true);}
    })().catch(cause=>{if(active)setError(cause instanceof Error?cause.message:"Review failed.");})
      .finally(()=>{if(active)setLoading(false);});
    return () => { active = false; };
  }, [attempt, action]);
  function close() { if (guard.current) return; if ((selected.length || removed.length) && !results.length && !window.confirm("Discard the selected bulk mappings? Saved resources will remain unchanged.")) return; onClose(); }
  function changeHierarchy(field:string,value:string) {
    const index = hierarchy.findIndex(name => name + "_id" === field);
    setFilters(previous => { const next = {...previous,[field]:value}; hierarchy.slice(index+1).forEach(name => delete next[name+"_id"]); return next; }); setPage(0);
  }
  const optionByKey=useMemo(()=>new Map(options.map(path=>[pathKey(path),path])),[options]);
  const additions=new Set(selected.map(pathKey)), removals=new Set(removed.map(pathKey));
  const mappingCounts=new Map<string,number>();
  rows.forEach(({resource})=>new Set(resource.paths.map(pathKey)).forEach(key=>mappingCounts.set(key,(mappingCounts.get(key)??0)+1)));
  // Saved-status filters remain stable while checkbox edits are pending.
  const matching=options.filter(path=>{
    const key=pathKey(path),count=mappingCounts.get(key)??0;
    const statusMatches=mappingStatus==="all" || mappingStatus==="mapped"&&count>0 || mappingStatus==="all_mapped"&&rows.length>0&&count===rows.length || mappingStatus==="partial"&&count>0&&count<rows.length || mappingStatus==="unmapped"&&count===0;
    const typeMatches=pathType==="all" || pathType==="topic"&&!path.subtopic_id || pathType==="subtopic"&&Boolean(path.subtopic_id);
    const changeMatches=changeStatus==="all" || changeStatus==="pending"&&(additions.has(key)||removals.has(key)) || changeStatus==="map"&&additions.has(key) || changeStatus==="unmap"&&removals.has(key);
    return statusMatches&&typeMatches&&changeMatches&&path.label.toLowerCase().includes(search.toLowerCase())&&hierarchy.every(name=>!filters[name+"_id"]||path[(name+"_id") as keyof LearningPath]===filters[name+"_id"]);
  });
  function clearPathFilters(){setMappingStatus("all");setPathType("all");setChangeStatus("all");setSearch("");setFilters({});setPage(0);}
  function mappedCount(path:ResourceMapping){const key=pathKey(path);return additions.has(key)?rows.length:removals.has(key)?0:mappingCounts.get(key)??0;}
  function changePaths(paths:ResourceMapping[],checked:boolean){
    const keys=new Set(paths.map(pathKey));
    setSelected(previous=>[...previous.filter(path=>!keys.has(pathKey(path))),...(checked?paths.map(path=>({topic_id:path.topic_id,subtopic_id:path.subtopic_id})):[])]);
    setRemoved(previous=>[...previous.filter(path=>!keys.has(pathKey(path))),...(!checked?paths.map(path=>({topic_id:path.topic_id,subtopic_id:path.subtopic_id})):[])]);
  }
  const allMatching=Boolean(rows.length&&matching.length)&&matching.every(path=>mappedCount(path)===rows.length);
  const someMatching=matching.some(path=>mappedCount(path)>0);
  const shown = Math.min(page,Math.max(0,Math.ceil(matching.length/50)-1));
  async function apply() {
    if (guard.current || !reviewed || !rows.length || action === "map" && (pathsLoading || Boolean(pathsError) || !selected.length && !removed.length) || action === "delete" && !confirmed) return;
    guard.current = true; setBusy(true); setError("");
    const reports = [...results.filter(row => completed.current.has(row.id))], handled:string[] = [];
    for (let index=0; index<rows.length; index++) {
      if (!mounted.current) break;
      const row = rows[index].resource;
      setProgress(`${labels[action]} ${index+1} of ${rows.length}: ${row.title}`);
      try {
        let unchanged = action === "publish" && row.published || action === "unpublish" && !row.published;
        let paths:ResourceMapping[] = [];
        if (action === "map") {
          paths = [...new Map([...row.paths.filter(path=>!removals.has(pathKey(path))),...selected].map(path => [pathKey(path),path])).values()];
          unchanged = paths.length === row.paths.length && paths.every(path=>row.paths.some(existing=>pathKey(existing)===pathKey(path)));
        }
        if (!unchanged) await b9Mutation(`admin/resources/${row.id}${action === "map" ? "" : "/"+action}`, action === "map" ? "PATCH" : "POST",
          { expected_version:row.version, ...(action === "map" ? {paths} : {}), ...(action === "delete" ? {confirm_resource_id:row.id} : {}) });
        completed.current.add(row.id); handled.push(row.id);
        reports.push({id:row.id,title:row.title,state:unchanged ? "unchanged" : "completed",message:unchanged ? "Already in the requested state." : action === "map" ? "Resource mappings updated successfully." : action === "publish" ? "Resource published successfully." : action === "unpublish" ? "Resource unpublished successfully." : "Resource deleted successfully."});
      } catch (cause) {
        const detail = cause instanceof B9Error ? cause : null;
        const prefix = detail?.code === "stale_version" ? "Resource changed elsewhere. Review latest before retrying. "
          : (!detail || detail.status >= 500) ? "Completion could not be confirmed. Review latest before retrying. "
          : `${labels[action]} was not saved. `;
        reports.push({id:row.id,title:row.title,state:"failed",message:prefix+(cause instanceof Error ? cause.message : "Retry after review.")+(detail?.reference ? " Reference: "+detail.reference : "")});
      }
      if (mounted.current) setResults([...reports]);
    }
    if (mounted.current) {
      const failures = reports.filter(row => row.state === "failed").length;
      const summary = `${labels[action]}: ${reports.filter(row=>row.state === "completed").length} completed, ${reports.filter(row=>row.state === "unchanged").length} unchanged, ${failures} failed.${failures ? " Failed resources remain selected." : ""}`;
      setReviewed(false); setConfirmed(false); setProgress(summary);
      try { await onApplied(handled,summary,Boolean(failures)); } catch { setError("The operation completed, but the library could not refresh. Refresh the library to verify its current state."); }
      setBusy(false);
    }
    guard.current = false;
  }
  return <dialog ref={dialog} className="resource-library-dialog resource-bulk-dialog" aria-label={`Bulk ${labels[action]}`} onCancel={event=>{event.preventDefault();close();}}>
    <header><h3>{labels[action]} · {initial.current.length} selected resources</h3><button disabled={busy} aria-label="Close bulk action" onClick={close}>×</button></header>
    <p>Each resource is validated and saved separately. Successful items are deselected; failures stay selected. A failure does not roll back completed items.</p>
    {action === "map" && <p>Checked paths are mapped to all reviewed resources; a mixed checkbox means only some resources are mapped. Unchecking a path removes that mapping from all reviewed resources. Untouched mappings are preserved. Topic links include all current subtopics. Published resources keep their status and update learner availability immediately.</p>}
    {action === "publish" && <p>Only saved drafts that pass the existing publication requirements will be published. Already published resources remain unchanged.</p>}
    {action === "unpublish" && <p>Published resources disappear from learner pages. Media, details and mappings remain in the library.</p>}
    {action === "delete" && <><p>Delete removes these resources and their mappings from the library. This cannot be undone from the admin screen. Shared media files and historical records are retained. Unpublish instead if you only want to hide resources from learners.</p><label><input type="checkbox" checked={confirmed} disabled={busy||loading||!reviewed} onChange={event=>setConfirmed(event.target.checked)}/> I confirm deletion of the reviewed resources.</label></>}
    <div className="resource-dialog-actions"><button className={action === "delete" ? "resource-delete-action" : "resource-primary"} disabled={busy||loading||!reviewed||!rows.length||action === "map"&&(pathsLoading||Boolean(pathsError)||!selected.length&&!removed.length)||action === "delete"&&!confirmed} onClick={()=>void apply()}>{action === "map" ? "Save bulk mappings" : labels[action]+" selected resources"}</button><button disabled={busy} onClick={close}>{results.length ? "Done" : "Cancel"}</button><button disabled={busy||loading} onClick={()=>setAttempt(value=>value+1)}>Review latest resources</button></div>
    {pathsLoading&&<p role="status">Loading learning paths…</p>}{pathsError&&<p role="alert">{pathsError} Use Review latest resources to retry.</p>}
    {loading && <p role="status">Reviewing resources{action === "delete" ? " and deletion dependencies" : ""}…</p>}{progress && <p role="status">{progress}</p>}{error && <p role="alert">{error}</p>}
    <details open={action !== "map"} className="resource-bulk-review"><summary>Reviewed resources and affected mappings · {rows.length}</summary><ul>{rows.map(({resource,dependencies})=><li key={resource.id}><strong>{resource.title}</strong> · {resource.published ? "Published" : "Draft"} · v{resource.version} · {resource.paths.length} mappings{action === "delete" && <><ul>{resource.paths.map(path=><li key={pathKey(path)}>{resource.path_details?.find(detail=>pathKey(detail)===pathKey(path))?.label ?? (path.subtopic_id ? "Subtopic mapping" : "Topic-wide mapping")}</li>)}</ul><small>{dependencies?.shared_resources ?? 0} shared resources; {dependencies?.activity_kits ?? 0} kits; {dependencies?.activity_records ?? 0} activity records; {dependencies?.conversation_references ?? 0} conversation references. Media/history retained.</small></>}</li>)}</ul></details>
    {results.length > 0 && <ul className="resource-bulk-results" aria-label="Bulk action results">{results.map(row=><li key={row.id} className={row.state === "failed" ? "b4-notice-error" : ""}><strong>{row.title}</strong> · {row.state}: {row.message}</li>)}</ul>}
    {action === "map" && <fieldset disabled={busy||pathsLoading||Boolean(pathsError)}><legend>Topic/subtopic mappings</legend><div className="b9-selected-paths" aria-label="Selected bulk learning paths"><strong>{selected.length} paths to map · {removed.length} paths to unmap</strong>{selected.map(path=><div key={pathKey(path)}><span>{optionByKey.get(pathKey(path))?.label ?? "Unavailable path"}</span><button aria-label={"Remove bulk mapping "+(optionByKey.get(pathKey(path))?.label ?? path.topic_id)} onClick={()=>setSelected(previous=>previous.filter(item=>pathKey(item)!==pathKey(path)))}>Remove</button></div>)}{removed.map(path=><div key={"remove:"+pathKey(path)}><span>Unmap · {optionByKey.get(pathKey(path))?.label ?? "Unavailable path"}</span><button aria-label={"Undo unmap "+path.topic_id} onClick={()=>setRemoved(previous=>previous.filter(item=>pathKey(item)!==pathKey(path)))}>Undo</button></div>)}</div><LibraryHierarchy options={options} values={filters} onChange={changeHierarchy}/><label>Search bulk learning paths<input type="search" value={search} onChange={event=>{setSearch(event.target.value);setPage(0);}}/></label><div className="resource-bulk-path-actions"><label><MappingCheckbox checked={allMatching} mixed={!allMatching&&someMatching} label="Select or deselect all matching paths" onChange={checked=>changePaths(matching,checked)}/> Select / deselect all {matching.length} matching paths (all pages)</label><label className="resource-bulk-filter">Saved mapping status<select aria-label="Saved mapping status" value={mappingStatus} onChange={event=>{setMappingStatus(event.target.value);setPage(0);}}><option value="all">All paths</option><option value="mapped">Mapped to any resource</option><option value="all_mapped">Mapped to all resources</option><option value="partial">Partially mapped</option><option value="unmapped">Unmapped in all resources</option></select></label><label className="resource-bulk-filter">Path type<select aria-label="Bulk mapping path type" value={pathType} onChange={event=>{setPathType(event.target.value);setPage(0);}}><option value="all">Topics and subtopics</option><option value="topic">Topic-wide only</option><option value="subtopic">Subtopic only</option></select></label><label className="resource-bulk-filter">Pending changes<select aria-label="Pending mapping changes" value={changeStatus} onChange={event=>{setChangeStatus(event.target.value);setPage(0);}}><option value="all">All paths</option><option value="pending">All pending changes</option><option value="map">Will map</option><option value="unmap">Will unmap</option></select></label><button onClick={clearPathFilters}>Clear path filters</button><button disabled={!matching.length} onClick={()=>changePaths(matching,true)}>Select all matching paths</button><button disabled={!matching.length} onClick={()=>changePaths(matching,false)}>Deselect all matching paths</button></div><p>Mapping status reflects saved direct links across the reviewed resources; pending edits stay selected when filters change. Only paths matching all current filters are affected by Select/Deselect all. Removing topic-wide links removes their inherited subtopic coverage. Direct subtopic links remain separate.</p><p role="status">{matching.length} matching paths{loading ? " · Reviewing saved mapping status…" : ""}</p>{!matching.length&&!pathsLoading&&<p>No paths match these filters. Clear path filters to show more.</p>}<div className="b9-path-options">{matching.slice(shown*50,(shown+1)*50).map(path=>{const count=mappedCount(path);return <label key={pathKey(path)}><MappingCheckbox checked={Boolean(rows.length)&&count===rows.length} mixed={count>0&&count<rows.length} label={(path.subtopic_id?"Subtopic":"Topic-wide")+" · "+path.label} onChange={checked=>changePaths([path],checked)}/><span>{path.subtopic_id ? "Subtopic" : "Topic-wide"} · {path.label}<small>Mapped to {mappingCounts.get(pathKey(path))??0} of {rows.length} reviewed resources{additions.has(pathKey(path))?" · Will map to all":removals.has(pathKey(path))?" · Will unmap from all":""}</small></span></label>;})}</div><nav className="b9-pages" aria-label="Bulk mapping pages"><button disabled={!shown} onClick={()=>setPage(shown-1)}>Previous paths</button><span>{matching.length ? shown*50+1 : 0}–{Math.min(matching.length,(shown+1)*50)} of {matching.length}</span><button disabled={(shown+1)*50>=matching.length} onClick={()=>setPage(shown+1)}>Next paths</button></nav></fieldset>}
  </dialog>;
}
