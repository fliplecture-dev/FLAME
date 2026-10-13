import { NextResponse } from "next/server";
import { apiJson, apiRequest, sessionValue } from "@/lib/api/auth-bff";

export async function GET() {
  const session = await sessionValue();
  if (!session) return NextResponse.json({ error: { code: "unauthenticated" } }, { status: 401 });
  const upstream = await apiRequest("me", "GET", undefined, session);
  return NextResponse.json(await apiJson(upstream), { status: upstream.status, headers: { "cache-control": "no-store" } });
}
