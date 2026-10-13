"use client";
import { useEffect, useRef, useState } from "react";

/** Original GIF for playback; canvas holds a still frame without rewriting media. */
export function AnimatedMedia({ src, description, caption, onLoad, onError }: {
  src: string; description: string; caption?: string | null; onLoad?: () => void; onError?: () => void;
}) {
  const image = useRef<HTMLImageElement>(null), canvas = useRef<HTMLCanvasElement>(null);
  const [playing, setPlaying] = useState(false), [ready, setReady] = useState(false);
  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPlaying(!motion.matches);
    const change = () => { if (motion.matches) setPlaying(false); };
    motion.addEventListener("change", change); return () => motion.removeEventListener("change", change);
  }, [src]);
  function freeze() {
    const img = image.current, frame = canvas.current;
    if (!img || !frame || !img.naturalWidth) return;
    frame.width = img.naturalWidth; frame.height = img.naturalHeight;
    frame.getContext("2d")?.drawImage(img, 0, 0);
  }
  return <figure className="animated-media" data-playing={playing ? "true" : "false"}>
    <img ref={image} src={src} alt={description} hidden={!playing} onLoad={() => { freeze(); setReady(true); onLoad?.(); }} onError={onError} />
    <canvas ref={canvas} hidden={playing} role="img" aria-label={description} />
    <figcaption>{caption && <span>{caption}</span>}<button type="button" disabled={!ready} aria-label={playing ? "Pause animation" : "Play animation"} aria-pressed={playing}
      onClick={() => { if (playing) freeze(); setPlaying(value => !value); }}>{playing ? "Pause" : "Play"} animation</button></figcaption>
  </figure>;
}
