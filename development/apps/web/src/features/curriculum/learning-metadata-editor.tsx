"use client";

export type LearningMetadata = { topic_labels?: string[]; concepts: string[]; synonyms: string[]; grade_min: number | null;
  grade_max: number | null; languages: string[]; purposes: string[] };
export type MetadataForm = { topicLabels: string; concepts: string; synonyms: string; gradeMin: string; gradeMax: string;
  languages: string; purposes: string[] };
export function metadataForm(value?: Partial<LearningMetadata>): MetadataForm {
  return { topicLabels:(value?.topic_labels ?? []).join(" | "), concepts: (value?.concepts ?? []).join(", "), synonyms: (value?.synonyms ?? []).join(", "),
    gradeMin: value?.grade_min == null ? "" : String(value.grade_min),
    gradeMax: value?.grade_max == null ? "" : String(value.grade_max),
    languages: (value?.languages ?? []).join(", "), purposes: value?.purposes ?? [] };
}
const terms = (value: string) => value.split(/[,\n]/).map(term => term.trim()).filter(Boolean);
export function metadataValue(value: MetadataForm): LearningMetadata {
  if ((value.gradeMin === "") !== (value.gradeMax === "") ||
    value.gradeMin !== "" && Number(value.gradeMin) > Number(value.gradeMax)) {
    throw new Error("Recommendation metadata: enter both grade limits in ascending order, or leave both unspecified.");
  }
  return { topic_labels:value.topicLabels.split("|").map(label=>label.trim()).filter(Boolean), concepts: terms(value.concepts), synonyms: terms(value.synonyms),
    grade_min: value.gradeMin === "" ? null : Number(value.gradeMin),
    grade_max: value.gradeMax === "" ? null : Number(value.gradeMax),
    languages: terms(value.languages).map(code => code.toLowerCase()), purposes: value.purposes };
}
export function LearningMetadataEditor({ value, onChange, disabled = false }: {
  value: MetadataForm; onChange: (value: MetadataForm) => void; disabled?: boolean }) {
  const update = (key: keyof MetadataForm, text: string) => onChange({ ...value, [key]: text });
  return <fieldset disabled={disabled} className="recommendation-metadata"><legend>Recommendation metadata (optional)</legend>
    <p>Describe what this content teaches. Mapping supplies candidates; these details help select content for the current question. Metadata is entered and reviewed by an administrator.</p>
    <div className="b4-fields">
      <label>Concepts (comma separated)<input value={value.concepts} onChange={e => update("concepts", e.target.value)} placeholder="gravity, falling objects" /></label>
      <label>Alternative terms (comma separated)<input value={value.synonyms} onChange={e => update("synonyms", e.target.value)} placeholder="things fall, gravitational pull" /></label>
      {(["gradeMin", "gradeMax"] as const).map((key, i) => <label key={key}>{i ? "Through grade" : "From grade"}<select value={value[key]} onChange={e => update(key, e.target.value)}>
        <option value="">Unspecified</option>{Array.from({ length: 13 }, (_, n) => <option key={n} value={n}>{n ? `Grade ${n}` : "KG"}</option>)}
      </select></label>)}
      <label>Teaching languages (codes)<input value={value.languages} onChange={e => update("languages", e.target.value)} placeholder="en, ta" /><small>For example en (English), ta (Tamil). Leave blank when unknown.</small></label>
    </div>
    <div className="recommendation-purpose-options" role="group" aria-label="Teaching purposes">{[["explain", "Explain concepts"], ["demonstrate", "Demonstrate a process"], ["practise", "Practise understanding"], ["human_help", "Human help"]].map(([key, label]) => <label key={key}>
      <input type="checkbox" checked={value.purposes.includes(key)} onChange={e => onChange({ ...value, purposes: e.target.checked ? [...value.purposes, key] : value.purposes.filter(p => p !== key) })} />{label}
    </label>)}</div>
    <small>Existing entries can still use their descriptions. Rights, publication and access checks remain required.</small>
  </fieldset>;
}
