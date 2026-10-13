export class B9Error extends Error {
  code: string;
  status: number;
  reference?: string;
  field?: string;
  fields: string[];
  invalidPaths: { topic_id: string; subtopic_id: string | null }[];
  constructor(data: { error?: { code?: string; message?: string; field?: string; fields?: string[]; invalid_paths?: { topic_id: string; subtopic_id: string | null }[] }; detail?: string; request_id?: string }, status: number) {
    super(data.error?.message || data.detail || "The request could not be completed.");
    this.code = data.error?.code ?? "request_failed"; this.status = status;
    this.reference = data.request_id; this.field = data.error?.field;
    this.fields = data.error?.fields ?? (this.field ? [this.field] : []);
    this.invalidPaths = data.error?.invalid_paths ?? [];
  }
}

export async function b9Get<T>(path: string): Promise<T> {
  const response = await fetch("/api/b9/" + path, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new B9Error(data, response.status);
  return data as T;
}

export async function b9Mutation<T>(path: string, method: "POST" | "PATCH", body: unknown): Promise<T> {
  const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store" });
  if (!csrfResponse.ok) throw new Error("Could not authorize this change.");
  const { csrf } = await csrfResponse.json();
  const response = await fetch("/api/b9/" + path, {
    method, headers: { "content-type": "application/json", "x-flame-csrf": csrf },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new B9Error(data, response.status);
  return data as T;
}

export async function b9Upload(file: File): Promise<{ upload_id: string; mime_type: string; byte_size: number }> {
  const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store" });
  if (!csrfResponse.ok) throw new Error("Could not authorize this upload.");
  const { csrf } = await csrfResponse.json();
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/b9/admin/resources/uploads", {
    method: "POST", headers: { "x-flame-csrf": csrf }, body,
  });
  const data = await response.json();
  if (!response.ok) throw new B9Error(data, response.status);
  return data;
}
