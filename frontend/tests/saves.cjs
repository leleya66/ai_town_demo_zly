// 验证存档、恢复和重新开始；测试不向用户现有世界提交操作。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1672,height:1150},reducedMotion:'reduce'});
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5175');await ready();
  assert.match(await page.locator('.world-clock').textContent(),/第 0 回合/);
  await page.locator('.advance-button').click();await ready();
  await page.getByRole('button',{name:'存档',exact:true}).click();await ready();
  assert.match(await page.locator('.toast').textContent(),/已存档/);
  await page.getByRole('button',{name:'打开设置',exact:true}).click();
  await page.getByRole('button',{name:'重新开始',exact:true}).click();await ready();
  assert.equal(await page.locator('dialog').isVisible(),false);
  assert.match(await page.locator('.world-clock').textContent(),/第 0 回合/);
  assert.match(await page.locator('.world-clock').textContent(),/4月12日/);
  await page.locator('.statusbar').getByRole('button',{name:'加载',exact:true}).click();await ready();
  assert.match(await page.locator('.world-clock').textContent(),/第 1 回合/);
  await page.getByRole('button',{name:'打开设置',exact:true}).click();
  await page.getByRole('button',{name:'存档列表',exact:true}).click();
  await page.getByRole('button',{name:'加载此存档'}).first().waitFor();
  const clock = await page.locator('.world-clock').textContent();
  await page.locator('.save-entry').first().getByRole('button',{name:'删除存档',exact:true}).click();
  await page.getByRole('button',{name:'取消',exact:true}).click();
  assert.equal(await page.getByRole('button',{name:'确认删除',exact:true}).count(),0);
  await page.locator('.save-entry').first().getByRole('button',{name:'删除存档',exact:true}).click();
  const before = await page.locator('.save-entry').count();
  await page.getByRole('button',{name:'确认删除',exact:true}).click();
  await page.waitForFunction(count=>document.querySelectorAll('.save-entry').length===count,before-1);
  assert.equal(await page.locator('.world-clock').textContent(),clock);
  // 填满独立测试库，验证满额按钮和删除后再次保存；不使用用户数据库运行此用例。
  for(let i=before-1;i<10;i++){
   await page.getByRole('button',{name:'存档当前进度',exact:true}).click();await ready();
   await page.waitForFunction(count=>document.querySelectorAll('.save-entry').length===count,i+1);
  }
  assert.equal(await page.getByRole('button',{name:'存档当前进度',exact:true}).isDisabled(),true);
  assert.match(await page.locator('.save-list').textContent(),/已使用 10 \/ 10/);
  await page.locator('.save-entry').first().getByRole('button',{name:'删除存档',exact:true}).click();
  await page.getByRole('button',{name:'确认删除',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.save-entry').length===9);
  await page.getByRole('button',{name:'存档当前进度',exact:true}).click();await ready();
  await page.waitForFunction(()=>document.querySelectorAll('.save-entry').length===10);
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  for(const width of [1672,1280,390]){await page.setViewportSize({width,height:1150});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
  console.log('Save UI passed: turn zero, one-click reset, durable save, restore, delete/cancel, 10-slot limit and responsive layouts.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
