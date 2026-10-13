"use client";
import { useEffect, useRef, useState } from "react";
import { b4Mutation } from "@/lib/api/student-learning";

type Candidate = {
  curriculum_id: string; level_id: string; subject_id: string; domain_id: string;
  category_id: string | null; topic_id: string; subtopic_id: string;
  curriculum: string; level: string; subject: string; domain: string;
  topic: string; subtopic: string; revision: number;
};
type Clarification = {
  status: "clarification"; request_id: string; clarification_id: string;
  question: string; prompt: string; candidates: Candidate[]; expires_at: string;
};
type Ready = { status: "ready"; request_id: string; question: string; context: Candidate; answer_available: boolean };
type OutOfScope = { status: "out_of_scope"; request_id: string; message: string };
type Closed = { status: "cancelled" | "expired"; request_id: string; message: string };
type Result = Clarification | Ready | OutOfScope | Closed;
type TopicEvent = { id: string; question: string; status: string; response: Result; created_at: string };
type Page = { items: TopicEvent[]; next_cursor: string | null };

function pathLabel(candidate: Candidate) {
  return [candidate.curriculum, candidate.level, candidate.subject,
    candidate.domain, candidate.topic, candidate.subtopic].join(" / ");
}

async function historyPage(sessionId: string, cursor?: string): Promise<Page> {
  const query = cursor ? "?cursor=" + encodeURIComponent(cursor) : "";
  const response = await fetch("/api/b4/sessions/" + sessionId + "/topic-check/history" + query,
    { cache: "no-store" });
  if (!response.ok) throw new Error("Topic-check history could not be loaded.");
  return response.json();
}

export function TopicCheckPanel({ sessionId, mode }: { sessionId: string; mode: "study" | "curiosity" }) {
  const [question, setQuestion] = useState("");
  const requestKey = useRef<{ question: string; key: string } | null>(null);
  const [reply, setReply] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [history, setHistory] = useState<TopicEvent[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [historyNotice, setHistoryNotice] = useState("");

  useEffect(() => {
    let active = true;
    historyPage(sessionId).then(page => {
      if (active) { setHistory(page.items); setCursor(page.next_cursor); }
    }).catch(error => { if (active) setHistoryNotice(error instanceof Error ? error.message : "History unavailable."); });
    if (mode === "curiosity") {
      fetch("/api/b4/sessions/" + sessionId + "/topic-check", { cache: "no-store" })
        .then(async response => {
          if (!response.ok) throw new Error("Pending topic choice could not be loaded.");
          return response.json() as Promise<{ pending: Clarification | null }>;
        })
        .then(data => { if (active && data.pending) { setResult(data.pending); setQuestion(data.pending.question); } })
        .catch(error => { if (active) setNotice(error instanceof Error ? error.message : "Topic choice unavailable."); });
    }
    return () => { active = false; };
  }, [sessionId, mode]);

  async function refreshHistory() {
    try {
      const page = await historyPage(sessionId);
      setHistory(page.items); setCursor(page.next_cursor); setHistoryNotice("");
    } catch (error) { setHistoryNotice(error instanceof Error ? error.message : "History unavailable."); }
  }

  async function moreHistory() {
    if (!cursor || busy) return;
    try {
      const page = await historyPage(sessionId, cursor);
      setHistory(previous => [...previous, ...page.items.filter(item =>
        !previous.some(old => old.id === item.id))]);
      setCursor(page.next_cursor); setHistoryNotice("");
    } catch (error) { setHistoryNotice(error instanceof Error ? error.message : "History unavailable."); }
  }

  async function check(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    setBusy(true); setNotice("");
    try {
      const normalized = question.trim();
      const key = requestKey.current?.question === normalized ? requestKey.current.key : crypto.randomUUID();
      requestKey.current = { question: normalized, key };
      const next = await b4Mutation("sessions/" + sessionId + "/topic-check", "POST",
                                    { question: normalized }, key) as Result;
      requestKey.current = null;
      setResult(next); setReply("");
      await refreshHistory();
    } catch (error) { setNotice(error instanceof Error ? error.message : "Topic check failed."); }
    finally { setBusy(false); }
  }

  async function choose(choice: { subtopic_id: string } | { reply: string }) {
    if (!result || result.status !== "clarification" || busy) return;
    setBusy(true); setNotice("");
    try {
      const next = await b4Mutation(
        "sessions/" + sessionId + "/clarifications/" + result.clarification_id, "POST",
        { clarification_id: result.clarification_id, ...choice }) as Ready;
      setResult(next); setReply("");
      await refreshHistory();
    } catch (error) { setNotice(error instanceof Error ? error.message : "Topic choice failed. Try another choice or check the topic again."); }
    finally { setBusy(false); }
  }

  return <section className="topic-check-panel" aria-label="School topic check">
    <h3>Check a school topic</h3>
    <p>Choose a school topic before asking for an explanation.</p>
    <form onSubmit={event => void check(event)}>
      <label htmlFor={"topic-question-" + sessionId}>Question</label>
      <textarea id={"topic-question-" + sessionId} value={question} maxLength={4000}
        onChange={event => setQuestion(event.target.value)} rows={2} />
      <button type="submit" disabled={busy || !question.trim()}>Check topic</button>
    </form>
    {notice && <p role="alert">{notice}</p>}
    {result?.status === "out_of_scope" && <p role="status">{result.message}</p>}
    {result?.status === "ready" && <p role="status">Matched: {pathLabel(result.context)}. Return to your question and retry it to get an explanation.</p>}
    {(result?.status === "cancelled" || result?.status === "expired") && <p role="status">{result.message}</p>}
    {result?.status === "clarification" && <div aria-label="Choose a school topic">
      <p role="status">{result.prompt}</p>
      <p>Choice expires {new Date(result.expires_at).toLocaleString()}.</p>
      <ul>{result.candidates.map(candidate => <li key={candidate.subtopic_id}>
        <button type="button" disabled={busy}
          onClick={() => void choose({ subtopic_id: candidate.subtopic_id })}>
          {pathLabel(candidate)}
        </button>
      </li>)}</ul>
      <form onSubmit={event => { event.preventDefault(); void choose({ reply: reply.trim() }); }}>
        <label htmlFor={"topic-choice-" + sessionId}>Or describe which topic you mean</label>
        <input id={"topic-choice-" + sessionId} value={reply} maxLength={500}
          onChange={event => setReply(event.target.value)} />
        <button type="submit" disabled={busy || !reply.trim()}>Choose topic</button>
      </form>
    </div>}
    <div className="topic-check-history" aria-label="Recent topic checks">
      <h4>Recent topic checks</h4>
      {historyNotice && <p role="alert">{historyNotice}</p>}
      {history.length ? <ul>{history.map(item => <li key={item.id}>
        <strong>{item.question}</strong>
        <span>{item.status === "ready" && item.response.status === "ready"
          ? "Matched: " + pathLabel(item.response.context)
          : item.status === "out_of_scope" && item.response.status === "out_of_scope"
            ? item.response.message
            : item.status === "clarification" ? "Choose a school topic above."
              : item.response.status === "cancelled" || item.response.status === "expired"
                ? item.response.message : "Topic choice updated."}</span>
      </li>)}</ul> : <p>No topic checks yet.</p>}
      {cursor && <button type="button" onClick={() => void moreHistory()}>Older topic checks</button>}
    </div>
  </section>;
}
