// 在独立世界验证 AI 开关与结局评定文案不冲突；只推进回合，不写入或删除存档。
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({ channel: 'msedge', headless: true });
 try {
  for (const enabled of [false, true]) {
   const context = await browser.newContext({ reducedMotion: 'reduce', viewport: { width: 1440, height: 1100 } });
   try {
    const page = await context.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.route('https://fonts.googleapis.com/**', route => route.abort());
    const ready = () => page.waitForFunction(() => document.querySelector('.game-shell')?.getAttribute('aria-busy') === 'false' && !!document.querySelector('.suggestion-panel'));
    await page.goto(process.env.TOWN_BASE_URL || 'http://127.0.0.1:5174'); await ready();
    if (enabled) { await page.getByRole('switch', { name: 'AI模式' }).click(); await ready(); }
    assert.equal(await page.getByRole('switch', { name: 'AI模式' }).getAttribute('aria-checked'), String(enabled));
    for (let turn = 0; turn < 6; turn++) { await page.locator('.advance-button').click(); await ready(); }
    await page.locator('.ending-panel').waitFor();
    const text = await page.locator('.ending-panel').textContent();
    assert.match(text, /结局依据实际状态与事件评定/);
    assert.doesNotMatch(text, /规则模式结局/);
    assert.equal(await page.locator('.ending-panel article').count(), 4);
    assert.deepEqual(errors, []);
   } finally { await context.close(); }
  }
  console.log('Ending mode UI passed: Mock and AI enabled, six turns, factual ending label, no save changes.');
 } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
