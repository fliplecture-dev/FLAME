import type { LearningResource } from "./learning-resources";
import type { PromptAttachment } from "./prompt-attachments";
import type { LearningBlock } from "./learning-content";
export interface ConversationTurn {
  id: string;
  question: string;
  attachments: PromptAttachment[];
  status: "pending" | "complete" | "unavailable" | "unsupported" | "error";
  blocks: LearningBlock[];
  resources?: LearningResource[];
  sessionId?: string;
  messageId?: string;
  requestId?: string;
  notice?: string;
}
export interface ConversationSession { draft: string; attachments: PromptAttachment[]; attachmentNotice: string; turns: ConversationTurn[] }
export const emptySession: ConversationSession = { draft: "", attachments: [], attachmentNotice: "", turns: [] };

