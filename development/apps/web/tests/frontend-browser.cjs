// Run after npm run dev. Temporary audit tools live outside the app dependencies.
// npm install --prefix E:/FLAME/.kilo/ui-check --no-save playwright @axe-core/playwright
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const toolRoot = process.env.FLAME_UI_TOOLS || path.resolve(__dirname, '../../../../.kilo/ui-check/node_modules');
const { chromium } = require(path.join(toolRoot, 'playwright'));
const AxeBuilder = require(path.join(toolRoot, '@axe-core/playwright')).default;
const artifactDir = path.resolve(__dirname, '../../../../.kilo/ui-check/stage8');
const baseURL = process.env.FLAME_UI_URL || 'http://localhost:3000/';
fs.mkdirSync(artifactDir, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const report = { audits: [], viewports: [], checks: [] };
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    const side = page.locator('.desktop-sidebar');
    const rail = page.locator('.sidebar-rail');
    const drawer = page.locator('.curriculum-drawer');
    const library = page.locator('.library-dialog');
    const confirmation = page.locator('.removal-dialog');
    const input = page.locator('#flame-prompt');
    async function audit(name) {
      const result = await new AxeBuilder({ page }).exclude('nextjs-portal')
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
      const violations = result.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => ({ target: n.target, message: n.failureSummary })) }));
      report.audits.push({ name, violations });
      console.log('Audit:', name, JSON.stringify(violations));
      assert.equal(violations.length, 0, name + ': accessibility violations');
    }
    async function trap(dialog, count = 12) {
      for (let i = 0; i < count; i++) { await page.keyboard.press('Tab'); assert(await dialog.evaluate(el => el.contains(document.activeElement)), 'Focus escaped dialog'); }
    }
    async function openNavigation(width) {
      if (width >= 1100) {
        if (!(await side.isVisible())) await rail.getByRole('button', { name: 'My Learning', exact: true }).click();
        return side;
      }
      await (width >= 768 ? rail.getByRole('button', { name: 'My Learning', exact: true }) : page.getByRole('button', { name: 'Open navigation', exact: true })).click();
      return drawer;
    }
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('.skip-link').evaluate(el => el === document.activeElement), true);
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#learning-workspace').evaluate(el => el === document.activeElement), true);
    await audit('desktop home');
    await side.locator('nav[aria-label="Curriculum"]').getByRole('button', { name: /^Gravity/ }).first().click();
    await page.getByRole('button', { name: 'Pin', exact: true }).click();
    await side.getByRole('button', { name: 'Find a subtopic', exact: true }).click();
    await side.getByRole('searchbox', { name: 'Find a subtopic', exact: true }).fill('no-such-subtopic');
    await side.getByRole('button', { name: 'Clear filters', exact: true }).click();
    await side.getByRole('button', { name: 'Close search', exact: true }).click();
    await audit('selected subtopic and resources');
    await input.fill('Preserve this learning draft.');
    await side.getByRole('button', { name: 'Collapse sidebar', exact: true }).click();
    await audit('desktop icon rail');
    await rail.getByRole('button', { name: 'Curiosity', exact: true }).click();
    await input.fill('A separate curiosity draft.');
    await audit('curiosity');
    await rail.getByRole('button', { name: 'My Learning', exact: true }).click();
    assert.equal(await input.inputValue(), 'Preserve this learning draft.');
    await side.getByRole('button', { name: 'Add from Library', exact: true }).click();
    await audit('library curriculum tab');
    await trap(library);
    await library.getByRole('tab', { name: 'Subject', exact: true }).click();
    await audit('library subject tab');
    await library.getByRole('button', { name: 'Remove Science from My Learning', exact: true }).first().click();
    await audit('removal confirmation above library');
    await trap(confirmation, 6);
    await page.keyboard.press('Escape');
    assert(await library.isVisible());
    await library.getByRole('button', { name: 'Done', exact: true }).click();
    assert(await side.getByRole('button', { name: 'Add from Library', exact: true }).evaluate(el => el === document.activeElement));
    await page.getByRole('button', { name: /See gravity/ }).click();
    await page.waitForFunction(() => document.querySelector('.resource-body img')?.naturalWidth > 0);
    await audit('diagram viewer');
    await page.keyboard.press('Escape');
    // Resize while a viewer is open: navigation must not cover it.
    await page.getByRole('button', { name: /See gravity/ }).click();
    await page.setViewportSize({ width: 768, height: 900 });
    assert.equal(await drawer.isVisible(), false);
    assert(await page.locator('.resource-dialog').isVisible());
    await page.keyboard.press('Escape');
    for (const width of [1920, 1440, 1280, 1100, 1024, 900, 768, 600, 430, 390, 360, 320]) {
      await page.setViewportSize({ width, height: 900 });
      const nav = await openNavigation(width);
      await nav.locator('nav[aria-label="Curriculum"]').getByRole('button', { name: /^Gravity/ }).first().click();
      assert.equal(await drawer.isVisible(), false);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Page overflow at ' + width);
      const rect = await page.locator('.prompt-form').boundingBox();
      assert(rect.x >= 0 && rect.x + rect.width <= width + 1 && rect.y + rect.height <= 901, 'Composer outside viewport at ' + width);
      report.viewports.push({ width, height: 900 });
      if ([1440, 768, 390, 320].includes(width)) await page.screenshot({ path: path.join(artifactDir, 'workspace-' + width + '.png') });
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await audit('mobile subtopic');
    await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await trap(drawer, 25);
    await audit('mobile navigation');
    await drawer.getByRole('button', { name: 'Add from Library', exact: true }).click();
    await audit('mobile library');
    await library.getByRole('button', { name: 'Remove CBSE from My Learning', exact: true }).click();
    await audit('mobile confirmation');
    await page.screenshot({ path: path.join(artifactDir, 'mobile-confirmation.png') });
    await confirmation.getByRole('button', { name: 'Cancel', exact: true }).click();
    await library.getByRole('button', { name: 'Done', exact: true }).click();
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('button', { name: 'Open navigation', exact: true }).evaluate(el => el === document.activeElement), true);
    await input.fill('LongName'.repeat(450));
    await page.getByRole('button', { name: 'Send learning request', exact: true }).click();
    assert(await page.getByRole('button', { name: 'Retry question', exact: true }).isVisible());
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await audit('long request and unavailable state');
    for (const size of [{width:390,height:430},{width:768,height:430},{width:320,height:568}]) {
      await page.setViewportSize(size);
      const rect = await page.locator('.prompt-form').boundingBox();
      assert(rect.y >= 0 && rect.y + rect.height <= size.height + 1, 'Short viewport composer');
      report.viewports.push(size);
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    const nav = await openNavigation(1440);
    for (const name of ['CBSE', 'Tamil Nadu State Board']) {
      await nav.getByRole('button', { name: 'Remove ' + name + ' from My Learning', exact: true }).click();
      await confirmation.getByRole('button', { name: 'Remove', exact: true }).click();
    }
    assert(await nav.getByText('Your learning space is empty.', { exact: true }).isVisible());
    await audit('empty learning');
    await nav.getByRole('button', { name: 'Add from Library', exact: true }).first().click();
    await library.getByRole('button', { name: 'Add CBSE', exact: true }).click();
    await library.getByRole('button', { name: 'Done', exact: true }).click();
    await nav.locator('nav[aria-label="Curriculum"]').getByRole('button', { name: /^Gravity/ }).first().click();
    assert((await nav.locator('.topic-button.selected').innerText()).includes('8 / 10'));
    assert.equal(await input.inputValue(), 'LongName'.repeat(450));
    report.checks.push('skip link', 'search reset', 'pin', 'mode/draft isolation', 'rail', 'nested dialogs and focus', 'resize with viewer', 'long text', 'empty learning', 'restored progress and drafts');
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(artifactDir, 'report.json'), JSON.stringify(report, null, 2));
    console.log('PASS Stage 8 integration:', report.audits.length, 'accessibility audits;', report.viewports.length, 'viewport cases');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
