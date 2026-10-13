"use client";
import { useEffect, useRef, useState } from "react";
import { ChevronUp, ShieldCheck, UserRound } from "lucide-react";
import Link from "next/link";
import { SignOutButton } from "@/features/auth/sign-out-button";

type Profile = { display_name: string | null; email: string | null; role: string };
export function StudentProfile({ compact = false }: { compact?: boolean }) {
  const root = useRef<HTMLDetailsElement>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);
  useEffect(() => {
    fetch("/api/me", { cache: "no-store" }).then(response => response.ok ? response.json() : null).then(setProfile).catch(() => setProfile(null));
    const outside = (e: PointerEvent) => { if (root.current && !root.current.contains(e.target as Node)) root.current.open = false; };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape" && root.current?.open) { e.stopPropagation(); root.current.open = false; root.current.querySelector("summary")?.focus(); } };
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", escape, true);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape, true); };
  }, []);
async function deleteAccount() {
    setDeleting(true); setDeleteError("");
    try {
      const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store" });
      if (!csrfResponse.ok) throw new Error("Could not authorize deletion.");
      const { csrf } = await csrfResponse.json();
      const response = await fetch("/api/b4/me", { method: "DELETE",
        headers: { "content-type": "application/json", "x-flame-csrf": csrf },
        body: JSON.stringify({ confirm: true }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result?.error?.code === "account_deletion_unavailable"
        ? "Account deletion is temporarily unavailable. Please try again later."
        : "Account deletion failed. Please try again.");
      await fetch("/api/auth/logout", { method: "POST", headers: { "x-flame-csrf": csrf } });
      window.location.assign(result.status === "pending_provider" ? "/sign-in?deletion=pending" : "/sign-in?deletion=complete");
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "Account deletion failed.");
      setDeleting(false);
    }
  }
  return <>{profile?.role === "admin" && <Link href="/admin"
    className={`profile-admin-link ${compact ? "profile-admin-link-compact" : ""}`}
    aria-label={compact ? "Open admin dashboard" : undefined} title="Admin dashboard">
    <ShieldCheck size={18} aria-hidden="true" /><span>Admin dashboard</span>
  </Link>}<details ref={root} className={`profile-section ${compact ? "profile-compact" : ""}`}><summary className="student-profile" aria-label={compact ? "Open profile details" : undefined} title={compact ? "Profile" : undefined}><span className="profile-avatar"><UserRound size={19} aria-hidden="true" /></span><span className="profile-text"><strong>{profile?.display_name || "Your learning space"}</strong><span>{profile?.role === "admin" ? "Admin" : "Student"}</span></span><ChevronUp size={16} aria-hidden="true" /><span className="sr-only">Open profile details</span></summary><div className="profile-popover"><strong>{profile?.email || "Student workspace"}</strong>{profile ? <><SignOutButton /><button type="button" onClick={() => setConfirmDelete(true)}>Delete account</button>{confirmDelete && <div role="group" aria-label="Confirm account deletion"><p>This removes your FLAME learning paths, conversations, and activity and signs you out.</p><button type="button" disabled={deleting} onClick={() => void deleteAccount()}>{deleting ? "Deleting…" : "Confirm account deletion"}</button><button type="button" disabled={deleting} onClick={() => setConfirmDelete(false)}>Cancel</button></div>}{deleteError && <p role="alert">{deleteError}</p>}</> : <><Link href="/sign-in">Sign in</Link><p>You’re using a local workspace. Your student account isn’t connected yet.</p><small>Pins, recent items, and drafts stay in this tab until you refresh.</small></>}</div></details></>;
}



