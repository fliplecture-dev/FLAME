"use client";
import { useEffect, useId, useRef, useState } from "react";
import { ArrowUpRight, BookOpen, ChevronRight, Gamepad2, Headphones, Image as ImageIcon, Play, Sparkles, X } from "lucide-react";
import { approvedExperiences, resourceLabels, resourceUrl, type LearningResource } from "./learning-resources";

function ResourceBody({ resource }: { resource: LearningResource }) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  const src = "src" in resource ? resourceUrl(resource.src) : undefined;
  const embedded = resource.kind === "simulation" ? approvedExperiences[resource.experience] : undefined;
  const loadable = "src" in resource || resource.kind === "simulation";
  const invalid = loadable && !src && !embedded;
  const ready = () => setStatus("ready");
  const fail = () => setStatus("error");
  useEffect(() => {
    if (status !== "loading" || !loadable || invalid) return;
    const timer = setTimeout(() => setStatus("error"), 20000);
    return () => clearTimeout(timer);
  }, [status, loadable, invalid, attempt]);
  return <div className="resource-body">
    {loadable && <>
      {status === "loading" && !invalid && <p role="status" className="resource-status">Loading resource…</p>}
      {(status === "error" || invalid) && <div className="resource-status" role="alert"><p>This resource couldn’t load.</p>{!invalid && <button onClick={() => { setStatus("loading"); setAttempt(value => value + 1); }}>Try again</button>}</div>}
    </>}
    {src && status !== "error" && (resource.kind === "image" || resource.kind === "diagram") && <figure><img key={attempt} src={src} alt={resource.alt} onLoad={ready} onError={fail} /><figcaption>{resource.caption}</figcaption></figure>}
    {src && status !== "error" && (resource.kind === "video" || resource.kind === "animation" || resource.kind === "audio") && <>
      {resource.kind === "audio" ? <audio key={attempt} controls preload="metadata" src={src} onLoadedMetadata={ready} onError={fail} aria-label={resource.title} /> : <video key={attempt} controls playsInline preload="metadata" src={src} onLoadedMetadata={ready} onError={fail} aria-label={resource.title}>{resource.captionsSrc && resourceUrl(resource.captionsSrc) && <track kind="captions" src={resourceUrl(resource.captionsSrc)} srcLang="en" label="English" default />}</video>}
    </>}
    {(resource.kind === "audio" || resource.kind === "video" || resource.kind === "animation") && resource.transcript && <details className="resource-transcript"><summary>Read transcript</summary><p>{resource.transcript}</p></details>}
    {embedded && status !== "error" && <iframe key={attempt} title={resource.title} src={embedded} sandbox="allow-scripts" onLoad={ready} onError={fail} />}
    {"details" in resource && <><ol className="resource-details">{resource.details.map((detail, index) => <li key={index}>{detail}</li>)}</ol>{resource.href && resourceUrl(resource.href) && <a className="resource-external" href={resourceUrl(resource.href)} target="_blank" rel="noopener noreferrer">Visit resource (new tab)<ArrowUpRight size={16} aria-hidden="true" /></a>}</>}
  </div>;
}

function ResourceViewer({ resource, onClose }: { resource: LearningResource; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const element = dialog.current;
    element?.showModal();
    return () => {
      element?.querySelectorAll("audio, video").forEach(node => (node as HTMLMediaElement).pause());
      element?.close();
      if (previous?.isConnected) previous.focus({ preventScroll: true });
    };
  }, []);
  return <dialog ref={dialog} className="resource-dialog" aria-labelledby={titleId} onKeyDown={event => {
    if (event.key !== "Tab") return;
    const elements = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], summary, audio[controls], video[controls], iframe, [tabindex="0"]')).filter(node => node.getClientRects().length > 0);
    const first = elements[0], last = elements.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }} onCancel={event => { event.preventDefault(); onClose(); }}>
    <header className="resource-dialog-header"><div><span>{resourceLabels[resource.kind]}</span><h2 id={titleId}>{resource.title}</h2></div><button autoFocus className="resource-close" aria-label="Close resource" onClick={onClose}><X size={20} aria-hidden="true" /></button></header>
    <div className="resource-dialog-scroll"><p className="resource-description">{resource.description}</p><ResourceBody resource={resource} /></div>
  </dialog>;
}

export function ResourceRecommendations({ resources }: { resources: LearningResource[] }) {
  const [selected, setSelected] = useState<LearningResource | null>(null);
  const [expanded, setExpanded] = useState(false);
  if (!resources.length) return null;
  return <section className="resource-recommendations" aria-label="Recommended resources">
    <div className="resource-section-heading"><h2><Sparkles size={18} aria-hidden="true" />Recommended for you</h2>{resources.length > 3 && <button aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? "Show less" : "Explore more"}<ChevronRight size={15} aria-hidden="true" /></button>}</div>
    <div className="resource-grid">{(expanded ? resources : resources.slice(0, 3)).map(resource => {
      const Icon = resource.kind === "audio" ? Headphones : resource.kind === "simulation" ? Gamepad2 : resource.kind === "video" || resource.kind === "animation" ? Play : resource.kind === "image" || resource.kind === "diagram" ? ImageIcon : BookOpen;
      return <button className={`resource-card resource-${resource.kind}`} key={resource.id} onClick={() => setSelected(resource)}><span className="resource-icon"><Icon size={23} aria-hidden="true" /></span><span className="resource-card-copy"><strong>{resource.title}</strong><span>{resource.description}</span><small>{resource.meta ?? resourceLabels[resource.kind]}</small></span><ChevronRight size={16} aria-hidden="true" /></button>;
    })}</div>
    {selected && <ResourceViewer key={selected.id} resource={selected} onClose={() => setSelected(null)} />}
  </section>;
}


