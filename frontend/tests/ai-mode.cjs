// 在独立浏览器世界验证真实开关、刷新、设置同步及合并后的 Qwen 承诺；不读取或覆盖用户存档。
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({ channel: 'msedge', headless: true });
 try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, reducedMotion: 'reduce' });
  page.setDefaultTimeout(45000);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.route('https://fonts.googleapis.com/**', route => route.abort());
  const ready = () => page.waitForFunction(() => document.querySelector('.game-shell')?.getAttribute('aria-busy') === 'false' && !!document.querySelector('.suggestion-panel'));
  const state = () => page.evaluate(async () => (await fetch('/api/worlds/' + sessionStorage.getItem('town-world-id'))).json());
  await page.goto(process.env.TOWN_BASE_URL || 'http://127.0.0.1:5174'); await ready();
  const toggle = page.getByRole('switch', { name: 'AI模式' });
  assert.equal(await toggle.getAttribute('aria-checked'), 'false');
  const before = await state();
  await toggle.click(); await ready();
  assert.equal(await toggle.getAttribute('aria-checked'), 'true');
  const enabled = await state();
  assert.equal(enabled.ai.enabled, true);
  assert.equal(enabled.ai.last_decision, null);
  assert.deepEqual(enabled.npcs, before.npcs);
  assert.equal(enabled.turn, before.turn);
  await page.reload(); await ready();
  assert.equal(await toggle.getAttribute('aria-checked'), 'true');
  await page.getByRole('button', { name: '打开设置', exact: true }).click();
  assert.match(await page.locator('.settings-content').textContent(), /运行模式 · AI 驱动模式/);
  assert.doesNotMatch(await page.locator('.settings-content').textContent(), /尚未连接真实 AI/);
  await page.getByRole('button', { name: '关闭弹窗', exact: true }).click();
  await toggle.click(); await ready();
  assert.equal((await state()).ai.enabled, false);
  await toggle.click(); await ready();
  await page.getByRole('button', { name: '观察林间长椅', exact: true }).click(); await ready();
  for (const id of ['stead', 'calm']) {
   await page.locator(`.npc-card[data-npc="${id}"]`).click();
   await page.getByLabel('建议活动', { exact: true }).selectOption('chat');
   await page.getByLabel('建议地点', { exact: true }).selectOption('forest');
   await page.getByRole('button', { name: '提出建议', exact: true }).click(); await ready();
  }
  await page.locator('.advance-button').click(); await ready();
  let result = await state();
  if (!result.ai.last_decision) {
   await page.locator('.npc-card[data-npc="stead"]').click();
   assert.match(await page.locator('.intention-panel').textContent(), /待 AI 判断/);
   await page.locator('.advance-button').click(); await ready();
   result = await state();
  }
  assert.equal(result.ai.last_decision.source, 'ai', JSON.stringify(result.ai.last_decision));
  assert.match(await page.locator('.ai-panel').textContent(), /真实 AI 调用成功/);
  console.log('Live Qwen merged decision:', result.ai.last_decision.choice, result.ai.last_decision.reason);
  if (process.env.TOWN_SCREENSHOT) await page.screenshot({ path: process.env.TOWN_SCREENSHOT, fullPage: true });
  // 关闭不会伪装或抹掉已发生的 AI 判断，也不会重复执行它。
  await toggle.click(); await ready();
  assert.deepEqual((await state()).ai.last_decision, result.ai.last_decision);
  assert.deepEqual(errors, []);
  console.log('AI mode UI passed: real backend toggle, unchanged game state, reload, settings and live Qwen merged result.');
 } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
