// 验证无干预自主移动、动作帧、双人交流，以及世界评估和终局展示的一致性。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5175');await ready();
  await page.getByRole('tab',{name:'居民生活',exact:true}).click();
  assert.equal(await page.locator('option[value="seek_company"]').count(),0);
  const visited=Object.fromEntries(['joe','wise','calm','stead'].map(id=>[id,new Set()]));
  const record=async()=>{for(const id of Object.keys(visited))visited[id].add(await page.locator(`[data-life-npc="${id}"]`).getAttribute('data-place'));};
  await record();await page.locator('.advance-button').click();
  await page.waitForFunction(()=>document.querySelector('[data-life-npc="calm"]')?.dataset.moving==='true');
  const samples=await page.evaluate(async()=>{
   const values=[];for(let i=0;i<40;i++){const el=document.querySelector('[data-life-npc="calm"]');values.push([el.dataset.direction,el.dataset.pose,el.getAttribute('style')]);await new Promise(r=>setTimeout(r,80));}return values;
  });
  assert.ok(new Set(samples.map(s=>s[1])).size>=2,'自主移动包含迈步动作');
  assert.ok(new Set(samples.map(s=>s[0])).size>=2,'沿路转向');
  await ready();await record();
  assert.equal(await page.locator('[data-source="npc"]').count(),2,'自主匹配成功后双方显示交流表情');
  await page.emulateMedia({reducedMotion:'reduce'});
  for(let i=1;i<6;i++){await page.locator('.advance-button').click();await ready();await record();}
  for(const [id,places] of Object.entries(visited))assert.ok(places.size>=2,`${id} 根据需求前往不同地点`);
  await page.locator('.ending-panel').waitFor();
  const title=await page.locator('.ending-panel > h3').textContent();
  const assessment=await page.locator('.assessment-panel').textContent();
  assert.match(assessment,/实际双人交流3次/);
  assert.ok((await page.locator('.statusbar').textContent()).includes(`本局结局：${title}`));
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  await page.getByRole('button',{name:'世界状态',exact:true}).click();
  assert.equal(await page.locator('.assessment-panel').textContent(),assessment);
  assert.ok((await page.locator('.world-summary').textContent()).includes(`本局结局：${title}`));
  assert.deepEqual(errors,[]);
  console.log('Autonomy UI passed: four residents travel, real turning/steps, three mutual chats, shared final assessment.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
