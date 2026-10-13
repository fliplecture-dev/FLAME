import type { SavedSession } from "./saved-sessions";

export function sessionTopicKey(row: SavedSession): string {
  if (row.mode === "curiosity" || !row.context) return row.id;
  const path = row.context;
  return JSON.stringify([path.curriculum_id, path.level_id, path.subject_id,
    path.domain_id, path.category_id, path.topic_id, path.subtopic_id]);
}

export function groupRecentSessions(rows: SavedSession[]): SavedSession[][] {
  const groups = new Map<string, SavedSession[]>();
  for (const row of rows) {
    const key = sessionTopicKey(row);
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  return [...groups.values()].sort((a, b) =>
    Number(b.some(row => row.pinned)) - Number(a.some(row => row.pinned)) ||
    b[0].updated_at.localeCompare(a[0].updated_at));
}

export function recentTitle(row: SavedSession): string {
  if (row.mode === "curiosity") return row.first_question?.trim() || "Curiosity";
  return row.context?.names?.subtopic || row.context?.names?.topic || "Study topic";
}