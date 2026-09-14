// 验证活动建议及执行结果；测试不向用户现有世界提交操作。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1672,height:1150}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  // 使用本地备用字体，让交互测试不依赖外部字体服务。
 await page.route('https://fonts.googleapis.com/**', route=>route.abort());
 await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5174');await ready();
  await page.getByRole('tab',{name:'居民生活',exact:true}).click();
  await page.locator('.npc-card[data-npc="wise"]').click();
  const initialEnergy=await page.locator('.npc-card[data-npc="wise"] .metric b').first().textContent();
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.match(await page.locator('.suggestion-reply').textContent(),/已接受/);
  assert.match(await page.locator('.pending-suggestion').textContent(),/当前仍在图书馆/);
  assert.equal(await page.locator('.npc-card[data-npc="wise"] .metric b').first().textContent(),initialEnergy);
  await page.locator('.advance-button').click();await ready();
  assert.equal(await page.locator('[data-life-npc="wise"]').getAttribute('data-place'),'forest');
  assert.match(await page.locator('.turn-result').textContent(),/图书馆 → 林间.*精力 \+12/);
  assert.match(await page.locator('.turn-result').textContent(),/第0回合.*林间.*休息/);
  assert.match(await page.locator('.turn-result').textContent(),new RegExp(`${initialEnergy}/100`));
  assert.equal(await page.locator('.pending-suggestion').count(),0);
  await page.getByLabel('建议活动',{exact:true}).selectOption('work');
  assert.equal(await page.getByLabel('建议地点',{exact:true}).inputValue(),'workshop');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.match(await page.locator('.suggestion-reply').textContent(),/已拒绝.*修缮不是/);
  await page.getByLabel('建议活动',{exact:true}).selectOption('read');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.match(await page.locator('.suggestion-reply').textContent(),/已接受/);
  assert.equal(await page.getByRole('button',{name:'提出建议',exact:true}).isDisabled(),false);
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.match(await page.locator('.suggestion-reply').textContent(),/不重复添加/);
  await page.getByLabel('建议活动',{exact:true}).selectOption('work');
  assert.equal(await page.getByRole('button',{name:'提出建议',exact:true}).isDisabled(),true);
  await page.locator('.advance-button').click();await ready();
  assert.match(await page.locator('.turn-result').textContent(),/阅读/);
  assert.equal(await page.locator('[data-life-npc="wise"]').getAttribute('data-place'),'library');
  await page.locator('.npc-card[data-npc="stead"]').click();
  await page.getByLabel('建议活动',{exact:true}).selectOption('chat');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.match(await page.locator('.suggestion-reply').textContent(),/已接受/);
  await page.locator('.npc-card[data-npc="joe"]').click();
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.locator('.advance-button').click();await ready();
  assert.match(await page.locator('.turn-result').textContent(),/闲聊/);
  await page.locator('.npc-card[data-npc="stead"]').click();
  assert.match(await page.locator('.turn-result').textContent(),/工坊 → 中心广场/);
  for(const width of [1672,1280,390]){await page.setViewportSize({width,height:1150});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
  await page.setViewportSize({width:1672,height:1150});
  if(process.env.TOWN_SCREENSHOT)await page.screenshot({path:process.env.TOWN_SCREENSHOT,fullPage:true});
  assert.deepEqual(errors,[]);console.log('Suggestions passed: delayed execution, refusal reason, read, mutual chat, quota and responsive UI.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
