import { NextResponse } from "next/server";
export const maxDuration = 300;
import { apiJson, apiRequest, checkMutation, sessionValue } from "@/lib/api/auth-bff";

const allowed = [
  /^admin\/transfers\/(?:configuration|authorize|complete|export)$/,
  /^admin\/bulk\/google-sheets\/(?:configuration|connections|template|preview|[0-9a-f-]+\/(?:commit|writeback))$/,
  /^explore(?:\/(?:context|curiosity|summary)|\/(?:resource|tutor|kit)\/[0-9a-f-]+)?$/,
  /^admin\/bulk\/(?:resources|teachers|students|activity-kits)\/(?:preview|export|template)$/,
  /^admin\/bulk\/imports\/[0-9a-f-]+(?:\/(?:review|commit|cancel))?$/,
  /^admin\/resources\/external-video\/inspect$/,
  /^admin\/resources(?:\/uploads|\/paths|\/[0-9a-f-]+(?:\/(?:publish|unpublish|preview|preview-content|delete-preview|delete))?)?$/,
  /^admin\/teachers(?:\/[0-9a-f-]+(?:\/(?:publish|unpublish))?)?$/,
  /^admin\/activity-kits(?:\/[0-9a-f-]+(?:\/(?:publish|unpublish))?)?$/,
  /^resources(?:\/[0-9a-f-]+(?:\/(?:delivery|activity))?)?$/,
  /^sessions\/[0-9a-f-]+\/(?:recommendations|images\/displayed)$/,
  /^sessions\/[0-9a-f-]+\/recommendations\/(?:displayed|[0-9a-f-]+)$/,
];

async function forward(request: Request, context: { params: Promise<{ path: string[] }> },
  method: "GET" | "POST" | "PATCH") {
  const { path } = await context.params;
  const route = path.join("/");
  if (!allowed.some(pattern => pattern.test(route)))
    return NextResponse.json({ error: { code: "not_found" } }, { status: 404 });
  const session = await sessionValue();
  if (!session)
    return NextResponse.json({ error: { code: "authentication_required" } }, { status: 401 });
  if (method !== "GET" && !(await checkMutation(request)))
    return NextResponse.json({ error: { code: "csrf_failed" } }, { status: 403 });
  const query = new URL(request.url).search;
  let upstream: Response;
  if (request.headers.get("content-type")?.startsWith("multipart/form-data")) {
    if (route !== "admin/resources/uploads" && !/^admin\/bulk\/[^/]+\/preview$/.test(route))
      return NextResponse.json({ error: { code: "invalid_upload" } }, { status: 422 });
    const length = Number(request.headers.get("content-length") ?? 0);
    if (length > (route.startsWith("admin/bulk/") ? 121 : 101) * 1024 * 1024)
      return NextResponse.json({ error: { code: "file_too_large" } }, { status: 413 });
    const secret = process.env.FLAME_BFF_SHARED_KEY;
    if (!secret)
      return NextResponse.json({ error: { code: "unavailable" } }, { status: 503 });
    try {
      upstream = await fetch((process.env.FLAME_API_URL ?? "http://127.0.0.1:8000") + "/api/v1/" + route, {
        method, headers: { "x-bff-key": secret, "x-flame-session": session },
        body: await request.formData(), cache: "no-store", signal: AbortSignal.timeout(150000),
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
    upstream = await apiRequest(route + query, method, body, session);
  }
  if (method === "GET" && (route.endsWith("/preview-content") || /^admin\/bulk\/[^/]+\/(?:export|template)$/.test(route))) {
    if (!upstream.ok) return NextResponse.json(await apiJson(upstream), { status: upstream.status });
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/octet-stream",
        "cache-control": "private, no-store",
        ...(upstream.headers.get("content-disposition") ? { "content-disposition": upstream.headers.get("content-disposition")! } : {}),
        "x-content-type-options": "nosniff",
      },
    });
  }
  return NextResponse.json(await apiJson(upstream), {
    status: upstream.status, headers: { "cache-control": "no-store" },
  });
}

export const GET = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "GET");
export const POST = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "POST");
export const PATCH = (request: Request, context: { params: Promise<{ path: string[] }> }) => forward(request, context, "PATCH");
