import { ArrowUp, ImagePlus, LoaderCircle, Mic, Paperclip, Square, X } from "lucide-react";
import { useLayoutEffect, useRef } from "react";
import { AttachmentList } from "./attachment-list";
import { FILE_ACCEPT, IMAGE_ACCEPT, type PromptAttachment } from "./prompt-attachments";
import { useAudioRecorder } from "./use-audio-recorder";
import { ResponseLanguagePicker } from "./response-language-picker";
import type { ResponseLanguage } from "./response-languages";
export function FlamePromptInput({ topicName, value, pending, attachments, attachmentNotice, onValueChange, onFiles, onRemoveAttachment, onSubmit, responseLanguage = "en", onResponseLanguageChange = () => {} }: {
  topicName?: string; value: string; pending: boolean; attachments: PromptAttachment[]; attachmentNotice: string;
  onValueChange: (value: string) => void; onFiles: (files: File[]) => void; onRemoveAttachment: (id: string) => void; onSubmit: () => void;
  responseLanguage?: ResponseLanguage; onResponseLanguageChange?: (value: ResponseLanguage) => void;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  const files = useRef<HTMLInputElement>(null);
  const images = useRef<HTMLInputElement>(null);
  const audio = useAudioRecorder(file => onFiles([file]));
  const recordingBusy = audio.state !== "idle";
  const canSend = !pending && !recordingBusy && Boolean(value.trim() || attachments.length);
  useLayoutEffect(() => {
    const el = input.current; if (!el) return;
    function resize() { if (!el) return; el.style.height = "auto"; el.style.height = `${Math.min(el.scrollHeight, 160)}px`; }
    resize();
    const observer = new ResizeObserver(entries => { if (entries[0].contentRect.width !== previousWidth) { previousWidth = entries[0].contentRect.width; resize(); } });
    let previousWidth = el.clientWidth; observer.observe(el);
    return () => observer.disconnect();
  }, [value]);
  function pick(selected: FileList | null) { if (selected) onFiles(Array.from(selected)); input.current?.focus(); }
  return <div className="composer-area">
    <div className="composer-feedback" aria-live="polite">{attachmentNotice && <p>{attachmentNotice}</p>}{audio.notice && <p>{audio.notice}</p>}</div>
    <form className="prompt-form" onSubmit={e => { e.preventDefault(); if (canSend) onSubmit(); }}>
      <AttachmentList attachments={attachments} onRemove={onRemoveAttachment} />
      <label className="sr-only" htmlFor="flame-prompt">Ask FLAME a question or learning request</label>
      <textarea ref={input} id="flame-prompt" placeholder={topicName ? `Ask FLAME anything about ${topicName}…` : "Ask FLAME anything…"} value={value} maxLength={4000} rows={1} onChange={e => onValueChange(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && !window.matchMedia("(pointer: coarse)").matches) { e.preventDefault(); if (canSend) onSubmit(); } }} />
      {recordingBusy && <div className="recording-status"><span role="status">{audio.state === "requesting" ? "Waiting for microphone permission…" : audio.state === "saving" ? "Attaching audio…" : `Recording ${Math.floor(audio.seconds / 60)}:${String(audio.seconds % 60).padStart(2, '0')}`}</span>{audio.state === "recording" && <button type="button" onClick={() => audio.stop()}><Square size={14} aria-hidden="true" />Stop & attach</button>}{audio.state !== "saving" && <button type="button" aria-label="Cancel recording" onClick={() => audio.stop(true)}><X size={15} /></button>}</div>}
      <div className="prompt-toolbar"><div className="prompt-tools">
        <input ref={files} type="file" multiple accept={FILE_ACCEPT} hidden aria-label="Choose attachments" onChange={e => { pick(e.target.files); e.target.value = ""; }} />
        <input ref={images} type="file" multiple accept={IMAGE_ACCEPT} hidden aria-label="Choose images" onChange={e => { pick(e.target.files); e.target.value = ""; }} />
        <button className="icon-button" type="button" aria-label="Attach files" title="Attach files (up to 5, 10 MB each)" onClick={() => files.current?.click()}><Paperclip size={19} /></button>
        <button className="icon-button" type="button" aria-label="Attach images" title="Attach images" onClick={() => images.current?.click()}><ImagePlus size={19} /></button>
        <button className="icon-button" type="button" aria-label="Record audio" title="Record audio (up to 2 minutes)" disabled={recordingBusy || pending || attachments.length >= 5} onClick={() => void audio.start()}><Mic size={19} /></button>
        <ResponseLanguagePicker value={responseLanguage} disabled={pending || recordingBusy} onChange={onResponseLanguageChange} />
      </div><span className="prompt-shortcut">Shift + Enter for a new line</span><button className="send-button" type="submit" disabled={!canSend} aria-label={pending ? "Sending request" : "Send learning request"}>{pending ? <LoaderCircle size={19} aria-hidden="true" /> : <ArrowUp size={20} aria-hidden="true" />}</button></div>
    </form><div className="composer-caption"><span>{recordingBusy ? "Switching topics stops and saves active recording to this topic." : "Files and voice notes stay in this tab until processing is connected."}</span></div>
  </div>;
}
