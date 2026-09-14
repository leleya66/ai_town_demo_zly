// 验证实际页面的邀请入口、角色切换、来源与状态、旧数据空态及响应式布局；受控数据不调用模型或改存档。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const base=process.env.DEMO_URL||'http://127.0.0.1:5174/';
 const errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);
  await page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false'&&document.querySelector('.dashboard-strip'));
  const id=await page.evaluate(()=>sessionStorage.getItem('town-world-id'));
  const response=await page.request.get(new URL('/api/worlds/'+id,base).href);
  assert.equal(response.status(),200);
  const world=await response.json();
  const button=page.getByRole('button',{name:'邀请链路',exact:true});
  await button.click();
  const panel=page.getByRole('region',{name:'邀请与回应'});
  await panel.waitFor();
  assert.match(await panel.innerText(),/暂无邀请/);
  await page.keyboard.press('Escape');
  await page.locator('dialog').waitFor({state:'hidden'});
  // 使用真实新世界结构，替换只读响应以稳定覆盖所有回应状态，不把测试数据写进后端。
  const states=['pending','accepted','deferred','declined','completed','expired','cancelled'];
  world.invitations=states.map((status,k)=>({id:'fixture-'+k,group:'group-'+k,event:'talk',sender:'wise',recipient:k%2?'calm':'joe',place:'library',due_turn:2,expires_turn:4,status,response_source:k%2?'rules':'ai',response_reason:k?'测试回应原因':'',result:status==='completed'?'双方实际到场并完成互动':'尚未完成'}));
  await page.route('**/api/worlds/'+id,r=>r.fulfill({json:world}));
  await page.reload();
  await button.click();
  await panel.getByRole('button',{name:'Wise',exact:true}).click();
  assert.equal(await panel.locator('article').count(),7);
  for(const label of ['待回应','已接受','暂缓','已拒绝','已完成','已过期','已撤回','AI回应','规则回应','有效至第4回合'])assert.ok((await panel.innerText()).includes(label),label);
  await panel.getByRole('button',{name:'Calm',exact:true}).click();
  assert.equal(await panel.locator('article').count(),3);
  await panel.getByRole('button',{name:'Stead',exact:true}).click();
  assert.match(await panel.innerText(),/暂无邀请/);
  await panel.getByRole('button',{name:'Wise',exact:true}).click();
  fs.mkdirSync('test-results',{recursive:true});
  await page.screenshot({path:'test-results/invitations-desktop.png'});
  await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
  await button.click();
  assert.equal(await panel.locator('article').count(),7);
  await page.setViewportSize({width:390,height:844});
  const bounds=await page.locator('dialog').boundingBox();
  assert.ok(bounds&&bounds.x>=0&&bounds.x+bounds.width<=391,'窄屏弹窗不越界');
  await page.screenshot({path:'test-results/invitations-mobile.png'});
  await page.keyboard.press('Escape');
  delete world.invitations;
  await page.reload();await button.click();
  assert.match(await panel.innerText(),/暂无邀请/);
  const unchanged=await (await page.request.get(new URL('/api/worlds/'+id,base).href)).json();
  assert.equal(unchanged.revision,world.revision,'浏览邀请不能修改世界版本');
  assert.deepEqual(errors,[]);
  console.log('邀请页面通过：真实连接、空态、七状态、来源、角色过滤、重开、旧数据兼容、桌面与窄屏。');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
