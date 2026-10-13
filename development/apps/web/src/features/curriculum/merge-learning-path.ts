import type { Curriculum } from "./types";

// IDs are compared within every ancestor path. Existing student fields win.
export function mergeLearningPath(existing: Curriculum[], incoming: Curriculum[]): Curriculum[] {
  const result = structuredClone(existing);
  for (const c of incoming) {
    let curriculum = result.find(x => x.id === c.id);
    if (!curriculum) { curriculum = { ...structuredClone(c), levels: [] }; result.push(curriculum); }
    for (const l of c.levels) {
      let level = curriculum.levels.find(x => x.id === l.id);
      if (!level) { level = { ...structuredClone(l), subjects: [] }; curriculum.levels.push(level); }
      for (const s of l.subjects) {
        let subject = level.subjects.find(x => x.id === s.id);
        if (!subject) { subject = { ...structuredClone(s), domains: [] }; level.subjects.push(subject); }
        for (const d of s.domains) {
          let domain = subject.domains.find(x => x.id === d.id);
          if (!domain) { domain = { ...structuredClone(d), topics: [] }; subject.domains.push(domain); }
          for (const t of d.topics) {
            let topic = domain.topics.find(x => x.id === t.id && x.categoryId === t.categoryId);
            if (!topic) { topic = { ...structuredClone(t), subtopics: [] }; domain.topics.push(topic); }
            for (const st of t.subtopics) if (!topic.subtopics.some(x => x.id === st.id)) topic.subtopics.push(structuredClone(st));
          }
        }
      }
    }
  }
  return result;
}
export function includesLearningPath(existing: Curriculum[], incoming: Curriculum[]): boolean {
  return incoming.every(c => {
    const current = existing.find(x => x.id === c.id);
    return Boolean(current && c.levels.every(l => {
      const level = current.levels.find(x => x.id === l.id);
      return level && l.subjects.every(s => {
        const subject = level.subjects.find(x => x.id === s.id);
        return subject && s.domains.every(d => {
          const domain = subject.domains.find(x => x.id === d.id);
          return domain && d.topics.every(t => {
            const topic = domain.topics.find(x => x.id === t.id && x.categoryId === t.categoryId);
            return topic && t.subtopics.every(st => topic.subtopics.some(x => x.id === st.id));
          });
        });
      });
    }));
  });
}
