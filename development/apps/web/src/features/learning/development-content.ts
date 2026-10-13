import type { LearningBlock } from "./learning-content";
// Static editorial fixture, never presented as a generated answer or assessment evidence.
export const gravityDevelopmentContent: LearningBlock[] = [
  { id: "title", kind: "heading", level: 2, text: "Gravity keeps us on Earth." },
  { id: "intro", kind: "text", text: "Gravity is an attractive force between objects with mass. Earth pulls objects toward its centre, which is why a dropped ball falls toward the ground." },
  { id: "effects", kind: "heading", level: 3, text: "Where can you notice gravity?" },
  { id: "examples", kind: "list", items: ["A ball returns to the ground after you throw it upward.", "Rain falls from clouds toward Earth.", "Gravity helps keep the Moon in orbit around Earth."] },
  { id: "mass-weight", kind: "table", caption: "Mass and weight describe different things", columns: ["", "Mass", "Weight"], rows: [["Meaning", "A measure of an object’s inertia", "The gravitational force on an object"], ["Unit", "Kilogram (kg)", "Newton (N)"], ["On the Moon", "Stays the same", "Less than on Earth"]] },
  { id: "formula", kind: "formula", description: "Weight equals mass multiplied by gravitational acceleration.", expression: { kind: "row", children: [{ kind: "symbol", value: "W" }, { kind: "operator", value: "=" }, { kind: "symbol", value: "m" }, { kind: "operator", value: "×" }, { kind: "symbol", value: "g" }] } },
  { id: "remember", kind: "callout", title: "Keep in mind", text: "Mass and weight are different. Changing location can change your weight even when your mass stays the same." },
  { id: "reflect", kind: "heading", level: 3, text: "Think it through" },
  { id: "steps", kind: "list", ordered: true, items: ["Imagine taking the same backpack from Earth to the Moon.", "Which changes: its mass, its weight, or both?", "Explain your reasoning in your own words."] },
];
