"use client";
import { useEffect, useRef, useState } from "react";

type Player = { playVideo?:()=>void; pauseVideo?:()=>void; destroy?:()=>void; play?:()=>Promise<void>; pause?:()=>Promise<void>; unload?:()=>Promise<void>; ready?:()=>Promise<void>; on?:(event:string,handler:()=>void)=>void };
type ProviderWindow = { YT?:{Player:new(element:HTMLIFrameElement,config:unknown)=>Player}; Vimeo?:{Player:new(element:HTMLIFrameElement)=>Player}; onYouTubeIframeAPIReady?:()=>void };
let youtubeReady:Promise<void>|null=null, vimeoReady:Promise<void>|null=null;
function sdk(provider:string){
  const target=window as unknown as ProviderWindow;
  if(provider==="youtube"){
    if(target.YT?.Player)return Promise.resolve();
    return youtubeReady??=new Promise<void>((resolve,reject)=>{const previous=target.onYouTubeIframeAPIReady;target.onYouTubeIframeAPIReady=()=>{previous?.();resolve();};const script=document.createElement("script");script.src="https://www.youtube.com/iframe_api";script.onerror=()=>{youtubeReady=null;reject(new Error("Player could not load."));};document.head.appendChild(script);});
  }
  if(target.Vimeo?.Player)return Promise.resolve();
  return vimeoReady??=new Promise<void>((resolve,reject)=>{const script=document.createElement("script");script.src="https://player.vimeo.com/api/player.js";script.onload=()=>resolve();script.onerror=()=>{vimeoReady=null;reject(new Error("Player could not load."));};document.head.appendChild(script);});
}
export function validatedEmbed(raw:string){
  try{const u=new URL(raw);if(u.protocol!=="https:"||u.username||u.password||u.port)return null;
    if(u.hostname==="www.youtube.com"&&/^\/embed\/[A-Za-z0-9_-]{11}$/.test(u.pathname))return {provider:"youtube",url:"https://www.youtube.com"+u.pathname+"?enablejsapi=1&playsinline=1&rel=0"};
    if(u.hostname==="player.vimeo.com"&&/^\/video\/[1-9][0-9]{0,11}$/.test(u.pathname))return {provider:"vimeo",url:"https://player.vimeo.com"+u.pathname+"?title=0&byline=0&portrait=0"};
  }catch{}return null;
}
export function ExternalVideoPlayer({url,title,onClose,onPlay}:{url:string;title:string;onClose?:()=>void;onPlay?:()=>void}){
  const frame=useRef<HTMLIFrameElement>(null),panel=useRef<HTMLDivElement>(null),player=useRef<Player|null>(null),playHandler=useRef(onPlay);playHandler.current=onPlay;
  const [attempt,setAttempt]=useState(0),[ready,setReady]=useState(false),[error,setError]=useState(""),[fullscreen,setFullscreen]=useState(false),[origin,setOrigin]=useState("");
  const embed=validatedEmbed(url);
  useEffect(()=>setOrigin(window.location.origin),[]);
  useEffect(()=>{if(!embed||!origin)return;let active=true;setReady(false);setError("");const timer=setTimeout(()=>{if(active)setError("Video is taking too long to load. Retry, or close and continue your conversation.");},20000);
    const loaded=()=>{if(active){clearTimeout(timer);setReady(true);setError("");}};
    const failed=()=>{if(active){clearTimeout(timer);setReady(false);setError("Video is unavailable, restricted or cannot be embedded. Retry or choose another resource. FLAME will not redirect you.");}};
    sdk(embed.provider).then(()=>{if(!active||!frame.current)return;const target=window as unknown as ProviderWindow;
      if(embed.provider==="youtube")player.current=new target.YT!.Player(frame.current,{events:{onReady:loaded,onError:failed,onStateChange:(event:{data:number})=>{if(event.data===1)playHandler.current?.();}}});
      else{const instance=new target.Vimeo!.Player(frame.current);player.current=instance;instance.on?.("error",failed);instance.on?.("play",()=>playHandler.current?.());instance.ready?.().then(loaded).catch(failed);}
    }).catch(failed);
    return()=>{active=false;clearTimeout(timer);player.current?.pauseVideo?.();void player.current?.pause?.().catch(()=>{});player.current=null;};
  },[url,attempt,origin]);
  useEffect(()=>{const update=()=>setFullscreen(document.fullscreenElement===panel.current);document.addEventListener("fullscreenchange",update);return()=>document.removeEventListener("fullscreenchange",update);},[]);
  async function expand(){try{if(fullscreen)await document.exitFullscreen();else await panel.current?.requestFullscreen();}catch{setError("Fullscreen is unavailable in this browser. Use the player controls or stay in FLAME's viewer.");}}
  if(!embed)return <p role="alert">This video provider or embed URL is not supported.</p>;
  return <div ref={panel} className="flame-external-player" aria-label={title+" player"}>
    {origin&&<iframe key={attempt} ref={frame} title={title} src={embed.url+(embed.provider==="youtube"?"&origin="+encodeURIComponent(origin):"")} referrerPolicy="strict-origin-when-cross-origin" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" allowFullScreen onError={()=>setError("Video player could not load. Retry without leaving FLAME.")}/>}
    {!ready&&!error&&<p role="status">Loading video…</p>}
    <div className="flame-video-controls"><button disabled={!ready} onClick={()=>{player.current?.playVideo?.();void player.current?.play?.().catch(()=>setError("Playback could not start. Try the provider's Play control."));}}>Play video</button><button disabled={!ready} onClick={()=>{player.current?.pauseVideo?.();void player.current?.pause?.().catch(()=>{});}}>Pause video</button><button onClick={()=>void expand()}>{fullscreen?"Exit fullscreen":"Fullscreen"}</button>{onClose&&<button onClick={onClose}>Close player</button>}</div>
    {error&&<div role="alert"><p>{error}</p><button onClick={()=>setAttempt(n=>n+1)}>Retry video</button></div>}
    <p className="external-video-notice">Provider branding or links may open the provider site.</p>
  </div>;
}
