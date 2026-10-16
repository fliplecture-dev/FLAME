"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { themePreferenceKey } from "@/lib/theme";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const system = window.matchMedia("(prefers-color-scheme: dark)");
    function sync() {
      let saved: string | null = null;
      try { saved = localStorage.getItem(themePreferenceKey); } catch { /* Theme still works without storage. */ }
      const next = saved === "dark" || saved !== "light" && system.matches;
      document.documentElement.dataset.theme = next ? "dark" : "light";
      setDark(next);
    }
    const storage = (event: StorageEvent) => { if (event.key === themePreferenceKey || event.key === null) sync(); };
    sync();
    system.addEventListener("change", sync);
    window.addEventListener("storage", storage);
    return () => { system.removeEventListener("change", sync); window.removeEventListener("storage", storage); };
  }, []);
  const label = dark ? "Switch to light mode" : "Switch to dark mode";
  return <button type="button" className="icon-button theme-toggle" aria-label={label} title={label} aria-pressed={dark} onClick={() => {
    const next = !dark;
    document.documentElement.dataset.theme = next ? "dark" : "light";
    setDark(next);
    try { localStorage.setItem(themePreferenceKey, next ? "dark" : "light"); } catch { /* Keep the choice for this page. */ }
  }}>{dark ? <Sun size={20} aria-hidden="true" /> : <Moon size={20} aria-hidden="true" />}</button>;
}
