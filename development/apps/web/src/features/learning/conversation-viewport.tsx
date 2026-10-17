import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { ArrowDown } from "lucide-react";
import { useLearningConversations } from "./use-learning-conversations";
export function ConversationViewport({ sessionId, children }: { sessionId: string; children: ReactNode }) {
  const viewport = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const { viewportPositions: positions } = useLearningConversations();
  const follow = useRef(true);
  const [away, setAway] = useState(false);
  useLayoutEffect(() => {
    const el = viewport.current!;
    el.scrollTop = positions.current.get(sessionId) ?? 0;
    follow.current = el.scrollHeight - el.clientHeight - el.scrollTop < 80;
    setAway(!follow.current);
    const observer = new ResizeObserver(() => {
      if (follow.current) el.scrollTop = el.scrollHeight;
      setAway(el.scrollHeight - el.clientHeight - el.scrollTop >= 80);
    });
    observer.observe(content.current!);
    return () => observer.disconnect();
  }, [sessionId]);
  return <div className="conversation-region"><div ref={viewport} className="workspace-scroll" onScroll={() => {
    const el = viewport.current!; positions.current.set(sessionId, el.scrollTop);
    follow.current = el.scrollHeight - el.clientHeight - el.scrollTop < 80; setAway(!follow.current);
  }}><div ref={content} className="reading-column">{children}</div></div>{away && <button className="latest-message" onClick={() => { follow.current = true; viewport.current?.scrollTo({ top: viewport.current.scrollHeight, behavior: "instant" }); setAway(false); }}><ArrowDown size={15} aria-hidden="true" />Jump to latest</button>}</div>;
}

