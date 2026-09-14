// 验证页面基本交互与响应布局；测试不向用户现有世界提交操作。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
 const page=await browser.newPage({viewport:{width:1672,height:1050}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 // 使用本地备用字体，让交互测试不依赖外部字体服务。
 await page.route('https://fonts.googleapis.com/**', route=>route.abort());
 await page.goto(process.env.TOWN_BASE_URL||'http://127.0.0.1:5173');await page.getByRole('heading',{name:'AI 智能体小镇',exact:true}).waitFor();await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'));
 assert.equal(await page.locator('.npc-card').count(),4);
 const settle=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false');
 assert.equal(await page.getByRole('switch',{name:'AI模式'}).getAttribute('aria-checked'),'false');assert.match(await page.locator('.ai-control').textContent(),/Mock/);
 await page.getByRole('tab',{name:'居民生活',exact:true}).click();assert.equal(await page.locator('.life-place-label').count(),4);assert.equal(await page.locator('.life-resident').count(),4);
 const mapSize=await page.locator('.life-map-art').evaluate(async node=>{const art=new Image();art.src=node.getAttribute('href');await art.decode();return {width:art.naturalWidth,height:art.naturalHeight};});
 assert.ok(mapSize.width>=1200,'life map must load its high-resolution artwork');assert.ok(Math.abs(mapSize.width/mapSize.height-4/3)<0.01,'life map matches overlay coordinates');
 const sprites=page.locator('.resident-sprite');assert.equal(await sprites.count(),4);
 assert.equal(new Set(await sprites.evaluateAll(nodes=>nodes.map(n=>n.querySelector('image').getAttribute('href')))).size,4,'each resident has an individual directional atlas');
 const alpha=await page.evaluate(async()=>{const img=new Image();img.src='/assets/resident-sprites.png';await img.decode();const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);const pixels=ctx.getImageData(0,0,img.width,img.height).data;let clear=0,solid=0;for(let i=3;i<pixels.length;i+=4){if(pixels[i]===0)clear++;if(pixels[i]>200)solid++;}return {clear,solid};});assert.ok(alpha.clear>10000&&alpha.solid>10000,'sprite atlas contains transparent margins and visible figures');
 for(const id of ['joe','wise','calm','stead']){await page.locator(`[data-life-npc="${id}"] button`).click();assert.equal(await page.locator(`[data-npc="${id}"]`).getAttribute('aria-pressed'),'true');}
 for(const label of await page.locator('.life-place-label').all()){assert.ok(await label.isVisible());await label.click();assert.equal(await label.getAttribute('aria-pressed'),'true');}
 await page.locator('[data-life-npc="wise"] button').click();assert.equal(await page.locator('[data-npc="wise"]').getAttribute('aria-pressed'),'true');assert.match(await page.locator('.chat-panel h2').textContent(),/Wise/);
 await page.getByRole('tab',{name:'小镇全景',exact:true}).click();assert.equal(await page.locator('[data-npc="wise"]').getAttribute('aria-pressed'),'true');
 for(const image of await page.locator('img').evaluateAll(nodes=>nodes.map(n=>({loaded:n.complete&&n.naturalWidth>0,src:n.src}))))assert.ok(image.loaded,image.src);
 await page.getByRole('button',{name:'查看图书馆',exact:true}).click();assert.match(await page.locator('.scene-copy h2').textContent(),/图书馆/);
 for(const width of [1672,1024,390]){await page.setViewportSize({width,height:1050});assert.equal(await page.locator('.scene-image.library').evaluate(n=>getComputedStyle(n).backgroundSize),'420% auto','library keeps its focused crop at every layout');}
 await page.setViewportSize({width:1672,height:1050});
 if(process.env.TOWN_SCREENSHOT)await page.locator('.scene-panel').screenshot({path:process.env.TOWN_SCREENSHOT.replace('.png','-library.png')});
 for(const [name,id,size] of [['林间','forest','440% auto'],['中心广场','plaza','380% auto']]){
  await page.getByRole('button',{name:`查看${name}`,exact:true}).click();
  for(const width of [1672,1024,390]){await page.setViewportSize({width,height:1050});assert.equal(await page.locator(`.scene-image.${id}`).evaluate(n=>getComputedStyle(n).backgroundSize),size,`${id} keeps focused crop at ${width}`);}
  await page.setViewportSize({width:1672,height:1050});
  if(process.env.TOWN_SCREENSHOT)await page.locator('.scene-panel').screenshot({path:process.env.TOWN_SCREENSHOT.replace('.png',`-${id}.png`)});
 }
 await page.locator('.npc-card[data-npc="wise"]').click();await page.getByRole('textbox',{name:'对话内容'}).fill('累了，去休息吧');await page.getByRole('button',{name:'发送消息',exact:true}).click();await settle();
 assert.match(await page.locator('.chat-messages').textContent(),/下一回合/);assert.equal(await page.locator('.event-task').count(),4);
 await page.locator('.advance-button').click();await settle();assert.match(await page.locator('.npc-card[data-npc="wise"] .npc-location').textContent(),/林间/);
 await page.getByRole('tab',{name:'居民生活',exact:true}).click();assert.equal(await page.locator('[data-life-npc="wise"]').getAttribute('data-place'),'forest');await page.getByRole('tab',{name:'小镇全景',exact:true}).click();
 await page.locator('.statusbar').getByRole('button',{name:'保存',exact:true}).click();await settle();await page.reload();await page.locator('.statusbar').getByRole('button',{name:'加载',exact:true}).click();await settle();assert.match(await page.locator('.world-clock').textContent(),/第 1 回合/);
 await page.locator('.npc-card[data-npc="wise"]').click();assert.match(await page.locator('.chat-messages').textContent(),/下一回合/);
 await page.getByRole('button',{name:'放大地图',exact:true}).click();assert.match(await page.locator('.map-world').getAttribute('style'),/scale\(1.2\)/);
 await page.getByRole('button',{name:'重置地图视角',exact:true}).click();
 await page.getByRole('button',{name:'打开设置',exact:true}).click();assert.ok(await page.locator('dialog').isVisible());await page.keyboard.press('Escape');assert.ok(!await page.locator('dialog').isVisible());
 await page.getByRole('textbox',{name:'对话内容'}).fill('<img src=x onerror=alert(1)>');await page.getByRole('button',{name:'发送消息',exact:true}).click();await settle();assert.ok(await page.locator('.chat-message p').filter({hasText:'<img src=x'}).count());
 for(const width of [1920,1672,1440,1280,1024,390]){await page.setViewportSize({width,height:1100});const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false,`horizontal overflow at ${width}`);}
 await page.setViewportSize({width:1672,height:1050});
 await page.evaluate(()=>sessionStorage.removeItem('town-world-id'));await page.reload();await page.evaluate(()=>document.fonts.ready);await settle();
 if(process.env.TOWN_SCREENSHOT)await page.screenshot({path:process.env.TOWN_SCREENSHOT,fullPage:true});
 await page.getByRole('tab',{name:'居民生活',exact:true}).click();
 for(const width of [1672,1280,1024,390]){await page.setViewportSize({width,height:1100});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`life map overflow ${width}`);}
 await page.setViewportSize({width:1672,height:1050});
 if(process.env.TOWN_SCREENSHOT)await page.screenshot({path:process.env.TOWN_SCREENSHOT.replace('.png','-life.png'),fullPage:true});
 assert.deepEqual(errors,[]);console.log('Browser passed: 6 viewport widths, images, scene selection, chat, tasks, turns, persistence, zoom, dialogs and safe text rendering.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
