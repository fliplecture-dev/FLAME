import { isResponseLanguage, type ResponseLanguage } from "../learning/response-languages";
const key = "fliplecture.question-intent";
export function preferredResponseLanguage(): ResponseLanguage {
  try { const value = localStorage.getItem("flame:response-language"); return isResponseLanguage(value) ? value : "en"; }
  catch { return "en"; }
}
type QuestionIntent = { requiresSignIn?: boolean; id: string; question: string; language: ResponseLanguage; createdAt: number; item?: { kind: string; id: string; version: number } };
export function saveQuestionIntent(question: string, language: ResponseLanguage, item?: QuestionIntent["item"], requiresSignIn = false) {
  const intent: QuestionIntent = { id: crypto.randomUUID(), question: question.trim().slice(0, 4000), language, createdAt: Date.now(), item, ...(requiresSignIn ? { requiresSignIn: true } : {}) };
  sessionStorage.setItem(key, JSON.stringify(intent));
}
function readQuestionIntent(): QuestionIntent | null {
  try {
    const value = sessionStorage.getItem(key);
    if (!value) return null;
    const parsed = JSON.parse(value);
    if (typeof parsed.question !== "string" || !parsed.question.trim() || parsed.question.length > 4000 ||
      typeof parsed.id !== "string" || !/^[0-9a-f-]{36}$/i.test(parsed.id) || !isResponseLanguage(parsed.language) ||
      typeof parsed.createdAt !== "number" || Date.now() - parsed.createdAt > 30 * 60 * 1000 || parsed.createdAt > Date.now() + 5000) return null;
    if (parsed.item && (!['books', 'kits', 'teachers', 'classes'].includes(parsed.item.kind) ||
      typeof parsed.item.id !== "string" || !/^[0-9a-f-]{36}$/i.test(parsed.item.id) || !Number.isInteger(parsed.item.version) || parsed.item.version < 1)) return null;
    return parsed;
  } catch { return null; }
}
export function takeQuestionIntent(guest = false): QuestionIntent | null {
  const intent = readQuestionIntent();
  if (guest && intent?.requiresSignIn) return null;
  try { sessionStorage.removeItem(key); } catch { /* Storage is optional. */ }
  return intent;
}
export function pendingQuestionReturnPath() { return readQuestionIntent() ? "/flame" : null; }
export function safeReturnPath(value: string | null) {
  if (!value || !/^\/(?:flame|learn|search|profile)(?:\?|$)/.test(value) || /[\\\r\n]/.test(value)) return null;
  return value.replace(/^\/learn(?=\?|$)/, "/flame");
}
