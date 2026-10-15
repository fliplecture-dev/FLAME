import { isSimulationSpec } from "./spec";
import type { SimulationSpec } from "./spec";

type Outcome = { status: "ready"; spec: SimulationSpec } | { status: "expired" | "ineligible" | "limited" | "error" };
type Request = (start: boolean, signal: AbortSignal) => Promise<unknown>;

/** Poll only the existing job after the first request; never request regeneration. */
export async function requestSimulation(request: Request, fresh: boolean, timeoutMs = 90000, pollMs = 1000): Promise<Outcome> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error("simulation_timeout"));
    }, timeoutMs);
  });
  try {
    let start = fresh;
    while (true) {
      const value = await Promise.race([request(start, controller.signal), deadline]);
      start = false;
      if (isSimulationSpec(value)) {
        // Strip transport fields before sending source to the strict compiler contract.
        return { status: "ready", spec: { version: 1, engine: value.engine, title: value.title, description: value.description, source: value.source } };
      }
      const status = (value as { status?: unknown } | null)?.status;
      if (status === "expired" || status === "ineligible" || status === "limited" || status === "error") return { status };
      if (status !== "pending") return { status: "error" };
      await Promise.race([new Promise<void>(resolve => setTimeout(resolve, pollMs)), deadline]);
    }
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}
