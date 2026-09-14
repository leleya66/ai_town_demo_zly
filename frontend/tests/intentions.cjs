// 在独立世界验证观察、NPC需求传递、意图待办、两次真实修缮和因果面板，不修改用户存档。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  await page.goto('http://127.0.0.1:5174');await ready();
  await page.getByRole('button',{name:'观察林间长椅',exact:true}).click();await ready();
  for(const id of ['stead','calm']){
   await page.locator(`.npc-card[data-npc="${id}"]`).click();
   await page.getByLabel('建议活动',{exact:true}).selectOption('chat');
   await page.getByLabel('建议地点',{exact:true}).selectOption('forest');
   await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  }
  await page.locator('.advance-button').click();await ready();
  await page.locator('.npc-card[data-npc="stead"]').click();
  assert.match(await page.locator('.intention-panel').textContent(),/AI 承诺判断|规则承诺判断/);
  assert.equal(await page.getByRole('switch',{name:'AI模式'}).getAttribute('aria-checked'),'false');
  console.log('Actual commitment panel:',await page.locator('.intention-panel').textContent());
  assert.match(await page.locator('.intention-panel').textContent(),/已接受/);
  await page.locator('.intention-panel summary').click();
  assert.match(await page.locator('.intention-panel').textContent(),/想恢复这处休息角/);
  await page.locator('.advance-button').click();await ready();
  assert.match(await page.locator('.intention-panel').textContent(),/进度1\/2/);
  await page.reload();await ready();
  await page.locator('.npc-card[data-npc="stead"]').click();
  assert.match(await page.locator('.intention-panel').textContent(),/修缮中/);
  await page.locator('.advance-button').click();await ready();
  assert.match(await page.locator('.intention-panel').textContent(),/已完成/);
  assert.match(await page.locator('.intention-panel').textContent(),/进度2\/2/);
  assert.deepEqual(errors,[]);
  console.log('Intention UI passed: observed knowledge, actual NPC demand, agenda, causal display, progress, reload and completion.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
