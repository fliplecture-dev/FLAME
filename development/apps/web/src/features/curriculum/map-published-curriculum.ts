import type { Curriculum, Domain, Topic } from "./types";

interface NamedNode { id: string; name: string; display_order?: number }
interface SourceSubtopic extends NamedNode { description?: string | null }
interface SourceTopic extends NamedNode { subtopics: SourceSubtopic[] }
interface SourceCategory extends NamedNode { topics: SourceTopic[] }
interface SourceDomain extends NamedNode { topics: SourceTopic[]; categories: SourceCategory[] }
interface SourceSubject extends NamedNode { domains: SourceDomain[] }
interface SourceLevel extends NamedNode { subjects: SourceSubject[] }
export interface PublishedCurriculumTree extends NamedNode { revision?: number; levels: SourceLevel[] }

function ordered<T extends NamedNode>(items: T[]): T[] {
  return [...items].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
}
function mapTopic(source: SourceTopic, categoryId: string | null): Topic {
  if (!source.subtopics.length) throw new Error("A published topic requires a subtopic");
  return { id: source.id, name: source.name, categoryId,
    subtopics: ordered(source.subtopics).map(st => ({
      id: st.id, name: st.name, description: st.description ?? null,
      proficiency: null, status: null,
    })),
  };
}
export function mapPublishedCurriculum(source: PublishedCurriculumTree): Curriculum {
  return { id: source.id, name: source.name, revision: source.revision, progress: null,
    levels: ordered(source.levels).map(l => ({ id: l.id, name: l.name, progress: null,
      subjects: ordered(l.subjects).map(s => ({ id: s.id, name: s.name, progress: null,
        domains: ordered(s.domains).map(d => ({ id: d.id, name: d.name, progress: null,
          topics: [
            ...ordered(d.topics).map(t => mapTopic(t, null)),
            ...ordered(d.categories).flatMap(category => ordered(category.topics).map(t => mapTopic(t, category.id))),
          ] as Domain["topics"],
        })),
      })),
    })),
  };
}
