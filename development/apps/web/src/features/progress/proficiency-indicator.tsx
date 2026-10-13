import type { Proficiency } from "@/features/curriculum/types";

export function proficiencyLabel(value: Proficiency | null) {
  if (value === null) return "Not yet available";
  if (value === 0) return "Not started";
  if (value <= 2) return "Initial exposure";
  if (value <= 4) return "Developing";
  if (value <= 6) return "Basic understanding";
  if (value <= 8) return "Strong understanding";
  if (value === 9) return "Near mastery";
  return "Mastered";
}
export function ProficiencyIndicator({ value, expanded = false }: { value: Proficiency | null; expanded?: boolean }) {
  const label = proficiencyLabel(value);
  if (value === null) return <span className="proficiency" aria-label="Proficiency unavailable" title="Proficiency unavailable">—</span>;
  return <span className={`proficiency ${expanded ? "proficiency-expanded" : ""}`} title={label}>
    {expanded && <span className="proficiency-caption">Proficiency</span>}
    <span aria-label={`Proficiency: ${value === null ? "unavailable" : `${value} out of 10`}. ${label}`}><strong>{value ?? "—"}</strong><span className="proficiency-denominator"> / 10</span></span>
    {expanded && <><span className="proficiency-track" aria-hidden="true"><span style={{ width: `${(value ?? 0) * 10}%` }} /></span><span className="proficiency-caption">{label}</span></>}
  </span>;
}
