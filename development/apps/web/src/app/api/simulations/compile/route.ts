import { Worker } from "node:worker_threads";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { apiRequest, checkMutation, sessionValue } from "@/lib/api/auth-bff";
import { isSimulationSpec } from "@/lib/simulations/spec";
import { trustedAdapter, runtimeDir } from "@/lib/simulations/compiler.cjs";

export const runtime = "nodejs";
export const maxDuration = 30;
let compiling = 0;
function compile(engine: string, source: string, signal: AbortSignal): Promise<string> {
  return new Promise((resolve, reject) => {
    // Native Node worker: bypass Turbopack's client-style Worker URL rewriting.
    const worker = Reflect.construct(Worker, [path.join(runtimeDir, "compile.cjs"), { workerData: { engine, source }, resourceLimits: { maxOldGenerationSizeMb: 128 } }]) as Worker;
    let settled = false;
    const finish = (error?: Error, result?: string) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer); signal.removeEventListener("abort", abort); void worker.terminate();
      if (error) reject(error); else resolve(result!);
    };
    const abort = () => finish(new Error("cancelled"));
    const timer = setTimeout(() => finish(new Error("compile_timeout")), 10000);
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) { abort(); return; }
    worker.once("message", value => value.error ? finish(new Error("compile_failed")) : finish(undefined, value.worker));
    worker.once("error", () => finish(new Error("compile_worker_failed")));
    worker.once("exit", () => { if (!settled) finish(new Error("compile_failed")); });
  });
}
export async function POST(request: Request) {
  const headers = { "cache-control": "no-store" };
  const session = await sessionValue();
  if (!session) return Response.json({ error: "authentication_required" }, { status: 401, headers });
  if (!await checkMutation(request)) return Response.json({ error: "csrf_failed" }, { status: 403, headers });
  if (!(await apiRequest("me", "GET", undefined, session)).ok) return Response.json({ error: "authentication_required" }, { status: 401, headers });
  // Bound streamed/chunked input too; Content-Length alone is not sufficient.
  let text = "";
  const reader = request.body?.getReader();
  if (!reader) return Response.json({ error: "invalid_simulation" }, { status: 422, headers });
  const decoder = new TextDecoder();
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
    if (text.length > 24000) { await reader.cancel(); return Response.json({ error: "source_too_large" }, { status: 413, headers }); }
  }
  let spec: unknown;
  try { spec = JSON.parse(text); } catch { return Response.json({ error: "invalid_simulation" }, { status: 422, headers }); }
  if (!isSimulationSpec(spec) || Object.keys(spec).some(key => !["version", "engine", "title", "description", "source"].includes(key))) return Response.json({ error: "invalid_simulation" }, { status: 422, headers });
  if (compiling >= 2) return Response.json({ error: "compiler_busy" }, { status: 429, headers });
  compiling++;
  try {
    const [worker, adapter, frame] = await Promise.all([
      compile(spec.engine, spec.source, request.signal), trustedAdapter(spec.engine), readFile(path.join(runtimeDir, "frame.js"), "utf8"),
    ]);
    const extra = spec.engine === "rive" ? {
      art: (await readFile(path.join(runtimeDir, "assets/weather.riv"))).toString("base64"),
      wasm: (await readFile(path.join(process.cwd(), "node_modules/@rive-app/canvas-lite/rive.wasm"))).toString("base64"),
    } : {};
    return Response.json({ worker, adapter, frame, ...extra }, { headers });
  } catch (error) { return Response.json({ error: "simulation_compilation_failed", code: error instanceof Error && ["compile_timeout", "compile_failed", "compile_worker_failed", "cancelled"].includes(error.message) ? error.message : "runtime_dependency_unavailable" }, { status: 422, headers }); }
  finally { compiling--; }
}
