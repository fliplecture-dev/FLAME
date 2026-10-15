"use client";
import { memo, useEffect, useState } from "react";
import type { highlightCode } from "./code-highlight";
type Tokens = Awaited<ReturnType<typeof highlightCode>>;

export const CodeBlock = memo(function CodeBlock({ code, language }: { code: string; language: string }) {
  const [highlighted, setHighlighted] = useState<{ code: string; language: string; tokens: Tokens } | null>(null);
  const [copied, setCopied] = useState("");
  useEffect(() => {
    let current = true;
    import("./code-highlight").then(module => module.highlightCode(code, language))
      .then(tokens => { if (current) setHighlighted({ code, language, tokens }); }).catch(() => { /* Plain code remains available. */ });
    return () => { current = false; };
  }, [code, language]);
  const tokens = highlighted?.code === code && highlighted.language === language ? highlighted.tokens : null;
  return <div className="response-code">
    <div className="response-code-toolbar"><span>{language || "Plain text"}</span><button type="button" onClick={async () => {
      try { await navigator.clipboard.writeText(code); setCopied("Copied"); } catch { setCopied("Select the code to copy"); }
    }}>Copy code</button><span role="status">{copied}</span></div>
    <pre tabIndex={0} aria-label={`${language || "Plain text"} code`}><code>{tokens ? tokens.map((line, i) => <span key={i}>{line.map((token, j) => <span key={j} style={{ color: token.color }}>{token.content}</span>)}{i < tokens.length - 1 ? "\n" : ""}</span>) : code}</code></pre>
  </div>;
});
