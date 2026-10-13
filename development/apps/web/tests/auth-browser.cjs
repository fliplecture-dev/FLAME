const path = require('node:path');
const assert = require('node:assert/strict');
const toolRoot = process.env.FLAME_UI_TOOLS || path.resolve(__dirname, '../../../../.kilo/ui-check/node_modules');
const { chromium } = require(path.join(toolRoot, 'playwright'));
const AxeBuilder = require(path.join(toolRoot, '@axe-core/playwright')).default;

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const base = process.env.FLAME_UI_URL || 'http://localhost:3000';
    for (const [route, heading] of [
      ['/sign-in', 'Sign in'],
      ['/sign-up', 'Create your account'],
      ['/recover', 'Reset your password'],
      ['/admin/sign-in', 'Admin sign in'],
      ['/auth/callback', 'Confirm your email'],
    ]) {
      await page.goto(base + route, { waitUntil: 'networkidle' });
      assert.equal(await page.getByRole('heading', { level: 1 }).textContent(), heading);
      if (route === '/sign-in') assert.equal(await page.getByRole('link', { name: 'Admin sign in' }).getAttribute('href'), '/admin/sign-in');
      if (route === '/admin/sign-in') assert.equal(await page.getByRole('link', { name: 'Student sign in' }).getAttribute('href'), '/sign-in');
      const result = await new AxeBuilder({ page }).exclude('nextjs-portal')
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
      assert.deepEqual(result.violations.map(v => v.id), [], route + ' accessibility violations');
    }
    await page.goto(base, { waitUntil: 'networkidle' });
    assert.match(page.url(), /\/sign-in$/);
    await page.goto(base + '/admin', { waitUntil: 'networkidle' });
    assert.match(page.url(), /\/admin\/sign-in$/);
    console.log('B3 account screens: 5 axe audits and 2 unauthenticated redirects passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
