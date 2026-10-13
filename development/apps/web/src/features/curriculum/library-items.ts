import type { Curriculum } from "./types";
export type LibraryTab = "curriculum" | "subject" | "topic";
export interface LibraryItem {
  id: string;
  title: string;
  subtitle: string;
  kind: string;
  curriculum: Curriculum;
  levelId?: string;
  subjectId?: string;
  domainId?: string;
  path: Curriculum[];
}
export function libraryItems(catalog: Curriculum[], tab: LibraryTab): LibraryItem[] {
  return catalog.flatMap(c => {
    if (tab === "curriculum") return [{ id: JSON.stringify([c.id]), title: c.name,
      subtitle: `${c.levels.length} levels`, kind: "Curriculum", curriculum: c, path: [c] }];
    return c.levels.flatMap(l => l.subjects.flatMap(s => {
      const base = { curriculum: c, levelId: l.id, subjectId: s.id };
      if (tab === "subject") return [{ ...base, id: JSON.stringify([c.id, l.id, s.id]),
        title: s.name, subtitle: `${c.name} / ${l.name}`, kind: "Subject",
        path: [{ ...c, levels: [{ ...l, subjects: [s] }] }] }];
      return s.domains.flatMap(d => d.topics.flatMap(t => {
        const topicPath = (subtopics = t.subtopics) => [{ ...c, levels: [{ ...l, subjects: [{ ...s,
          domains: [{ ...d, topics: [{ ...t, subtopics }] }],
        }] }] }];
        const common = { ...base, domainId: d.id, subtitle: `${c.name} / ${l.name} / ${s.name} / ${d.name}` };
        return [
          { ...common, id: JSON.stringify([c.id, l.id, s.id, d.id, t.categoryId, t.id]),
            title: t.name, kind: "Topic", path: topicPath() },
          ...t.subtopics.map(st => ({ ...common,
            id: JSON.stringify([c.id, l.id, s.id, d.id, t.categoryId, t.id, st.id]),
            title: st.name, kind: "Subtopic", path: topicPath([st]),
          })),
        ];
      }));
    }));
  });
}
