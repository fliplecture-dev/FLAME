"use client";
import { useEffect, useRef, useState } from "react";
import { Image as ImageIcon } from "lucide-react";
import { b9Get } from "@/lib/api/b9-client";

/** Only static image thumbnails. Viewing a catalogue preview never acknowledges
 * a recommendation or creates an activity event; signed URLs stay local. */
export function ExploreThumbnail({ id, version, title, description, parameters, thumbnailUrl, video = false }: {
  id: string; version: number; title: string; description?: string | null; parameters: string; thumbnailUrl?: string | null; video?: boolean;
}) {
  const element = useRef<HTMLSpanElement>(null);
  const [url, setUrl] = useState("");
  useEffect(() => {
    let active = true, requested = false;
    setUrl(thumbnailUrl || "");
    if (thumbnailUrl) return; 
    const observer = new IntersectionObserver(entries => {
      if (!active || requested || !entries.some(entry => entry.isIntersecting)) return;
      requested = true;
      const query = new URLSearchParams(parameters);
      for (const key of ["offset", "limit", "kind", "search", "media_type", "focus_id"]) query.delete(key);
      query.set("version", String(version));
      if (video) query.set("thumbnail", "true");
      void b9Get<{ url: string; version: number; launch_mode: string }>(`resources/${id}/delivery?${query}`)
        .then(delivery => { if (active && delivery.version === version && delivery.launch_mode === "media") setUrl(delivery.url); })
        .catch(() => {});
    }, { root: element.current?.closest(".explore-scroll"), rootMargin: "60px" });
    if (element.current) observer.observe(element.current);
    return () => { active = false; observer.disconnect(); };
  }, [id, version, parameters, thumbnailUrl, video]);
  const alt = description && !/^(png|jpe?g|webp|image|diagram)\.?$/i.test(description.trim()) ? description : title;
  return <span ref={element} className="explore-thumbnail">{url ? <img src={url} alt={alt} referrerPolicy="no-referrer" onError={() => setUrl("")} /> : <ImageIcon size={20} aria-hidden="true" />}</span>;
}
