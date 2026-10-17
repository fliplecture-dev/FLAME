import { NextResponse } from "next/server";
import { apiRequest, apiJson, checkMutation, guestValue, sessionValue } from "@/lib/api/auth-bff";
export async function POST(request: Request) {
  if (!await checkMutation(request)) return NextResponse.json({ error: { code: "csrf_failed" } }, { status: 403 });
  if (await sessionValue()) return NextResponse.json({ error: { code: "signed_in_allowance_required" } }, { status: 403 });
  const current = await guestValue();
  if (current) {
    const upstream = await apiRequest("guest/me", "GET", undefined, undefined, { "x-flame-guest": current });
    return NextResponse.json(await apiJson(upstream), { status: upstream.status, headers: { "cache-control": "no-store" } });
  }
  const upstream = await apiRequest("guest/identity", "POST");
  const data = await apiJson(upstream);
  if (!upstream.ok || typeof data.token !== "string") return NextResponse.json({ error: { code: "guest_unavailable", message: "Guest access is unavailable. Try again shortly." } }, { status: upstream.ok ? 503 : upstream.status });
  const response = NextResponse.json({ role: "guest" }, { headers: { "cache-control": "no-store" } });
  response.cookies.set("flame_guest", data.token, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 7 * 24 * 60 * 60 });
  return response;
}
