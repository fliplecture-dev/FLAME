/** F11 wire data. Keep limits aligned with teaching/schemas.py. */
import type { LearningBlock } from "./learning-content";
import { isMathVisualBlock } from "./math-spec";
export type MarkdownBlock = { id: string; kind: "markdown"; text: string };
export type ChartBlock = {
  id: string; kind: "chart"; chartType: "bar" | "line" | "pie";
  title: string; description: string; xKey: string; xLabel?: string; yLabel?: string;
  illustrative: boolean;
  series: { key: string; label: string }[];
  data: Record<string, string | number>[];
};
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const bounded = (value: unknown, max: number, empty = false): value is string => typeof value === "string" && (empty || !!value.trim()) && value.length <= max && !/[\u0000-\u0008\u000b-\u001f]/.test(value);
const key = (value: unknown): value is string => typeof value === "string" && /^[A-Za-z][A-Za-z0-9_]{0,39}$/.test(value) && !["constructor", "prototype", "__proto__"].includes(value);
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && Math.abs(value) <= 1e12;

export function isChartBlock(value: unknown): value is ChartBlock {
  if (!record(value) || value.kind !== "chart" || !bounded(value.id, 100) ||
      !["bar", "line", "pie"].includes(String(value.chartType)) || !bounded(value.title, 200) ||
      !bounded(value.description, 500) || !key(value.xKey) || typeof value.illustrative !== "boolean" ||
      (value.xLabel !== undefined && !bounded(value.xLabel, 100, true)) ||
      (value.yLabel !== undefined && !bounded(value.yLabel, 100, true)) ||
      !Array.isArray(value.series) || !value.series.length || value.series.length > 4 ||
      !Array.isArray(value.data) || !value.data.length || value.data.length > 50) return false;
  const series = value.series;
  if (!series.every(item => record(item) && key(item.key) && bounded(item.label, 100))) return false;
  const keys = series.map(item => item.key as string);
  if (new Set(keys).size !== keys.length || keys.includes(value.xKey) || (value.chartType === "pie" && keys.length !== 1)) return false;
  const xKey = value.xKey;
  if (!value.data.every(row => record(row) && Object.keys(row).length === keys.length + 1 &&
      (bounded(row[xKey], 100) || finite(row[xKey])) &&
      keys.every(name => finite(row[name]) && (value.chartType !== "pie" || (row[name] as number) >= 0)))) return false;
  return value.chartType !== "pie" || value.data.reduce((sum, row) => sum + Number(row[keys[0]]), 0) > 0;
}

export function isMarkdownBlock(value: unknown): value is MarkdownBlock {
  return record(value) && value.kind === "markdown" && bounded(value.id, 100) && bounded(value.text, 6000);
}

export function safeResponseUrl(value: string): string | undefined {
  if (value.includes("\\") || /[\u0000-\u0020\u007f]/.test(value)) return undefined;
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  try { const url = new URL(value); return url.protocol === "https:" ? url.href : undefined; } catch { return undefined; }
}

/** Both live and restored wire blocks take the same validation/fallback path. */
export function responseBlock(value: unknown, fallbackId: string): LearningBlock {
  const fallback: LearningBlock = { id: fallbackId, kind: "text", text: "This part of the answer could not be displayed." };
  if (!record(value)) return fallback;
  const block: Record<string, unknown> & { id: string } = { ...value, id: bounded(value.id, 100) ? value.id : fallbackId };
  if (isMarkdownBlock(block) || isChartBlock(block) || isMathVisualBlock(block)) return block;
  const strings = (items: unknown, max: number, length: number): items is string[] => Array.isArray(items) && items.length <= max && items.every(item => bounded(item, length, true));
  if ((block.kind === "text" && bounded(block.text, 6000)) ||
      (block.kind === "heading" && bounded(block.text, 200) && [2, 3].includes(Number(block.level))) ||
      (block.kind === "callout" && bounded(block.title, 200) && bounded(block.text, 2000)) ||
      (block.kind === "list" && strings(block.items, 20, 500) && block.items.length > 0 && (block.ordered === undefined || typeof block.ordered === "boolean")) ||
      (block.kind === "table" && bounded(block.caption, 200) && strings(block.columns, 8, 500) && block.columns.length > 0 &&
        Array.isArray(block.rows) && block.rows.length <= 30 && block.rows.every(row => strings(row, 8, 500) && row.length === (block.columns as string[]).length)))
    return block as LearningBlock;
  return fallback;
}
