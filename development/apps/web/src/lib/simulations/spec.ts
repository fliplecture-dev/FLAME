export const simulationEngines = ["matter", "three", "r3f", "phaser", "rive", "html5"] as const;
export type SimulationEngine = typeof simulationEngines[number];
export type SimulationSpec = { version: 1; engine: SimulationEngine; title: string; description: string; source: string };
export function isSimulationSpec(value: unknown): value is SimulationSpec {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const v = value as Record<string, unknown>;
  return v.version === 1 && simulationEngines.includes(v.engine as SimulationEngine) &&
    [["title", 160], ["description", 500], ["source", 16000]].every(([key, max]) =>
      typeof v[key] === "string" && (v[key] as string).trim().length > 0 && (v[key] as string).length <= Number(max));
}
