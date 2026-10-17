import { NextResponse } from "next/server";
import { apiJson, apiRequest, checkMutation, sessionValue } from "@/lib/api/auth-bff";

async function forward(request: Request, context: { params: Promise<{ path?: string[] }> }, method: "GET" | "POST" | "PATCH") {
  if (!process.env.FLAME_BFF_SHARED_KEY) return NextResponse.json({ error: { message: "Catalogue search isn't connected yet. Please try again later." } }, { status: 503 });
  const { path = [] } = await context.params;
  const route = path.join("/");
  const publicRoute = route === "" || /^(books|kits|teachers|classes)\/[0-9a-f-]{36}$/.test(route);
  const adminRoute = /^admin\/(books|classes)(?:\/[0-9a-f-]{36}(?:\/publication)?)?$/.test(route);
  if ((!publicRoute && !adminRoute) || (publicRoute && method !== "GET")) return NextResponse.json({ error: { message: "Not found." } }, { status: 404 });
  const session = adminRoute ? await sessionValue() : undefined;
  if (adminRoute && !session) return NextResponse.json({ error: { message: "Sign in to manage the catalogue." } }, { status: 401 });
  if (method !== "GET" && !(await checkMutation(request))) return NextResponse.json({ error: { message: "Could not authorize this change." } }, { status: 403 });
  let body;
  if (method !== "GET") {
    try { body = await request.json(); } catch { return NextResponse.json({ error: { message: "Invalid request." } }, { status: 400 }); }
  }
  const upstreamRoute = adminRoute ? `admin/catalogue/${route.slice(6)}` : `catalogue${route ? "/" + route : ""}`;
  const response = await apiRequest(upstreamRoute + new URL(request.url).search, method, body, session);
  return NextResponse.json(await apiJson(response), { status: response.status, headers: { "Cache-Control": "no-store" } });
}
export const GET = (request: Request, context: { params: Promise<{ path?: string[] }> }) => forward(request, context, "GET");
export const POST = (request: Request, context: { params: Promise<{ path?: string[] }> }) => forward(request, context, "POST");
export const PATCH = (request: Request, context: { params: Promise<{ path?: string[] }> }) => forward(request, context, "PATCH");
