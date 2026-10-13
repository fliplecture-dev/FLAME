"use client";
import { useState } from "react";
import { ExternalVideoPlayer } from "./external-video-player";
export type ExternalVideoInfo = { provider:string; provider_name:string; video_id:string; canonical_url:string; title:string; description?:string; thumbnail_url:string|null; verification:string; student_playback_allowed:boolean; playback_reason:string };
export const resourceTypes=["image","video","interactive"];
export const resourceFamily=(type:string)=>({diagram:"image",animation:"video",external_video:"video"} as Record<string,string>)[type]??type;
export const resourceTypeLabel=(type:string)=>({image:"Image",video:"Video",interactive:"Interactive"} as Record<string,string>)[resourceFamily(type)]??type;
export function ExternalVideoSummary({info,description}:{info?:ExternalVideoInfo|null;description?:string}) {
  const [imageFailed,setImageFailed]=useState(false);
  const embed=info?.provider==="youtube"&&/^[A-Za-z0-9_-]{11}$/.test(info.video_id)?"https://www.youtube.com/embed/"+info.video_id:info?.provider==="vimeo"&&/^[1-9][0-9]{0,11}$/.test(info.video_id)?"https://player.vimeo.com/video/"+info.video_id:"";
  return <section className="external-video-summary" aria-label="External video preview">
    {info?.thumbnail_url&&!imageFailed&&<img src={info.thumbnail_url} alt={description||info.title+" video thumbnail"} referrerPolicy="no-referrer" onError={()=>setImageFailed(true)}/>}
    {info&&<p><strong>Source: {info.provider_name}</strong> · Video ID: {info.video_id}</p>}
    {info&&<p>Provider metadata checked. No API key is required. Embedding availability is checked by the player when opened.</p>}
    {embed?<ExternalVideoPlayer url={embed} title={info?.title||description||"External video"}/>:<p>Enter a YouTube or public Vimeo video URL, then validate or save to preview.</p>}
    <p>Publish explicitly after completing rights and accessibility details. Published videos appear to learners through valid curriculum mappings.</p>
  </section>;
}
