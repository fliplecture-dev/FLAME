/** Safe, actionable messages shared by streamed and complete answer failures. */
export function answerErrorMessage(code: unknown): string {
  switch (code) {
    case "catalogue_context_too_large":
      return "This question and listing are too long to process together. Shorten your question and send it again.";
    case "catalogue_item_unavailable":
      return "This listing changed or is no longer available. Return to search and open its latest details. Your question is kept.";
    case "daily_limit_reached":
      return "You've reached today's question limit. Your question is kept. Your allowance resets at midnight India time (Asia/Kolkata).";
    case "request_in_progress":
    case "session_request_in_progress":
      return "An answer is still being prepared in this conversation. Wait briefly, then retry to check its saved status.";
    case "unavailable_context":
    case "session_context_mismatch":
      return "This learning context has changed. Select the topic again and start a new conversation. Your question is kept.";
    case "provider_budget_exceeded":
      return "Learning answers are paused because the API spending limit has been reached. Your question is kept; try again after access is restored.";
    case "provider_rate_limited":
      return "The answer provider is busy. Your question is kept; try again shortly.";
    default:
      return "The answer could not be completed. Retry to check its saved status.";
  }
}
