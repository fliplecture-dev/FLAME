import { BookOpen, Lightbulb, ChevronDown } from "lucide-react";
import { useEffect, useRef } from "react";
export type LearningMode = "study" | "curiosity";
export function ModeSwitcher({ mode, onChange, variant = "tabs" }: { mode: LearningMode; onChange: (mode: LearningMode) => void; variant?: "tabs" | "brand" }) {
  const menu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const outside = (event: PointerEvent) => { if (menu.current && !menu.current.contains(event.target as Node)) menu.current.open = false; };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  return <div className={variant === "brand" ? "flame-mode-brand" : "mode-switcher"} role="group" aria-label="Learning mode">
    {variant === "tabs" ? <><button type="button" aria-pressed={mode === "study"} onClick={() => onChange("study")}><BookOpen size={18} aria-hidden="true" />Study</button>
    <button type="button" aria-pressed={mode === "curiosity"} onClick={() => onChange("curiosity")}><Lightbulb size={18} aria-hidden="true" />Curiosity</button></> : <details ref={menu} className="mode-dropdown" onKeyDown={event => {
      if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); if (menu.current) menu.current.open = false; menu.current?.querySelector("summary")?.focus(); }
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault(); if (menu.current) menu.current.open = true;
        const options = Array.from(menu.current?.querySelectorAll<HTMLButtonElement>('button') ?? []);
        const index = options.indexOf(document.activeElement as HTMLButtonElement);
        options[event.key === "Home" ? 0 : event.key === "End" ? options.length - 1 : index < 0 ? event.key === "ArrowUp" ? options.length - 1 : 0 : (index + (event.key === "ArrowUp" ? -1 : 1) + options.length) % options.length]?.focus();
      }
    }}><summary aria-label="FLAME learning mode" title="Choose Study or Curiosity"><span>FLAME</span><ChevronDown size={15} aria-hidden="true" /></summary><div className="mode-dropdown-menu" role="menu" aria-label="Choose learning mode">
      <button type="button" role="menuitemradio" aria-checked={mode === "study"} onClick={() => { onChange("study"); if (menu.current) menu.current.open = false; menu.current?.querySelector("summary")?.focus(); }}><BookOpen size={17} />Study</button>
      <button type="button" role="menuitemradio" aria-checked={mode === "curiosity"} onClick={() => { onChange("curiosity"); if (menu.current) menu.current.open = false; menu.current?.querySelector("summary")?.focus(); }}><Lightbulb size={17} />Curiosity</button>
    </div></details>}
  </div>;
}
