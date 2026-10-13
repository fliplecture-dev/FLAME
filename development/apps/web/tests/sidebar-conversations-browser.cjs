const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');
const { spawn } = require('node:child_process');
const { chromium } = require(path.resolve(__dirname, '../../../../.kilo/ui-check/node_modules/playwright'));
const cwd = path.resolve(__dirname, '..');
const base = 'http://localhost:3112';
const uid = n => `${String(n).padStart(8, '0')}-1111-4111-8111-111111111111`;
const ids = { c: uid(1), l: uid(2), s: uid(3), d: uid(4), t: uid(5), st: uid(6) };
const tree = { id: ids.c, name: 'Sidebar curriculum', revision: 1, levels: [{ id: ids.l, name: 'Grade 1', subjects: [{ id: ids.s, name: 'Science', domains: [{ id: ids.d, name: 'Motion', categories: [], topics: [{ id: ids.t, name: 'Gravity', subtopics: [{ id: ids.st, name: 'Falling objects' }] }] }] }] }] };
const contextPath = { curriculum_id: ids.c, level_id: ids.l, subject_id: ids.s, domain_id: ids.d, category_id: null, topic_id: ids.t, subtopic_id: ids.st, names: { topic: 'Gravity', subtopic: 'Falling objects' } };
const now = new Date().toISOString();
const rows = [
  { id: uid(10), mode: 'study', context: contextPath, revision: 1, pinned: false, first_question: 'Why do objects fall?', created_at: now, updated_at: now, recent_at: now },
  { id: uid(11), mode: 'curiosity', context: null, revision: null, pinned: false, first_question: 'How do enormous aeroplanes stay in the air when they are so heavy?', created_at: now, updated_at: now, recent_at: now },
  { id: uid(12), mode: 'curiosity', context: null, revision: null, pinned: true, first_question: 'Why is the sky blue?', created_at: now, updated_at: now, recent_at: now },
];
let opens = 0;
const messages = new Map(rows.map((row, index) => [row.id, [
  { id: uid(20 + index * 2), role: 'user', turn_number: 1, blocks: [{ kind: 'text', text: row.first_question }] },
  { id: uid(21 + index * 2), role: 'assistant', turn_number: 1, blocks: [{ kind: 'text', text: 'Fixture answer for ' + row.first_question }] },
]]));
const json = (response, value, status = 200) => { response.writeHead(status, { 'content-type': 'application/json' }); response.end(JSON.stringify(value)); };
const body = async request => { const chunks = []; for await (const chunk of request) chunks.push(chunk); return JSON.parse(Buffer.concat(chunks).toString() || '{}'); };
const mock = http.createServer(async (request, response) => {
  const route = new URL(request.url, 'http://fixture').pathname.replace('/api/v1/', '');
  if (request.headers['x-bff-key'] !== 'sidebar-test-secret' || request.headers['x-flame-session'] !== 'sidebar-test-session') return json(response, {}, 401);
  if (route === 'me') return json(response, { id: uid(99), role: 'member', email: 'sidebar@example.test' });
  if (route === 'curricula') return json(response, { items: [{ id: ids.c }] });
  if (route === `curricula/${ids.c}/tree`) return json(response, tree);
  if (route === 'me/learning') return json(response, { items: [{ id: uid(98), curriculum_id: ids.c, visible: true, version: 1 }] });
  if (route === 'me/activity') return json(response, { recorded: true });
  if (route === 'sessions') return json(response, { items: rows, next_cursor: null });
  if (route === 'sessions/recent/clear') { rows.forEach(row => { if (!row.pinned) row.recent_at = null; }); return json(response, { status: 'cleared' }); }
  if (route === 'sessions/pins/clear') { rows.forEach(row => { if (row.pinned) { row.pinned = false; row.recent_at = new Date().toISOString(); } }); return json(response, { status: 'unpinned' }); }
  const match = route.match(/^sessions\/([^/]+)\/(pin|recent|messages|recommendations)$/);
  if (match) {
    const row = rows.find(row => row.id === match[1]);
    if (!row) return json(response, {}, 404);
    if (match[2] === 'messages') return json(response, { items: messages.get(row.id), next_cursor: null });
    if (match[2] === 'recommendations') return json(response, { status: 'available', resources: [], teachers: [] });
    if (match[2] === 'pin') { row.pinned = (await body(request)).pinned; row.recent_at ||= new Date().toISOString(); return json(response, row); }
    if (match[2] === 'recent') { opens++; row.recent_at = new Date().toISOString(); return json(response, row); }
  }
  json(response, { error: { code: 'not_found' } }, 404);
});
(async () => {
  await new Promise(resolve => mock.listen(0, '127.0.0.1', resolve));
  const server = spawn(process.execPath, [path.join(cwd, 'node_modules/next/dist/bin/next'), 'start', '-p', '3112'], { cwd, windowsHide: true, env: { ...process.env, FLAME_API_URL: `http://127.0.0.1:${mock.address().port}`, FLAME_BFF_SHARED_KEY: 'sidebar-test-secret', FLAME_WEB_ORIGIN: base } });
  let browser;
  let log = '';
  server.stdout.on('data', data => log += data); server.stderr.on('data', data => log += data);
  try {
    let ready = false;
    for (let i = 0; i < 40; i++) { try { if ((await fetch(base + '/sign-in')).ok) { ready = true; break; } } catch {} await new Promise(resolve => setTimeout(resolve, 500)); }
    assert(ready, log);
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    const browserContext = await browser.newContext({ viewport: { width: 1200, height: 850 } });
    await browserContext.addCookies([{ name: 'flame_session', value: 'sidebar-test-session', url: base, httpOnly: true }]);
    const page = await browserContext.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(base, { waitUntil: 'networkidle' });
    const sidebar = page.locator('.desktop-sidebar');
    const sections = sidebar.locator('.shortcut-section');
    assert.deepEqual(await sections.locator('.shortcut-toggle span').allTextContents(), ['Pinned', 'Recent']);
    const pinned = sections.nth(0), recent = sections.nth(1);
    const learning = sidebar.locator('.curriculum-navigation');
    const learningToggle = learning.getByRole('button', { name: 'My Learning', exact: true });
    assert.equal(await learning.getByRole('button', { name: /^(Expand|Collapse) all$/ }).count(), 0);
    await learningToggle.click();
    assert.equal(await learningToggle.getAttribute('aria-expanded'), 'false');
    assert.equal(await learning.getByRole('button', { name: 'Add from Library', exact: true }).count(), 0);
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await learningToggle.getAttribute('aria-expanded'), 'false');
    await learningToggle.press('Space');
    await learning.getByRole('button', { name: 'Add from Library', exact: true }).waitFor();
    await learning.getByRole('button', { name: 'Find a subtopic', exact: true }).click();
    await learning.getByRole('searchbox', { name: 'Find a subtopic', exact: true }).waitFor();
    await learning.getByRole('button', { name: 'Close search', exact: true }).click();
    const curriculumToggle = learning.getByRole('button', { name: /^Sidebar curriculum/ }).first();
    await curriculumToggle.click();
    assert.equal(await curriculumToggle.getAttribute('aria-expanded'), 'false');
    await curriculumToggle.click();
    assert.equal(await curriculumToggle.getAttribute('aria-expanded'), 'true');

    const longLink = recent.getByRole('button', { name: /How do enormous aeroplanes.*curiosity/ });
    await longLink.waitFor();
    assert(await longLink.locator('span').first().evaluate(el => el.scrollWidth > el.clientWidth), 'Long title did not truncate');
    const actionsFit = await recent.locator('li').evaluateAll(items => items.every(item => item.scrollWidth <= item.clientWidth));
    assert(actionsFit, 'Long title pushed icons out of its row');

    await pinned.locator('.shortcut-toggle').click();
    assert.equal(await pinned.locator('.shortcut-toggle').getAttribute('aria-expanded'), 'false');
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await pinned.locator('.shortcut-toggle').getAttribute('aria-expanded'), 'false');
    await pinned.locator('.shortcut-toggle').press('Enter');
    await recent.locator('.shortcut-toggle').click();
    assert.equal(await recent.locator('.shortcut-toggle').getAttribute('aria-expanded'), 'false');
    await recent.locator('.shortcut-toggle').click();
    await recent.getByRole('button', { name: 'Falling objects (study)' }).click();
    const titlePin = page.locator('.conversation-title-row').getByRole('button', { name: 'Pin conversation', exact: true });
    await titlePin.waitFor();
    await titlePin.click();
    await pinned.getByRole('button', { name: 'Falling objects (study)' }).waitFor();
    assert.equal(await recent.getByRole('button', { name: 'Falling objects (study)' }).count(), 0);
    await page.locator('.conversation-title-row').getByRole('button', { name: 'Unpin conversation', exact: true }).click();
    await recent.getByRole('button', { name: 'Falling objects (study)' }).waitFor();
    await recent.getByRole('button', { name: 'Pin conversation: Falling objects' }).click();
    await pinned.getByRole('button', { name: 'Unpin conversation: Falling objects' }).waitFor();
    await page.reload({ waitUntil: 'networkidle' });
    await pinned.getByRole('button', { name: 'Falling objects (study)' }).waitFor();
    await Promise.all([
      page.waitForResponse(response => response.url().endsWith(`/api/b4/sessions/${uid(10)}/recent`) && response.request().method() === 'POST'),
      pinned.getByRole('button', { name: 'Falling objects (study)' }).click(),
    ]);
    await page.locator('.conversation-title-row').getByRole('button', { name: 'Unpin conversation', exact: true }).waitFor();
    const beforeOpen = opens;
    await pinned.getByRole('button', { name: 'Unpin conversation: Falling objects' }).click();
    await recent.getByRole('button', { name: 'Falling objects (study)' }).waitFor();
    assert.equal(opens, beforeOpen, 'Unpin accidentally opened conversation');
    await page.locator('.conversation-title-row').getByRole('button', { name: 'Pin conversation', exact: true }).waitFor();
    await recent.getByRole('button', { name: 'Recent options' }).press('ArrowDown');
    await page.getByRole('menuitem', { name: 'Clear recent history' }).waitFor();
    assert(await page.getByRole('menuitem', { name: 'Clear recent history' }).evaluate(el => document.activeElement === el));
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('menu').count(), 0);
    await recent.getByRole('button', { name: 'Recent options' }).click();
    await page.locator('.conversation-title-row h1').click();
    assert.equal(await page.getByRole('menu').count(), 0);
    await recent.getByRole('button', { name: 'Recent options' }).click();
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('menuitem', { name: 'Clear recent history' }).click();
    assert.equal(await recent.locator('li').count(), 2);
    await recent.getByRole('button', { name: 'Recent options' }).click();
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('menuitem', { name: 'Clear recent history' }).click();
    await recent.getByText('No recent conversations.').waitFor();
    assert.equal(rows.length, 3); assert.equal(messages.size, 3); assert.equal(rows.filter(row => row.pinned).length, 1);
    await page.reload({ waitUntil: 'networkidle' });
    await recent.getByText('No recent conversations.').waitFor();
    await sidebar.locator('.curriculum-navigation').getByRole('button', { name: /^Falling objects/ }).click();
    await recent.getByRole('button', { name: 'Falling objects (study)' }).waitFor();
    await page.locator('.conversation-title-row').getByRole('button', { name: 'Pin conversation', exact: true }).click();
    await pinned.getByRole('button', { name: 'Falling objects (study)' }).waitFor();
    await pinned.getByRole('button', { name: 'Pinned options' }).click();
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('menuitem', { name: 'Unpin all', exact: true }).click();
    await pinned.getByText('No pinned conversations yet.').waitFor();
    assert.equal(rows.length, 3); assert.equal(messages.size, 3);
    await page.locator('.conversation-title-row').getByRole('button', { name: 'Pin conversation', exact: true }).waitFor();
    await page.reload({ waitUntil: 'networkidle' });
    await recent.getByRole('button', { name: 'Why is the sky blue? (curiosity)' }).waitFor();
    await recent.getByRole('button', { name: 'Why is the sky blue? (curiosity)' }).click();
    await page.locator('.conversation-title-row').getByRole('button', { name: 'Pin conversation', exact: true }).click();
    await pinned.getByRole('button', { name: 'Why is the sky blue? (curiosity)' }).waitFor();
    await page.setViewportSize({ width: 820, height: 700 });
    await page.locator('.sidebar-rail').getByRole('button', { name: 'My Learning', exact: true }).click();
    const drawer = page.locator('.drawer-navigation');
    await drawer.locator('.shortcut-section').first().getByRole('button', { name: 'Pinned options' }).click();
    const box = await page.getByRole('menu').boundingBox();
    assert(box.x >= 0 && box.x + box.width <= 820, 'Menu outside viewport');
    await page.keyboard.press('Escape');
    assert(await drawer.locator('.shortcut-section').evaluateAll(elements => elements.every(el => el.scrollWidth <= el.clientWidth)), 'Sidebar content overflowed');
    const artifact = path.resolve(cwd, '../../../work/sidebar-conversations-narrow.png');
    fs.mkdirSync(path.dirname(artifact), { recursive: true });
    await page.screenshot({ path: artifact });
    assert.deepEqual(errors, []);
    console.log('PASS: section order, collapse persistence, title/sidebar pin sync, clear preservation, unpin all, reload persistence, My Learning restoration, keyboard menus, and narrow layout');
  } finally { await browser?.close(); server.kill(); mock.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
