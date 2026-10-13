import type { Curriculum, LearningContext, TopicContext } from "./types";

export type ProgressFilter = "all" | "in-progress" | "mastered" | "not-started";
export const nodeKey = (...ids: (string | null)[]) => JSON.stringify(ids);
export const contextKey = (c: TopicContext) => nodeKey(c.curriculum.id, c.level.id, c.subject.id, c.domain.id, c.topic.categoryId, c.topic.id, c.subtopic?.id ?? null);
export const ancestorKeys = (c: TopicContext) => [
  nodeKey(c.curriculum.id),
  nodeKey(c.curriculum.id, c.level.id),
  nodeKey(c.curriculum.id, c.level.id, c.subject.id),
  nodeKey(c.curriculum.id, c.level.id, c.subject.id, c.domain.id),
  nodeKey(c.curriculum.id, c.level.id, c.subject.id, c.domain.id, c.topic.categoryId, c.topic.id),
];
export function requestContext(c: TopicContext): LearningContext {
  return { curriculumId: c.curriculum.id, levelId: c.level.id, subjectId: c.subject.id,
    domainId: c.domain.id, categoryId: c.topic.categoryId, topicId: c.topic.id, subtopicId: c.subtopic?.id ?? null };
}
export function firstBranchKeys(data: Curriculum[]): string[] {
  const c = data[0], l = c?.levels[0], s = l?.subjects[0], d = s?.domains[0], t = d?.topics[0];
  if (!c) return [];
  return [nodeKey(c.id),
    ...(l ? [nodeKey(c.id, l.id)] : []),
    ...(l && s ? [nodeKey(c.id, l.id, s.id)] : []),
    ...(l && s && d ? [nodeKey(c.id, l.id, s.id, d.id)] : []),
    ...(l && s && d && t ? [nodeKey(c.id, l.id, s.id, d.id, t.categoryId, t.id)] : []),
  ];
}

export function allBranchKeys(data: Curriculum[]): string[] {
  return data.flatMap(c => [nodeKey(c.id), ...c.levels.flatMap(l => [
    nodeKey(c.id, l.id), ...l.subjects.flatMap(s => [nodeKey(c.id, l.id, s.id),
      ...s.domains.flatMap(d => [nodeKey(c.id, l.id, s.id, d.id),
        ...d.topics.map(t => nodeKey(c.id, l.id, s.id, d.id, t.categoryId, t.id))])])])]);
}
export function filterCurricula(data: Curriculum[], query: string, filter: ProgressFilter): Curriculum[] {
  const term = query.trim().toLowerCase();
  if (!term && filter === "all") return data;
  return data.map(c => ({ ...c, levels: c.levels.map(l => ({ ...l, subjects: l.subjects.map(s => ({
    ...s, domains: s.domains.map(d => ({ ...d, topics: d.topics.map(t => ({ ...t,
      subtopics: t.subtopics.filter(st => {
        const matchesText = `${c.name} ${l.name} ${s.name} ${d.name} ${t.name} ${st.name}`.toLowerCase().includes(term);
        const matchesStatus = filter === "all" || (filter === "in-progress" ? st.status === "in-progress" || st.status === "review-due" : st.status === filter);
        return matchesText && matchesStatus;
      }),
    })).filter(t => t.subtopics.length) })).filter(d => d.topics.length),
  })).filter(s => s.domains.length) })).filter(l => l.subjects.length) })).filter(c => c.levels.length);
}
