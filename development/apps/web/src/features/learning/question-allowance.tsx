"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ensureGuestAccess } from "@/lib/api/guest-access";
type Usage = { limit: number | null; used: number; remaining: number | null; resets_at: string; timezone: string };
export function QuestionAllowance({ guest = false, onSignIn }: { guest?: boolean; onSignIn?: () => boolean }) {
  const [usage,setUsage] = useState<Usage | null>(null);
  useEffect(() => {
    let active = true, generation = 0;
    async function refresh() {
      const current = ++generation;
      try {
        if (guest) await ensureGuestAccess();
        const response = await fetch(guest ? "/api/guest/usage" : "/api/b4/me/usage", { cache: "no-store" });
        if (!response.ok) return;
        const result = await response.json();
        if (active && current === generation && typeof result.used === "number" && (typeof result.limit === "number" || result.limit === null)) setUsage(result);
      } catch { /* A counter failure must not hide the question or answer. */ }
    }
    void refresh();window.addEventListener("flame:usage-updated",refresh);window.addEventListener("focus",refresh);
    return () => {active=false;window.removeEventListener("flame:usage-updated",refresh);window.removeEventListener("focus",refresh);};
  },[guest]);
  useEffect(() => {
    if (!usage?.resets_at) return;
    const reset = Date.parse(usage.resets_at);
    if (!Number.isFinite(reset)) return;
    const timer = window.setTimeout(() => window.dispatchEvent(new Event("flame:usage-updated")), Math.max(1000, reset-Date.now()+500));
    return () => window.clearTimeout(timer);
  }, [usage?.resets_at]);
  return <div className="question-allowance" role="status">
    <span>{usage ? usage.limit === null ? "Administrator access" : `${usage.remaining} of ${usage.limit} questions left today` : guest ? "10 Curiosity questions per day" : "25 questions per day"}. <span>Resets at midnight India time.</span></span>
    {guest && <Link href="/sign-in?next=%2Fflame" onClick={event=>{if(onSignIn&&!onSignIn())event.preventDefault();}}>Sign in for 25 questions and Study</Link>}
  </div>;
}
