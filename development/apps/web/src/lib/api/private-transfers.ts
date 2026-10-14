"use client";

type Target = { purpose: "resource" | "curriculum" | "bulk"; curriculum_id?: string; kind?: string };
type Permit = { ticket: string; upload_url: string; storage_origin: string; expires_in: number };
type State = { permit?: Permit; uploaded?: boolean; pending?: Promise<unknown | null> };
const attempts = new WeakMap<File, Map<string, State>>();
const mimeTypes: Record<string, string> = { html: "text/html", htm: "text/html", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", gif: "image/gif", mp4: "video/mp4", webm: "video/webm", zip: "application/zip", xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" };

async function configuration() {
  const response = await fetch("/api/b9/admin/transfers/configuration", { cache: "no-store", credentials: "same-origin" });
  if (response.status === 404) return { direct_upload: false };
  const data = await response.json();
  if (!response.ok) throw new Error(data?.error?.message || "Upload configuration could not be loaded.");
  return data as { direct_upload: boolean };
}

async function mutation<T>(action: string, body: unknown): Promise<T> {
  const auth = await fetch("/api/auth/csrf", { cache: "no-store", credentials: "same-origin" });
  if (!auth.ok) throw new Error("Could not authorize this upload.");
  const { csrf } = await auth.json();
  const response = await fetch("/api/b9/admin/transfers/" + action, {
    method: "POST", credentials: "same-origin",
    headers: { "content-type": "application/json", "x-flame-csrf": csrf }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    const code = data?.error?.code || data?.detail;
    const messages: Record<string, string> = {
      upload_content_mismatch: "The uploaded file did not match the selected file. Select it again and retry.",
      upload_size_mismatch: "The uploaded file size changed. Select it again and retry.",
      upload_in_progress: "This file is still being validated. Wait briefly and retry the same upload.",
      upload_ticket_expired_or_invalid: "The upload authorization expired. Try uploading again.",
      staged_upload_missing: "The file has not reached private storage. Try uploading again.",
    };
    const reference = typeof data?.request_id === "string" && /^[a-zA-Z0-9_-]{1,100}$/.test(data.request_id) ? " Reference: " + data.request_id : "";
    const error = new Error((messages[code] || data?.error?.message || (typeof data?.detail === "string" ? data.detail : "The file could not be validated.")) + reference);
    Object.assign(error, { status: response.status, code });
    throw error;
  }
  return data as T;
}

function checkedUrl(value: string, origin: string, prefix: string) {
  const url = new URL(value);
  if (url.protocol !== "https:" || url.origin !== new URL(origin).origin || !url.pathname.startsWith(prefix) || url.username || url.password)
    throw new Error("The storage service returned an invalid transfer address.");
  return url.href;
}

export async function uploadPrivateFile<T>(file: File, target: Target): Promise<T | null> {
  const key = JSON.stringify(target);
  const entries = attempts.get(file) ?? new Map<string, State>();
  attempts.set(file, entries);
  const state = entries.get(key) ?? {};
  entries.set(key, state);
  if (state.pending) return state.pending as Promise<T | null>;
  const pending = (async () => {
    if (!(await configuration()).direct_upload) { entries.delete(key); return null; }
    if (!file.size || file.size > 120 * 1024 * 1024) throw new Error("Select a nonempty file within the upload size limit.");
    if (!state.permit) {
      const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", await file.arrayBuffer()));
      state.permit = await mutation<Permit>("authorize", {
        ...target, filename: file.name, byte_size: file.size,
        mime_type: file.type || mimeTypes[file.name.split(".").at(-1)?.toLowerCase() ?? ""] || "application/octet-stream",
        sha256: Array.from(digest, byte => byte.toString(16).padStart(2, "0")).join(""),
      });
    }
    const permit = state.permit;
    if (!state.uploaded) {
      const url = checkedUrl(permit.upload_url, permit.storage_origin, "/storage/v1/object/upload/sign/");
      const result = await fetch(url, { method: "PUT", body: file, credentials: "omit", redirect: "error",
        referrerPolicy: "no-referrer", headers: { "content-type": "application/octet-stream", "x-upsert": "false" } });
      if (!result.ok) {
        const data = await result.json().catch(() => ({}));
        if (result.status !== 409 && data.error !== "Duplicate" && String(data.statusCode) !== "409") {
          if ([401, 403, 410].includes(result.status)) state.permit = undefined;
          throw new Error("Private storage could not accept this file. Your selected file is kept; retry when the service is available.");
        }
      }
      state.uploaded = true;
    }
    try {
      const result = await mutation<T>("complete", { ticket: permit.ticket });
      entries.delete(key);
      return result;
    } catch (error) {
      const failure = error as { status?: number; code?: string };
      if (failure.status === 410 || failure.code === "staged_upload_missing") { state.permit = undefined; state.uploaded = false; }
      throw error;
    }
  })();
  state.pending = pending;
  try { return await pending; }
  finally { state.pending = undefined; }
}

export type ExportTarget = { purpose: "bulk" | "curriculum"; kind?: string; action?: "template" | "export"; package?: boolean; curriculum_id?: string; source?: "draft" | "published" | "revision"; revision_number?: number };
export async function privateExport(target: ExportTarget): Promise<{ blob: Blob; filename: string } | null> {
  if (!(await configuration()).direct_upload) return null;
  const artifact = await mutation<{ url: string; storage_origin: string; filename: string }>("export", target);
  const url = checkedUrl(artifact.url, artifact.storage_origin, "/storage/v1/object/sign/");
  const response = await fetch(url, { credentials: "omit", redirect: "error", referrerPolicy: "no-referrer", cache: "no-store" });
  if (!response.ok) throw new Error("The export download expired or could not be loaded. Request the export again.");
  return { blob: await response.blob(), filename: artifact.filename };
}
