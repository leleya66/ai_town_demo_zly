// 验证真实页面中的待办排序、拒绝保留、跨回合履约与恢复；独立浏览器世界不改用户进度。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5174');await ready();
  await page.getByRole('button',{name:'观察林间长椅',exact:true}).click();await ready();
  await page.getByRole('button',{name:'邀请 Stead 修缮',exact:true}).click();await ready();
  await page.getByLabel('建议活动',{exact:true}).selectOption('chat');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.equal(await page.locator('.agenda-item').count(),2);
  assert.match(await page.locator('.suggestion-reply').textContent(),/先处理修好林间长椅/);
  await page.locator('.advance-button').click();await ready();
  assert.match(await page.locator('.turn-result').textContent(),/修好林间长椅/);
  assert.equal(await page.getByRole('progressbar',{name:'长椅修缮进度'}).getAttribute('value'),'1');
  await page.getByLabel('建议活动',{exact:true}).selectOption('rest');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  // Stead此时精力79，休息可以接受；为验证拒绝不清队，改用Wise修缮。
  await page.locator('.npc-card[data-npc="wise"]').click();
  await page.getByLabel('建议活动',{exact:true}).selectOption('work');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.match(await page.locator('.suggestion-reply').textContent(),/已拒绝/);
  await page.locator('.npc-card[data-npc="stead"]').click();
  assert.equal(await page.locator('.agenda-item').count(),3);
  await page.reload();await ready();
  await page.locator('.npc-card[data-npc="stead"]').click();
  assert.equal(await page.locator('.agenda-item').count(),3);
  await page.locator('.advance-button').click();await ready();
  assert.equal(await page.getByRole('progressbar',{name:'长椅修缮进度'}).getAttribute('value'),'2');
  assert.equal(await page.locator('.agenda-item').count(),2);
  for(const width of [1440,390]){await page.setViewportSize({width,height:1100});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
  assert.deepEqual(errors,[]);
  console.log('Agenda UI passed: queue, priority, started commitment, reload and responsive display.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
