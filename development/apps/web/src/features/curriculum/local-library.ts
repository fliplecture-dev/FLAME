import type { Curriculum, Subtopic } from "./types";
import { localCurriculum } from "./local-curriculum";
const subtopic = (id: string, name: string): Subtopic => ({ id, name, description: `Explore ${name.toLowerCase()} step by step.`, proficiency: null, status: "not-started" });
export const localLibrary: Curriculum[] = structuredClone(localCurriculum);
localLibrary[0].levels[0].subjects[0].domains.push({ id: "living-world", name: "The Living World", progress: null, topics: [
  { id: "plants", name: "Plants", categoryId: null, subtopics: [subtopic("photosynthesis", "Photosynthesis"), subtopic("plant-parts", "Parts of a Plant")] },
] });
localLibrary[0].levels[0].subjects.push({ id: "social-science", name: "Social Science", progress: null, domains: [
  { id: "maps", name: "Maps and Directions", progress: null, topics: [
    { id: "using-maps", name: "Using Maps", categoryId: null, subtopics: [subtopic("map-symbols", "Map Symbols"), subtopic("directions", "Directions")] },
  ] },
] });
localLibrary[0].levels.push({ id: "grade-6", name: "Grade 6", progress: null, subjects: [
  { id: "science", name: "Science", progress: null, domains: [
    { id: "electricity", name: "Electricity and Circuits", progress: null, topics: [
      { id: "circuits", name: "Circuits", categoryId: null, subtopics: [subtopic("simple-circuits", "Simple Circuits"), subtopic("conductors", "Conductors and Insulators")] },
    ] },
  ] },
] });
localLibrary.push({ id: "fliplecture", name: "Fliplecture", progress: null, levels: [
  { id: "grade-1", name: "Grade 1", progress: null, subjects: [
    { id: "science", name: "Science", progress: null, domains: [
      { id: "lighthouse", name: "The Lighthouse (Light & Sound)", progress: null, topics: [
        { id: "lighthouse-story", name: "Story of lighthouse (Light and Sound Signals)", categoryId: "category:lighthouse", subtopics: [
          subtopic("light-signals", "Light signals"), subtopic("sound-signals", "Sound signals"),
          subtopic("communication-signals", "Signals for communication"),
        ] },
      ] },
    ] },
  ] },
] });
