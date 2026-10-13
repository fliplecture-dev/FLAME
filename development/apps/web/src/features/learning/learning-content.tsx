import { createElement, type ReactNode } from "react";
export type MathExpression =
  | { kind: "symbol" | "number" | "operator"; value: string }
  | { kind: "row"; children: MathExpression[] }
  | { kind: "fraction"; numerator: MathExpression; denominator: MathExpression }
  | { kind: "power"; base: MathExpression; exponent: MathExpression };
export type LearningBlock =
  | { id: string; kind: "text"; text: string }
  | { id: string; kind: "heading"; text: string; level: 2 | 3 }
  | { id: string; kind: "list"; ordered?: boolean; items: string[] }
  | { id: string; kind: "table"; caption: string; columns: string[]; rows: string[][] }
  | { id: string; kind: "callout"; title: string; text: string }
  | { id: string; kind: "formula"; expression: MathExpression; description: string }
  | { id: string; kind: "image" | "diagram"; src: string; alt: string; caption?: string }
  | { id: string; kind: "video"; src: string; caption: string; captionsSrc: string }
  | { id: string; kind: "resource"; href: string; title: string; description: string };
function MathNode({ expression: e }: { expression: MathExpression }): ReactNode {
  if (e.kind === "row") return createElement("mrow", null, e.children.map((child, i) => <MathNode key={i} expression={child} />));
  if (e.kind === "fraction") return createElement("mfrac", null, <MathNode expression={e.numerator} />, <MathNode expression={e.denominator} />);
  if (e.kind === "power") return createElement("msup", null, <MathNode expression={e.base} />, <MathNode expression={e.exponent} />);
  return createElement(e.kind === "number" ? "mn" : e.kind === "operator" ? "mo" : "mi", null, e.value);
}
function safeUrl(value: string) {
  if (value.includes("\\") || /[\u0000-\u001f]/.test(value)) return undefined;
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  try { const url = new URL(value); return url.protocol === "https:" ? url.href : undefined; } catch { return undefined; }
}
export function LearningContent({ blocks, children }: { blocks: LearningBlock[]; children?: ReactNode }) {
  return <div className="learning-content">{blocks.map(block => {
    if (block.kind === "text") return <p className="content-text" key={block.id}>{block.text}</p>;
    if (block.kind === "heading") { const Heading = block.level === 2 ? "h2" : "h3"; return <Heading key={block.id}>{block.text}</Heading>; }
    if (block.kind === "list") { const List = block.ordered ? "ol" : "ul"; return <List key={block.id}>{block.items.map((item, i) => <li key={i}>{item}</li>)}</List>; }
    if (block.kind === "table") return <div key={block.id} className="content-table" role="region" aria-label={block.caption} tabIndex={0}><table><caption>{block.caption}</caption><thead><tr>{block.columns.map((name, i) => <th key={i} scope="col">{name}</th>)}</tr></thead><tbody>{block.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody></table></div>;
    if (block.kind === "callout") return <aside className="content-callout" key={block.id}><strong>{block.title}</strong><p>{block.text}</p></aside>;
    if (block.kind === "formula") return <figure className="content-formula" key={block.id}>{createElement("math", { display: "block", "aria-label": block.description }, <MathNode expression={block.expression} />)}<figcaption>{block.description}</figcaption></figure>;
    if (block.kind === "resource") { const href = safeUrl(block.href); return href ? <a className="learning-resource" key={block.id} href={href} target="_blank" rel="noopener noreferrer"><strong>{block.title} ↗</strong><span>{block.description}</span></a> : null; }
    const src = safeUrl(block.src); if (!src) return null;
    if (block.kind === "video") return <figure key={block.id}><video controls preload="metadata" src={src}><track kind="captions" src={safeUrl(block.captionsSrc)} srcLang="en" label="English" default /></video><figcaption>{block.caption}</figcaption></figure>;
    return <figure key={block.id}><img src={src} alt={block.alt} loading="lazy" /><figcaption>{block.caption}</figcaption></figure>;
  })}{children}</div>;
}
