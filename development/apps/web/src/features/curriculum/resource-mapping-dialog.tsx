"use client";
import { useEffect, useRef, useState } from "react";
import { B9Error, b9Get, b9Mutation } from "@/lib/api/b9-client";
import { hierarchy, LibraryHierarchy, LearningPath, MediaPreview } from "./resource-library-ui";
import { ExternalVideoInfo, ExternalVideoSummary } from "@/components/ui/external-video-info";
export type ResourceMapping = { topic_id:string; subtopic_id:string|null };
export type MappableResource = { id:string; title:string; type:string; version:number; published:boolean; mime_type?:string|null; external_video?:ExternalVideoInfo|null; alt_text?:string|null; paths:ResourceMapping[]; path_details?:LearningPath[] };
const key=(p:ResourceMapping)=>p.topic_id+":"+(p.subtopic_id??"");
const signature=(paths:ResourceMapping[])=>paths.map(key).sort().join("|");

export function ResourceMappingDialog({resource,onSaved,onClose}:{resource:MappableResource;onSaved:(id:string)=>Promise<void>;onClose:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null), guard=useRef(false); const known=useRef(new Map<string,LearningPath>());
  const [current,setCurrent]=useState(resource); const [selected,setSelected]=useState<ResourceMapping[]>(resource.paths);
  const [options,setOptions]=useState<LearningPath[]>([]);const [filters,setFilters]=useState<Record<string,string>>({});
  const [search,setSearch]=useState("");const [depth,setDepth]=useState("");const [page,setPage]=useState(0);
  const [loaded,setLoaded]=useState(false); const [loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [preview,setPreview]=useState("");const [invalid,setInvalid]=useState<string[]>([]);const [reviewed,setReviewed]=useState(true);
  const [loadAttempt,setLoadAttempt]=useState(0),[notice,setNotice]=useState("");
  const dirty=signature(selected)!==signature(current.paths);
  useEffect(()=>{dialog.current?.showModal();return()=>dialog.current?.close();},[]);
  useEffect(()=>{let active=true;setLoading(true);setError("");Promise.all([
    b9Get<MappableResource>("admin/resources/"+resource.id), b9Get<{items:LearningPath[]}>("admin/resources/paths")
  ]).then(([latest,paths])=>{if(active){setLoaded(true);setCurrent(latest);if(loadAttempt===0)setSelected(latest.paths);paths.items.forEach(p=>known.current.set(key(p),p));setOptions(paths.items);setInvalid(old=>old.filter(k=>!paths.items.some(p=>key(p)===k)));}})
    .catch(e=>{if(active)setError("Mappings could not load: "+e.message);}).finally(()=>{if(active)setLoading(false);});
    b9Get<{url:string}>("admin/resources/"+resource.id+"/preview").then(d=>{if(active)setPreview(d.url);}).catch(()=>{});
    return()=>{active=false;};
  },[resource.id,loadAttempt]);
  useEffect(()=>{if(!dirty)return;const warn=(event:BeforeUnloadEvent)=>event.preventDefault();window.addEventListener("beforeunload",warn);return()=>window.removeEventListener("beforeunload",warn);},[dirty]);
  function cancel(){if(guard.current)return;if(dirty&&!window.confirm("Discard unsaved mapping changes? Saved mappings will remain unchanged."))return;onClose();}
  function hierarchyChange(name:string,value:string){const index=hierarchy.findIndex(field=>field+"_id"===name);setFilters(previous=>{const next={...previous,[name]:value};hierarchy.slice(index+1).forEach(field=>delete next[field+"_id"]);return next;});setPage(0);}
  const matches=options.filter(p=>p.label.toLowerCase().includes(search.toLowerCase())&&hierarchy.every(field=>!filters[field+"_id"]||p[(field+"_id") as keyof LearningPath]===filters[field+"_id"])&&(!depth||(depth==="topic"?!p.subtopic_id:Boolean(p.subtopic_id))));
  const last=Math.max(0,Math.ceil(matches.length/50)-1), shown=Math.min(page,last);
  function detail(path:ResourceMapping){return options.find(p=>key(p)===key(path))??known.current.get(key(path))??current.path_details?.find(p=>key(p)===key(path));}
  async function save(){
    if(guard.current)return;guard.current=true;setBusy(true);setError("");setNotice("");
    try{
      const saved=await b9Mutation<MappableResource>("admin/resources/"+current.id,"PATCH",{expected_version:current.version,paths:selected});
      setCurrent(saved);setSelected(saved.paths);await onSaved(saved.id);onClose();
    }catch(cause){
      const e=cause instanceof B9Error?cause:null;
      setError((e?.code==="stale_version"?"Resource changed elsewhere. Review latest mappings, compare them with your selections, then save again.":"Mappings were not saved. ")+(cause instanceof Error?cause.message:"Retry after reviewing current paths.")+(e?.reference?" Reference: "+e.reference:""));
      if(e?.code==="stale_version")setReviewed(false);
      if(e?.invalidPaths.length)setInvalid(e.invalidPaths.map(key));
    }finally{guard.current=false;setBusy(false);}
  }
  async function review(){
    if(guard.current)return;guard.current=true;setBusy(true);setError("");
    try{const [latest,paths]=await Promise.all([b9Get<MappableResource>("admin/resources/"+current.id),b9Get<{items:LearningPath[]}>("admin/resources/paths")]);setLoaded(true);setCurrent(latest);paths.items.forEach(p=>known.current.set(key(p),p));setOptions(paths.items);setInvalid(old=>old.filter(k=>!paths.items.some(p=>key(p)===k)));setReviewed(true);setNotice("Latest saved mappings loaded below. Your selections are preserved; compare before saving.");}
    catch(e){setError("Latest mappings could not load: "+(e instanceof Error?e.message:"Retry."));}finally{guard.current=false;setBusy(false);}
  }
  return <dialog ref={dialog} className="resource-library-dialog resource-mapping-dialog" aria-label={"Map topics for "+current.title} onCancel={e=>{e.preventDefault();cancel();}}>
    <header><div><h3>{current.title}</h3><p>{current.published?"Published":"Draft"} · v{current.version}</p></div><button disabled={busy} aria-label="Close mapping dialog" onClick={cancel}>×</button></header>
    {preview&&<div className="resource-mapping-thumbnail"><MediaPreview url={preview} type={current.type} mime={current.mime_type} description={current.alt_text||current.title}/></div>}
    {Boolean(current.external_video)&&<ExternalVideoSummary info={current.external_video} description={current.alt_text||current.title}/>}
    <p>Topic links cover the topic and all its current subtopics. Subtopic links cover only the selected subtopic.</p>
    <p>{Boolean(current.external_video)?"Published videos appear on mapped learning paths immediately. Draft videos require publication before learner playback.":current.published?"Saved mapping changes update learner availability immediately. Removing every mapping leaves this resource published, with no placement on learning pages.":"Mapping does not publish the resource. Learners see it only after resource and curriculum publication."}</p>
    <div className="resource-dialog-actions"><button className="resource-primary" disabled={busy||loading||!loaded||!reviewed} onClick={()=>void save()}>Save mappings</button><button disabled={busy} onClick={cancel}>Cancel</button>{busy&&<span role="status">Saving…</span>}</div>
    {error&&<div role="alert"><p>{error}</p><button disabled={busy} onClick={()=>loading?setLoadAttempt(n=>n+1):void review()}>Review latest mappings</button></div>}{notice&&<p role="status">{notice}</p>}
    {notice&&<details open><summary>Latest saved mappings · {current.paths.length}</summary><ul>{current.paths.map(p=><li key={key(p)}>{current.path_details?.find(d=>key(d)===key(p))?.label??key(p)}</li>)}</ul></details>}
    <fieldset disabled={loading||busy} className="b9-resource-paths"><legend>Topic/subtopic selection</legend>
      <div className="b9-selected-paths" aria-label="Selected learning paths"><strong>{selected.length} selected</strong>{!selected.length&&<span>Not mapped</span>}{selected.map(p=>{
        const d=detail(p);const label=d?.label??"Unavailable path "+p.topic_id.slice(0,8);const unavailable=invalid.includes(key(p))||!options.some(o=>key(o)===key(p));
        return <div key={key(p)} className={unavailable?"b9-path-unavailable":""}><span><b>{p.subtopic_id?"Subtopic":"Topic"}</b> · {label}{unavailable?" · Unavailable: remove or replace":""}</span><button aria-label={"Remove "+label} onClick={()=>setSelected(old=>old.filter(o=>key(o)!==key(p)))}>Remove</button></div>;
      })}</div>
      <LibraryHierarchy options={options} values={filters} onChange={hierarchyChange}/>
      <div className="b9-path-filters"><label>Search topics and subtopics<input type="search" value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}/></label><label>Link type<select aria-label="Link type" value={depth} onChange={e=>{setDepth(e.target.value);setPage(0);}}><option value="">Topics and subtopics</option><option value="topic">Topic-wide</option><option value="subtopic">Specific subtopic</option></select></label><button onClick={()=>{setSearch("");setFilters({});setDepth("");setPage(0);}}>Clear mapping filters</button></div>
      {loading&&<p role="status">Loading mappings…</p>}
      <div className="b9-path-options">{matches.slice(shown*50,(shown+1)*50).map(p=><label key={key(p)}><input type="checkbox" checked={selected.some(o=>key(o)===key(p))} onChange={e=>setSelected(old=>e.target.checked?[...old.filter(o=>key(o)!==key(p)),{topic_id:p.topic_id,subtopic_id:p.subtopic_id}]:old.filter(o=>key(o)!==key(p)))}/><span><b>{p.subtopic_id?"Subtopic":"Topic-wide"}</b> · {p.label}</span></label>)}</div>
      <nav className="b9-pages" aria-label="Mapping pages"><button disabled={shown===0} onClick={()=>setPage(shown-1)}>Previous paths</button><span>{matches.length?shown*50+1:0}–{Math.min(matches.length,(shown+1)*50)} of {matches.length} · {selected.length} selected across all pages</span><button disabled={shown===last} onClick={()=>setPage(shown+1)}>Next paths</button></nav>
    </fieldset>
  </dialog>;
}

export function ResourceDeleteDialog({resource,onDeleted,onClose}:{resource:MappableResource;onDeleted:(id:string)=>Promise<void>;onClose:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null),guard=useRef(false);
  const [impact,setImpact]=useState<{resource:MappableResource;dependencies:Record<string,number>}|null>(null);
  const [confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [attempt,setAttempt]=useState(0);
  useEffect(()=>{dialog.current?.showModal();return()=>dialog.current?.close();},[]);
  useEffect(()=>{let active=true;setConfirmed(false);setImpact(null);setError("");b9Get<{resource:MappableResource;dependencies:Record<string,number>}>("admin/resources/"+resource.id+"/delete-preview").then(data=>{if(active)setImpact(data);}).catch(e=>{if(active)setError("Deletion could not be reviewed: "+e.message);});return()=>{active=false;};},[resource.id,attempt]);
  async function remove(){if(!impact||!confirmed||guard.current)return;guard.current=true;setBusy(true);setError("");try{
    await b9Mutation("admin/resources/"+resource.id+"/delete","POST",{expected_version:impact.resource.version,confirm_resource_id:resource.id});await onDeleted(resource.id);onClose();
  }catch(cause){const e=cause instanceof B9Error?cause:null;setError((e?.code==="stale_version"?"Resource changed elsewhere. Review deletion again and confirm the latest mappings.":"Resource deletion could not be confirmed. Refresh the library or retry. ")+(cause instanceof Error?cause.message:"")+(e?.reference?" Reference: "+e.reference:""));setConfirmed(false);}finally{guard.current=false;setBusy(false);}}
  return <dialog ref={dialog} className="resource-library-dialog resource-delete-dialog" aria-label={"Delete "+resource.title} onCancel={e=>{e.preventDefault();if(!busy)onClose();}}><header><h3>Delete ‘{impact?.resource.title??resource.title}’?</h3><button disabled={busy} aria-label="Close deletion dialog" onClick={onClose}>×</button></header>
    <p>Unpublish removes learner visibility while keeping the resource in the library. Delete removes it from the library and all topic/subtopic placements.</p><p>This cannot be undone from the admin screen. Media and historical records are retained; shared files are not deleted.</p>
    {impact?<><h4>Affected mappings · {impact.resource.paths.length}</h4>{impact.resource.paths.length?<ul>{impact.resource.paths.map(p=><li key={key(p)}>{impact.resource.path_details?.find(d=>key(d)===key(p))?.label??key(p)}</li>)}</ul>:<p>Not mapped</p>}<p>{impact.dependencies.shared_resources} other resources and {impact.dependencies.activity_kits} activity kits share the media. Their files remain intact. {impact.dependencies.activity_records} activity records and {impact.dependencies.conversation_references} conversation references are retained.</p><label><input type="checkbox" disabled={busy} checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/> I confirm deletion of ‘{impact.resource.title}’ from the library.</label></>:!error&&<p role="status">Checking dependencies and mappings…</p>}
    {error&&<div role="alert"><p>{error}</p><button disabled={busy} onClick={()=>setAttempt(n=>n+1)}>Review deletion again</button></div>}
    <div className="resource-dialog-actions"><button className="resource-delete-action" disabled={busy||!impact||!confirmed} onClick={()=>void remove()}>Delete resource</button><button disabled={busy} onClick={onClose}>Cancel</button>{busy&&<span role="status">Deleting…</span>}</div>
  </dialog>;
}

