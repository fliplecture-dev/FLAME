import type { LearningResource } from "@/features/learning/learning-resources";
import { validateAnswerComposition, type ComposedLearningResponse } from "./learning-response";
import type { PromptAttachment } from "@/features/learning/prompt-attachments";
import type { LearningBlock } from "@/features/learning/learning-content";
import { responseBlock } from "@/features/learning/rich-blocks";
import { localLibrary } from "@/features/curriculum/local-library";
import { localCurriculum } from "@/features/curriculum/local-curriculum";
import type { Curriculum, LearningContext } from "@/features/curriculum/types";
import { catalogueFromTrees } from "./b4-catalogue";
import type { PublishedCurriculumTree } from "@/features/curriculum/map-published-curriculum";
import type { ResponseLanguage } from "@/features/learning/response-languages";

export type LearningRequest = { responseLanguage?: ResponseLanguage; sessionId?: string; attachments?: PromptAttachment[]; history?: { question: string; blocks: LearningBlock[]; attachments?: PromptAttachment[] }[] } & (
  | { message: string; mode: "study"; context: LearningContext | null }
  | { message: string; mode: "curiosity"; context: null });
export type LearningResult = { status: "available"; blocks: LearningBlock[]; resources?: LearningResource[]; sessionId: string; messageId: string; requestId?: string } | { status: "unavailable" | "unsupported"; reason: string };

// The local curriculum provider remains a development fixture. Live answers and learning data use the authenticated BFF.
// Proficiency aggregates and learning access remain server-owned.
export async function getCurriculum(): Promise<Curriculum[]> { return localCurriculum; }

const answerSessions = new Map<string, string>();
export function forgetLearningAnswerSession(sessionId: string) {
  for (const [key, value] of answerSessions) if (value === sessionId) answerSessions.delete(key);
}

export async function sendLearningRequest(request: LearningRequest, requestId?: string, live = false, answerKey?: string, onText?: (text: string) => void): Promise<LearningResult> {
  if (!request.message.trim() && !request.attachments?.length) throw new Error("Enter a learning request first.");
  if (request.attachments?.length) return { status: "unavailable", reason: "File processing and audio transcription aren't connected yet. Your attachments are kept in this tab; nothing has been uploaded." };
  if (!live) return { status: "unavailable", reason: "FLAME replies aren't connected yet. Your question is still here so you can try again when learning is available." };
  if (request.mode === "study" && !request.context) return { status: "unavailable", reason: "Choose a topic or subtopic before asking a Study question." };
  const context = request.context ? {
    curriculum_id: request.context.curriculumId, level_id: request.context.levelId,
    subject_id: request.context.subjectId, domain_id: request.context.domainId,
    category_id: request.context.categoryId, topic_id: request.context.topicId,
    subtopic_id: request.context.subtopicId,
  } : null;
  const sessionKey = JSON.stringify([request.mode, context]);
  let sessionId = request.sessionId ?? answerSessions.get(sessionKey);
  if (!sessionId) {
    const created = await b4Mutation("sessions", "POST", { mode: request.mode, context }) as { id: string };
    sessionId = created.id;
    answerSessions.set(sessionKey, sessionId);
    window.dispatchEvent(new Event("flame:sessions-updated"));
  }
  const key = requestId ?? crypto.randomUUID();
  if (request.mode === "curiosity") {
    const capability = await b4Mutation("sessions/" + sessionId + "/capability-check", "POST",
      { question: request.message.trim() }) as { status: string };
    if (capability.status !== "continue" && capability.status !== "unsupported")
      throw new Error("The request capability could not be checked.");
  }
  const answer = await streamedAnswer("sessions/" + sessionId, {
    question: request.message.trim(), mode: request.mode, action: "explain", context,
    ...(request.responseLanguage ? { response_language: request.responseLanguage } : {}),
  }, answerKey ?? key, onText) as { status: string; route?: string; knowledge_source?: string; grounded?: boolean; blocks?: LearningBlock[]; code?: string; message?: string; message_id?: string; request_id?: string; learning_response?:ComposedLearningResponse };
  if (answer.status === "unsupported" && answer.code && answer.message)
    return { status: "unsupported", reason: answer.message };
  if (answer.status !== "ok" || answer.route !== "direct_llm" ||
      answer.knowledge_source !== "model_generated" || answer.grounded !== false ||
      !answer.message_id || !Array.isArray(answer.blocks) || !answer.blocks.length || answer.blocks.length > 30) {
    throw new Error("The answer could not be displayed.");
  }
  validateAnswerComposition(answer);
  window.dispatchEvent(new Event("flame:sessions-updated"));
  return { status: "available", blocks: answer.blocks.map((block, index) => responseBlock(block, `${answer.message_id}-${index}`)), sessionId, messageId: answer.message_id,
    requestId: typeof answer.request_id === "string" && /^[0-9a-f-]{36}$/i.test(answer.request_id) ? answer.request_id : undefined };
}

async function b4Get(path: string) {
  const response = await fetch("/api/b4/" + path, { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error("The library could not be loaded.");
  return response.json();
}

export async function getLearningLibrary(live = false): Promise<Curriculum[]> {
  if (!live) return structuredClone(localLibrary);
  const listing = await b4Get("curricula");
  const trees = await Promise.all((listing.items as { id: string }[]).map(
    item => b4Get("curricula/" + item.id + "/tree") as Promise<PublishedCurriculumTree>
  ));
  return catalogueFromTrees(trees);
}

export class LearningApiError extends Error {
  constructor(message: string, public code: string) { super(message); }
}

export async function b4Mutation(path: string, method: "POST" | "PATCH", body: unknown, idempotencyKey?: string, signal?: AbortSignal) {
  const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store", credentials: "same-origin", signal });
  if (!csrfResponse.ok) throw new Error("Could not authorize this change.");
  const { csrf } = await csrfResponse.json();
  const response = await fetch("/api/b4/" + path, {
    method, credentials: "same-origin", signal,
    headers: { "content-type": "application/json", "x-flame-csrf": csrf,
      ...(idempotencyKey ? { "idempotency-key": idempotencyKey } : {}) },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {const reference=typeof data?.request_id==="string"&&/^[a-zA-Z0-9_-]{1,100}$/.test(data.request_id)?" Reference: "+data.request_id:"";throw new LearningApiError((data?.detail || data?.error?.message || "The change could not be saved.")+reference, data?.error?.code || "request_failed");}
  return data;
}



/** Stream text separately; final validated/stored blocks replace the provisional preview. */
async function streamedAnswer(path: string, body: unknown, key: string, onText?: (text: string) => void): Promise<unknown> {
  if (!onText) return b4Mutation(path + "/ask", "POST", body, key);
  const auth = await fetch("/api/auth/csrf", { cache: "no-store", credentials: "same-origin" });
  if (!auth.ok) throw new Error("Could not authorize this question.");
  const { csrf } = await auth.json();
  const response = await fetch("/api/b4/" + path + "/ask-stream", { method: "POST", credentials: "same-origin", cache: "no-store",
    headers: { "content-type": "application/json", "x-flame-csrf": csrf, "idempotency-key": key }, body: JSON.stringify(body) });
  // Older API deployments/fixtures can keep the existing idempotent complete-answer path.
  if (response.status === 404 || response.status === 405) return b4Mutation(path + "/ask", "POST", body, key);
  if (!response.ok || !response.body) throw new Error("The answer could not be completed. Retry to check its saved status.");
  if (!response.headers.get("content-type")?.includes("application/x-ndjson")) return response.json();
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let pending = "", text = "", received = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      received += value.byteLength;
      if (received > 250000) throw new Error("The response exceeded its display limit.");
      pending += decoder.decode(value, { stream: true });
      let newline;
      while ((newline = pending.indexOf("\n")) >= 0) {
        const raw = pending.slice(0, newline); pending = pending.slice(newline + 1);
        if (!raw.trim()) continue;
        const event = JSON.parse(raw);
        if (event.type === "delta" && typeof event.text === "string") {
          text += event.text;
          // Structured blocks wait for final validation; intent tags are never visible.
          if (!text.trimStart().startsWith("{") && !text.trimStart().startsWith("```json")) onText(text.split("<")[0]);
        }
        if (event.type === "answer") { if (event.answer?.status === "error") throw new LearningApiError("The answer could not be completed.", event.answer.code); return event.answer; }
        if (event.type === "failure") throw new Error("The answer could not be completed. Retry to check its saved status.");
      }
    }
    throw new Error("The answer stream was interrupted. Retry to check its saved status.");
  } finally { await reader.cancel().catch(() => {}); }
}
