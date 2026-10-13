/** Additive B11 envelopes; legacy split endpoints remain valid during migration. */
export type RecommendationStatus = "completed" | "none" | "pending" | "unavailable";
export type ComposedLearningResponse = {
  schema_version: 1;
  message_id: string | null;
  request_id?: string | null;
  answer?: {status:"completed"|"unsupported"|"unavailable";blocks:unknown[]} | null;
  recommendations: {status:RecommendationStatus;data?:unknown;code?:string|null};
};

type Envelope = {learning_response?:ComposedLearningResponse;message_id?:string};

export function recommendationPayload<T>(value:T & Envelope, messageId:string):T {
  const envelope=value.learning_response;
  if(!envelope)return value;
  if(envelope.schema_version!==1 || envelope.message_id!==messageId)throw new Error("These suggestions belong to another answer. Retry learning suggestions.");
  if(envelope.recommendations.status==="unavailable")throw new Error("Learning suggestions are temporarily unavailable. Your explanation is still available.");
  return (envelope.recommendations.data ?? value) as T;
}

export function validateAnswerComposition<T extends Envelope>(value:T):T {
  const envelope=value.learning_response;
  if(envelope && (envelope.schema_version!==1 || envelope.message_id!==value.message_id || envelope.answer?.status!=="completed"))
    throw new Error("The answer could not be matched to this conversation. Your question is preserved.");
  return value;
}
