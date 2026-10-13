"use client";
import { InAppVideo } from "@/components/ui/in-app-video";
import { InteractiveExperience } from "@/components/ui/interactive-experience";
import { ExternalVideoPlayer } from "@/components/ui/external-video-player";
import { b9Mutation } from "@/lib/api/b9-client";
import { recommendationPayload, type ComposedLearningResponse } from "@/lib/api/learning-response";
import { useExplore } from "./explore-context";

import { AnimatedMedia } from "@/components/ui/animated-media";
import { useEffect, useRef, useState } from "react";
import { BookOpen, Headphones, Image as ImageIcon, Play, UserRound, X } from "lucide-react";

export type ResourceCard = {
  id: string; version: number; mime_type?: string | null; type: string; title: string; description: string | null;
  alt_text: string | null; caption_or_transcript: string | null;
  accessibility_note: string | null; attribution: string | null;
};
export type TeacherCard = {
  id: string; name: string; bio: string | null; qualifications: string | null;
  experience: string | null; languages: string[]; availability: string | null;
  expertise: { subject_id: string; topic_id: string | null; claim_status: string }[];
};
type KitCard = { id:string; version:number; name:string; description:string|null; materials:string[]; instructions:string; supervision:string; cost:string|null; currency:string|null; availability:string|null; prerequisites:string };
type Choice = { candidate_id:string; candidate_kind:"resource"|"kit"|"tutor"; candidate_type:string; version:number; display_mode:"inline"|"optional card"|"reference earlier"; reason:string; availability_state:string; reference_message_id:string|null };
type Decision = { learning_intent:string; concept:string; primary:Choice|null; alternative:Choice|null; display_mode:string };
type ImageDecision = { resource_id: string | null; resource_version: number | null; display_mode: "inline" | "reference earlier" | "none"; reason: string; reference_message_id: string | null };
type Result = { status: string; resources: ResourceCard[]; teachers: TeacherCard[]; kits?:KitCard[]; image_decision?: ImageDecision; recommendation_decision?:Decision; learning_response?:ComposedLearningResponse };
type Delivery = { poster_url?: string | null; status: string; version: number; url: string; html_document?: string; launch_mode: "media" | "separate_page" | "external_video" | "interactive"; expires_at: string | null };

async function b9Get(path: string) {
  const response = await fetch("/api/b9/" + path, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data?.error?.message || data?.detail || "Resources could not be loaded.");
  return data;
}
// Serialize display/activity acknowledgements: the existing CSRF endpoint rotates
// its cookie, so simultaneous token requests can invalidate each other's posts.
let acknowledgementQueue: Promise<unknown> = Promise.resolve();
function markAcknowledgement(path:string,body:unknown) {
  const result=acknowledgementQueue.then(()=>b9Mutation(path,"POST",body));
  acknowledgementQueue=result.catch(()=>{});
  return result;
}
async function recordActivity(resourceId: string, eventType: "open" | "play", key: string, sessionId?: string) {
  await markAcknowledgement("resources/" + resourceId + "/activity", {event_type:eventType,deduplication_key:key,session_id:sessionId});
}

function isVisual(resource: ResourceCard) { return ["image", "diagram"].includes(resource.type) || ["video", "animation"].includes(resource.type) && resource.mime_type === "image/gif"; }

function imageDescription(resource: ResourceCard) {
  const meaningful = (value: string | null) => value && !/^(?:png|jpe?g|webp|gif|image|picture|photo|diagram|file|image\/(?:png|jpeg|webp))\.?$/i.test(value.trim());
  return meaningful(resource.alt_text) ? resource.alt_text! : meaningful(resource.description) ? resource.description! : resource.title;
}

function InlineImage({ resource, sessionId, messageId, onEnlarge }: { resource: ResourceCard; sessionId: string; messageId: string; onEnlarge: () => void }) {
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [error, setError] = useState(""); const [attempt, setAttempt] = useState(0);
  const acknowledged = useRef(false);
  useEffect(() => {
    let active = true;
    b9Get("resources/" + resource.id + "/delivery").then((data: Delivery) => {
      if (!active) return;
      if (data.version !== resource.version || data.launch_mode !== "media") { failed("This image changed or is no longer available."); return; }
      setDelivery(data); setError("");
    }).catch(() => { if (active) failed(); });
    return () => { active = false; };
  }, [resource.id, resource.version, attempt]);
  useEffect(() => {
    if (!delivery) return;
    const timer = setTimeout(() => { if (!acknowledged.current) { failed(); } }, 20000);
    return () => clearTimeout(timer);
  }, [delivery]);
  async function markDisplay(displayStatus: "displayed" | "failed") {
    const acknowledge = async () => {
      await markAcknowledgement("sessions/" + sessionId + "/images/displayed", {message_id:messageId,resource_id:resource.id,resource_version:resource.version,display_status:displayStatus});
    };
    try { await acknowledge(); } catch { try { await acknowledge(); } catch { /* Answer and image remain usable. */ } }
  }
  function failed(message = "This image could not load. Your explanation is still available.") {
    setDelivery(null); setError(message); void markDisplay("failed");
  }
  function loaded() {
    if (acknowledged.current) return;
    acknowledged.current = true; void markDisplay("displayed");
  }
  const caption = resource.caption_or_transcript && !/^(?:png|jpe?g|webp|image|diagram)\.?$/i.test(resource.caption_or_transcript.trim())
    ? resource.caption_or_transcript : resource.description || resource.title;
  return <figure id={"learning-image-" + messageId} tabIndex={-1} className="conversation-inline-image" aria-label={resource.title}>
    {!delivery && !error && <p role="status">Loading illustration…</p>}
    {error && <div className="resource-status"><p>{error}</p><button onClick={() => { acknowledged.current = false; setError(""); setDelivery(null); setAttempt(value => value + 1); }}>Retry image</button></div>}
    {delivery && ["video", "animation"].includes(resource.type) && resource.mime_type === "image/gif" && <><AnimatedMedia src={delivery.url} description={imageDescription(resource)} caption={caption} onLoad={loaded} onError={() => failed()} /><button onClick={onEnlarge} aria-label={"Enlarge " + resource.title}>Enlarge animation</button></>}
    {delivery && resource.mime_type !== "image/gif" && <button className="conversation-image-enlarge" aria-label={"Enlarge " + resource.title} onClick={onEnlarge}>
      <img src={delivery.url} alt={imageDescription(resource)} onLoad={() => void loaded()} onError={() => failed()} />
    </button>}
    {delivery && resource.mime_type !== "image/gif" && <figcaption>{caption}{resource.attribution && <small>Credit: {resource.attribution}</small>}<span>Click image to enlarge</span></figcaption>}
  </figure>;
}

export function CatalogueViewer({ resource, sessionId, onClose, deliveryPath }: { resource: ResourceCard; sessionId?: string; onClose: () => void; deliveryPath?: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const playKey = useRef(crypto.randomUUID());
  const openKey = useRef(crypto.randomUUID());
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => { element?.querySelectorAll("audio, video").forEach(node => (node as HTMLMediaElement).pause()); element?.close(); };
  }, []);
  useEffect(() => {
    let active = true;
    b9Get(deliveryPath ?? "resources/" + resource.id + "/delivery").then((result: Delivery) => {
      if (active) {
        if (result.version !== resource.version) { setError("This resource changed. Refresh the catalogue and review its latest version."); return; }
        setDelivery(result); setError("");
      }
    }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : "Resource unavailable."); });
    return () => { active = false; };
  }, [resource.id, resource.version, deliveryPath, attempt]);
  useEffect(() => {
    if (!delivery) return;
    void recordActivity(resource.id, "open", openKey.current, sessionId).catch(() => {});
  }, [delivery, resource.id, sessionId]);
  const refresh = () => { setDelivery(null); setError(""); setAttempt(value => value + 1); };
  const play = () => { void recordActivity(resource.id, "play", playKey.current, sessionId).catch(() => {}); };
  return <dialog ref={dialog} className="resource-dialog" aria-label={resource.title}
    onCancel={event => { event.preventDefault(); onClose(); }}>
    <header className="resource-dialog-header"><div><span>{resource.type}</span><h2>{resource.title}</h2></div>
      <button autoFocus className="resource-close" aria-label="Close resource" onClick={onClose}><X size={20} /></button></header>
    <div className="resource-dialog-scroll">
      {resource.description && <p>{resource.description}</p>}
      {!delivery && !error && <p role="status">Loading resource…</p>}
      {error && <div role="alert"><p>{error}</p><button onClick={refresh}>Try again</button></div>}
      {resource.type === "interactive" && delivery?.launch_mode === "interactive" && delivery.html_document && <InteractiveExperience document={delivery.html_document} title={resource.title} />}
      {delivery?.launch_mode==="external_video"&&<ExternalVideoPlayer url={delivery.url} title={resource.title} onClose={onClose} onPlay={play}/>}
      {delivery?.launch_mode === "separate_page" && resource.type!=="external_video" && <p><a href={delivery.url} target="_blank" rel="noopener noreferrer">Open reviewed experience in a new tab</a></p>}
      {delivery?.launch_mode === "media" && ["video", "animation"].includes(resource.type) && resource.mime_type === "image/gif" && <AnimatedMedia src={delivery.url} description={imageDescription(resource)} caption={resource.caption_or_transcript} onError={() => { setDelivery(null); setError("This resource could not load."); }} />}
      {delivery?.launch_mode === "media" && (resource.type === "image" || resource.type === "diagram") &&
        <figure><img src={delivery.url} alt={imageDescription(resource)} onError={() => { setDelivery(null); setError("This resource could not load."); }} />
          {resource.caption_or_transcript && <figcaption>{resource.caption_or_transcript}</figcaption>}</figure>}
      {delivery?.launch_mode === "media" && resource.type === "audio" &&
        <audio controls preload="metadata" src={delivery.url} onPlay={play} onError={() => { setDelivery(null); setError("This resource could not load."); }} aria-label={resource.title} />}
      {delivery?.launch_mode === "media" && ["video", "animation"].includes(resource.type) && resource.mime_type !== "image/gif" &&
        <InAppVideo src={delivery.url} poster={delivery.poster_url} title={resource.title} onPlay={play} onClose={onClose} onError={() => { setDelivery(null); setError("This resource could not load."); }} />}
      {resource.caption_or_transcript && !["image", "diagram"].includes(resource.type) &&
        <details><summary>Read transcript or captions</summary><p>{resource.caption_or_transcript}</p></details>}
      {resource.accessibility_note && <p>{resource.accessibility_note}</p>}
      {resource.attribution && <p><small>Credit: {resource.attribution}</small></p>}
    </div>
  </dialog>;
}

export function LearningSupportViewer({item,kind,availabilityState,onClose}:{item:KitCard|TeacherCard;kind:"kit"|"tutor";availabilityState:string;onClose:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{dialog.current?.showModal();return()=>dialog.current?.close();},[]);
  const kit=kind==="kit"?item as KitCard:null, teacher=kind==="tutor"?item as TeacherCard:null;
  return <dialog ref={dialog} className="resource-dialog" aria-label={item.name} onCancel={e=>{e.preventDefault();onClose();}}>
    <header className="resource-dialog-header"><h2>{item.name}</h2><button autoFocus aria-label="Close resource" onClick={onClose}><X size={20}/></button></header>
    <div className="resource-dialog-scroll">{kit&&<><p>{kit.description}</p><p>{kit.prerequisites}</p><h3>Materials</h3><ul>{kit.materials.map((m,i)=><li key={i}>{m}</li>)}</ul><h3>Instructions</h3><p className="resource-instructions">{kit.instructions}</p><h3>Adult supervision</h3><p>{kit.supervision}</p>{kit.cost&&<p>Listed cost: {kit.cost} {kit.currency}</p>}<p>This is an activity guide. FLAME does not verify that you have the materials or provide checkout.</p></>}
    {teacher&&<><p>{teacher.bio}</p><p>{teacher.qualifications}</p><p>{teacher.experience}</p><p>Languages: {teacher.languages.join(", ")||"Not specified"}</p><p>Availability: {availabilityState==="unknown"?"Unknown — confirm with the tutor":"Listed as "+teacher.availability+"; not live-verified"}</p><p>Expertise: {teacher.expertise.some(e=>e.claim_status==="reviewed")?"Includes reviewed expertise":"Tutor-declared expertise"}</p><p>Viewing this profile does not book a session or contact the tutor. Scheduling is not yet available in FLAME.</p></>}
    </div>
  </dialog>;
}

export function CatalogueRecommendations({ sessionId, messageId }: { sessionId: string; messageId: string }) {
  const explore = useExplore();
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<ResourceCard | null>(null);
  const [support,setSupport]=useState<{item:KitCard|TeacherCard;kind:"kit"|"tutor";availabilityState:string}|null>(null);
  const [openError,setOpenError]=useState("");
  const [opening,setOpening]=useState(false);
  const generation=useRef(0), acknowledged=useRef(new Set<string>());
  useEffect(() => {
    let active = true;
    const run=++generation.current;
    setResult(null); setSelected(null); setSupport(null); setError("");setOpenError("");setOpening(false);
    b9Get("sessions/" + sessionId + "/recommendations?message_id=" + encodeURIComponent(messageId))
      .then((data: Result) => { if (active) { setResult(recommendationPayload(data,messageId)); setError(""); } })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : "Recommendations unavailable."); });
    return () => { active = false;if(generation.current===run)generation.current++; };
  }, [sessionId, messageId, retry]);
  useEffect(()=>{
    const choices=[result?.recommendation_decision?.primary,result?.recommendation_decision?.alternative].filter((c):c is Choice=>Boolean(c&&c.display_mode==="optional card"));
    for(const choice of choices){
      const key=messageId+":"+choice.candidate_id+":"+choice.version;
      if(acknowledged.current.has(key))continue;
      acknowledged.current.add(key);
      const mark=()=>markAcknowledgement("sessions/"+sessionId+"/recommendations/displayed",{message_id:messageId,candidate_id:choice.candidate_id,version:choice.version});
      void mark().catch(()=>mark().catch(()=>acknowledged.current.delete(key)));
    }
  },[result,sessionId,messageId]);
  async function openChoice(choice:Choice){
    if(opening)return;setOpening(true);setOpenError("");const run=generation.current;
    try{const current=await b9Get("sessions/"+sessionId+"/recommendations/"+choice.candidate_id+"?message_id="+encodeURIComponent(messageId));if(run!==generation.current)return;
      if(choice.candidate_kind==="resource")setSelected(current.item);else setSupport({item:current.item,kind:choice.candidate_kind,availabilityState:current.decision.availability_state});
    }catch{if(run===generation.current)setOpenError("This recommendation changed or is unavailable. Close it and continue learning, or try opening it again.");}
    finally{if(run===generation.current)setOpening(false);}
  }
  if (error) return <button className="resource-image-retry" onClick={() => { setError(""); setRetry(value => value + 1); }}>Retry learning suggestions</button>;
  if (!result) return null;
  if(result.status==="pending" || result.learning_response?.recommendations.status==="pending")return <p role="status">Checking learning suggestions…</p>;
  if(result.recommendation_decision){
    const choices=[result.recommendation_decision.primary,result.recommendation_decision.alternative].filter((c):c is Choice=>Boolean(c));
    if(!choices.length)return null;
    return <section className="resource-recommendations" aria-label="Learning recommendations">
      {choices.map(choice=>{
        const resource=result.resources.find(r=>r.id===choice.candidate_id), tutor=result.teachers.find(t=>t.id===choice.candidate_id), kit=result.kits?.find(k=>k.id===choice.candidate_id);
        const title=resource?.title||tutor?.name||kit?.name||"Learning resource";
        const isVideo=["video","external_video","animation"].includes(choice.candidate_type);
        const Icon=choice.candidate_kind==="tutor"?UserRound:choice.candidate_kind==="kit"?BookOpen:isVideo?Play:ImageIcon;
        return <div key={choice.candidate_id} id={"learning-resource-"+messageId+"-"+choice.candidate_id} tabIndex={-1} className="learning-recommendation">
          {choice.display_mode==="inline"&&resource?<InlineImage resource={resource} sessionId={sessionId} messageId={messageId} onEnlarge={()=>void openChoice(choice)}/>:choice.display_mode==="reference earlier"?<button className="conversation-image-reference" disabled={opening} onClick={()=>{
            const earlier=document.getElementById("learning-resource-"+choice.reference_message_id+"-"+choice.candidate_id)||document.getElementById("learning-image-"+choice.reference_message_id);
            if(earlier){earlier.scrollIntoView({behavior:"smooth",block:"center"});earlier.focus({preventScroll:true});}else void openChoice(choice);
          }}>View earlier resource · {title}</button>:<button className={"resource-card"+(isVideo?" resource-video-button":"")} title={title} aria-label={(isVideo?"Play video: ":choice.candidate_kind==="kit"?"View activity kit: ":choice.candidate_kind==="tutor"?"View tutor: ":"Open resource: ")+title} disabled={opening} onClick={()=>void openChoice(choice)}>
            <span className="resource-icon"><Icon size={isVideo?17:23} fill={isVideo?"currentColor":"none"} aria-hidden="true"/></span><span className="resource-card-copy"><strong>{title}</strong>{tutor&&<small>Availability: {choice.availability_state==="unknown"?"Unknown — confirm with tutor":"Listed as "+tutor.availability}</small>}</span>
          </button>}
          <p className="recommendation-reason">{choice.reason}</p>
          {explore && <button className="explore-answer-link" onClick={() => void explore.fromAnswer(sessionId, messageId, choice.candidate_kind, choice.candidate_id)}>Explore related {choice.candidate_kind === "resource" ? "media" : choice.candidate_kind === "kit" ? "kits" : "teachers"}</button>}
        </div>;
      })}
      {openError&&<p role="alert">{openError}</p>}
      {selected&&<CatalogueViewer key={selected.id} resource={selected} sessionId={sessionId} onClose={()=>setSelected(null)}/>}
      {support&&<LearningSupportViewer {...support} onClose={()=>setSupport(null)}/>}
    </section>;
  }
  const decision = result.image_decision;
  const image = decision?.display_mode !== "none" ? result.resources.find(resource => resource.id === decision?.resource_id && resource.version === decision.resource_version && isVisual(resource)) : undefined;
  const otherResources = result.resources.filter(resource => !isVisual(resource));
  if (!image && !otherResources.length && !result.teachers.length) return null;
  return <section className="resource-recommendations" aria-label="Learning resources and teachers">
    {image && decision?.display_mode === "inline" && <InlineImage key={image.id + ":" + image.version} resource={image} sessionId={sessionId} messageId={messageId} onEnlarge={() => setSelected(image)} />}
    {image && decision?.display_mode === "reference earlier" && <button className="conversation-image-reference" onClick={() => {
      const earlier = document.getElementById("learning-image-" + decision.reference_message_id);
      if (earlier) { earlier.scrollIntoView({ behavior: "smooth", block: "center" }); earlier.focus({ preventScroll: true }); }
      else setSelected(image);
    }}>View earlier image · {image.title}</button>}
    {Boolean(otherResources.length || result.teachers.length) && <div className="resource-section-heading"><h2>Explore further</h2></div>}
    {otherResources.length > 0 && <div className="resource-grid">{otherResources.map(resource => {
      const isVideo = resource.type === "video" || resource.type === "external_video";
      const Icon = resource.type === "audio" ? Headphones : isVideo || resource.type === "animation" ? Play : resource.type === "image" || resource.type === "diagram" ? ImageIcon : BookOpen;
      return <button className={"resource-card" + (isVideo ? " resource-video-button" : "")} key={resource.id} title={resource.title} aria-label={isVideo ? "Play video: " + resource.title : undefined} onClick={() => setSelected(resource)}>
        <span className="resource-icon"><Icon size={isVideo ? 17 : 23} fill={isVideo ? "currentColor" : "none"} aria-hidden="true" /></span>
        <span className="resource-card-copy"><strong>{resource.title}</strong>{!isVideo && <><span>{resource.description}</span><small>{resource.type}</small></>}</span>
      </button>;
    })}</div>}
    {result.teachers.length > 0 && <div className="resource-grid" aria-label="Subject-matched teachers">{result.teachers.map(teacher =>
      <article className="resource-card" key={teacher.id}>
        <span className="resource-icon"><UserRound size={23} aria-hidden="true" /></span>
        <span className="resource-card-copy"><strong>{teacher.name}</strong><span>{teacher.bio}</span>
          <small>{teacher.expertise.some(item => item.claim_status === "reviewed") ? "Reviewed" : "Declared"} subject expertise</small>
          {teacher.qualifications && <small>{teacher.qualifications}</small>}
          {teacher.languages.length > 0 && <small>{teacher.languages.join(", ")}</small>}</span>
      </article>)}</div>}
    {selected && <CatalogueViewer key={selected.id} resource={selected} sessionId={sessionId} onClose={() => setSelected(null)} />}
  </section>;
}
