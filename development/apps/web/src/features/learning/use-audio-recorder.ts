import { useEffect, useRef, useState } from "react";
import { MAX_FILE_BYTES } from "./prompt-attachments";
export function useAudioRecorder(onFile: (file: File) => void) {
  const [state, setState] = useState<"idle" | "requesting" | "recording" | "saving">("idle");
  const [seconds, setSeconds] = useState(0);
  const [notice, setNotice] = useState("");
  const mounted = useRef(true);
  const fileCallback = useRef(onFile); fileCallback.current = onFile;
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const generation = useRef(0);
  const discard = useRef(false);
  const starting = useRef(false);
  function release() {
    if (timer.current) clearInterval(timer.current); timer.current = null;
    stream.current?.getTracks().forEach(track => track.stop()); stream.current = null;
  }
  function stop(cancel = false) {
    generation.current++; starting.current = false;
    if (recorder.current?.state === "recording" || !recorder.current) discard.current = cancel;
    if (recorder.current && recorder.current.state !== "inactive") {
      if (mounted.current) setState("saving");
      recorder.current.stop(); release();
    } else { release(); if (mounted.current) setState("idle"); }
  }
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; stop(false); }; }, []);
  async function start() {
    if (starting.current || recorder.current?.state === "recording") return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") { setNotice("Audio recording isn’t supported here. Try a supported browser on localhost or HTTPS, or attach an audio file."); return; }
    starting.current = true; const token = ++generation.current;
    setNotice(""); setSeconds(0); setState("requesting"); discard.current = false;
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current || token !== generation.current) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current = media;
      const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find(type => MediaRecorder.isTypeSupported(type));
      const recording = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
      recorder.current = recording;
      const chunks: Blob[] = []; let bytes = 0;
      recording.ondataavailable = e => { if (e.data.size) { chunks.push(e.data); bytes += e.data.size; if (bytes >= MAX_FILE_BYTES && recording.state === "recording") stop(); } };
      recording.onerror = () => { discard.current = true; if (mounted.current) setNotice("Recording failed. Check your microphone and try again."); stop(true); };
      recording.onstop = () => {
        release(); recorder.current = null;
        if (!discard.current && chunks.length) {
          const type = recording.mimeType || chunks[0].type || "audio/webm";
          const ext = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
          fileCallback.current(new File(chunks, `Voice note ${new Date().toISOString().replace(/[:.]/g, '-')}.${ext}`, { type }));
        } else if (!discard.current && mounted.current) setNotice("No audio was captured. Try recording again.");
        if (mounted.current) setState("idle");
      };
      recording.start(250); starting.current = false; setState("recording");
      const began = Date.now();
      timer.current = setInterval(() => { const elapsed = Math.floor((Date.now() - began) / 1000); if (mounted.current) setSeconds(elapsed); if (elapsed >= 120) { if (mounted.current) setNotice("The 2-minute recording limit was reached. Your audio has been attached."); stop(); } }, 250);
    } catch (error) {
      if (!mounted.current || token !== generation.current) return;
      release(); starting.current = false;
      setState("idle");
      const name = error instanceof DOMException ? error.name : "";
      setNotice(name === "NotAllowedError" ? "Microphone permission was denied. Allow microphone access in your browser and try again." : name === "NotFoundError" ? "No microphone was found. Connect a microphone or attach an audio file." : "The microphone couldn’t start. It may be busy in another app. Please try again.");
    }
  }
  return { state, seconds, notice, start, stop };
}
