import type { Curriculum, Subtopic } from "./types";
// Illustrative development data, not imported workbook content or live progress.
const subtopic = (id: string, name: string, proficiency: Subtopic["proficiency"], description: string): Subtopic => ({
  id, name, description, proficiency,
  status: proficiency === 10 ? "mastered" : proficiency === 0 ? "not-started" : "in-progress",
});
export const localCurriculum: Curriculum[] = [
  { id: "cbse", name: "CBSE", progress: 46, levels: [
    { id: "grade-5", name: "Grade 5", progress: 46, subjects: [
      { id: "science", name: "Science", progress: 52, domains: [
        { id: "force-energy", name: "Force and Energy", progress: 45, topics: [
          { id: "forces", name: "Forces", categoryId: "category:force-energy", subtopics: [
            subtopic("gravity", "Gravity", 8, "Explore why objects fall and how gravity shapes the world around us."),
            subtopic("friction", "Friction", 5, "Understand the force that resists movement between surfaces."),
          ] },
          { id: "machines", name: "Machines", categoryId: "category:force-energy", subtopics: [
            subtopic("simple-machines", "Simple Machines", 3, "Explore how simple machines make everyday work easier."),
          ] },
        ] },
        { id: "matter", name: "Matter", progress: 32, topics: [
          { id: "states", name: "States of Matter", categoryId: null, subtopics: [
            subtopic("solids", "Solids", 10, "Explore the structure and properties of solid materials."),
            subtopic("liquids", "Liquids", 0, "Understand how liquids flow and take the shape of a container."),
          ] },
        ] },
      ] },
      { id: "mathematics", name: "Mathematics", progress: 38, domains: [
        { id: "fractions", name: "Fractions", progress: 38, topics: [
          { id: "fraction-types", name: "Fraction Types", categoryId: null, subtopics: [
            subtopic("equivalent-fractions", "Equivalent Fractions", 4, "Learn how different fractions can describe the same amount."),
          ] },
        ] },
      ] },
      { id: "english", name: "English", progress: 62, domains: [
        { id: "grammar", name: "Grammar", progress: 62, topics: [
          { id: "parts-of-speech", name: "Parts of Speech", categoryId: null, subtopics: [
            subtopic("nouns", "Nouns", 10, "Identify the words we use to name people, places, and things."),
          ] },
        ] },
      ] },
    ] },
  ] },
  { id: "tn-state-board", name: "Tamil Nadu State Board", progress: 12, levels: [
    { id: "grade-6", name: "Grade 6", progress: 12, subjects: [
      { id: "science", name: "Science", progress: 10, domains: [
        { id: "motion", name: "Force and Motion", progress: 10, topics: [
          { id: "gravitation", name: "Gravitation", categoryId: "category:motion", subtopics: [
            subtopic("gravity", "Gravity", 2, "Investigate gravitational attraction between objects."),
          ] },
        ] },
      ] },
      { id: "mathematics", name: "Mathematics", progress: 15, domains: [
        { id: "numbers", name: "Numbers", progress: 15, topics: [
          { id: "whole-numbers", name: "Whole Numbers", categoryId: null, subtopics: [
            subtopic("number-line", "Number Line", 0, "Explore whole numbers and their place on the number line."),
          ] },
        ] },
      ] },
    ] },
  ] },
];
