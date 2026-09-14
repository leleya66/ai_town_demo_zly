// 验证实际页面的规则交流、双方记忆和后续决策引用；只创建独立测试世界，不操作存档。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  await page.goto('http://127.0.0.1:5174');await ready();
  await page.locator('.advance-button').click();await ready();
  await page.getByRole('button',{name:'查看记忆',exact:true}).click();
  assert.match(await page.locator('.social-memories').textContent(),/普通寒暄/);
  assert.match(await page.locator('.social-memories').textContent(),/calm/);
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  await page.locator('.npc-card[data-npc="calm"]').click();
  await page.getByRole('button',{name:'查看记忆',exact:true}).click();
  assert.match(await page.locator('.social-memories').textContent(),/joe/);
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  for(let i=1;i<4;i++){await page.locator('.advance-button').click();await ready();}
  assert.match(await page.locator('.suggestion-panel').textContent(),/记得第1回合.*普通寒暄/);
  await page.getByRole('button',{name:'查看记忆',exact:true}).click();
  assert.match(await page.locator('.social-memories').textContent(),/分享经历/);
  await page.reload();await ready();
  await page.getByRole('button',{name:'查看记忆',exact:true}).click();
  assert.ok(await page.locator('.social-memories article').count()>0);
  assert.deepEqual(errors,[]);console.log('Conversation UI passed: bilateral memories, real experience, later decision citation and reload.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
