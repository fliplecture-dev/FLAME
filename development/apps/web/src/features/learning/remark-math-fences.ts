type MarkdownNode = {
  type: string;
  lang?: string | null;
  value?: string;
  data?: Record<string, unknown>;
  children?: MarkdownNode[];
};

/** Recover model-authored math fences through the same KaTeX path as $$ math. */
export function remarkMathFences() {
  return (tree: unknown) => {
    function visit(node: MarkdownNode) {
      if (node.type === "code" && /^(?:math|latex|tex|katex)$/i.test(node.lang ?? "")) {
        let value = node.value ?? "";
        const trimmed = value.trim();
        for (const [open, close] of [["$$", "$$"], ["\\[", "\\]"], ["\\(", "\\)"]]) {
          if (trimmed.startsWith(open) && trimmed.endsWith(close) && trimmed.length > open.length + close.length) {
            value = trimmed.slice(open.length, -close.length).trim();
            break;
          }
        }
        node.type = "math";
        node.value = value;
        delete node.lang;
        // Match remark-math's display node contract, so rehype-katex handles
        // typography, accessible MathML and its existing untrusted-TeX policy.
        node.data = { hName: "pre", hChildren: [{ type: "element", tagName: "code",
          properties: { className: ["language-math", "math-display"] },
          children: [{ type: "text", value }] }] };
      }
      node.children?.forEach(visit);
    }
    visit(tree as MarkdownNode);
  };
}
