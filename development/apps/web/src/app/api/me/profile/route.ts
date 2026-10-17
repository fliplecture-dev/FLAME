import { NextResponse } from "next/server";
import { apiJson, apiRequest, checkMutation, sessionValue } from "@/lib/api/auth-bff";
async function forward(request: Request, method: "GET" | "PATCH") {
  const session = await sessionValue();
  if (!session) return NextResponse.json({ error: { code: "authentication_required" } }, { status: 401 });
  if (method === "PATCH" && !await checkMutation(request)) return NextResponse.json({ error: { code: "csrf_failed" } }, { status: 403 });
  let body: unknown;
  if (method === "PATCH") { try { body = await request.json(); } catch { return NextResponse.json({ error: { code: "invalid_request" } }, { status: 400 }); } }
  const upstream = await apiRequest("me/profile", method, body, session);
  return NextResponse.json(await apiJson(upstream), { status: upstream.status, headers: { "cache-control": "no-store" } });
}
export const GET = (request: Request) => forward(request, "GET");
export const PATCH = (request: Request) => forward(request, "PATCH");
