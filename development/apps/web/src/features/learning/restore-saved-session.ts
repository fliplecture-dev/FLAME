import type { Curriculum, TopicContext } from "@/features/curriculum/types";
import type { LearningBlock } from "./learning-content";
import type { ConversationTurn } from "./conversation-types";
import type { SavedMessage, SavedSession } from "./saved-sessions";

export function findSavedContext(catalogue: Curriculum[], row: SavedSession): TopicContext | null {
  const path = row.context;
  if (!path) return null;
  const curriculum = catalogue.find(item => item.id === path.curriculum_id);
  const level = curriculum?.levels.find(item => item.id === path.level_id);
  const subject = level?.subjects.find(item => item.id === path.subject_id);
  const domain = subject?.domains.find(item => item.id === path.domain_id);
  const topic = domain?.topics.find(item => item.id === path.topic_id && item.categoryId === path.category_id);
  const subtopic = path.subtopic_id ? topic?.subtopics.find(item => item.id === path.subtopic_id) : undefined;
  return curriculum && level && subject && domain && topic && (!path.subtopic_id || subtopic)
    ? { curriculum, level, subject, domain, topic, ...(subtopic ? { subtopic } : {}) } : null;
}

export function restoredTurns(messages: SavedMessage[], sessionId?: string): ConversationTurn[] {
  const pairs = new Map<number, { user?: SavedMessage; assistant?: SavedMessage }>();
  for (const message of messages) {
    const pair = pairs.get(message.turn_number) ?? {};
    pair[message.role] = message;
    pairs.set(message.turn_number, pair);
  }
  return [...pairs.entries()].sort(([a], [b]) => a - b).flatMap(([, pair]) => {
    const question = pair.user?.blocks.find(block => block.kind === "text")?.text;
    if (!question || !pair.assistant) return [];
    const blocks = pair.assistant.blocks.filter(block =>
      ["text", "heading", "list", "table", "callout"].includes(block.kind)
    ).map((block, index) => ({ ...block, id: block.id ?? pair.assistant!.id + "-" + index })) as LearningBlock[];
    if (!blocks.length) return [];
    return [{ id: pair.assistant.id, question, attachments: [], status: "complete" as const, blocks, sessionId, messageId: pair.assistant.id }];
  });
}
