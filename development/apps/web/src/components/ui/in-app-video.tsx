"use client";
import { useEffect, useRef, useState } from "react";

/** Native licensed-media player: no provider links, downloads or sharing UI. */
export function InAppVideo({src,title,poster,onPlay,onError,onClose}:{src:string;poster?:string|null;title:string;onPlay?:()=>void;onError?:()=>void;onClose?:()=>void}) {
  const panel=useRef<HTMLDivElement>(null), video=useRef<HTMLVideoElement>(null);
  const [playing,setPlaying]=useState(false),[fullscreen,setFullscreen]=useState(false),[position,setPosition]=useState(0),[duration,setDuration]=useState(0),[error,setError]=useState("");
  useEffect(()=>{const element=video.current;const update=()=>setFullscreen(document.fullscreenElement===panel.current);document.addEventListener("fullscreenchange",update);return()=>{document.removeEventListener("fullscreenchange",update);element?.pause();};},[]);
  useEffect(()=>{setError("");setPlaying(false);setPosition(0);setDuration(0);},[src]);
  async function toggle(){if(!video.current)return;try{if(video.current.paused)await video.current.play();else video.current.pause();}catch{setError("Playback could not start. Try Play again.");}}
  async function expand(){try{if(fullscreen)await document.exitFullscreen();else await panel.current?.requestFullscreen();}catch{setError("Fullscreen is unavailable in this browser. Playback stays in FLAME.");}}
  return <div ref={panel} className="flame-video-player" aria-label={title+" player"}>
    <video ref={video} src={src} poster={poster||undefined} playsInline preload="metadata" disablePictureInPicture disableRemotePlayback aria-label={title}
      onPlay={()=>{setPlaying(true);onPlay?.();}} onPause={()=>setPlaying(false)} onEnded={()=>setPlaying(false)} onTimeUpdate={()=>setPosition(video.current?.currentTime||0)}
      onLoadedMetadata={()=>setDuration(Number.isFinite(video.current?.duration)?video.current!.duration:0)} onError={()=>{setError("Video could not load. Close the player or retry without leaving FLAME.");onError?.();}}/>
    <div className="flame-video-controls"><button onClick={()=>void toggle()} aria-label={playing?"Pause video":"Play video"}>{playing?"Pause":"Play"}</button>
      <label>Position<input type="range" min="0" max={duration||0} step="0.1" value={Math.min(position,duration)} disabled={!duration} onChange={e=>{if(video.current)video.current.currentTime=Number(e.target.value);setPosition(Number(e.target.value));}}/></label>
      <label>Volume<input type="range" min="0" max="1" step="0.05" defaultValue="1" onChange={e=>{if(video.current)video.current.volume=Number(e.target.value);}}/></label>
      <button onClick={()=>void expand()} aria-label={fullscreen?"Exit fullscreen":"Enter fullscreen"}>{fullscreen?"Exit fullscreen":"Fullscreen"}</button>
      {onClose&&<button onClick={()=>{video.current?.pause();onClose();}}>Close player</button>}
    </div>{error&&<p role="alert">{error}</p>}
  </div>;
}
