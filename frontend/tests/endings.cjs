// 在独立测试库验证六回合、最后一轮动画、事件去重、结局恢复及存档失败不重开。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5175');await ready();
  await page.locator('.advance-button').click();await ready();

  await page.locator('.advance-button').click();await ready();
  assert.equal(await page.locator('.event-list .event').filter({hasText:/第2回合.*Stead/}).count(),0,'Stead 重复修缮不刷新最近事件');
  for(let i=2;i<5;i++){await page.locator('.advance-button').click();await ready();}
  await page.locator('.npc-card[data-npc="wise"]').click();
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.locator('.advance-button').click();await page.locator('.replay-banner').waitFor();
  assert.equal(await page.locator('.ending-panel').count(),0,'移动尚未结束时不提前展示结局');
  await ready();await page.locator('.ending-panel').waitFor();
  assert.equal(await page.locator('.ending-panel article').count(),4);
  assert.match(await page.locator('.ending-panel').textContent(),/游戏结束/);
  const finalText=await page.locator('.ending-panel').textContent();
  await page.reload();await ready();await page.locator('.ending-panel').waitFor();
  assert.equal(await page.locator('.ending-panel').textContent(),finalText);
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  assert.equal(await page.locator('.advance-button').isDisabled(),true);
  await page.getByRole('button',{name:'打开设置',exact:true}).click();
  await page.getByRole('button',{name:'存档列表',exact:true}).click();
  await page.locator('.save-list').waitFor();
  await page.waitForFunction(()=>!document.querySelector('.save-list [role=status]'));
  const count=await page.locator('.save-entry').count();
  for(let i=count;i<10;i++){
   await page.getByRole('button',{name:'存档当前进度',exact:true}).click();await ready();
   await page.waitForFunction(n=>document.querySelectorAll('.save-entry').length===n,i+1);
  }
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  await page.getByRole('button',{name:'查看结局',exact:true}).click();
  await page.getByRole('button',{name:'存档并重新开始',exact:true}).click();await ready();
  assert.match(await page.locator('.ending-panel [role=alert]').textContent(),/结局已保留/);
  assert.match(await page.locator('.world-clock').textContent(),/第 6 回合/);
  await page.getByRole('button',{name:'管理存档',exact:true}).click();
  await page.locator('.save-entry').first().getByRole('button',{name:'删除存档',exact:true}).click();
  await page.getByRole('button',{name:'确认删除',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.save-entry').length===9);
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  await page.getByRole('button',{name:'查看结局',exact:true}).click();
  for(const width of [1440,390]){await page.setViewportSize({width,height:1100});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
  await page.getByRole('button',{name:'存档并重新开始',exact:true}).click();await ready();
  assert.match(await page.locator('.world-clock').textContent(),/第 0 回合/);
  assert.equal(await page.locator('.ending-panel').count(),0);
  await page.getByRole('button',{name:'打开设置',exact:true}).click();
  await page.getByRole('button',{name:'存档列表',exact:true}).click();
  await page.getByRole('button',{name:'加载此存档',exact:true}).first().click();await ready();
  await page.locator('.ending-panel').waitFor();
  assert.equal(await page.locator('.ending-panel').textContent(),finalText);
  assert.deepEqual(errors,[]);
  console.log('Ending UI passed: deduped events, six turns, final animation, reload, full-save failure, save/restart, restore and narrow layout.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
