import type { LearningMode } from "./mode-switcher";

export type SavedSession = {
  id: string;
  mode: LearningMode;
  context: ({ names?: Record<string, string | null>; curriculum_id: string; level_id: string; subject_id: string; domain_id: string; category_id: string | null; topic_id: string; subtopic_id: string | null }) | null;
  revision: number | null;
  pinned: boolean;
  recent_at?: string | null;
  first_question?: string;
  created_at: string;
  updated_at: string;
};
export type SavedMessage = { id: string; role: "user" | "assistant"; blocks: { kind: string; id?: string; text?: string; title?: string; items?: string[] }[]; turn_number: number };
export type SavedPage<T> = { items: T[]; next_cursor: string | null };

async function get<T>(path: string): Promise<T> {
  const response = await fetch("/api/b4/" + path, { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error("Conversations could not be loaded.");
  return response.json();
}
async function change(path: string, method: "POST" | "PATCH" | "DELETE", body: unknown) {
  const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store", credentials: "same-origin" });
  if (!csrfResponse.ok) throw new Error("Could not authorize this change.");
  const { csrf } = await csrfResponse.json();
  const response = await fetch("/api/b4/" + path, {
    method, credentials: "same-origin",
    headers: { "content-type": "application/json", "x-flame-csrf": csrf },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("The conversation could not be changed.");
  return response.json();
}
export function getSavedSessions(cursor?: string) {
  return get<SavedPage<SavedSession>>("sessions?limit=100" + (cursor ? "&cursor=" + encodeURIComponent(cursor) : ""));
}
export async function getSavedMessages(id: string): Promise<SavedMessage[]> {
  const messages: SavedMessage[] = [];
  let cursor: string | null = null;
  do {
    const page: SavedPage<SavedMessage> = await get("sessions/" + id + "/messages?limit=100" + (cursor ? "&cursor=" + encodeURIComponent(cursor) : ""));
    messages.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor);
  return messages;
}
export function pinSavedSession(id: string, pinned: boolean): Promise<SavedSession> {
  return change("sessions/" + id + "/pin", "PATCH", { pinned }) as Promise<SavedSession>;
}
export function deleteSavedSession(id: string): Promise<unknown> {
  return change("sessions/" + id, "DELETE", { confirm: true });
}
export async function getAllSavedSessions(): Promise<SavedSession[]> {
  const rows: SavedSession[] = [];
  let cursor: string | undefined;
  do {
    const page = await getSavedSessions(cursor);
    rows.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  } while (cursor);
  return rows;
}
export function markConversationOpened(id: string): Promise<SavedSession> {
  return change("sessions/" + id + "/recent", "POST", { confirm: true }) as Promise<SavedSession>;
}
export function clearRecentHistory(): Promise<unknown> {
  return change("sessions/recent/clear", "POST", { confirm: true });
}
export function unpinAllConversations(): Promise<unknown> {
  return change("sessions/pins/clear", "POST", { confirm: true });
}
