// 在真实页面验证SSE草稿先于提交出现、最终仅结算一次，以及结果在人物动画结束前显示。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  page.setDefaultTimeout(60000);
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false'&&!!document.querySelector('.suggestion-panel'));
  await page.goto('http://127.0.0.1:5174/');await ready();
  await page.getByRole('switch',{name:'AI模式'}).click();await ready();
  assert.match(await page.locator('.ai-panel').textContent(),/qwen3.8-flash.*非思考模式/);
  await page.locator('.npc-card[data-npc="wise"]').click();
  await page.evaluate(()=>{
   window.streamSamples=[];
   window.streamObserver=new MutationObserver(()=>{
    const text=document.querySelector('.stream-draft')?.textContent;
    if(text)window.streamSamples.push({text,final:document.querySelector('.dialogue-feedback')?.textContent||'',at:performance.now()});
   });
   window.streamObserver.observe(document.body,{subtree:true,childList:true,characterData:true});
  });
  await page.getByRole('textbox',{name:'对话内容'}).fill('不用去休息，我想请你准备一次读书分享。');
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/commands/stream'));
  const started=Date.now();
  await page.getByRole('button',{name:'发送消息',exact:true}).click();
  const response=await responsePromise;assert.match(response.headers()['content-type'],/text\/event-stream/);
  await page.locator('.stream-draft').waitFor({state:'visible'});
  fs.mkdirSync('test-results',{recursive:true});
  await page.screenshot({path:'test-results/qwen-streaming.png'});
  await ready();
  const dialogueSeconds=(Date.now()-started)/1000;
  const samples=await page.evaluate(()=>{window.streamObserver.disconnect();return window.streamSamples;});
  assert.ok(new Set(samples.map(s=>s.text)).size>1,'必须收到多次文本增长，不能只有最终整段');
  assert.ok(samples.some(s=>!s.final),'草稿必须出现在最终对话反馈之前');
  const state=()=>page.evaluate(async()=> (await fetch('/api/worlds/'+sessionStorage.getItem('town-world-id'))).json());
  let w=await state();
  const wise=w.npcs.find(n=>n.id==='wise');
  assert.equal(wise.last_dialogue.source,'ai');assert.equal(w.interventions_remaining,1);
  assert.equal(wise.agenda.filter(t=>t.activity==='prepare_talk').length,1);
  await page.locator('.advance-button').click();await ready();
  w=await state();assert.equal(w.last_decisions.length,4);
  fs.writeFileSync('test-results/qwen-browser-decisions.json',JSON.stringify(w.last_decisions,null,2));
  // 用明确的休息待办触发从图书馆到林间的移动，检验结果已显示而动画尚在播放。
  await page.getByLabel('建议活动',{exact:true}).selectOption('rest');
  await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
  await page.getByRole('switch',{name:'AI模式'}).click();await ready();
  await page.locator('.advance-button').click();
  await page.waitForFunction(()=>document.querySelector('[data-life-npc="wise"]')?.getAttribute('data-moving')==='true');
  assert.match(await page.locator('.turn-result').textContent(),/上一回合结果 · 休息/);
  await ready();
  console.log(JSON.stringify({passed:true,dialogueSeconds,draftVersions:new Set(samples.map(s=>s.text)).size,aiChoices:w.last_decisions.filter(d=>d.source==='ai').length}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
