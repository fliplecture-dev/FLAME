const assert = require("node:assert/strict");
const http = require("node:http");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { chromium } = require(path.resolve(__dirname, "../../../../.kilo/ui-check/node_modules/playwright"));
const AxeBuilder = require(path.resolve(__dirname, "../../../../.kilo/ui-check/node_modules/@axe-core/playwright")).default;

const cwd = path.resolve(__dirname, "..");
const base = "http://localhost:3107";
const ids = {
  curriculum: "11111111-1111-4111-8111-111111111111",
  level: "22222222-2222-4222-8222-222222222222",
  otherLevel: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  otherSubject: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  subject: "33333333-3333-4333-8333-333333333333",
  domain: "44444444-4444-4444-8444-444444444444",
  topic: "55555555-5555-4555-8555-555555555555",
  subtopic: "66666666-6666-4666-8666-666666666666",
  sibling: "77777777-7777-4777-8777-777777777777",
};
const tree = {
  id: ids.curriculum, name: "B4 Test", levels: [{
    id: ids.level, name: "Level 1", subjects: [{
      id: ids.subject, name: "Science", domains: [{
        id: ids.domain, name: "Motion", categories: [], topics: [{
          id: ids.topic, name: "Gravity", subtopics: [{ id: ids.subtopic, name: "Falling objects" }, { id: ids.sibling, name: "Orbit" }],
        }],
      }],
    }],
  }],
};
const otherTree = {
  id: ids.curriculum, name: "B4 Test", levels: [{
    id: ids.otherLevel, name: "Level 2", subjects: [{
      id: ids.otherSubject, name: "Mathematics", domains: [{
        id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", name: "Numbers", categories: [], topics: [{
          id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", name: "Counting",
          subtopics: [{ id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", name: "Counting to ten" }],
        }],
      }],
    }],
  }],
};
let memberships = [];
let catalogueFailure = false;
let adminRows = [];
const adminTrees = new Map();
let importRows = [];
let savedSessions = [];
const savedMessages = new Map();
const pendingTopics = new Map();
const topicHistory = new Map();
const topicKeys = new Map();
let messageFailure = false;
let askAttempts = 0;
let curiosityAsks = 0;
let topicCheckPosts = 0;
const curiosityBodies = [];
const curiositySessionIds = [];
const askKeys = [];
const studySessionIds = [];
const studyBodies = [];
const { randomUUID } = require("node:crypto");
function json(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}
async function body(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
}
const mock = http.createServer(async (request, response) => {
  const pathname = new URL(request.url, "http://localhost").pathname;
  const session = request.headers["x-flame-session"];
  if (request.headers["x-bff-key"] !== "b4-browser-secret" ||
      !["b4-browser-session", "b4-admin-session"].includes(session))
    return json(response, 401, { error: { code: "unauthenticated" } });
  if (pathname === "/api/v1/sessions" && request.method === "GET")
    return json(response, 200, { items: savedSessions, next_cursor: null });
  if (pathname === "/api/v1/sessions" && request.method === "POST") {
    const input = await body(request);
    const now = new Date().toISOString();
    const row = { id: randomUUID(), mode: input.mode, context: input.context
      ? { ...input.context, names: { topic: "Gravity", subtopic: input.context.subtopic_id ? "Falling objects" : null } } : null,
      revision: input.mode === "study" ? 1 : null, created_at: now, updated_at: now };
    savedSessions.unshift(row);
    return json(response, 201, row);
  }
  if (/^\/api\/v1\/sessions\/[0-9a-f-]+\/capability-check$/.test(pathname) && request.method === "POST") {
    const input = await body(request);
    return input.question === "Watch this video"
      ? json(response, 200, { status: "unsupported", code: "media_understanding_unavailable",
          message: "I cannot watch videos, listen to audio, or transcribe recordings." })
      : json(response, 200, { status: "continue" });
  }
  if (/^\/api\/v1\/sessions\/[0-9a-f-]+\/ask$/.test(pathname) && request.method === "POST") {
    const input = await body(request);
    if (input.question === "Watch this video") return json(response, 200, {
      status: "unsupported", request_id: randomUUID(),
      code: "media_understanding_unavailable",
      message: "I cannot watch videos, listen to audio, or transcribe recordings." });
    if (input.mode === "curiosity") {
      curiosityAsks++;
      curiosityBodies.push(input);
      curiositySessionIds.push(pathname.split("/")[4]);
      return json(response, 200, { status: "ok", request_id: randomUUID(),
        response_id: randomUUID(), message_id: randomUUID(), curriculum_version: null,
        blocks: [{ id: randomUUID(), kind: "text", text: "Computers follow instructions to work with information." }],
        route: "direct_llm", knowledge_source: "model_generated", grounded: false,
        confidence: null, citations: [], resources: [] });
    }
    askAttempts++;
    studySessionIds.push(pathname.split("/")[4]);
    studyBodies.push(input);
    askKeys.push(request.headers["idempotency-key"]);
    if (input.question === "Grade my answer") return json(response, 200, {
      status: "unsupported", request_id: randomUUID(),
      code: "official_grading_unavailable",
      message: "I cannot provide official answers or grades. I can help explain the selected topic." });
    if (askAttempts === 1) return json(response, 503, {
      error: { code: "provider_unavailable", message: "Learning answers are unavailable right now." } });
    return json(response, 200, { status: "ok", request_id: randomUUID(),
      response_id: randomUUID(), message_id: randomUUID(), curriculum_version: "revision-1",
      blocks: [{ id: randomUUID(), kind: "text", text: "Earth pulls the ball down." }],
      route: "direct_llm", knowledge_source: "model_generated", grounded: false,
      confidence: null, citations: [], resources: [] });
  }
  if (/^\/api\/v1\/sessions\/[0-9a-f-]+\/recommendations$/.test(pathname) && request.method === "GET") {
    const mode = savedSessions.find(row => row.id === pathname.split("/")[4])?.mode;
    return json(response, 200, mode === "study" ? { status: "ok", resources: [{
      id: "99999999-9999-4999-8999-999999999999", type: "diagram", title: "Gravity figure",
      description: "Falling objects", alt_text: "Ball falling", caption_or_transcript: null,
      accessibility_note: null, attribution: "FLAME" }], teachers: [{
      id: "88888888-8888-4888-8888-888888888888", name: "Science guide",
      bio: "Explains motion", qualifications: null, experience: null,
      languages: ["English"], availability: null,
      expertise: [{ subject_id: ids.subject, topic_id: null, claim_status: "reviewed" }] }] }
      : { status: "no_results", resources: [], teachers: [] });
  }
  if (/^\/api\/v1\/admin\/(resources|teachers|activity-kits)$/.test(pathname) && request.method === "GET")
    return json(response, 200, { items: [], total: 0, offset: 0, limit: 30 });
  if (/^\/api\/v1\/sessions\/[0-9a-f-]+\/topic-check\/history$/.test(pathname)) {
    const sessionId = pathname.split("/")[4];
    return json(response, 200, { items: topicHistory.get(sessionId) ?? [], next_cursor: null });
  }
  if (/^\/api\/v1\/sessions\/[0-9a-f-]+\/topic-check$/.test(pathname)) {
    const sessionId = pathname.split("/")[4];
    if (request.method === "GET") return json(response, 200, { pending: pendingTopics.get(sessionId) ?? null });
    topicCheckPosts++;
    const key = request.headers["idempotency-key"];
    if (!key) return json(response, 422, { error: { code: "validation_error" } });
    const input = await body(request);
    const keyId = sessionId + ":" + key;
    const prior = topicKeys.get(keyId);
    if (prior) return prior.question === input.question
      ? json(response, 200, prior.response)
      : json(response, 409, { error: { code: "idempotency_key_conflict" } });
    const older = pendingTopics.get(sessionId);
    if (older) {
      const row = (topicHistory.get(sessionId) ?? []).find(item => item.id === older.request_id);
      if (row) {
        row.status = "cancelled";
        row.response = { status: "cancelled", request_id: row.id,
          message: "This topic choice was replaced by a new question." };
      }
    }
    const requestId = randomUUID();
    let result;
    if (input.question.toLowerCase().includes("gravity")) {
      const makeCandidate = (subtopic_id, subtopic) => ({
        curriculum_id: ids.curriculum, level_id: ids.level, subject_id: ids.subject,
        domain_id: ids.domain, category_id: null, topic_id: ids.topic, subtopic_id,
        curriculum: "B4 Test", level: "Level 1", subject: "Science", domain: "Motion",
        topic: "Gravity", subtopic, revision: 1,
      });
      result = { status: "clarification", request_id: requestId,
        clarification_id: randomUUID(), question: input.question,
        prompt: "Which school topic do you mean?",
        expires_at: new Date(Date.now() + 600000).toISOString(),
        candidates: [makeCandidate(ids.subtopic, "Falling objects"),
          makeCandidate("77777777-7777-4777-8777-777777777777", "Orbit")] };
      pendingTopics.set(sessionId, result);
    } else {
      pendingTopics.delete(sessionId);
      result = { status: "out_of_scope", request_id: requestId,
        message: "I can help with topics in the school catalogue. Choose a topic and ask me again." };
    }
    topicKeys.set(keyId, { question: input.question, response: result });
    topicHistory.set(sessionId, [{ id: requestId, question: input.question,
      status: result.status, response: result, created_at: new Date().toISOString() },
      ...(topicHistory.get(sessionId) ?? [])]);
    return json(response, 200, result);
  }
  if (/^\/api\/v1\/sessions\/[0-9a-f-]+\/clarifications\/[0-9a-f-]+$/.test(pathname) && request.method === "POST") {
    const sessionId = pathname.split("/")[4];
    const pending = pendingTopics.get(sessionId);
    const input = await body(request);
    if (!pending || input.clarification_id !== pending.clarification_id)
      return json(response, 404, { error: { code: "clarification_not_found" } });
    const chosen = pending.candidates.find(row => row.subtopic_id === input.subtopic_id);
    if (!chosen) return json(response, 422, { error: { code: "clarification_choice_unclear" } });
    pendingTopics.delete(sessionId);
    const result = { status: "ready", request_id: pending.request_id, question: pending.question,
      context: chosen, answer_available: true };
    const row = (topicHistory.get(sessionId) ?? []).find(item => item.id === pending.request_id);
    if (row) { row.status = "ready"; row.response = result; }
    return json(response, 200, result);
  }  if (/^\/api\/v1\/sessions\/[0-9a-f-]+\/messages$/.test(pathname)) {
    if (messageFailure) { messageFailure = false; return json(response, 503, { error: { code: "unavailable" } }); }
    const sessionId = pathname.split("/")[4];
    const messages = savedMessages.get(sessionId) ?? [];
    const cursor = new URL(request.url, "http://localhost").searchParams.get("cursor");
    return json(response, 200, { items: cursor ? messages.slice(1) : messages.slice(0, 1),
      next_cursor: !cursor && messages.length > 1 ? "older" : null });
  }
  if (/^\/api\/v1\/sessions\/[0-9a-f-]+$/.test(pathname) && request.method === "DELETE") {
    savedSessions = savedSessions.filter(row => !pathname.endsWith(row.id));
    return json(response, 200, { status: "deleted" });
  }
  if (pathname === "/api/v1/me/activity" && request.method === "POST")
    return json(response, 201, { recorded: true });
  if (pathname === "/api/v1/me") return json(response, 200,
    { id: session === "b4-admin-session" ? "browser-admin" : "browser-student",
      role: session === "b4-admin-session" ? "admin" : "member", email: "admin@example.test" });
  if (pathname === "/api/v1/admin/curriculum/imports" && request.method === "POST") {
    importRows = [{ import_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", status: "uploaded",
      created_at: new Date().toISOString() }];
    return json(response, 201, { import_id: importRows[0].import_id, status: "uploaded", sheets: ["Level 1"] });
  }
  if (pathname === "/api/v1/admin/curriculum/imports" && request.method === "GET")
    return json(response, 200, { items: importRows, next_cursor: null });
  if (/^\/api\/v1\/admin\/curriculum\/imports\/[0-9a-f-]+\/preview$/.test(pathname) && request.method === "POST")
    return json(response, 200, { import_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      preview_revision: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", status: "previewed", issue_count: 0,
      counts: { created: 1, reused: 0, updated: 0, invalid: 0, duplicates: 0 },
      rows: [{ sheet: "Level 1", row_number: 2, normalized_path: ["Science", "Gravity", "Falling"],
        operation: "created", errors: [] }] });
  if (/^\/api\/v1\/admin\/curriculum\/imports\/[0-9a-f-]+\/source-rows$/.test(pathname) && request.method === "GET")
    return json(response, 200, { items: [{ sheet: "Level 1", row_number: 2,
      values: ["b4-browser", "Level 1", "Science", "Motion", "", "Gravity", "Falling"] }],
      total: 1, next_offset: null, workbook_codes: ["b4-browser"], expected_code: "b4-browser" });
  if (/^\/api\/v1\/admin\/curriculum\/imports\/[0-9a-f-]+\/review-rows$/.test(pathname) && request.method === "GET")
    return json(response, 200, { items: [{ sheet: "Level 1", row_number: 2,
      values: ["Level 1", "Science", "Motion", "", "Gravity", "Falling"],
      operation: "created", errors: [] }], total: 1, next_offset: null });
  if (/^\/api\/v1\/admin\/curriculum\/imports\/[0-9a-f-]+\/review$/.test(pathname) && request.method === "POST")
    return json(response, 200, { import_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      preview_revision: randomUUID(), status: "previewed", issue_count: 0,
      counts: { created: 1, reused: 0, updated: 0, invalid: 0, duplicates: 0 } });
  if (/^\/api\/v1\/admin\/curriculum\/imports\/[0-9a-f-]+\/commit$/.test(pathname) && request.method === "POST") {
    importRows = [{ import_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", status: "committed",
      created_at: new Date().toISOString(), counts: { created: 1, reused: 0, updated: 0 } }];
    const row = adminRows[0];
    const hierarchy = adminTrees.get(row.id);
    hierarchy.levels = [{ id: randomUUID(), name: "Level 1", version: 1, subjects: [{
      id: randomUUID(), name: "Science", version: 1, domains: [{
        id: randomUUID(), name: "Motion", version: 1, categories: [], topics: [{
          id: randomUUID(), name: "Gravity", version: 1, subtopics: [
            { id: randomUUID(), name: "Falling", version: 1 }],
        }],
      }],
    }] }];
    row.draft_revision += 1;
    return json(response, 200, { status: "replacement_draft_created", draft_revision: row.draft_revision, counts: importRows[0].counts });
  }
  if (/^\/api\/v1\/admin\/curriculum\/imports\/[0-9a-f-]+\/issues$/.test(pathname) && request.method === "GET")
    return json(response, 200, { items: [], total: 0 });
  if (/^\/api\/v1\/admin\/curriculum\/imports\/[0-9a-f-]+$/.test(pathname) && request.method === "GET")
    return json(response, 200, { import_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", status: importRows[0]?.status ?? "uploaded",
      filename: "curriculum.xlsx", curriculum_id: adminRows[0]?.id, sheets: ["Level 1"],
      sheet_levels: null, preview: null, payload_expires_at: new Date().toISOString() });
  if (pathname === "/api/v1/admin/curricula" && request.method === "GET")
    return json(response, 200, { items: adminRows, total: adminRows.length });
  if (pathname === "/api/v1/admin/curricula" && request.method === "POST") {
    const input = await body(request);
    const row = { id: randomUUID(), code: input.code, name: input.name, state: "draft", version: 1,
      revision: 0, published_revision: 0, draft_revision: 1, has_draft: true,
      updated_at: new Date().toISOString(), can_delete: true };
    adminRows.push(row);
    adminTrees.set(row.id, { ...row, levels: [] });
    return json(response, 201, row);
  }
  if (/^\/api\/v1\/admin\/curricula\/[0-9a-f-]+\/deletion-review$/.test(pathname)) {
    const row = adminRows.find(item => pathname.includes(item.id));
    return row ? json(response, 200, { ...row, counts: {
      hierarchy_nodes: 5, published_revisions: row.state === "published" ? 1 : 0,
      linked_resources: 0, activity_kits: 0, student_associations: 0,
      teacher_associations: 0, import_history: importRows.length }, blockers: {}, can_delete: true })
      : json(response, 404, {});
  }
  if (/^\/api\/v1\/admin\/curricula\/[0-9a-f-]+\/permanent$/.test(pathname) && request.method === "POST") {
    const input = await body(request);
    const index = adminRows.findIndex(item => pathname.includes(item.id));
    if (index < 0 || ![adminRows[index].name, adminRows[index].code].includes(input.confirm))
      return json(response, 422, { detail: "confirmation_mismatch" });
    const [removed] = adminRows.splice(index, 1);
    adminTrees.delete(removed.id);
    return json(response, 200, { id: removed.id, status: "deleted" });
  }
  if (/^\/api\/v1\/admin\/curricula\/[0-9a-f-]+\/paths\/batch$/.test(pathname) && request.method === "POST") {
    const input = await body(request);
    const row = adminRows.find(item => pathname.includes(item.id));
    const root = adminTrees.get(row.id);
    function node(parent, collection, name) {
      parent[collection] ??= [];
      let found = parent[collection].find(item => item.name === name);
      if (!found) { found = { id: randomUUID(), name, version: 1 }; parent[collection].push(found); }
      return found;
    }
    for (const change of input.changes) {
      if (change.action === "delete") continue;
      const v = change.values;
      const level = node(root, "levels", v.level);
      const subject = node(level, "subjects", v.subject);
      const domain = node(subject, "domains", v.domain);
      const category = v.category ? node(domain, "categories", v.category) : null;
      const topic = node(category ?? domain, "topics", v.topic);
      node(topic, "subtopics", v.subtopic);
    }
    row.draft_revision++;
    return json(response, 200, { draft_revision: row.draft_revision, rows: [] });
  }
  if (pathname.startsWith("/api/v1/admin/curricula/") && pathname.endsWith("/draft/rename") && request.method === "POST") {
    const input = await body(request);
    const row = adminRows.find(item => pathname.includes(item.id));
    const root = adminTrees.get(row.id);
    const scan = node => {
      if (node.id === input.node_id) { node.name = input.name; return true; }
      for (const key of ["levels", "subjects", "domains", "categories", "topics", "subtopics"])
        for (const child of node[key] ?? []) if (scan(child)) return true;
      return false;
    };
    scan(root);
    row.draft_revision += 1;
    return json(response, 200, { draft_revision: row.draft_revision, affected_paths: 1 });
  }
  if (/^\/api\/v1\/admin\/curricula\/[0-9a-f-]+\/tree$/.test(pathname)) {
    const row = adminRows.find(item => pathname.includes(item.id));
    return row ? json(response, 200, { ...row, levels: adminTrees.get(row.id).levels }) : json(response, 404, {});
  }
  if (/^\/api\/v1\/admin\/curriculum\/(level|subject|domain|category|topic|subtopic)$/.test(pathname) && request.method === "POST") {
    const input = await body(request);
    const kind = pathname.split("/").at(-1);
    const collection = { level: "levels", subject: "subjects", domain: "domains",
      category: "categories", topic: "topics", subtopic: "subtopics" }[kind];
    const root = adminTrees.get(adminRows[0].id);
    const scan = node => {
      if (node.id === input.parent_id) return node;
      for (const key of ["levels", "subjects", "domains", "categories", "topics", "subtopics"])
        for (const child of node[key] ?? []) { const found = scan(child); if (found) return found; }
      return null;
    };
    const parent = scan(root);
    const created = { id: randomUUID(), name: input.name, version: 1 };
    parent[collection] ??= [];
    parent[collection].push(created);
    adminRows[0].revision += 1;
    return json(response, 201, { id: created.id, version: 1, revision: adminRows[0].revision });
  }
  if (/^\/api\/v1\/admin\/curriculum\/(level|subject|domain|category|topic|subtopic)\/[0-9a-f-]+$/.test(pathname) && request.method === "PATCH") {
    const input = await body(request);
    const id = pathname.split("/").at(-1);
    const scan = node => {
      if (node.id === id) { node.name = input.name; node.version += 1; return node; }
      for (const key of ["levels", "subjects", "domains", "categories", "topics", "subtopics"])
        for (const child of node[key] ?? []) { const found = scan(child); if (found) return found; }
      return null;
    };
    const found = scan(adminTrees.get(adminRows[0].id));
    adminRows[0].revision += 1;
    return json(response, 200, { id, version: found.version, revision: adminRows[0].revision });
  }
  if (/^\/api\/v1\/admin\/curriculum\/curriculum\/[0-9a-f-]+\/publish$/.test(pathname) && request.method === "POST") {
    const row = adminRows[0];
    row.state = "published"; row.version += 1; row.revision += 1; row.published_revision = row.revision; row.draft_revision = 0;
    return json(response, 200, { id: row.id, state: row.state, version: row.version, revision: row.revision });
  }
  if (/^\/api\/v1\/admin\/curricula\/[0-9a-f-]+\/revisions$/.test(pathname))
    return json(response, 200, { items: [] });
  if (pathname === "/api/v1/curricula") return catalogueFailure
    ? json(response, 503, { error: { code: "unavailable" } })
    : json(response, 200, { items: [{ id: ids.curriculum, name: "B4 Test" }] });
  if (pathname === "/api/v1/curricula/" + ids.curriculum + "/levels")
    return json(response, 200, { items: [{ id: ids.level, name: "Level 1" }, { id: ids.otherLevel, name: "Level 2" }] });
  if (pathname.endsWith("/tree")) return json(response, 200, pathname.includes(ids.otherLevel) ? otherTree : { ...tree, levels: [...tree.levels, ...otherTree.levels] });
  if (pathname === "/api/v1/me/learning" && request.method === "GET")
    return json(response, 200, { items: memberships });
  if (pathname === "/api/v1/me/learning" && request.method === "POST") {
    const input = await body(request);
    let row = memberships.find(m => ["curriculum", "level", "subject", "domain", "category", "topic", "subtopic"]
      .every(key => (m[key + "_id"] ?? null) === (input[key + "_id"] ?? null)));
    if (!row) {
      row = { ...input, id: randomUUID(), visible: true, version: 1 };
      memberships.push(row);
    } else if (!row.visible) { row.visible = true; row.version++; }
    return json(response, 200, row);
  }
  if (pathname.startsWith("/api/v1/me/learning/") && request.method === "PATCH") {
    const input = await body(request);
    const row = memberships.find(m => pathname.endsWith("/" + m.id));
    if (!row) return json(response, 404, { error: { code: "not_found" } });
    if (row.version !== input.expected_version) return json(response, 409, { error: { code: "version_conflict" } });
    row.visible = input.visible; row.version++;
    return json(response, 200, row);
  }
  json(response, 404, { error: { code: "not_found" } });
});

(async () => {
  await new Promise(resolve => mock.listen(0, "127.0.0.1", resolve));
  const apiPort = mock.address().port;
  const next = spawn(process.execPath, [path.join(cwd, "node_modules/next/dist/bin/next"), "start", "-p", "3107"], {
    cwd, windowsHide: true, env: { ...process.env,
      FLAME_API_URL: "http://127.0.0.1:" + apiPort,
      FLAME_BFF_SHARED_KEY: "b4-browser-secret",
      FLAME_WEB_ORIGIN: base,
    },
  });
  let browser;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt++) {
      try { const response = await fetch(base + "/sign-in"); if (response.ok) { ready = true; break; } }
      catch {}
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    assert(ready, "Next server did not start");
    browser = await chromium.launch({ channel: "msedge", headless: true });
    const context = await browser.newContext();
    await context.addCookies([{ name: "flame_session", value: "b4-browser-session", url: base, httpOnly: true }]);
    const page = await context.newPage();
    await page.goto(base, { waitUntil: "domcontentloaded" });
    assert(await page.getByText("Your learning space is empty.").first().isVisible());
    await page.getByRole("button", { name: "Add from Library" }).first().click();
    const library = page.locator(".library-dialog");
    await library.getByRole("tab", { name: "Subject", exact: true }).click();
    await library.getByRole("combobox", { name: "Level" }).selectOption(ids.level);
    assert.deepEqual(await library.getByRole("combobox", { name: "Subject" }).locator("option").allTextContents(),
      ["All subjects", "Science"]);
    assert.equal(await library.getByRole("button", { name: "Add Mathematics" }).count(), 0);
    await library.getByRole("combobox", { name: "Level" }).selectOption(ids.otherLevel);
    assert.deepEqual(await library.getByRole("combobox", { name: "Subject" }).locator("option").allTextContents(),
      ["All subjects", "Mathematics"]);
    assert.equal(await library.getByRole("button", { name: "Add Science" }).count(), 0);
    await library.getByRole("combobox", { name: "Level" }).selectOption("");
    await library.getByRole("tab", { name: "Topic & Subtopic" }).click();
    await library.getByRole("searchbox", { name: "Search library" }).fill("Falling");
    assert(await library.getByRole("button", { name: "Add Falling objects" }).isVisible());
    await library.getByRole("button", { name: "Add Falling objects" }).click();
    await page.getByText("Falling objects added to My Learning.").waitFor();
    assert.equal(memberships[0].subtopic_id, ids.subtopic);
    await library.getByRole("button", { name: "Done" }).click();
    await page.reload({ waitUntil: "domcontentloaded" });
    assert(await page.getByText("Falling objects").first().isVisible());
    const learningNav = page.locator(".desktop-sidebar .curriculum-navigation");
    await learningNav.getByRole("button", { name: "Find a subtopic" }).click();
    const subtopicSearch = learningNav.getByRole("searchbox", { name: "Find a subtopic" });
    await subtopicSearch.fill("Falling");
    await learningNav.getByText("1 matching subtopic").waitFor();
    assert(await learningNav.getByRole("button", { name: "Falling objects" }).isVisible());
    await subtopicSearch.fill("not-a-subtopic");
    await learningNav.getByText("No subtopics match these filters.").waitFor();
    await learningNav.getByRole("button", { name: "Close search" }).click();
    await page.getByRole("button", { name: "Remove Science from My Learning" }).first().click();
    await page.locator(".removal-dialog").getByRole("button", { name: /Remove|Hide/ }).last().click();
    await page.waitForTimeout(1500);
    await page.getByText("Your learning space is empty.").first().waitFor();
    await page.reload({ waitUntil: "domcontentloaded" });
    assert(await page.getByText("Your learning space is empty.").first().isVisible());
    const subjectMembership = memberships.find(m => m.subject_id === ids.subject && !m.domain_id);
    assert(subjectMembership && !subjectMembership.visible);
    await page.getByRole("button", { name: "Add from Library" }).first().click();
    await page.locator(".library-dialog").getByRole("tab", { name: "Subject", exact: true }).click();
    await page.locator(".library-dialog").getByRole("button", { name: "Add Science" }).click();
    await page.getByText("Science added to My Learning.").waitFor();
    assert.equal(memberships.find(m => m.id === subjectMembership.id).visible, true);
    await page.locator(".library-dialog").getByRole("button", { name: "Done" }).click();
    await page.reload({ waitUntil: "domcontentloaded" });
    assert(await page.getByText("Falling objects").first().isVisible());
    catalogueFailure = true;
    await page.reload({ waitUntil: "domcontentloaded" });
    assert(await page.getByRole("heading", { name: "Learning space unavailable" }).isVisible());
    catalogueFailure = false;
    await page.getByRole("link", { name: "Try again" }).click();
    await page.getByText("Falling objects").first().waitFor();
    await page.getByRole("button", { name: "Curiosity", exact: true }).first().click();
    await page.locator(".desktop-sidebar .saved-sessions").getByRole("button", { name: "Start Curiosity session" }).click();
    const savedDialog = page.locator(".desktop-sidebar .saved-session-dialog");
    await savedDialog.getByRole("heading", { name: "Curiosity" }).waitFor();
    assert.equal(savedSessions.length, 1);
    savedMessages.set(savedSessions[0].id, [
      { id: randomUUID(), role: "assistant", turn_number: 1, blocks: [{ kind: "text", text: "Because of gravity." }] },
      { id: randomUUID(), role: "user", turn_number: 1, blocks: [{ kind: "text", text: "Why do objects fall?" }] },
    ]);
    assert.equal(await savedDialog.getByText("Check a school topic").count(), 0);
    await savedDialog.getByRole("button", { name: "Close" }).click();
    await page.reload({ waitUntil: "domcontentloaded" });
    messageFailure = true;
    await page.locator(".desktop-sidebar .saved-sessions").getByRole("button", { name: /Curiosity/ }).last().click();
    await savedDialog.getByRole("alert").getByText("Saved conversations could not be loaded.").waitFor();
    await savedDialog.getByRole("button", { name: "Try loading messages again" }).click();
    await savedDialog.getByText("Because of gravity.").waitFor();
    await savedDialog.getByRole("button", { name: "Older messages" }).click();
    await savedDialog.getByText("Why do objects fall?").waitFor();
    const resumedId = savedSessions[0].id;
    await savedDialog.getByRole("button", { name: "Continue in workspace" }).click();
    await savedDialog.waitFor({ state: "hidden" });
    await page.locator(".conversation-turn").getByText("Because of gravity.").waitFor();
    await page.locator("#flame-prompt").fill("Tell me more about gravity.");
    await page.getByRole("button", { name: "Send learning request" }).click();
    await page.getByText("Computers follow instructions to work with information.").waitFor();
    assert.equal(curiositySessionIds[0], resumedId);
    await page.locator(".desktop-sidebar .saved-sessions").getByRole("button", { name: /Curiosity/ }).last().click();
    await savedDialog.getByRole("button", { name: "Delete this conversation" }).click();
    await savedDialog.getByRole("button", { name: "Confirm deletion" }).click();
    await savedDialog.waitFor({ state: "hidden" });
    assert.equal(savedSessions.length, 0);
    await page.getByRole("button", { name: "Curiosity", exact: true }).first().click();
    await page.getByRole("button", { name: "How do computers work?" }).click();
    assert.equal(await page.locator("#flame-prompt").inputValue(), "How do computers work?");
    await page.getByRole("button", { name: "Send learning request" }).click();
    await page.getByText("Computers follow instructions to work with information.").waitFor();
    assert.equal(curiosityAsks, 2);
    assert.equal(topicCheckPosts, 0);
    assert.equal(curiosityBodies[1].topic_check_id, undefined);
    assert.equal(curiosityBodies[1].context, null);
    await page.getByRole("button", { name: "Study", exact: true }).first().click();
    await page.locator(".desktop-sidebar .topic-button").first().click();
    await page.locator(".desktop-sidebar .saved-sessions").getByRole("button", { name: "Start Study session" }).click();
    await savedDialog.getByRole("heading", { name: "Falling objects" }).waitFor();
    const studyId = savedSessions[0].id;
    await savedDialog.getByRole("button", { name: "Close" }).click();
    savedMessages.set(studyId, [
      { id: randomUUID(), role: "assistant", turn_number: 1, blocks: [{ kind: "text", text: "A ball falls because Earth pulls it." }] },
      { id: randomUUID(), role: "user", turn_number: 1, blocks: [{ kind: "text", text: "Why do balls fall?" }] },
    ]);
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.locator(".desktop-sidebar .saved-sessions").getByRole("button", { name: /Falling objects/ }).last().click();
    await savedDialog.getByText("A ball falls because Earth pulls it.").waitFor();
    await savedDialog.getByRole("button", { name: "Older messages" }).click();
    await savedDialog.getByText("Why do balls fall?").waitFor();
    await savedDialog.getByRole("button", { name: "Continue in workspace" }).click();
    await page.locator(".conversation-turn").getByText("A ball falls because Earth pulls it.").waitFor();
    await page.locator("#flame-prompt").fill("Why does a ball fall?");
    await page.getByRole("button", { name: "Send learning request" }).click();
    await page.getByText("Learning answers are unavailable right now.").waitFor();
    await page.getByRole("button", { name: "Retry question" }).click();
    await page.getByText("Earth pulls the ball down.").waitFor();
    await page.getByRole("button", { name: /Gravity figure/ }).first().waitFor();
    await page.getByText("Science guide").first().waitFor();
    assert.equal(await page.getByText("Math guide").count(), 0);
    assert.equal(askAttempts, 2);
    assert.deepEqual(studySessionIds, [studyId, studyId]);
    assert.notEqual(askKeys[0], askKeys[1]);
    await page.getByText("AI-generated explanation").first().waitFor();
    await page.locator("#flame-prompt").fill("Grade my answer");
    await page.getByRole("button", { name: "Send learning request" }).click();
    await page.getByText("I cannot provide official answers or grades.").waitFor();
    assert.equal(await page.locator(".conversation-turn").last()
      .getByRole("button", { name: "Retry question" }).count(), 0);
    await page.locator(".desktop-sidebar .topic-open").filter({ hasText: "Gravity" }).first().click();
    await page.getByRole("heading", { name: "Gravity", exact: true }).last().waitFor();
    await page.screenshot({ path: path.resolve(__dirname, "../../../../work/topic-view.png") });
    assert.equal(await page.locator(".subtopic-actions").getByRole("button", { name: "Falling objects" }).count(), 1);
    assert.equal(await page.locator(".subtopic-actions-bottom").count(), 0);
    assert(await page.locator(".topic-workspace h1").evaluate(heading =>
      Boolean(heading.compareDocumentPosition(document.querySelector(".subtopic-actions")) & Node.DOCUMENT_POSITION_FOLLOWING)));
    await page.locator("#flame-prompt").fill("What is gravity?");
    await page.getByRole("button", { name: "Send learning request" }).click();
    await page.getByText("Earth pulls the ball down.").last().waitFor();
    assert.equal(studyBodies.at(-1).context.subtopic_id, null);
    assert(savedSessions.some(row => row.mode === "study" && row.context?.subtopic_id === null));
    await page.locator(".desktop-sidebar .saved-sessions").getByRole("button", { name: /Gravity ·/ }).first().click();
    await savedDialog.getByRole("heading", { name: "Gravity" }).waitFor();
    await savedDialog.getByRole("button", { name: "Continue in workspace" }).click();
    await page.getByRole("heading", { name: "Gravity", exact: true }).last().waitFor();
    await page.locator(".subtopic-actions").getByRole("button", { name: "Falling objects" }).click();
    await page.getByRole("heading", { name: "Falling objects", exact: true }).last().waitFor();
    await page.screenshot({ path: path.resolve(__dirname, "../../../../work/subtopic-view.png") });
    assert.equal(await page.locator(".subtopic-actions").count(), 0);
    const familyNav = page.locator(".topic-family-nav");
    assert(await familyNav.getByRole("button", { name: "View Gravity topic" }).isVisible());
    assert.equal(await familyNav.getByRole("button", { name: "Falling objects" }).getAttribute("aria-current"), "page");
    const topicFill = await familyNav.locator(".topic-family-topic").evaluate(el => getComputedStyle(el).backgroundColor);
    const siblingFill = await familyNav.getByRole("button", { name: "Orbit" }).evaluate(el => getComputedStyle(el).backgroundColor);
    const selectedFill = await familyNav.getByRole("button", { name: "Falling objects" }).evaluate(el => getComputedStyle(el).backgroundColor);
    assert.notEqual(topicFill, siblingFill);
    assert.notEqual(selectedFill, siblingFill);
    await familyNav.getByRole("button", { name: "Orbit" }).click();
    await page.getByRole("heading", { name: "Orbit", exact: true }).last().waitFor();
    assert.equal(await familyNav.getByRole("button", { name: "Orbit" }).getAttribute("aria-current"), "page");
    await familyNav.getByRole("button", { name: "Falling objects" }).click();
    await page.getByRole("heading", { name: "Falling objects", exact: true }).last().waitFor();
    await familyNav.getByRole("button", { name: "View Gravity topic" }).click();
    await page.getByRole("heading", { name: "Gravity", exact: true }).last().waitFor();
    await page.getByRole("button", { name: "Curiosity", exact: true }).first().click();
    await page.locator("#flame-prompt").fill("Watch this video");
    await page.getByRole("button", { name: "Send learning request" }).click();
    await page.getByText("I cannot watch videos, listen to audio, or transcribe recordings.").waitFor();
    assert.equal(await page.locator(".conversation-turn").last()
      .getByRole("button", { name: "Retry question" }).count(), 0);
    const adminContext = await browser.newContext();
    await adminContext.addCookies([{ name: "flame_session", value: "b4-admin-session", url: base, httpOnly: true }]);
    const adminPage = await adminContext.newPage();
    await adminPage.goto(base + "/admin", { waitUntil: "domcontentloaded" });
    assert(await adminPage.getByRole("heading", { name: "FLAME administration" }).isVisible());
    await adminPage.getByRole("button", { name: "Create curriculum" }).click();
    await adminPage.getByRole("button", { name: /Import from Excel/ }).click();
    await adminPage.getByRole("textbox", { name: "Curriculum code" }).fill("b4-browser");
    await adminPage.getByRole("textbox", { name: "Curriculum name" }).fill("Browser curriculum");
    await adminPage.getByRole("button", { name: "Create draft" }).click();
    await adminPage.getByText("Draft curriculum created.").waitFor();
    assert.equal(adminRows[0].code, "b4-browser");
    assert.equal(await adminPage.getByRole("button", { name: "Excel Imports" }).count(), 0);
    await adminPage.screenshot({ path: path.resolve(__dirname, "../../../../work/admin-curriculum-ux.png"), fullPage: true });
    await adminPage.getByLabel("Excel workbook").setInputFiles({ name: "curriculum.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", buffer: Buffer.from("mock workbook") });
    await adminPage.getByRole("button", { name: "Upload workbook" }).click();
    await adminPage.getByText("Map sheets to levels").waitFor();
    assert.equal(await adminPage.getByPlaceholder("Level name, or leave out").inputValue(), "Level 1");
    await adminPage.getByRole("button", { name: "Open hierarchy" }).click();
    await adminPage.getByRole("heading", { name: "Uploaded Excel hierarchy" }).waitFor();
    await adminPage.getByRole("region", { name: "Uploaded Excel rows" }).getByText("Falling").waitFor();
    assert.equal(adminRows[0].draft_revision, 1);
    await adminPage.reload({ waitUntil: "domcontentloaded" });
    await adminPage.getByRole("button", { name: "Browser curriculum" }).click();
    await adminPage.getByRole("heading", { name: "Uploaded Excel hierarchy" }).waitFor();
    await adminPage.getByRole("region", { name: "Uploaded Excel rows" }).getByText("Falling").waitFor();
    await adminPage.getByRole("button", { name: "Continue import" }).click();
    await adminPage.getByPlaceholder("Level name, or leave out").fill("Level 1");
    await adminPage.getByRole("button", { name: "Validate and preview" }).click();
    await adminPage.getByText("No blocking row issues.").waitFor();
    await adminPage.screenshot({ path: path.resolve(__dirname, "../../../../work/admin-import-ux.png"), fullPage: true });
    await adminPage.locator(".admin-import-review input[aria-label='Subtopic import row 1']").fill("Falling corrected");
    await adminPage.getByRole("button", { name: "Save corrections" }).click();
    await adminPage.getByText("Workbook corrections saved and validated.").waitFor();

    const adminAudit = await new AxeBuilder({ page: adminPage }).exclude("nextjs-portal")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    assert.deepEqual(adminAudit.violations.map(violation => violation.id), [],
      JSON.stringify(adminAudit.violations.map(violation => ({ id: violation.id, nodes: violation.nodes.map(node => ({ target: node.target, summary: node.failureSummary })) }))));
    await adminPage.getByLabel(/Type REPLACE b4-browser/).fill("REPLACE b4-browser");
    adminPage.once("dialog", dialog => dialog.accept());
    await adminPage.getByRole("button", { name: "Create replacement draft" }).click();
    await adminPage.getByRole("heading", { name: "Hierarchy Table" }).waitFor();
    await adminPage.evaluate(() => window.scrollTo(0, 0));
    await adminPage.screenshot({ path: path.resolve(__dirname, "../../../../work/admin-hierarchy-compact.png") });
    const workspaceGeometry = await adminPage.evaluate(() => {
      const grid = document.querySelector(".admin-grid-scroll");
      const header = document.querySelector(".admin-workspace-header");
      return { gridTop: grid.getBoundingClientRect().top,
        gridHeight: grid.getBoundingClientRect().height,
        headerHeight: header.getBoundingClientRect().height,
        viewportHeight: window.innerHeight };
    });
    assert(workspaceGeometry.headerHeight < workspaceGeometry.viewportHeight * .4,
      JSON.stringify(workspaceGeometry));
    assert(workspaceGeometry.gridTop < workspaceGeometry.viewportHeight * .75,
      JSON.stringify(workspaceGeometry));
    assert.equal(adminRows[0].state, "draft");
    const firstPath = adminPage.locator(".admin-grid-table tbody tr").first();
    await firstPath.getByRole("button", { name: "Edit topic Gravity" }).click();
    await firstPath.locator("input[data-grid-field=topic]").fill("Gravity revised");
    await firstPath.getByRole("button", { name: "Save", exact: true }).click();
    await firstPath.locator("input[data-grid-field=topic]").waitFor({ state: "detached" });
    await adminPage.getByRole("button", { name: "Add row" }).first().click();
    const newPath = adminPage.locator(".admin-grid-table tbody tr").last();
    await newPath.locator("input[data-grid-field=subtopic]").fill("New subtopic");
    await newPath.getByRole("button", { name: "Save", exact: true }).click();
    await newPath.locator("input[data-grid-field=subtopic]").waitFor({ state: "detached" });
    const lastPath = adminPage.locator(".admin-grid-table tbody tr").last();
    const menuDetails = lastPath.locator("details.admin-row-overflow");
    const menuTrigger = lastPath.locator('summary[aria-label="More actions for path 2"]');
    await menuTrigger.click();
    assert(await menuDetails.evaluate(menu => menu.open));
    await adminPage.getByRole("heading", { name: "Hierarchy Table" }).click();
    assert.equal(await menuDetails.evaluate(menu => menu.open), false);
    await menuTrigger.click();
    await menuTrigger.click();
    assert.equal(await menuDetails.evaluate(menu => menu.open), false);
    await menuTrigger.click();
    const rowMenu = await lastPath.locator(".admin-overflow-menu").boundingBox();
    assert(rowMenu && rowMenu.y >= 0 && rowMenu.y + rowMenu.height <= 720, JSON.stringify(rowMenu));
    await lastPath.getByRole("button", { name: "Duplicate" }).click();
    await adminPage.getByText("This complete path already exists.").waitFor();
    adminPage.once("dialog", dialog => dialog.accept());
    await adminPage.getByRole("button", { name: "Discard changes" }).click();
    const workspaceMenu = adminPage.locator(".admin-workspace-actions details.admin-overflow");
    const workspaceTrigger = workspaceMenu.locator('summary[aria-label="More curriculum actions"]');
    await workspaceTrigger.click();
    const workspaceTriggerBox = await workspaceTrigger.boundingBox();
    const workspacePanelBox = await workspaceMenu.locator(".admin-overflow-menu").boundingBox();
    assert(workspaceTriggerBox && workspacePanelBox);
    assert(Math.abs(workspacePanelBox.x + workspacePanelBox.width / 2 - workspaceTriggerBox.x - workspaceTriggerBox.width / 2) < 75);
    await adminPage.getByRole("heading", { name: "Browser curriculum" }).click();
    assert.equal(await workspaceMenu.evaluate(menu => menu.open), false);
    await workspaceTrigger.click();
    await workspaceTrigger.click();
    assert.equal(await workspaceMenu.evaluate(menu => menu.open), false);
    await workspaceTrigger.click();
    await adminPage.getByRole("button", { name: "Delete permanently" }).first().click();
    await adminPage.getByRole("heading", { name: "Delete Browser curriculum permanently?" }).waitFor();
    await adminPage.getByText("hierarchy nodes").waitFor();
    await adminPage.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
    await adminPage.getByRole("tab", { name: "Import History" }).click();
    await adminPage.getByRole("button", { name: /committed/ }).waitFor();
    await adminPage.getByRole("tab", { name: "Hierarchy" }).click();
    adminPage.once("dialog", dialog => dialog.accept());
    await adminPage.getByRole("button", { name: "Publish changes" }).click();
    await adminPage.getByText("Curriculum published at revision").waitFor();
    await adminPage.getByRole("button", { name: "← All curricula" }).click();
    const catalogueRow = adminPage.locator(".admin-curricula-table tbody tr").filter({ hasText: "Browser curriculum" });
    const catalogueMenu = catalogueRow.locator("details.admin-overflow");
    const catalogueTrigger = catalogueMenu.locator('summary[aria-label="More actions for Browser curriculum"]');
    await catalogueTrigger.click();
    const catalogueTriggerBox = await catalogueTrigger.boundingBox();
    const cataloguePanelBox = await catalogueMenu.locator(".admin-overflow-menu").boundingBox();
    assert(catalogueTriggerBox && cataloguePanelBox);
    assert(Math.abs(cataloguePanelBox.x + cataloguePanelBox.width / 2 - catalogueTriggerBox.x - catalogueTriggerBox.width / 2) < 20);
    assert(await catalogueMenu.evaluate(menu => menu.open));
    await adminPage.getByRole("heading", { name: "Curricula" }).click();
    assert.equal(await catalogueMenu.evaluate(menu => menu.open), false);
    await catalogueTrigger.click();
    await catalogueTrigger.click();
    assert.equal(await catalogueMenu.evaluate(menu => menu.open), false);
    await adminPage.getByRole("button", { name: "Create curriculum" }).click();
    await adminPage.getByRole("textbox", { name: "Curriculum code" }).fill("empty-browser");
    await adminPage.getByRole("textbox", { name: "Curriculum name" }).fill("Empty curriculum");
    await adminPage.getByRole("button", { name: "Create draft" }).click();
    await adminPage.getByRole("heading", { name: "Empty curriculum" }).waitFor();
    await adminPage.getByText("No saved hierarchy is ready.").waitFor();
    assert.equal(await adminPage.locator(".admin-workspace-metrics").getByText("Published revision").locator("..").locator("strong").textContent(), "0");
    assert(await adminPage.getByRole("button", { name: "Publish changes" }).isDisabled());
    await adminPage.getByRole("button", { name: "Resource Library" }).click();
    await adminPage.getByRole("heading", { name: "Resource Library" }).waitFor();
    await adminPage.getByRole("button", { name: "Teachers", exact: true }).click();
    await adminPage.getByRole("heading", { name: "Teacher Management" }).waitFor();
    await adminPage.getByRole("button", { name: "Activity Kits" }).click();
    await adminPage.getByRole("heading", { name: "Activity Kit Management" }).waitFor();
    await adminPage.goto(base, { waitUntil: "domcontentloaded" });
    const adminLink = adminPage.locator(".desktop-sidebar").getByRole("link", { name: "Admin dashboard" });
    await adminLink.waitFor();
    await adminLink.click();
    await adminPage.getByRole("heading", { name: "FLAME administration" }).waitFor();
    await adminPage.setViewportSize({ width: 390, height: 844 });
    await adminPage.screenshot({ path: path.resolve(__dirname, "../../../../work/admin-mobile-ux.png"), fullPage: true });
    const overflow = await adminPage.evaluate(() => ({ width: window.innerWidth, scroll: document.documentElement.scrollWidth, nodes: [...document.querySelectorAll("*")].filter(el => el.getBoundingClientRect().right > window.innerWidth + 2).slice(0, 12).map(el => ({ tag: el.tagName, className: el.className, right: el.getBoundingClientRect().right })) }));
    assert(overflow.scroll <= overflow.width + 1, JSON.stringify(overflow));
    await adminContext.close();
    console.log("B4-B9 browser catalogue, Study/Curiosity continuation, answer retry, recommendation cards and admin navigation passed");
  } finally {
    if (browser) await browser.close();
    next.kill();
    await new Promise(resolve => mock.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });





















