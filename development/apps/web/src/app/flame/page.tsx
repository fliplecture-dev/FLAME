import { redirect } from "next/navigation";
import { GuestWorkspace } from "@/features/learning/guest-workspace";
import { StudentWorkspace } from "@/features/learning/student-workspace";
import { getCurriculum } from "@/lib/api/student-learning";
import { apiRequest, sessionValue } from "@/lib/api/auth-bff";
import { loadStudentB4 } from "@/lib/api/b4-server";
import { learningFromMemberships } from "@/lib/api/b4-catalogue";

export default async function Flame() {
  const live = Boolean(process.env.FLAME_BFF_SHARED_KEY || process.env.NODE_ENV === "production");
  if (!live) return <StudentWorkspace curricula={await getCurriculum()} />;
  const session = await sessionValue();
  if (!session) return <GuestWorkspace />;
  const me = await apiRequest("me", "GET", undefined, session);
  if (!me.ok) redirect("/sign-in?next=%2Fflame");
  try {
    const { catalogue, memberships } = await loadStudentB4(session);
    return <StudentWorkspace curricula={learningFromMemberships(catalogue, memberships)} catalogue={catalogue} memberships={memberships} live />;
  } catch {
    return <main className="auth-page"><section className="auth-card" role="alert"><h1>Learning space unavailable</h1><p>Your question is kept in this tab. Please try again.</p><a href="/flame">Try again</a></section></main>;
  }
}
