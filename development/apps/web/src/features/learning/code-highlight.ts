import { createHighlighterCore } from "shiki/core";
import { createJavaScriptRegexEngine } from "shiki/engine/javascript";

const languages = {
  javascript: () => import("shiki/langs/javascript.mjs"),
  typescript: () => import("shiki/langs/typescript.mjs"),
  python: () => import("shiki/langs/python.mjs"),
  json: () => import("shiki/langs/json.mjs"),
  html: () => import("shiki/langs/html.mjs"),
  css: () => import("shiki/langs/css.mjs"),
  bash: () => import("shiki/langs/bash.mjs"),
  sql: () => import("shiki/langs/sql.mjs"),
};
const aliases: Record<string, string> = { js: "javascript", ts: "typescript", py: "python", shell: "bash", sh: "bash" };
const cache = new Map<string, Awaited<ReturnType<typeof highlight>>>();
let highlighter: ReturnType<typeof createHighlighterCore> | undefined;
function instance() {
  return highlighter ??= createHighlighterCore({
    themes: [import("shiki/themes/github-light.mjs")], langs: [], engine: createJavaScriptRegexEngine(),
  }).catch(error => { highlighter = undefined; throw error; });
}
async function highlight(code: string, language: string) {
  const languageKey = (aliases[language] ?? language) as keyof typeof languages;
  if (!Object.hasOwn(languages, languageKey) || code.length > 6000 || code.split("\n").some(line => line.length > 1000)) return null;
  const highlighter = await instance();
  await highlighter.loadLanguage(await languages[languageKey]());
  return highlighter.codeToTokens(code, { lang: languageKey, theme: "github-light" }).tokens;
}
export async function highlightCode(code: string, language: string) {
  const key = language + "\0" + code;
  if (cache.has(key)) return cache.get(key)!;
  const tokens = await highlight(code, language);
  if (cache.size >= 40) cache.delete(cache.keys().next().value!);
  cache.set(key, tokens);
  return tokens;
}
