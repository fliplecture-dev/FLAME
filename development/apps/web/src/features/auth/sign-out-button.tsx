"use client";

import { useState } from "react";

export function SignOutButton() {
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

  return <><button type="button" onClick={signOut} disabled={busy}>{busy ? "Signing out…" : "Sign out"}</button>{error && <p role="alert">{error}</p>}</>;
}