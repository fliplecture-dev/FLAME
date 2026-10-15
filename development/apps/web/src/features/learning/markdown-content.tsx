"use client";
import { Children, isValidElement, memo, type ReactNode } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { CodeBlock } from "./code-block";
import { safeResponseUrl } from "./rich-blocks";
import { remarkMathFences } from "./remark-math-fences";

const components: Components = {
  h1: ({ children }) => <h2>{children}</h2>,
  table: ({ children }) => <div className="content-table" role="region" aria-label="Answer table" tabIndex={0}><table>{children}</table></div>,
  th: ({ children }) => <th scope="col">{children}</th>,
  input: ({ checked }) => <input type="checkbox" disabled checked={checked ?? false} aria-label={checked ? "Completed checklist item" : "Incomplete checklist item"} />,
  a: ({ href, children }) => {
    const safe = href ? safeResponseUrl(href) : undefined;
    return safe ? <a href={safe} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span>;
  },
  img: ({ alt }) => <span>{alt ? `[Image: ${alt}]` : "[Image omitted]"}</span>,
  pre: ({ children }) => {
    const child = Children.toArray(children)[0];
    if (isValidElement<{ className?: string; children?: ReactNode }>(child) && child.type === "code") {
      const language = /language-([\w+-]+)/.exec(child.props.className ?? "")?.[1] ?? "";
      return <CodeBlock code={String(child.props.children ?? "").replace(/\n$/, "")} language={language} />;
    }
    // KaTeX display output is already a React tree; don't re-interpret it as source code.
    return <div className="response-math">{children}</div>;
  },
};
const remarkPlugins = [remarkGfm, [remarkMath, { singleDollarTextMath: false }], remarkMathFences] as NonNullable<Parameters<typeof Markdown>[0]["remarkPlugins"]>;
const rehypePlugins = [[rehypeKatex, { trust: false, maxExpand: 100, maxSize: 10, output: "htmlAndMathml", strict: "warn" }]] as NonNullable<Parameters<typeof Markdown>[0]["rehypePlugins"]>;

export const MarkdownContent = memo(function MarkdownContent({ text }: { text: string }) {
  return <div className="response-markdown"><Markdown skipHtml remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins} components={components}
    urlTransform={value => safeResponseUrl(value) ?? ""}>{text}</Markdown></div>;
});
