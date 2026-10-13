import { redirect } from "next/navigation";
import { apiJson, apiRequest, sessionValue } from "@/lib/api/auth-bff";
import { SignOutButton } from "@/features/auth/sign-out-button";
import { AdminPanel } from "@/features/curriculum/admin-panel";
import { FlameBrand } from "@/components/ui/flame-brand";
export default async function AdminPage() {
  const session = await sessionValue();
  if (!session) redirect("/admin/sign-in");
  const response = await apiRequest("me", "GET", undefined, session);
  const profile = await apiJson(response);
  if (!response.ok || profile.role !== "admin") return <main className="auth-page"><div className="auth-card"><h1>Access denied</h1><p>This account does not have admin access.</p><a href="/">Return to learning space</a></div></main>;
  return <main className="b4-admin-page"><header className="admin-topbar">
    <div className="admin-topbar-brand"><FlameBrand logoSrc="/brand/flame-logo-horizontal-v1.png" />
      <div><h1>FLAME administration</h1><p>Signed in as {profile.email}</p></div></div>
    <div className="admin-topbar-actions"><a href="/">Learning space</a><SignOutButton /></div>
  </header><AdminPanel /></main>;
}
