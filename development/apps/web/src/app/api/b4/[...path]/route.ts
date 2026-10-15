import { NextResponse } from "next/server";
import { apiJson, apiRequest, checkMutation, sessionValue } from "@/lib/api/auth-bff";

const allowed = [
  /^curricula$/,
  /^curricula\/search$/,
  /^curricula\/[0-9a-f-]+\/tree$/,
  /^curricula\/[0-9a-f-]+\/levels$/,
  /^curricula\/[0-9a-f-]+\/levels\/[0-9a-f-]+\/tree$/,
  /^me\/learning(?:\/[0-9a-f-]+)?$/,
  /^admin\/curricula(?:\/[0-9a-f-]+\/(?:tree|revisions|deletion-review|permanent|restore|export))?$/,
  /^admin\/curricula\/[0-9a-f-]+\/paths\/batch$/,
  /^admin\/curricula\/[0-9a-f-]+\/draft\/rename$/,
  /^admin\/curriculum\/(?:level|subject|domain|category|topic|subtopic)$/,
  /^admin\/curriculum\/(?:curriculum|level|subject|domain|category|topic|subtopic)\/[0-9a-f-]+(?:\/publish|\/archive)?$/,
  /^admin\/curriculum\/imports(?:\/[0-9a-f-]+(?:\/cancel|\/preview|\/commit|\/rows|\/issues|\/review|\/review-rows|\/source-rows)?)?$/,
  /^admin\/students(?:\/[0-9a-f-]+)?$/,
  /^admin\/students\/[0-9a-f-]+\/activity$/,
  /^sessions\/(?:recent|pins)\/clear$/,
  /^sessions(?:\/[0-9a-f-]+(?:\/messages|\/pin|\/recent|\/topic-check(?:\/history)?|\/ask|\/ask-stream|\/simulation|\/capability-check|\/clarifications\/[0-9a-f-]+)?)?$/,
  /^me\/activity$/,
  /^me$/,
];

async function forward(request: Request, context: { params: Promise<{ path: string[] }> }, method: "GET" | "POST" | "PATCH" | "DELETE") {
  const { path } = await context.params;
  const route = path.join("/");
  if (!allowed.some(pattern => pattern.test(route))) return NextResponse.json({ error: { code: "not_found" } }, { status: 404 });
  const session = await sessionValue();
  if (!session) return NextResponse.json({ error: { code: "authentication_required" } }, { status: 401 });
  if (method !== "GET" && !(await checkMutation(request)))
    return NextResponse.json({ error: { code: "csrf_failed" } }, { status: 403 });
  const query = new URL(request.url).search;
  let upstream: Response;
  if (request.headers.get("content-type")?.startsWith("multipart/form-data")) {
    const length = Number(request.headers.get("content-length") ?? 0);
    if (length > 11 * 1024 * 1024)
      return NextResponse.json({ error: { code: "file_too_large", message: "Workbook is too large." } }, { status: 413 });
    const secret = process.env.FLAME_BFF_SHARED_KEY;
    if (!secret) return NextResponse.json({ error: { code: "unavailable" } }, { status: 503 });
    try {
      upstream = await fetch((process.env.FLAME_API_URL ?? "http://127.0.0.1:8000") + "/api/v1/" + route + query, {
        method, headers: { "x-bff-key": secret, "x-flame-session": session },
        body: await request.formData(), cache: "no-store", signal: AbortSignal.timeout(30000),
      });
    } catch {
      return NextResponse.json({ error: { code: "unavailable" } }, { status: 503 });
    }
  } else {
    let body: unknown;
    if (method !== "GET") {
      try { body = await request.json(); }
      catch { return NextResponse.json({ error: { code: "invalid_request" } }, { status: 400 }); }
    }
    const key = request.headers.get("idempotency-key");
    upstream = await apiRequest(route + query, method, body, session, key ? { "idempotency-key": key } : undefined);
  }
  if (method === "GET" && route.endsWith("/export")) {
    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/octet-stream",
        "content-disposition": upstream.headers.get("content-disposition") ?? "attachment",
        "cache-control": "no-store",
      },
    });
  }
  if (route.endsWith("/ask-stream") && upstream.ok && upstream.headers.get("content-type")?.includes("application/x-ndjson"))
    return new Response(upstream.body, { status: 200, headers: { "content-type": "application/x-ndjson", "cache-control": "no-store", "x-accel-buffering": "no" } });
  return NextResponse.json(await apiJson(upstream), { status: upstream.status, headers: { "cache-control": "no-store" } });
}

export const GET = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "GET");
export const POST = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "POST");
export const DELETE = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "DELETE");
export const PATCH = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "PATCH");








