// 验证方向动作帧和交流表情；测试不向用户现有世界提交操作。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1672,height:1150}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
  // 使用本地备用字体，让交互测试不依赖外部字体服务。
 await page.route('https://fonts.googleapis.com/**', route=>route.abort());
 await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5174');await ready();
  assert.equal(await page.locator('[data-emotion-npc]').count(),0);
  await page.getByRole('button',{name:'最近的见闻',exact:true}).click();await ready();
  assert.equal(await page.locator('[data-emotion-npc="joe"]').getAttribute('data-emotion'),'happy');
  await page.getByRole('tab',{name:'居民生活',exact:true}).click();
  assert.equal(await page.locator('[data-emotion-npc="joe"]').count(),1);
  await page.waitForFunction(()=>!document.querySelector('[data-emotion-npc]'),{},{timeout:7000});
  for(const id of ['joe','wise','calm','stead']) {
   const alpha=await page.evaluate(async(id)=>{const img=new Image();img.src=`/assets/npc-${id}-walk.png`;await img.decode();const c=document.createElement('canvas');c.width=img.width;c.height=img.height;const ctx=c.getContext('2d');ctx.drawImage(img,0,0);const data=ctx.getImageData(0,0,c.width,c.height).data;let clear=0,solid=0;for(let i=3;i<data.length;i+=4){if(data[i]===0)clear++;if(data[i]>200)solid++;}return {clear,solid,width:c.width,height:c.height};},id);
   assert.deepEqual([alpha.width,alpha.height],[1024,1536]);assert.ok(alpha.clear>10000 && alpha.solid>10000);
  }
  await page.locator('.npc-card[data-npc="wise"]').click();
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.equal(await page.locator('[data-emotion-npc="wise"]').getAttribute('data-emotion'),'pleased');
  await page.locator('.advance-button').click();
  await page.waitForFunction(()=>document.querySelector('[data-life-npc="wise"]')?.getAttribute('data-moving')==='true');
  const frames=await page.evaluate(async()=>{
   const samples=[];for(let i=0;i<42;i++){const n=document.querySelector('[data-life-npc="wise"]');samples.push({direction:n.dataset.direction,pose:n.dataset.pose,view:n.querySelector('.resident-sprite').getAttribute('viewBox'),moving:n.dataset.moving});await new Promise(r=>setTimeout(r,80));}return samples;
  });
  assert.ok(new Set(frames.filter(f=>f.moving==='true').map(f=>f.pose)).size===3);
  assert.ok(new Set(frames.map(f=>f.view)).size>=3);
  assert.ok(frames.some(f=>f.direction==='down'));
  await ready();assert.equal(await page.locator('[data-life-npc="wise"]').getAttribute('data-pose'),'0');
  await page.getByLabel('建议活动',{exact:true}).selectOption('work');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  assert.equal(await page.locator('[data-emotion-npc="wise"]').getAttribute('data-emotion'),'hesitant');
  if(process.env.TOWN_SCREENSHOT)await page.screenshot({path:process.env.TOWN_SCREENSHOT,fullPage:true});
  await page.reload();await ready();assert.equal(await page.locator('[data-emotion-npc]').count(),0);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('.advance-button').click();await ready();
  await page.locator('.npc-card[data-npc="stead"]').click();
  await page.getByLabel('建议活动',{exact:true}).selectOption('chat');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.locator('.npc-card[data-npc="joe"]').click();
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.locator('.advance-button').click();await ready();
  await page.getByRole('tab',{name:'居民生活',exact:true}).click();
  assert.equal(await page.locator('[data-source="npc"]').count(),2);
  assert.equal(await page.locator('[data-emotion-npc="stead"]').getAttribute('data-emotion'),'happy');
  assert.deepEqual(errors,[]);
  console.log('Expressions and sprite frames passed: transparent atlases, real pose changes, player reactions, expiry, reload, mutual NPC chat and reduced motion.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
