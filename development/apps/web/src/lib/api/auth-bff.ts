import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const sessionName = "flame_session";
const csrfName = "flame_csrf";
const api = process.env.FLAME_API_URL ?? "http://127.0.0.1:8000";

function upstreamTimeoutMs(path: string) {
  if (path.split("?")[0].startsWith("explore")) return 30000;
  if (path.startsWith("admin/transfers/")) return 240000;
  if (path.startsWith("admin/bulk/")) return 240000;
  if (path.endsWith("/ask") || path.endsWith("/ask-stream") || path.endsWith("/simulation")) return 45000;
  if (/^admin\/curriculum\/imports\/[0-9a-f-]+\/commit$/.test(path)) return 240000;
  if (/^admin\/curriculum\/imports\/[0-9a-f-]+\/preview$/.test(path)) return 60000;
  if (/^admin\/curriculum\/curriculum\/[0-9a-f-]+\/publish$/.test(path)) return 240000;
  return 12000;
}

export function upstreamTimeoutMessage(path:string) {
  const route=path.split("?")[0];
  if(route==="admin/transfers/complete")return "File validation took too long. Your selected file is preserved. Retry this upload to check for completed validation.";
  if(route==="admin/transfers/export")return "Export generation took too long. Request the export again.";
  if(/^sessions\/[^/]+\/ask$/.test(route))return "The learning answer took too long. Your question is preserved. Use Retry on this question to check for a saved answer before trying again.";
  if(/^sessions\/[^/]+\/capability-check$/.test(route))return "The learning request check took too long. An LLM answer has not been requested yet. Your question is preserved; retry shortly.";
  if(route==="sessions")return "The conversation request took too long. Refresh your conversation list before retrying; completion could not be confirmed.";
  if(route.startsWith("admin/curriculum/"))return "The API took too long. Refresh the curriculum status before retrying.";
  return "The API request took too long. Refresh the latest state before retrying; completion could not be confirmed.";
}

export async function apiRequest(path: string, method: string, body?: unknown, session?: string, extraHeaders?: Record<string, string>) {
  const secret = process.env.FLAME_BFF_SHARED_KEY;
  if (!secret) return new Response(JSON.stringify({ error: { code: "unavailable", message: "Authentication is unavailable." } }), { status: 503 });
  try {
    return await fetch(api + "/api/v1/" + path, {
      method,
      headers: {
        "content-type": "application/json",
        "x-bff-key": secret,
        ...(session ? { "x-flame-session": session } : {}),
        ...extraHeaders,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(upstreamTimeoutMs(path)),
    });
  } catch (cause) {
    const timedOut = cause instanceof Error && cause.name === "TimeoutError";
    const reference=crypto.randomUUID();
    console.warn(JSON.stringify({event:"bff_upstream_failure",request_id:reference,method,route:path.split("?")[0].replace(/[0-9a-f]{8}-[0-9a-f-]{27}/gi,":id"),code:timedOut?"upstream_timeout":"upstream_unavailable",timeout_ms:upstreamTimeoutMs(path)}));
    return new Response(JSON.stringify({ request_id:reference, error: {
      code: timedOut ? "upstream_timeout" : "upstream_unavailable",
      message: timedOut ? upstreamTimeoutMessage(path) :
        "The API is unavailable. Try again shortly.",
    } }), { status: timedOut ? 504 : 503 });
  }
}

export function sameOrigin(request: Request) {
  const origin = request.headers.get("origin");
  const expected = process.env.FLAME_WEB_ORIGIN ?? new URL(request.url).origin;
  return !!origin && origin === expected;
}

export async function checkMutation(request: Request) {
  if (!sameOrigin(request)) return false;
  const jar = await cookies();
  const cookie = jar.get(csrfName)?.value;
  const header = request.headers.get("x-flame-csrf");
  return !!cookie && !!header && cookie === header && cookie.length >= 32;
}

export async function sessionValue() {
  return (await cookies()).get(sessionName)?.value;
}

export async function setSession(response: NextResponse, value: string) {
  response.cookies.set(sessionName, value, {
    httpOnly: true, secure: process.env.NODE_ENV === "production",
    sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 7,
  });
}

export function clearSession(response: NextResponse) {
  response.cookies.delete(sessionName);
}

export async function apiJson(response: Response) {
  try { return await response.json(); } catch { return { error: { code: "unavailable", message: "Authentication is unavailable." } }; }
}

export async function guestValue() { return (await cookies()).get("flame_guest")?.value; }
