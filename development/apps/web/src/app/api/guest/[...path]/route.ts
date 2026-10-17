import { NextResponse } from "next/server";
import { apiJson, apiRequest, checkMutation, guestValue, sessionValue } from "@/lib/api/auth-bff";
async function forward(request: Request, context: { params: Promise<{ path: string[] }> }, method: "GET" | "POST") {
  const route = (await context.params).path.join("/");
  const allowed = method === "GET" ? /^(?:usage|me)$/.test(route) : /^sessions(?:\/[0-9a-f-]+\/(?:ask|ask-stream|capability-check|simulation))?$/.test(route);
  if (!allowed) return NextResponse.json({ error: { code: "not_found" } }, { status: 404 });
  if (method === "POST" && !await checkMutation(request)) return NextResponse.json({ error: { code: "csrf_failed" } }, { status: 403 });
  if (await sessionValue()) return NextResponse.json({ error: { code: "signed_in_allowance_required" } }, { status: 403 });
  const guest = await guestValue();
  if (!guest) return NextResponse.json({ error: { code: "guest_access_required" } }, { status: 401 });
  let body: unknown;
  if (method === "POST") { try { body = await request.json(); } catch { return NextResponse.json({ error: { code: "invalid_request" } }, { status: 400 }); } }
  const key = request.headers.get("idempotency-key");
  const upstream = await apiRequest("guest/" + route, method, body, undefined, { "x-flame-guest": guest, ...(key ? { "idempotency-key": key } : {}) });
  if (route.endsWith("/ask-stream") && upstream.ok && upstream.headers.get("content-type")?.includes("application/x-ndjson"))
    return new Response(upstream.body, { headers: { "content-type": "application/x-ndjson", "cache-control": "no-store", "x-accel-buffering": "no" } });
  return NextResponse.json(await apiJson(upstream), { status: upstream.status, headers: { "cache-control": "no-store" } });
}
export const GET = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "GET");
export const POST = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "POST");
