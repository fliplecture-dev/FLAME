"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronRight, ChevronUp, LogIn, ShieldCheck, Trash2, UserRound } from "lucide-react";
import Link from "next/link";
import { SignOutButton } from "@/features/auth/sign-out-button";
type Profile = { display_name: string | null; email: string | null; role: string };
export function StudentProfile({ compact = false, guest = false, allowance }: { compact?: boolean; guest?: boolean; allowance?: ReactNode }) {
  const root = useRef<HTMLDetailsElement>(null);
  const deleteTrigger = useRef<HTMLButtonElement>(null);
  const cancelDelete = useRef<HTMLButtonElement>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);
  useEffect(() => {
    if (!guest) fetch("/api/me", { cache: "no-store" }).then(response => response.ok ? response.json() : null).then(setProfile).catch(() => setProfile(null));
    const outside = (e: PointerEvent) => { if (root.current && !root.current.contains(e.target as Node)) root.current.open = false; };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape" && root.current?.open) { e.preventDefault(); e.stopPropagation(); root.current.open = false; root.current.querySelector("summary")?.focus(); } };
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", escape, true);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape, true); };
  }, [guest]);
  useEffect(() => { if (confirmDelete) cancelDelete.current?.focus(); }, [confirmDelete]);
  function dismissDeletion() {
    setConfirmDelete(false);
    setDeleteError("");
    deleteTrigger.current?.focus();
  }
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

  const name = profile?.display_name || (guest ? "Guest" : "Your learning space");

  return <>

    {profile?.role === "admin" && <Link href="/admin"

      className={`profile-admin-link ${compact ? "profile-admin-link-compact" : ""}`}

      aria-label={compact ? "Open admin dashboard" : undefined} title="Admin dashboard">

      <ShieldCheck size={18} aria-hidden="true" /><span>Admin dashboard</span>

    </Link>}

    <details ref={root} className={`profile-section ${compact ? "profile-compact" : ""}`}

      onToggle={event => { if (!event.currentTarget.open) { setConfirmDelete(false); setDeleteError(""); } }}>

      <summary className="student-profile" aria-label="Open profile details" title={compact ? "Profile" : undefined}>

        <span className="profile-avatar"><UserRound size={19} aria-hidden="true" /></span>

        <span className="profile-text"><strong>{name}</strong><span>{profile?.role === "admin" ? "Admin" : guest ? "Curiosity" : "Student"}</span></span>

        <ChevronUp size={16} aria-hidden="true" />

      </summary>

      <div className="profile-popover">

        <div className="account-menu-header">

          <span className="account-menu-avatar"><UserRound size={20} aria-hidden="true" /></span>

          <div><strong>{name}</strong><span>{profile?.email || "Explore with FLAME"}</span></div>

        </div>

        {allowance}

        {profile ? <>

          <div className="account-menu-actions">

            <Link className="account-menu-action" href="/profile">

              <UserRound size={18} aria-hidden="true" /><span>Student profile</span><ChevronRight size={15} aria-hidden="true" />

            </Link>

            <SignOutButton className="account-menu-action" showIcon />

          </div>

          <div className="account-menu-danger">

            <button ref={deleteTrigger} className="account-menu-action account-menu-delete" type="button"

              aria-expanded={confirmDelete} disabled={deleting} onClick={() => setConfirmDelete(true)}>

              <Trash2 size={18} aria-hidden="true" /><span>Delete account</span>

            </button>

            {confirmDelete && <div className="account-delete-confirmation" role="group" aria-label="Confirm account deletion">

              <strong>Delete your account?</strong>

              <p>This removes your FLAME learning paths, conversations, and activity and signs you out.</p>

              <div className="account-delete-actions">

                <button ref={cancelDelete} className="account-delete-cancel" type="button" disabled={deleting} onClick={dismissDeletion}>Cancel</button>

                <button className="account-delete-confirm" type="button" disabled={deleting} onClick={() => void deleteAccount()}>

                  {deleting ? "Deleting…" : "Confirm account deletion"}

                </button>

              </div>

            </div>}

            {deleteError && <p className="account-menu-error" role="alert">{deleteError}</p>}

          </div>

        </> : <div className="account-menu-guest">

          <Link className="account-menu-action" href="/sign-in"><LogIn size={18} aria-hidden="true" /><span>Sign in</span><ChevronRight size={15} aria-hidden="true" /></Link>

          <p>{guest ? "You’re exploring Curiosity as a guest. Sign in for Study and your student profile." : "You’re using a local workspace. Your student account isn’t connected yet."}</p>

          <small>Pins, recent items, and drafts stay in this tab until you refresh.</small>

        </div>}

      </div>

    </details>

  </>;

}

