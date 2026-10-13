"use client";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatedMedia } from "@/components/ui/animated-media";
import { InteractiveExperience } from "@/components/ui/interactive-experience";
import { ExternalVideoInfo, ExternalVideoSummary } from "@/components/ui/external-video-info";
import { InAppVideo } from "@/components/ui/in-app-video";
import { b9Get } from "@/lib/api/b9-client";
export const hierarchy = ["curriculum", "level", "subject", "domain", "category", "topic", "subtopic"] as const;
export type LearningPath = { topic_id: string; subtopic_id: string | null; label: string; curriculum_id?: string; level_id?: string; subject_id?: string; domain_id?: string; category_id?: string | null; curriculum?: string; level?: string; subject?: string; domain?: string; category?: string; topic?: string; subtopic?: string; valid?: boolean; available_for_publication?: boolean };
export function mediaFormat(mime?: string | null, source?: string) {
  if (!mime) return source === "external" ? "Approved URL" : "Unknown";
  return ({"image/png":"PNG", "image/jpeg":"JPEG", "image/gif":"GIF", "image/webp":"WEBP", "audio/mpeg":"MP3", "audio/mp4":"M4A", "video/mp4":"MP4", "video/webm":"WEBM", "application/pdf":"PDF", "text/html":"HTML5"} as Record<string,string>)[mime] ?? mime;
}
function SearchChoice({ label, value, choices, onChange }: {label:string; value:string; choices:{id:string; label:string}[]; onChange:(id:string)=>void}) {
  const id = useId();
  const [text,setText] = useState("");
  useEffect(()=>{setText(choices.find(c=>c.id===value)?.label ?? "");},[value, choices.map(c=>c.id).join(",")]);
  return <label>{label}<input type="search" list={id} value={text} placeholder="All" aria-label={"Library " + label}
    onChange={e=>{setText(e.target.value);onChange(choices.find(c=>c.label===e.target.value)?.id ?? "");}}
    onBlur={()=>{if(!value)setText("");}} /><datalist id={id}>{choices.map(c=><option key={c.id} value={c.label}/>)}</datalist></label>;
}
export function LibraryHierarchy({options, values, onChange}:{options:LearningPath[]; values:Record<string,string>; onChange:(key:string,value:string)=>void}) {
  return <div className="resource-hierarchy-filters">{hierarchy.map((field,index)=>{
    const parentMatches=options.filter(o=>hierarchy.slice(0,index).every(parent=>!values[parent+"_id"]||o[(parent+"_id") as keyof LearningPath]===values[parent+"_id"]));
    const unique=new Map<string,string>(); parentMatches.forEach(o=>{const id=o[(field+"_id") as keyof LearningPath];if(typeof id==="string" && id)unique.set(id, String(o[field]||o.label.split(" / ")[0]));});
    const counts=new Map<string,number>();unique.forEach(name=>counts.set(name,(counts.get(name)??0)+1)); const choices=[...unique].map(([id,name])=>({id,label:(counts.get(name)??0)>1?name+" · "+id.slice(0,8):name})).sort((a,b)=>a.label.localeCompare(b.label));
    return <SearchChoice key={field} label={field[0].toUpperCase()+field.slice(1)} value={values[field+"_id"]??""} choices={choices} onChange={id=>onChange(field+"_id",id)}/>;
  })}</div>;
}
export function ResourceMenu({title,busy,published,onEdit,onPublication,onDelete}:{title:string;busy:boolean;published:boolean;onEdit:()=>void;onPublication:()=>void;onDelete:()=>void}) {
  const trigger=useRef<HTMLButtonElement>(null), panel=useRef<HTMLDivElement>(null);
  const [position,setPosition]=useState<{left:number;top:number}|null>(null); const menuId=useId();
  useEffect(()=>{
    if(!position)return;
    if(!panel.current?.contains(document.activeElement))panel.current?.querySelector<HTMLButtonElement>("button")?.focus({preventScroll:true});
    const outside=(e:PointerEvent)=>{if(!panel.current?.contains(e.target as Node)&&!trigger.current?.contains(e.target as Node))setPosition(null);};
    const update=()=>{
      const r=trigger.current?.getBoundingClientRect();if(!r)return;
      if(r.bottom<0 || r.top>window.innerHeight || r.right<0 || r.left>window.innerWidth){setPosition(null);return;}
      const next={left:Math.max(8,Math.min(r.right-180,window.innerWidth-188)),top:window.innerHeight-r.bottom>155?r.bottom+4:Math.max(8,r.top-155)};
      setPosition(previous=>previous && previous.left===next.left && previous.top===next.top ? previous : next);
    };
    document.addEventListener("pointerdown",outside);window.addEventListener("resize",update);window.addEventListener("scroll",update,true);
    return()=>{document.removeEventListener("pointerdown",outside);window.removeEventListener("resize",update);window.removeEventListener("scroll",update,true);};
  },[position]);
  function close(){setPosition(null);trigger.current?.focus();}
  return <><button ref={trigger} type="button" aria-label={"Actions for "+title} aria-haspopup="menu" aria-expanded={Boolean(position)} aria-controls={position?menuId:undefined} disabled={busy} onClick={()=>{
    if(position){close();return;} const r=trigger.current!.getBoundingClientRect();setPosition({left:Math.max(8,Math.min(r.right-180,window.innerWidth-188)),top:window.innerHeight-r.bottom>155?r.bottom+4:Math.max(8,r.top-155)});
  }}>•••</button>{position && createPortal(<div ref={panel} id={menuId} role="menu" className="resource-row-menu" style={position} onKeyDown={e=>{
    const buttons=[...panel.current!.querySelectorAll<HTMLButtonElement>("button")];const index=buttons.indexOf(document.activeElement as HTMLButtonElement);
    if(e.key==="Escape"||e.key==="Tab"){if(e.key==="Escape")e.preventDefault();close();}
    if(["ArrowDown","ArrowUp","Home","End"].includes(e.key)){e.preventDefault();buttons[e.key==="Home"?0:e.key==="End"?buttons.length-1:(index+(e.key==="ArrowDown"?1:-1)+buttons.length)%buttons.length]?.focus();}
  }}><button role="menuitem" onClick={()=>{close();onEdit();}}>Edit</button><button role="menuitem" onClick={()=>{close();onPublication();}}>{published?"Unpublish":"Publish"}</button><button role="menuitem" className="resource-delete-action" onClick={()=>{close();onDelete();}}>Delete</button></div>,document.body)}</>;
}
export function MediaPreview({url,type,mime,description,caption,htmlDocument}:{url:string;type:string;mime?:string|null;description:string;caption?:string|null;htmlDocument?:string}) {
  const [error,setError]=useState(false);useEffect(()=>setError(false),[url]);
  if(error)return <p role="alert">Media preview could not load. You can keep editing and retry Preview.</p>;
  if(type==="interactive" && htmlDocument)return <InteractiveExperience document={htmlDocument} title={description}/>;
  if(type==="external_video")return <ExternalVideoSummary/>;
  if(["video","animation"].includes(type)&&mime==="image/gif")return <AnimatedMedia src={url} description={description} caption={caption} onError={()=>setError(true)}/>;
  if(["image","diagram"].includes(type))return <figure className="resource-media-preview"><img src={url} alt={description} onError={()=>setError(true)}/>{caption&&<figcaption>{caption}</figcaption>}</figure>;
  if(type==="audio")return <audio controls preload="metadata" src={url} aria-label={description} onError={()=>setError(true)}/>;
  if(["video","animation"].includes(type))return <InAppVideo src={url} title={description} onError={()=>setError(true)}/>;
  return <a href={url} target="_blank" rel="noopener noreferrer">Open approved resource</a>;
}
export function ResourcePreviewDialog({resource,onClose}:{resource:{id:string;type:string;mime_type?:string|null;title:string;alt_text?:string|null;caption_or_transcript?:string|null};onClose:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null);const [url,setUrl]=useState("");const [error,setError]=useState("");const [htmlDocument,setHtmlDocument]=useState("");
  const [external,setExternal]=useState<ExternalVideoInfo|null>(null);
  useEffect(()=>{dialog.current?.showModal();let active=true;b9Get<{url:string;html_document?:string;message?:string;launch_mode?:string;external_video?:ExternalVideoInfo}>("admin/resources/"+resource.id+"/preview").then(d=>{if(active){setUrl(d.url||"");setHtmlDocument(d.html_document||"");if(d.launch_mode==="interactive_pending")setError(d.message||"Paste or upload HTML5 in Edit before previewing.");setExternal(d.external_video??null);}}).catch(e=>{if(active)setError("Preview failed: "+e.message);});return()=>{active=false;dialog.current?.querySelectorAll("video,audio").forEach(node=>(node as HTMLMediaElement).pause());dialog.current?.close();};},[resource.id]);
  return <dialog ref={dialog} className="resource-library-dialog" aria-label={"Preview "+resource.title} onCancel={e=>{e.preventDefault();onClose();}}><header><h3>{resource.title}</h3><button autoFocus aria-label="Close preview" onClick={onClose}>×</button></header>{error?<p role="alert">{error}</p>:external?<ExternalVideoSummary info={external} description={resource.alt_text||resource.title}/>:(url||htmlDocument)?<MediaPreview htmlDocument={htmlDocument} url={url} type={resource.type} mime={resource.mime_type} description={resource.alt_text||resource.title} caption={resource.caption_or_transcript}/>:<p role="status">Loading preview…</p>}{resource.caption_or_transcript&&resource.type==="external_video"&&<details><summary>Read transcript or captions</summary><p>{resource.caption_or_transcript}</p></details>}</dialog>;
}
export function MappingsDialog({title,paths,onClose}:{title:string;paths:LearningPath[];onClose:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null);useEffect(()=>{dialog.current?.showModal();return()=>dialog.current?.close();},[]);
  return <dialog ref={dialog} className="resource-library-dialog" aria-label={"Mappings for "+title} onCancel={e=>{e.preventDefault();onClose();}}><header><h3>Mappings · {title}</h3><button autoFocus aria-label="Close mappings" onClick={onClose}>×</button></header><ul>{paths.map(p=><li key={p.topic_id+":"+p.subtopic_id}><b>{p.subtopic_id?"Direct subtopic":"Topic-wide coverage"}</b> · {p.label}{!p.subtopic_id&&<small> Includes all current subtopics under this topic.</small>}{p.valid===false&&<strong> · Unavailable path</strong>}</li>)}</ul></dialog>;
}
