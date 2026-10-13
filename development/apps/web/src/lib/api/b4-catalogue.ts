import { mapPublishedCurriculum, type PublishedCurriculumTree } from "@/features/curriculum/map-published-curriculum";
import { mergeLearningPath } from "@/features/curriculum/merge-learning-path";
import type { Curriculum } from "@/features/curriculum/types";

export interface Membership {
  id: string;
  curriculum_id: string;
  level_id: string | null;
  subject_id: string | null;
  domain_id: string | null;
  category_id: string | null;
  topic_id: string | null;
  subtopic_id: string | null;
  visible: boolean;
  version: number;
}

export function catalogueFromTrees(trees: PublishedCurriculumTree[]): Curriculum[] {
  const combined = new Map<string, PublishedCurriculumTree>();
  for (const tree of trees) {
    const existing = combined.get(tree.id);
    if (existing) existing.levels.push(...tree.levels);
    else combined.set(tree.id, { ...tree, levels: [...tree.levels] });
  }
  return [...combined.values()].map(mapPublishedCurriculum);
}

function memberPath(curriculum: Curriculum, membership: Membership): Curriculum {
  return {
    ...curriculum,
    levels: curriculum.levels.filter(l => !membership.level_id || l.id === membership.level_id).map(l => ({
      ...l,
      subjects: l.subjects.filter(s => !membership.subject_id || s.id === membership.subject_id).map(s => ({
        ...s,
        domains: s.domains.filter(d => !membership.domain_id || d.id === membership.domain_id).map(d => ({
          ...d,
          topics: d.topics.filter(t => !membership.topic_id || (t.id === membership.topic_id && t.categoryId === membership.category_id)).map(t => ({
            ...t,
            subtopics: t.subtopics.filter(st => !membership.subtopic_id || st.id === membership.subtopic_id),
          })),
        })),
      })),
    })),
  };
}

export function learningFromMemberships(catalogue: Curriculum[], memberships: Membership[]): Curriculum[] {
  let learning: Curriculum[] = [];
  for (const membership of memberships.filter(item => item.visible)) {
    const curriculum = catalogue.find(c => c.id === membership.curriculum_id);
    if (!curriculum) continue;
    const path = memberPath(curriculum, membership);
    if (membership.level_id && !path.levels.length) continue;
    if (membership.subject_id && !path.levels.some(l => l.subjects.length)) continue;
    if (membership.domain_id && !path.levels.some(l => l.subjects.some(s => s.domains.length))) continue;
    if (membership.topic_id && !path.levels.some(l => l.subjects.some(s => s.domains.some(d => d.topics.length)))) continue;
    if (membership.subtopic_id && !path.levels.some(l => l.subjects.some(s => s.domains.some(d => d.topics.some(t => t.subtopics.length))))) continue;
    learning = mergeLearningPath(learning, [path]);
  }
  // A hidden subject masks every selected descendant, even under a visible curriculum.
  for (const item of memberships.filter(item => !item.visible && item.subject_id && !item.domain_id && item.level_id)) {
    learning = learning.map(c => c.id !== item.curriculum_id ? c : {
      ...c, levels: c.levels.map(l => l.id !== item.level_id ? l : {
        ...l, subjects: l.subjects.filter(s => s.id !== item.subject_id),
      }),
    });
  }
  return learning.map(c => ({ ...c, levels: c.levels.map(l => ({
    ...l, subjects: l.subjects.filter(s => s.domains.length > 0),
  })).filter(l => l.subjects.length > 0) })).filter(c => c.levels.length > 0);
}

