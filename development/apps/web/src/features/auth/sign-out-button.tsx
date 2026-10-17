"use client";

import { useState } from "react";
import { LoaderCircle, LogOut } from "lucide-react";

export function SignOutButton({ className, showIcon = false }: { className?: string; showIcon?: boolean }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function signOut() {
    setBusy(true);
    setError("");
    try {
      const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store" });
      if (!csrfResponse.ok) throw new Error("CSRF request failed");
      const { csrf } = await csrfResponse.json();
      const response = await fetch("/api/auth/logout", {
        method: "POST", headers: { "x-flame-csrf": csrf },
      });
      if (!response.ok) throw new Error("Sign-out request failed");
      window.location.assign("/sign-in");
    } catch {
      setError("Sign out failed. Please try again.");
      setBusy(false);
    }
  }

  return <>
    <button className={className} type="button" onClick={signOut} disabled={busy} aria-busy={busy}>
      {showIcon && (busy ? <LoaderCircle size={18} aria-hidden="true" /> : <LogOut size={18} aria-hidden="true" />)}
      <span>{busy ? "Signing out…" : "Sign out"}</span>
    </button>
    {error && <p role="alert">{error}</p>}
  </>;
}
