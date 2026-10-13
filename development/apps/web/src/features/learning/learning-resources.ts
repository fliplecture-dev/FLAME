type ResourceBase = { id: string; title: string; description: string; meta?: string };
export type LearningResource = ResourceBase & (
  | { kind: "image" | "diagram"; src: string; alt: string; caption: string }
  | { kind: "audio" | "video" | "animation"; src: string; transcript?: string; captionsSrc?: string }
  | { kind: "simulation"; experience: "gravity-lab" }
  | { kind: "activity" | "experiment" | "book" | "kit" | "tutor" | "class"; details: string[]; href?: string }
);

// Embeds are selected from reviewed application assets, never arbitrary response HTML/URLs.
export const approvedExperiences = { "gravity-lab": "/learning-assets/gravity-lab.html" } as const;
export function resourceUrl(value: string): string | undefined {
  if (value.includes("\\") || /[\u0000-\u0020]/.test(value)) return undefined;
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  try { const url = new URL(value); return url.protocol === "https:" ? url.href : undefined; } catch { return undefined; }
}
export const resourceLabels: Record<LearningResource["kind"], string> = {
  image: "Image", diagram: "Diagram", audio: "Audio", video: "Video", animation: "Animation",
  simulation: "Interactive web experience", activity: "Activity", experiment: "Experiment",
  book: "Book", kit: "Learning kit", tutor: "Tutor", class: "Class",
};
