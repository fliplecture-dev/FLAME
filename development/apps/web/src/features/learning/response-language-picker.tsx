"use client";
import { ChevronDown, Languages } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { responseLanguages, type ResponseLanguage } from "./response-languages";

export function ResponseLanguagePicker({ value, disabled, onChange }: { value: ResponseLanguage; disabled: boolean; onChange: (value: ResponseLanguage) => void }) {
  const [open, setOpen] = useState(false), id = useId();
  const root = useRef<HTMLDivElement>(null), trigger = useRef<HTMLButtonElement>(null);
  const selected = responseLanguages.find(language => language.code === value);
  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLButtonElement>('[aria-pressed="true"]')?.focus();
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  function choose(language: ResponseLanguage) { onChange(language); setOpen(false); trigger.current?.focus(); }
  return <div className="response-language-picker" ref={root} onKeyDown={event => {
    if (event.key === "Escape" && open) { event.preventDefault(); event.stopPropagation(); setOpen(false); trigger.current?.focus(); }
  }}>
    <button ref={trigger} type="button" className="response-language-trigger" disabled={disabled}
      aria-label={`Answer language: ${selected?.name ?? "English"}`} title="Choose the language for FLAME’s answers"
      aria-expanded={open} aria-controls={id} onClick={() => setOpen(value => !value)}>
      <Languages size={17} aria-hidden="true" /><span>{selected?.native ?? "English"}</span><ChevronDown size={13} aria-hidden="true" />
    </button>
    {open && !disabled && <div id={id} className="response-language-options" role="group" aria-label="Choose answer language">
      <p>Answer language</p>
      <div className="response-language-list">
        {responseLanguages.map(language => <button key={language.code} type="button" aria-pressed={value === language.code}
          aria-label={language.name} onClick={() => choose(language.code)}>
          <span lang={language.code} dir="auto">{language.native}</span><small>{language.name}</small>
        </button>)}
      </div>
    </div>}
  </div>;
}
