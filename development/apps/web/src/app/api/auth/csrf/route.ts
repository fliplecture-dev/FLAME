import { NextResponse } from "next/server";
import { randomBytes } from "node:crypto";

export async function GET() {
  const token = randomBytes(32).toString("hex");
  const response = NextResponse.json({ csrf: token }, { headers: { "cache-control": "no-store" } });
  response.cookies.set("flame_csrf", token, {
    httpOnly: true, secure: process.env.NODE_ENV === "production",
    sameSite: "strict", path: "/", maxAge: 60 * 60,
  });
  return response;
}
