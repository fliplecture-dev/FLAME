import { apiJson, apiRequest } from "@/lib/api/auth-bff";
import { catalogueFromTrees, type Membership } from "@/lib/api/b4-catalogue";
import type { PublishedCurriculumTree } from "@/features/curriculum/map-published-curriculum";

async function required(path: string, session: string) {
  const response = await apiRequest(path, "GET", undefined, session);
  if (!response.ok) throw new Error("B4 data unavailable");
  return apiJson(response);
}

export async function loadStudentB4(session: string) {
  const [listing, saved] = await Promise.all([
    required("curricula", session),
    required("me/learning", session),
  ]);
  const trees = await Promise.all((listing.items as { id: string }[]).map(
    item => required("curricula/" + item.id + "/tree", session) as Promise<PublishedCurriculumTree>
  ));
  return { catalogue: catalogueFromTrees(trees), memberships: saved.items as Membership[] };
}

