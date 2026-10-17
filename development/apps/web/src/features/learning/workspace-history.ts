import type { TopicContext } from "@/features/curriculum/types";
import type { TreeViewState } from "@/features/curriculum/curriculum-navigator";
import type { LearningMode } from "./mode-switcher";
import type { SavedSession } from "./saved-sessions";

export type WorkspaceSnapshot = {
  mode: LearningMode; selected: TopicContext | null; resumed: SavedSession | null;
  openedConversationId: string | null; view: TreeViewState;
};
