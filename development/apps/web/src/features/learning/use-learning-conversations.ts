"use client";
import { createContext, createElement, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { LearningApiError, sendLearningRequest, type LearningRequest } from "@/lib/api/student-learning";
import { attachmentKind, validateAttachments } from "./prompt-attachments";
import { emptySession, type ConversationSession, type ConversationTurn } from "./conversation-types";
import type { WorkspaceSnapshot } from "./workspace-history";
function useConversationStore(live = false) {
  const [sessions, setSessions] = useState<Record<string, ConversationSession>>({});
  const current = useRef(sessions);
  const busy = useRef(new Set<string>());
  const mounted = useRef(true);
  const requests = useRef(new Map<string, LearningRequest>());
  const answerKeys = useRef(new Map<string, string>());
  const workspaceSnapshots = useRef(new Map<string, WorkspaceSnapshot>());
  const viewportPositions = useRef(new Map<string, number>());
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  function update(key: string, transform: (session: ConversationSession) => ConversationSession) {
    if (!mounted.current) return;
    current.current = { ...current.current, [key]: transform(current.current[key] ?? emptySession) };
    setSessions(current.current);
  }
  function setDraft(key: string, draft: string) { update(key, session => ({ ...session, draft })); }
  function restore(key: string, turns: ConversationTurn[]) {
    update(key, session => ({ ...session, turns: [...turns, ...session.turns.filter(turn => turn.status === "pending")] }));
  }
  function forget(key: string) {
    const next = { ...current.current };
    for (const cached of Object.keys(next)) {
      if (cached === key || next[cached].turns.some(turn => turn.sessionId === key)) delete next[cached];
    }
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
  async function submit(key: string, request: LearningRequest, retryId?: string, submissionId?: string) {
    if (busy.current.has(key) || (!request.message.trim() && !request.attachments?.length)) return;
    busy.current.add(key);
    const id = retryId ?? submissionId ?? crypto.randomUUID();
    const submitted = retryId ? requests.current.get(id) ?? request : { ...request, attachments: [...(request.attachments ?? [])] };
    requests.current.set(id, submitted);
    if (!answerKeys.current.has(id)) answerKeys.current.set(id, id);
    const pending: ConversationTurn = { id, guest: submitted.guest, question: submitted.message, attachments: submitted.attachments ?? [], status: "pending", blocks: [] };
    update(key, session => ({ ...session, turns: retryId ? session.turns.map(t => t.id === id ? pending : t) : [...session.turns, pending] }));
    let turn: ConversationTurn;
    try {
      const result = await sendLearningRequest(submitted, id, live, answerKeys.current.get(id), text => update(key, session => ({ ...session, turns: session.turns.map(t => t.id === id ? { ...t, blocks: [{ id: id + "-stream", kind: "markdown", text }] } : t) })));
      turn = result.status === "available" ? { ...pending, status: "complete", freshSimulation: true, blocks: result.blocks, resources: result.resources ?? [], sessionId: result.sessionId, messageId: result.messageId, requestId: result.requestId } : { ...pending, status: result.status, notice: result.reason };
    } catch (error) {
      if (error instanceof LearningApiError && ["provider_unavailable", "provider_rate_limited", "provider_budget_exceeded", "invalid_provider_output", "retry_exhausted"].includes(error.code))
        answerKeys.current.set(id, crypto.randomUUID());
      turn = { ...pending, status: "error", notice: error instanceof LearningApiError && error.code === "provider_budget_exceeded" ? "Learning answers are paused because the API spending limit has been reached. Your question is kept; try again after access is restored." : error instanceof Error ? error.message : "Something went wrong while sending your question. Your text and attachments are kept. Please try again." };
    }
    finally { busy.current.delete(key); window.dispatchEvent(new Event("flame:usage-updated")); }
    if (turn.status === "complete" || turn.status === "unsupported") { requests.current.delete(id); answerKeys.current.delete(id); }
    update(key, session => ({
      ...session,
      draft: turn.status === "complete" && session.draft.trim() === submitted.message ? "" : session.draft,
      attachments: turn.status === "complete" ? session.attachments.filter(item => !submitted.attachments?.some(sent => sent.id === item.id)) : session.attachments,
      turns: session.turns.map(t => t.id === id ? turn : t).filter((item, index, all) => !item.messageId || all.findLastIndex(other => other.messageId === item.messageId) === index),
    }));
  }
  return { sessions, setDraft, restore, forget, addFiles, removeAttachment, submit, workspaceSnapshots, viewportPositions };
}

const ConversationStore = createContext<ReturnType<typeof useConversationStore> | null>(null);
export function LearningConversationsProvider({ live, children }: { live: boolean; children: ReactNode }) {
  const store = useConversationStore(live);
  return createElement(ConversationStore.Provider, { value: store }, children);
}
export function useLearningConversations() {
  const store = useContext(ConversationStore);
  if (!store) throw new Error("Learning conversations require their application provider.");
  return store;
}

