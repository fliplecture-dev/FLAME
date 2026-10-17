import { catalogues } from "./catalogue";

const nouns = { books: /\b(?:books?|textbooks?|workbooks?)\b/i, kits: /\bkits?\b/i,
  teachers: /\b(?:teachers?|tutors?)\b/i, classes: /\b(?:classes|class|courses?)\b/i };
// These are explicit catalogue shortcuts, not an inference that every lesson needs products.
export function requestedCatalogues(question: string) {
  const clauses = question.split(/[.!?;]|\bbut\b/i);
  return catalogues.filter(({ id }) => clauses.some(clause => {
    if (!nouns[id].test(clause)) return false;
    if (/\b(?:meaning|definition)\s+of\b|\b(?:need|want)\s+to\s+(?:know|understand|learn|explain|create|write|define|implement)\b/i.test(clause)) return false;
    if (/\b(?:do\s+not|don['’]?t|never|no|not|without)\s+(?:(?:recommend|suggest|find|show|any|a|an|the|more)\s+)*$/i.test(clause.slice(0, clause.search(nouns[id])))) return false;
    const before = clause.slice(0, clause.search(nouns[id]));
    if (/\b(?:from|by)\s+(?:(?:my|our|the|a|your)\s+)?$/i.test(before)) return false;
    return /\b(?:recommend|suggest|find|show\s+me|search\s+for|look(?:ing)?\s+for|buy|purchase|enrol(?:l)?|sign\s+up\s+for)\b[^.!?;]{0,100}$|\b(?:i|we)\s+(?:would\s+like|need|want)\b[^.!?;]{0,100}$/i.test(before)
      || new RegExp(nouns[id].source + "\\s+recommendations?\\b", "i").test(clause);
  }));
}
