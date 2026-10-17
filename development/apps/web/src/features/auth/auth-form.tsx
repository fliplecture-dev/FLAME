"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { FliplectureLogo } from "@/components/ui/fliplecture-logo";
import { pendingQuestionReturnPath, safeReturnPath } from "@/features/discovery/question-intent";

type Mode = "login" | "register" | "recover" | "callback";
type Profile = { role: "member" | "admin" };
const titles = { login: "Sign in", register: "Create your account", recover: "Reset your password", callback: "Confirm your email" };

export function AuthForm({ mode, admin = false }: { mode: Mode; admin?: boolean }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState<"verify" | "reset">("verify");
  const [returnPath, setReturnPath] = useState<string | null>(null);
  const [verification, setVerification] = useState<{ token_hash: string; type: string } | null>(null);
  useEffect(() => {
    setReturnPath(safeReturnPath(new URLSearchParams(window.location.search).get("next")) ?? pendingQuestionReturnPath());
    if (mode !== "callback") return;
    const query = new URLSearchParams(window.location.search);
    const token_hash = query.get("token_hash");
    const type = query.get("type");
    if (token_hash && type) {
      setVerification({ token_hash, type });
      history.replaceState(null, "", "/auth/callback");
    }
  }, [mode]);
  async function mutate(action: string, body: object) {
    const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store" });
    if (!csrfResponse.ok) throw new Error("Authentication is unavailable.");
    const { csrf } = await csrfResponse.json();
    const response = await fetch("/api/auth/" + action, {
      method: "POST", headers: { "content-type": "application/json", "x-flame-csrf": csrf },
      body: JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok) {
      if (action === "login" && response.status === 401)
        throw new Error("We couldn't sign you in. Check your email and password, and make sure you've confirmed your email. Use Forgot password if you need to reset it.");
      throw new Error(result.error?.message ?? "The request could not be completed.");
    }
    return result;
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setMessage("");
    const fields = new FormData(event.currentTarget);
    try {
      if (mode === "callback" && step === "verify") {
        if (!verification || !["email", "signup", "recovery"].includes(verification.type)) throw new Error("This link is invalid or has expired.");
        await mutate("verify", verification);
        const type = verification.type;
        setVerification(null);
        if (type === "recovery") { setStep("reset"); setMessage("Choose a new password."); return; }
        window.location.assign(returnPath ?? pendingQuestionReturnPath() ?? "/");
        return;
      }
      if (mode === "callback") {
        await mutate("reset-password", { password: fields.get("password") });
        window.location.assign(returnPath ?? pendingQuestionReturnPath() ?? "/");
        return;
      }
      if (mode === "register") {
        await mutate("register", { email: fields.get("email"), password: fields.get("password"), display_name: fields.get("display_name"), phone_number: fields.get("phone_number") || null });
        setMessage("Check your email for a verification link. If you already have an account, sign in or reset your password.");
        return;
      }
      if (mode === "recover") {
        await mutate("recover", { email: fields.get("email") });
        setMessage("If an account exists, a recovery link is on its way.");
        return;
      }
      await mutate("login", { email: fields.get("email"), password: fields.get("password"), phone_number: fields.get("phone_number") || null });
      const me = await fetch("/api/me", { cache: "no-store" });
      const profile: Profile = await me.json();
      if (!me.ok) throw new Error("Your account could not be loaded. Please try again.");
      if (admin && profile.role !== "admin") {
        await mutate("logout", {});
        throw new Error("This account does not have admin access.");
      }
      const next = safeReturnPath(new URLSearchParams(window.location.search).get("next")) ?? pendingQuestionReturnPath();
      window.location.assign(next ?? (profile.role === "admin" ? "/admin" : "/"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The request could not be completed.");
    } finally { setBusy(false); }
  }
  return <main className="auth-page"><div className="auth-card">
    <Link href="/" className="auth-brand" aria-label="Fliplecture home"><FliplectureLogo /></Link>
    <h1>{admin ? "Admin sign in" : titles[mode]}</h1>
    <p>{mode === "register" ? "Create your individual learning account." :
      mode === "recover" ? "We will send a recovery link to your email." :
      mode === "callback" ? step === "reset" ? "Set a new password for your account." : "Use the button below to finish verification." :
      admin ? "Continue to your administration workspace." : "Continue to your learning space."}</p>
    <form onSubmit={submit}>
      {mode === "register" && <label>Display name<input name="display_name" autoComplete="name" required maxLength={255} /></label>}
      {mode !== "callback" && <label>Email<input name="email" type="email" autoComplete="email" required /></label>}
      {((mode === "login" || mode === "register") || (mode === "callback" && step === "reset")) &&
        <label>Password<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "login" ? 1 : 12} /></label>}
      {(mode === "login" || mode === "register") && <label>Phone number (optional)<input name="phone_number" type="tel" autoComplete="tel" maxLength={32} /></label>}
      <button disabled={busy} type="submit">{busy ? "Please wait…" : mode === "callback" ? step === "reset" ? "Update password" : "Confirm email" : mode === "register" ? "Create account" : mode === "recover" ? "Send recovery link" : "Sign in"}</button>
    </form>
    {message && <p role="status" className="auth-message">{message}</p>}
    <nav aria-label="Account options">
      {mode !== "login" && <Link href={(admin ? "/admin/sign-in" : "/sign-in") + (returnPath ? `?next=${encodeURIComponent(returnPath)}` : "")}>Sign in</Link>}
      {mode !== "register" && !admin && <Link href={"/sign-up" + (returnPath ? `?next=${encodeURIComponent(returnPath)}` : "")}>Create account</Link>}
      {mode !== "recover" && <Link href={"/recover" + (returnPath ? `?next=${encodeURIComponent(returnPath)}` : "")}>Forgot password?</Link>}
      {mode === "login" && <Link href={admin ? "/sign-in" : "/admin/sign-in"}>{admin ? "Student sign in" : "Admin sign in"}</Link>}
    </nav>
  </div></main>;
}

