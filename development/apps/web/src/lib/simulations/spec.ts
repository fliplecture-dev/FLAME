export const simulationEngines = ["matter", "three", "r3f", "phaser", "rive", "html5"] as const;
export type SimulationEngine = typeof simulationEngines[number];
export type SimulationSpec = { version: 1; engine: SimulationEngine; title: string; description: string; source: string };
export type CatalogueSimulation = { resourceId: string; version: number; title: string; document: string };

export function catalogueSimulation(value: unknown): CatalogueSimulation | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const v = value as Record<string, unknown>;
  if (v.status !== "resource" || typeof v.resource_id !== "string" || !/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(v.resource_id) ||
      !Number.isSafeInteger(v.version) || Number(v.version) < 1 || typeof v.title !== "string" || !v.title.trim() || v.title.length > 200 ||
      typeof v.html_document !== "string" || !v.html_document.trim() || v.html_document.length > 2 * 1024 * 1024 + 2048 || v.html_document.includes("\0")) return null;
  return { resourceId: v.resource_id, version: Number(v.version), title: v.title, document: v.html_document };
}
export function isSimulationSpec(value: unknown): value is SimulationSpec {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const v = value as Record<string, unknown>;
  return v.version === 1 && simulationEngines.includes(v.engine as SimulationEngine) &&
    [["title", 160], ["description", 500], ["source", 16000]].every(([key, max]) =>
      typeof v[key] === "string" && (v[key] as string).trim().length > 0 && (v[key] as string).length <= Number(max));
}
