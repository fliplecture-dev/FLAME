"use client";
import { useEffect, useState } from "react";
import { useExplore } from "./explore-context";

type Counts = { videos: number; images: number; interactives: number };
export function AnswerExploreResources({ sessionId, messageId }: { sessionId: string; messageId: string }) {
  const explore = useExplore(), enabled = Boolean(explore);
  const [summary, setSummary] = useState<{ key: string; counts: Counts } | null>(null);
  const key = `${sessionId}/${messageId}`;
  useEffect(() => {
    if (!enabled) return;
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 15000);
    void fetch(`/api/b9/explore/summary?session_id=${encodeURIComponent(sessionId)}&message_id=${encodeURIComponent(messageId)}`, { cache: "no-store", signal: abort.signal })
      .then(async response => {
        if (!response.ok) return;
        const counts = await response.json();
        if (!abort.signal.aborted && ["videos", "images", "interactives"].every(name => Number.isSafeInteger(counts?.[name]) && counts[name] >= 0)) setSummary({ key, counts });
      }).catch(() => { /* Missing/unavailable catalogue counts do not distract from the answer. */ })
      .finally(() => clearTimeout(timer));
    return () => { abort.abort(); clearTimeout(timer); };
  }, [sessionId, messageId, key, enabled]);
  if (!explore || summary?.key !== key) return null;
  const { videos, images, interactives } = summary.counts;
  const label = [videos ? `${videos} ${videos === 1 ? "video" : "videos"}` : "", images ? `${images} ${images === 1 ? "image" : "images"}` : "", interactives ? `${interactives} ${interactives === 1 ? "interactive" : "interactives"}` : ""].filter(Boolean).join(" · ");
  return label ? <button className="explore-answer-link" aria-label={`Explore resources: ${label}`} onClick={() => void explore.fromAnswer(sessionId, messageId)}>{label}</button> : null;
}
