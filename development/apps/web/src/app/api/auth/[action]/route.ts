import { NextResponse } from "next/server";
import { apiJson, apiRequest, checkMutation, clearSession, sessionValue, setSession } from "@/lib/api/auth-bff";

const actions = new Set(["register", "login", "recover", "verify", "reset-password", "refresh", "logout"]);

export async function POST(request: Request, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  if (!actions.has(action)) return NextResponse.json({ error: { code: "not_found" } }, { status: 404 });
  if (!(await checkMutation(request))) return NextResponse.json({ error: { code: "csrf_failed", message: "Refresh this page and try again." } }, { status: 403 });
  let body: unknown = undefined;
  if (!["logout", "refresh"].includes(action)) {
    try { body = await request.json(); }
    catch { return NextResponse.json({ error: { code: "invalid_request", message: "Invalid request." } }, { status: 400 }); }
  }
  const current = await sessionValue();
  if (action === "reset-password") body = { ...(body as object), session: current };
  const result = await apiRequest("auth/" + action, "POST", body, current);
  const data = await apiJson(result);
  const response = NextResponse.json(
    result.ok && (action === "login" || action === "verify") ? { status: "signed_in", type: data.type } : data,
    { status: result.status, headers: { "cache-control": "no-store" } },
  );
  if (result.ok && (action === "login" || action === "verify") && typeof data.session === "string")
    await setSession(response, data.session);
  if (action === "logout" && result.ok) clearSession(response);
  return response;
}
