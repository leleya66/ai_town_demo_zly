// 验证长椅事件及移动回放；测试不向用户现有世界提交操作。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1672,height:1150}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.bench-event'));
  // 使用本地备用字体，让交互测试不依赖外部字体服务。
 await page.route('https://fonts.googleapis.com/**', route=>route.abort());
 await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5174');await ready();
  const event=page.locator('.bench-event');
  await event.getByRole('button',{name:'观察林间长椅',exact:true}).click();await ready();
  assert.equal(await page.locator('.forest-bench').getAttribute('data-state'),'broken');
  assert.equal(await event.locator('progress').getAttribute('value'),'0');
  await event.getByRole('button',{name:'邀请 Stead 修缮',exact:true}).click();await ready();
  assert.match(await page.locator('.suggestion-reply').textContent(),/已接受/);
  const energy=await page.locator('.npc-card[data-npc="stead"] .metric b').first().textContent();
  await page.locator('.advance-button').click();
  await page.waitForFunction(()=>document.querySelector('[data-life-npc="stead"]')?.getAttribute('data-moving')==='true');
  assert.equal(await page.locator('.advance-button').isDisabled(),true);
  assert.equal(await event.locator('progress').getAttribute('value'),'0','progress waits for playback');
  assert.equal(await page.locator('.npc-card[data-npc="stead"] .metric b').first().textContent(),energy);
  await page.waitForFunction(()=>Math.abs(Number(document.querySelector('[data-life-npc="stead"]')?.getAttribute('data-y'))-270)<1);
  assert.ok(await page.locator('.resident-route').isVisible());
  if(process.env.TOWN_SCREENSHOT)await page.screenshot({path:process.env.TOWN_SCREENSHOT.replace('.png','-moving.png'),fullPage:true});
  await ready();
  assert.equal(await event.locator('progress').getAttribute('value'),'1');
  assert.equal(await page.locator('[data-life-npc="stead"]').getAttribute('data-place'),'forest');
  assert.equal(await page.locator('.forest-bench').getAttribute('data-state'),'repairing');
  await page.locator('.statusbar').getByRole('button',{name:'保存',exact:true}).click();await ready();
  // Force another movement on the completion turn, then reload during playback.
  await page.locator('.npc-card[data-npc="wise"]').click();
  await page.getByLabel('建议活动',{exact:true}).selectOption('rest');
  await page.getByLabel('建议地点',{exact:true}).selectOption('forest');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.locator('.advance-button').click();await page.locator('.replay-banner').waitFor();
  await page.reload();await ready();
  await page.getByRole('tab',{name:'居民生活',exact:true}).click();
  assert.equal(await event.locator('progress').getAttribute('value'),'2');
  assert.equal(await page.locator('.forest-bench').getAttribute('data-state'),'repaired');
  assert.equal(await page.locator('.replay-banner').count(),0);
  await page.locator('.statusbar').getByRole('button',{name:'加载',exact:true}).click();await ready();
  assert.equal(await page.locator('.forest-bench').getAttribute('data-state'),'repairing');
  assert.equal(await event.locator('progress').getAttribute('value'),'1');
  await page.locator('.npc-card[data-npc="wise"]').click();
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.locator('.advance-button').click();await page.locator('.replay-banner').waitFor();
  await page.getByRole('button',{name:'跳过动画',exact:true}).click();await ready();
  assert.equal(await event.locator('progress').getAttribute('value'),'2');
  await page.locator('.npc-card[data-npc="calm"]').click();
  await page.getByLabel('建议活动',{exact:true}).selectOption('sit_bench');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.locator('.advance-button').click();await ready();
  assert.match(await page.locator('.turn-result').textContent(),/长椅休憩/);
  for(const width of [1672,1280,390]){await page.setViewportSize({width,height:1150});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
  await page.setViewportSize({width:1672,height:1150});
  if(process.env.TOWN_SCREENSHOT)await page.screenshot({path:process.env.TOWN_SCREENSHOT,fullPage:true});
  // Reduced-motion skips replay but still settles exactly once.
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('.npc-card[data-npc="wise"]').click();
  await page.getByLabel('建议活动',{exact:true}).selectOption('read');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.locator('.advance-button').click();await ready();
  assert.equal(await page.locator('.replay-banner').count(),0);
  assert.equal(await page.locator('[data-life-npc="wise"]').getAttribute('data-place'),'library');
  assert.deepEqual(errors,[]);console.log('Bench passed: discover, repair, road animation, deferred UI, reload, skip, save/restore, unlock, reduced motion and responsive layouts.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
