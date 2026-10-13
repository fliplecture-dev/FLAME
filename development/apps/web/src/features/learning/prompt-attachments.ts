export interface PromptAttachment { id: string; file: File; kind: "image" | "audio" | "file" }
export const MAX_ATTACHMENTS = 5;
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const MAX_TOTAL_BYTES = 25 * 1024 * 1024;
export const IMAGE_ACCEPT = ".png,.jpg,.jpeg,.webp,.gif";
export const FILE_ACCEPT = `${IMAGE_ACCEPT},.pdf,.txt,.md,.csv,.xls,.xlsx,.docx,.mp3,.wav,.m4a,.mp4,.webm,.ogg`;
const allowed: Record<string, string[]> = {
  png: ["image/png"], jpg: ["image/jpeg"], jpeg: ["image/jpeg"], webp: ["image/webp"], gif: ["image/gif"],
  pdf: ["application/pdf"], txt: ["text/plain"], md: ["text/markdown", "text/plain"], csv: ["text/csv", "application/vnd.ms-excel", "text/plain"],
  xls: ["application/vnd.ms-excel"], xlsx: ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
  docx: ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
  mp3: ["audio/mpeg"], wav: ["audio/wav", "audio/x-wav"], m4a: ["audio/mp4", "audio/x-m4a"], mp4: ["audio/mp4"], webm: ["audio/webm"], ogg: ["audio/ogg", "application/ogg"],
};
export function attachmentKind(file: File): PromptAttachment["kind"] {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? "";
  if (["png", "jpg", "jpeg", "webp", "gif"].includes(ext)) return "image";
  if (["mp3", "wav", "m4a", "mp4", "webm", "ogg"].includes(ext)) return "audio";
  return "file";
}
export function validateAttachments(existing: PromptAttachment[], files: File[]) {
  const accepted: File[] = [], errors: string[] = [];
  let total = existing.reduce((sum, item) => sum + item.file.size, 0);
  for (const file of files) {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? "";
    const mime = file.type.split(';')[0];
    if (!allowed[ext] || (mime && mime !== "application/octet-stream" && !allowed[ext].includes(mime))) { errors.push(`${file.name}: this file type isn’t supported.`); continue; }
    if (file.size === 0) { errors.push(`${file.name}: the file is empty.`); continue; }
    if (file.size > MAX_FILE_BYTES) { errors.push(`${file.name}: choose a file under 10 MB.`); continue; }
    if ([...existing.map(item => item.file), ...accepted].some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) { errors.push(`${file.name}: already attached.`); continue; }
    if (existing.length + accepted.length >= MAX_ATTACHMENTS) { errors.push("You can attach up to 5 files per question."); continue; }
    if (total + file.size > MAX_TOTAL_BYTES) { errors.push("Attachments must total 25 MB or less."); continue; }
    accepted.push(file); total += file.size;
  }
  return { accepted, errors: [...new Set(errors)] };
}
export function formatFileSize(bytes: number) { return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.ceil(bytes / 1024))} KB`; }
