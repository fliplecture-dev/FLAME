import { ResponseSimulation } from "./response-simulation";
import { ResourceRecommendations } from "./resource-recommendations";
import { CatalogueRecommendations } from "./catalogue-recommendations";
import { AnswerExploreResources } from "./answer-explore-resources";
import { AttachmentList } from "./attachment-list";
import { LoaderCircle, RotateCcw } from "lucide-react";
import { LearningContent } from "./learning-content";
import type { ConversationTurn } from "./conversation-types";
export function FlameConversation({ turns, pending, onRetry }: { turns: ConversationTurn[]; pending: boolean; onRetry: (turn: ConversationTurn) => void }) {
  return <section className="flame-conversation" aria-label="Learning conversation">{turns.map(turn => <article className="conversation-turn" key={turn.id} aria-label="Question and response">
    <div className="student-message"><span className="message-author">You</span>{turn.question && <p>{turn.question}</p>}<AttachmentList attachments={turn.attachments} /></div>
    <div className="flame-message"><span className="sr-only">FLAME{turn.status === "complete" ? " / AI-generated explanation" : ""}</span>
      {turn.status === "complete" ? <><LearningContent blocks={turn.blocks} />{turn.sessionId && turn.messageId && <ResponseSimulation sessionId={turn.sessionId} messageId={turn.messageId} fresh={turn.freshSimulation} />}<ResourceRecommendations resources={turn.resources ?? []} />{turn.sessionId && turn.messageId && <CatalogueRecommendations sessionId={turn.sessionId} messageId={turn.messageId} />}</> : turn.status === "pending" ? <><LearningContent blocks={turn.blocks} /><p className="response-pending" role="status"><LoaderCircle size={16} aria-hidden="true" />Writing your response…</p></> : turn.status === "unsupported" ? <div className="response-notice"><p role="status">{turn.notice}</p></div> : <div className="response-notice"><p role="status">{turn.notice}</p><button disabled={pending} onClick={() => onRetry(turn)}><RotateCcw size={14} aria-hidden="true" />Retry question</button></div>}
      {turn.status === "complete" && turn.sessionId && turn.messageId && <AnswerExploreResources sessionId={turn.sessionId} messageId={turn.messageId} />}
    </div>
  </article>)}</section>;
}

