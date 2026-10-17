let creating: Promise<void> | null = null;
/** Cookie is HttpOnly; the browser never reads or submits a guest identity. */
export function ensureGuestAccess(): Promise<void> {
  if (!creating) creating = (async () => {
    const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store" });
    if (!csrfResponse.ok) throw new Error("Guest access is unavailable. Please try again.");
    const { csrf } = await csrfResponse.json();
    const response = await fetch("/api/auth/guest", { method: "POST", headers: { "x-flame-csrf": csrf } });
    if (!response.ok) throw new Error("Guest access is unavailable. Please try again.");
  })().catch(error => { creating = null; throw error; });
  return creating;
}
