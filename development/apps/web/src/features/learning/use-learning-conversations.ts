import { useEffect, useRef, useState } from "react";
import { LearningApiError, sendLearningRequest, type LearningRequest } from "@/lib/api/student-learning";
import { attachmentKind, validateAttachments } from "./prompt-attachments";
import { emptySession, type ConversationSession, type ConversationTurn } from "./conversation-types";
export function useLearningConversations(live = false) {
  const [sessions, setSessions] = useState<Record<string, ConversationSession>>({});
  const current = useRef(sessions);
  const busy = useRef(new Set<string>());
  const mounted = useRef(true);
  const requests = useRef(new Map<string, LearningRequest>());
  const answerKeys = useRef(new Map<string, string>());
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  function update(key: string, transform: (session: ConversationSession) => ConversationSession) {
    if (!mounted.current) return;
    current.current = { ...current.current, [key]: transform(current.current[key] ?? emptySession) };
    setSessions(current.current);
  }
  function setDraft(key: string, draft: string) { update(key, session => ({ ...session, draft })); }
  function restore(key: string, turns: ConversationTurn[]) { update(key, session => ({ ...session, turns })); }
  function forget(key: string) {
    const next = { ...current.current };
    delete next[key];
    current.current = next;
    if (mounted.current) setSessions(next);
  }
  function addFiles(key: string, files: File[]) {
    const session = current.current[key] ?? emptySession;
    const { accepted, errors } = validateAttachments(session.attachments, files);
    const additions = accepted.map(file => ({ id: crypto.randomUUID(), file, kind: attachmentKind(file) }));
    update(key, previous => ({ ...previous, attachments: [...previous.attachments, ...additions], attachmentNotice: errors.join(" ") }));
  }
  function removeAttachment(key: string, id: string) { update(key, session => ({ ...session, attachments: session.attachments.filter(item => item.id !== id), attachmentNotice: "" })); }
  async function submit(key: string, request: LearningRequest, retryId?: string) {
    if (busy.current.has(key) || (!request.message.trim() && !request.attachments?.length)) return;
    busy.current.add(key);
    const id = retryId ?? crypto.randomUUID();
    const submitted = retryId ? requests.current.get(id) ?? request : { ...request, attachments: [...(request.attachments ?? [])] };
    requests.current.set(id, submitted);
    if (!answerKeys.current.has(id)) answerKeys.current.set(id, id);
    const pending: ConversationTurn = { id, question: submitted.message, attachments: submitted.attachments ?? [], status: "pending", blocks: [] };
    update(key, session => ({ ...session, turns: retryId ? session.turns.map(t => t.id === id ? pending : t) : [...session.turns, pending] }));
    let turn: ConversationTurn;
    try {
      const result = await sendLearningRequest(submitted, id, live, answerKeys.current.get(id));
      turn = result.status === "available" ? { ...pending, status: "complete", blocks: result.blocks, resources: result.resources ?? [], sessionId: result.sessionId, messageId: result.messageId, requestId: result.requestId } : { ...pending, status: result.status, notice: result.reason };
    } catch (error) {
      if (error instanceof LearningApiError && ["provider_unavailable", "provider_rate_limited", "provider_budget_exceeded", "invalid_provider_output", "retry_exhausted"].includes(error.code))
        answerKeys.current.set(id, crypto.randomUUID());
      turn = { ...pending, status: "error", notice: error instanceof LearningApiError && error.code === "provider_budget_exceeded" ? "Learning answers are paused because the API spending limit has been reached. Your question is kept; try again after access is restored." : error instanceof Error ? error.message : "Something went wrong while sending your question. Your text and attachments are kept. Please try again." };
    }
    finally { busy.current.delete(key); }
    if (turn.status === "complete" || turn.status === "unsupported") { requests.current.delete(id); answerKeys.current.delete(id); }
    update(key, session => ({
      ...session,
      draft: turn.status === "complete" && session.draft.trim() === submitted.message ? "" : session.draft,
      attachments: turn.status === "complete" ? session.attachments.filter(item => !submitted.attachments?.some(sent => sent.id === item.id)) : session.attachments,
      turns: session.turns.map(t => t.id === id ? turn : t),
    }));
  }
  return { sessions, setDraft, restore, forget, addFiles, removeAttachment, submit };
}

