import { NextResponse } from "next/server";
import { randomBytes } from "node:crypto";
import { cookies } from "next/headers";

export async function GET() {
  // Parallel answer, recommendation and compiler calls must not invalidate each other.
  const existing = (await cookies()).get("flame_csrf")?.value;
  const token = existing && /^[a-f0-9]{64}$/.test(existing) ? existing : randomBytes(32).toString("hex");
  const response = NextResponse.json({ csrf: token }, { headers: { "cache-control": "no-store" } });
  response.cookies.set("flame_csrf", token, {
    httpOnly: true, secure: process.env.NODE_ENV === "production",
    sameSite: "strict", path: "/", maxAge: 60 * 60,
  });
  return response;
}
