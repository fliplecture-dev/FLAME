"use client";

import { useEffect, useMemo, useState } from "react";
import { LearningMetadataEditor, LearningMetadata, metadataForm, metadataValue } from "./learning-metadata-editor";
import { BulkTransfer } from "./bulk-transfer";
import { ResourcePanel } from "./resource-panel";
import { useCatalogue, ListPages } from "./b9-catalogue";
import { b9Get, b9Mutation, b9Upload } from "@/lib/api/b9-client";

type Tree = { id: string; name: string; levels?: Tree[]; subjects?: Tree[]; domains?: Tree[];
  categories?: Tree[]; topics?: Tree[]; subtopics?: Tree[] };
type Path = { topic_id: string; subtopic_id: string | null };
type PathChoice = Path & { label: string; subject_id: string };
type SubjectChoice = { id: string; label: string };
type ResourceRow = { id: string; type: string; title: string; description: string | null;
  external_url: string | null; source: string; alt_text: string | null; caption_or_transcript: string | null;
  accessibility_note: string | null; rights_basis: string | null; rights_holder: string | null;
  rights_reference: string | null; attribution: string | null; distribution_scope: string | null;
  availability: string; paths: Path[]; published: boolean; version: number };
type Expertise = { subject_id: string; topic_id: string | null; claim_status: string };
type TeacherRow = { learning_metadata?: LearningMetadata; id: string; name: string; bio: string | null; qualifications: string | null;
  experience: string | null; languages: string[]; availability: string | null;
  expertise: Expertise[]; published: boolean; version: number };
type KitRow = { learning_metadata?: LearningMetadata; id: string; name: string; description: string | null; image_upload_ids: string[];
  materials: string[]; instructions: string | null; supervision: string | null;
  cost: string | null; currency: string | null; availability: string | null;
  supplier_url: string | null; paths: Path[]; published: boolean; version: number };

function choices(tree: Tree | null) {
  const paths: PathChoice[] = [], subjects: SubjectChoice[] = [];
  if (!tree) return { paths, subjects };
  for (const level of tree.levels ?? []) for (const subject of level.subjects ?? []) {
    const root = tree.name + " / " + level.name + " / " + subject.name;
    subjects.push({ id: subject.id, label: root });
    for (const domain of subject.domains ?? []) {
      const groups = [...(domain.topics ?? []).map(topic => ({ topic, category: "" })),
        ...(domain.categories ?? []).flatMap(category => (category.topics ?? [])
          .map(topic => ({ topic, category: category.name })))];
      for (const { topic, category } of groups) {
        const label = root + " / " + domain.name + (category ? " / " + category : "") + " / " + topic.name;
        paths.push({ topic_id: topic.id, subtopic_id: null, subject_id: subject.id, label });
        for (const subtopic of topic.subtopics ?? [])
          paths.push({ topic_id: topic.id, subtopic_id: subtopic.id, subject_id: subject.id,
            label: label + " / " + subtopic.name });
      }
    }
  }
  return { paths, subjects };
}
const pathKey = (path: Path) => path.topic_id + ":" + (path.subtopic_id ?? "");

function PathPicker({ options, value, onChange }: { options: PathChoice[]; value: Path[];
  onChange: (paths: Path[]) => void }) {
  const [search, setSearch] = useState("");
  const shown = options.filter(option => option.label.toLowerCase().includes(search.toLowerCase()) ||
    value.some(item => pathKey(item) === pathKey(option))).slice(0, 100);
  return <fieldset className="b9-path-picker"><legend>Topic associations</legend>
    <label>Find a path<input type="search" value={search} onChange={event => setSearch(event.target.value)}
      placeholder="Search current curriculum" /></label>
    <div className="b9-path-options">{shown.map(option => <label key={pathKey(option)}>
      <input type="checkbox" checked={value.some(item => pathKey(item) === pathKey(option))}
        onChange={event => onChange(event.target.checked
          ? [...value, { topic_id: option.topic_id, subtopic_id: option.subtopic_id }]
          : value.filter(item => pathKey(item) !== pathKey(option)))} />{option.label}</label>)}</div>
    <small>{value.length} selected; showing up to 100 matching paths.</small>
  </fieldset>;
}

function TeacherPanel({ subjects, paths }: { subjects: SubjectChoice[]; paths: PathChoice[] }) {
  const listing = useCatalogue<TeacherRow>("admin/teachers");
  const [selected, setSelected] = useState<TeacherRow | null>(null);
  const [education, setEducation] = useState(metadataForm());
  const [form, setForm] = useState({ name: "", bio: "", qualifications: "", experience: "", languages: "", availability: "" });
  const [expertise, setExpertise] = useState<Expertise[]>([]);
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [claim, setClaim] = useState("declared");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  function choose(row: TeacherRow | null) {
    setEducation(metadataForm(row?.learning_metadata)); setSelected(row); setExpertise(row?.expertise ?? []); setNotice("");
    setForm({ name: row?.name ?? "", bio: row?.bio ?? "", qualifications: row?.qualifications ?? "",
      experience: row?.experience ?? "", languages: row?.languages.join(", ") ?? "", availability: row?.availability ?? "" });
  }
  function field(name: keyof typeof form, value: string) { setForm(previous => ({ ...previous, [name]: value })); }
  async function act(task: () => Promise<void>) {
    setBusy(true); setNotice("");
    try { await task(); await listing.refresh(); }
    catch (cause) { setNotice(cause instanceof Error ? cause.message : "Request failed."); }
    finally { setBusy(false); }
  }
  return <section className="b9-admin-section"><h2>Teacher Management</h2><BulkTransfer kind="teachers" onImported={listing.refresh} />
    <label>Search teachers<input type="search" value={listing.search} onChange={event => listing.setSearch(event.target.value)} /></label>
    <label>Subject<select value={listing.filters.subject_id ?? ""} onChange={event => listing.setFilter("subject_id", event.target.value)}>
      <option value="">All subjects</option>{subjects.map(subject => <option key={subject.id} value={subject.id}>{subject.label}</option>)}</select></label>
    <label>Status<select value={listing.filters.published ?? ""} onChange={event => listing.setFilter("published", event.target.value)}>
      <option value="">All</option><option value="true">Published</option><option value="false">Draft</option></select></label>
    {listing.loading && <p role="status">Loading teachers…</p>}
    {listing.error && <p role="alert">{listing.error}</p>}
    {!listing.loading && !listing.rows.length && <p>No teachers match this search.</p>}
    <ul className="b9-admin-list">{listing.rows.map(row => <li key={row.id}><button onClick={() => choose(row)}>{row.name}</button> · {row.published ? "Published" : "Draft"} · v{row.version}</li>)}</ul>
    <ListPages listing={listing} />
    <button onClick={() => choose(null)}>New teacher</button>
    <div className="b9-editor"><h3>{selected ? "Edit teacher" : "Add teacher"}</h3>
      <div className="b4-fields">
        <label>Name<input value={form.name} onChange={event => field("name", event.target.value)} /></label>
        <label>Bio<textarea value={form.bio} onChange={event => field("bio", event.target.value)} /></label>
        <label>Qualifications<textarea value={form.qualifications} onChange={event => field("qualifications", event.target.value)} /></label>
        <label>Experience<textarea value={form.experience} onChange={event => field("experience", event.target.value)} /></label>
        <label>Languages (comma separated)<input value={form.languages} onChange={event => field("languages", event.target.value)} /></label>
        <label>Availability<input value={form.availability} onChange={event => field("availability", event.target.value)} /></label>
      </div>
      <LearningMetadataEditor value={education} onChange={setEducation} disabled={busy} />
      <fieldset><legend>Subject expertise</legend>
        <label>Subject<select value={subject} onChange={event => { setSubject(event.target.value); setTopic(""); }}>
          <option value="">Choose subject</option>{subjects.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
        <label>Topic (optional)<select value={topic} onChange={event => setTopic(event.target.value)}>
          <option value="">Entire subject</option>{paths.filter(path => path.subject_id === subject && !path.subtopic_id)
            .map(path => <option key={path.topic_id} value={path.topic_id}>{path.label}</option>)}</select></label>
        <label>Claim status<select value={claim} onChange={event => setClaim(event.target.value)}>
          <option value="declared">Declared</option><option value="reviewed">Reviewed by admin</option></select></label>
        <button disabled={!subject || expertise.some(item => item.subject_id === subject && item.topic_id === (topic || null))}
          onClick={() => setExpertise(items => [...items, { subject_id: subject, topic_id: topic || null, claim_status: claim }])}>Add expertise</button>
        <ul>{expertise.map((item, index) => <li key={item.subject_id + ":" + item.topic_id}>
          {subjects.find(option => option.id === item.subject_id)?.label ?? item.subject_id}
          {item.topic_id ? " / " + (paths.find(path => path.topic_id === item.topic_id && !path.subtopic_id)?.label ?? "Topic") : ""}
          {" · " + item.claim_status} <button onClick={() => setExpertise(items => items.filter((_, i) => i !== index))}>Remove</button></li>)}</ul>
      </fieldset>
      <button disabled={busy || !form.name.trim()} onClick={() => void act(async () => {
        const body = { ...form, learning_metadata: metadataValue(education), languages: form.languages.split(",").map(value => value.trim()).filter(Boolean), expertise,
          ...(selected ? { expected_version: selected.version } : {}) };
        const saved = await b9Mutation<TeacherRow>(selected ? "admin/teachers/" + selected.id : "admin/teachers",
          selected ? "PATCH" : "POST", body);
        choose(saved); setNotice("Teacher draft saved.");
      })}>Save draft</button>
      {selected && <><button disabled={busy || selected.published} onClick={() => void act(async () => {
        const saved = await b9Mutation<TeacherRow>("admin/teachers/" + selected.id + "/publish", "POST",
          { expected_version: selected.version }); choose(saved); setNotice("Teacher published.");
      })}>Publish</button>
        <button disabled={busy || !selected.published} onClick={() => {
          if (!window.confirm("Unpublish this teacher profile?")) return;
          void act(async () => {
            const saved = await b9Mutation<TeacherRow>("admin/teachers/" + selected.id + "/unpublish", "POST",
              { expected_version: selected.version }); choose(saved); setNotice("Teacher unpublished.");
          });
        }}>Unpublish</button></>}
      {notice && <p role="status">{notice}</p>}
    </div>
  </section>;
}

function KitPanel({ paths }: { paths: PathChoice[] }) {
  const listing = useCatalogue<KitRow>("admin/activity-kits");
  const [selected, setSelected] = useState<KitRow | null>(null);
  const [education, setEducation] = useState(metadataForm());
  const [form, setForm] = useState({ name: "", description: "", materials: "", instructions: "",
    supervision: "", cost: "", currency: "", availability: "", supplier_url: "" });
  const [assigned, setAssigned] = useState<Path[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  function choose(row: KitRow | null) {
    setEducation(metadataForm(row?.learning_metadata)); setSelected(row); setAssigned(row?.paths ?? []); setFile(null); setNotice("");
    setForm({ name: row?.name ?? "", description: row?.description ?? "",
      materials: row?.materials.join("\n") ?? "", instructions: row?.instructions ?? "",
      supervision: row?.supervision ?? "", cost: row?.cost ?? "", currency: row?.currency ?? "",
      availability: row?.availability ?? "", supplier_url: row?.supplier_url ?? "" });
  }
  function field(name: keyof typeof form, value: string) { setForm(previous => ({ ...previous, [name]: value })); }
  async function act(task: () => Promise<void>) {
    setBusy(true); setNotice("");
    try { await task(); await listing.refresh(); }
    catch (cause) { setNotice(cause instanceof Error ? cause.message : "Request failed."); }
    finally { setBusy(false); }
  }
  return <section className="b9-admin-section"><h2>Activity Kit Management</h2><BulkTransfer kind="activity-kits" onImported={listing.refresh} />
    <p>Kits can be associated with several topics. Costs are descriptive; there is no checkout.</p>
    <label>Search kits<input type="search" value={listing.search} onChange={event => listing.setSearch(event.target.value)} /></label>
    <label>Topic<select value={listing.filters.topic_id ?? ""} onChange={event => listing.setFilter("topic_id", event.target.value)}>
      <option value="">All topics</option>{paths.filter(path => !path.subtopic_id).map(path =>
        <option key={path.topic_id} value={path.topic_id}>{path.label}</option>)}</select></label>
    <label>Status<select value={listing.filters.published ?? ""} onChange={event => listing.setFilter("published", event.target.value)}>
      <option value="">All</option><option value="true">Published</option><option value="false">Draft</option></select></label>
    {listing.loading && <p role="status">Loading kits…</p>}
    {listing.error && <p role="alert">{listing.error}</p>}
    {!listing.loading && !listing.rows.length && <p>No kits match this search.</p>}
    <ul className="b9-admin-list">{listing.rows.map(row => <li key={row.id}><button onClick={() => choose(row)}>{row.name}</button> · {row.published ? "Published" : "Draft"} · v{row.version}</li>)}</ul>
    <ListPages listing={listing} />
    <button onClick={() => choose(null)}>New kit</button>
    <div className="b9-editor"><h3>{selected ? "Edit kit" : "Add kit"}</h3>
      <div className="b4-fields">
        <label>Name<input value={form.name} onChange={event => field("name", event.target.value)} /></label>
        <label>Description<textarea value={form.description} onChange={event => field("description", event.target.value)} /></label>
        <label>Materials (one per line)<textarea value={form.materials} onChange={event => field("materials", event.target.value)} /></label>
        <label>Instructions<textarea value={form.instructions} onChange={event => field("instructions", event.target.value)} /></label>
        <label>Supervision<textarea value={form.supervision} onChange={event => field("supervision", event.target.value)} /></label>
        <label>Image<input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
        <label>Cost<input type="number" min="0" step="0.01" value={form.cost} onChange={event => field("cost", event.target.value)} /></label>
        <label>Currency (three letters)<input value={form.currency} maxLength={3} onChange={event => field("currency", event.target.value.toUpperCase())} /></label>
        <label>Availability<input value={form.availability} onChange={event => field("availability", event.target.value)} /></label>
        <label>Supplier HTTPS link<input type="url" value={form.supplier_url} onChange={event => field("supplier_url", event.target.value)} /></label>
      </div>
      <LearningMetadataEditor value={education} onChange={setEducation} disabled={busy} />
      <PathPicker options={paths} value={assigned} onChange={setAssigned} />
      <button disabled={busy || !form.name.trim() || !assigned.length} onClick={() => void act(async () => {
        const learning_metadata = metadataValue(education);
        const imageIds = file ? [...(selected?.image_upload_ids ?? []), (await b9Upload(file)).upload_id] :
          selected?.image_upload_ids ?? [];
        const body = { learning_metadata, name: form.name, description: form.description,
          materials: form.materials.split("\n").map(value => value.trim()).filter(Boolean),
          instructions: form.instructions, supervision: form.supervision,
          cost: form.cost || null, currency: form.currency || null,
          availability: form.availability, supplier_url: form.supplier_url || null,
          image_upload_ids: imageIds, paths: assigned,
          ...(selected ? { expected_version: selected.version } : {}) };
        const saved = await b9Mutation<KitRow>(selected ? "admin/activity-kits/" + selected.id : "admin/activity-kits",
          selected ? "PATCH" : "POST", body);
        choose(saved); setNotice("Kit draft saved.");
      })}>Save draft</button>
      {selected && <><button disabled={busy || selected.published} onClick={() => void act(async () => {
        const saved = await b9Mutation<KitRow>("admin/activity-kits/" + selected.id + "/publish", "POST",
          { expected_version: selected.version }); choose(saved); setNotice("Kit published.");
      })}>Publish</button>
        <button disabled={busy || !selected.published} onClick={() => {
          if (!window.confirm("Unpublish this activity kit?")) return;
          void act(async () => {
            const saved = await b9Mutation<KitRow>("admin/activity-kits/" + selected.id + "/unpublish", "POST",
              { expected_version: selected.version }); choose(saved); setNotice("Kit unpublished.");
          });
        }}>Unpublish</button></>}
      {notice && <p role="status">{notice}</p>}
    </div>
  </section>;
}

export function B9Admin({ section, tree }: { section: "resources" | "teachers" | "kits"; tree: Tree | null }) {
  const options = useMemo(() => choices(tree), [tree]);
  return <div className="b9-admin">
    {!tree && section !== "resources" && <p>Choose a curriculum to edit topic associations and expertise.</p>}
    {section === "resources" && <ResourcePanel curriculumId={tree?.id ?? ""} />}
    {section === "teachers" && <TeacherPanel subjects={options.subjects} paths={options.paths} />}
    {section === "kits" && <KitPanel paths={options.paths} />}
  </div>;
}
