// 在真实页面创建同起点对照，验证语义、四人AI选择、开放日执行；输出可复核录制记录，不改用户存档。
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const report={};
 const base=process.env.TOWN_BASE_URL||'http://127.0.0.1:5174';
 const ready=page=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false' && !!document.querySelector('.suggestion-panel'),null,{timeout:95000});
 const state=page=>page.evaluate(async()=> (await fetch('/api/worlds/'+sessionStorage.getItem('town-world-id'))).json());
 async function open(url){const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});page.setDefaultTimeout(95000);await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.goto(url);await ready(page);return page;}
 async function say(page,npc,text){await page.locator(`.npc-card[data-npc="${npc}"]`).click();await page.getByRole('textbox',{name:'对话内容'}).fill(text);await page.getByRole('button',{name:'发送消息',exact:true}).click();await ready(page);return (await state(page)).npcs.find(n=>n.id===npc).last_dialogue;}
 async function suggest(page,npc,activity,place){await page.locator(`.npc-card[data-npc="${npc}"]`).click();await page.getByLabel('建议活动',{exact:true}).selectOption(activity);await page.getByLabel('建议地点',{exact:true}).selectOption(place);await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready(page);}
 try{
  fs.mkdirSync('test-results',{recursive:true});
  const root=await open(base);
  await root.getByRole('button',{name:'确认支持',exact:true}).click();await ready(root);
  await root.getByRole('button',{name:'创建同起点对照',exact:true}).click();await ready(root);
  const mock=await open(base+await root.getByRole('link',{name:'打开 Mock 对照'}).getAttribute('href'));
  const ai=await open(base+await root.getByRole('link',{name:'打开 AI 对照'}).getAttribute('href'));
  const initialMock=await state(mock),initialAi=await state(ai);
  assert.deepEqual(initialMock.npcs,initialAi.npcs);
  const text='不用去休息，我想请你准备一次读书分享。';
  report.semantic={input:text,mock:await say(mock,'wise',text),ai:await say(ai,'wise',text)};
  assert.equal(report.semantic.ai.source,'ai',JSON.stringify(report.semantic.ai));
  assert.equal((await state(mock)).npcs.find(n=>n.id==='wise').agenda[0].activity,'rest');
  assert.equal((await state(ai)).npcs.find(n=>n.id==='wise').agenda[0].activity,'prepare_talk');
  await mock.locator('.dialogue-feedback').screenshot({path:'test-results/mock-dialogue.png'});
  await ai.locator('.dialogue-feedback').screenshot({path:'test-results/ai-dialogue.png'});
  await ai.locator('.advance-button').click();await ready(ai);
  let w=await state(ai);
  report.first_turn=w.last_decisions;
  // 实际服务允许单人超时降级；必须有真实AI选择，每个降级都留下原因，不能伪装四人全成功。
  report.first_turn_ai_count=w.last_decisions.filter(d=>d.source==='ai').length;
  assert.equal(w.last_decisions.length,4);
  assert.ok(report.first_turn_ai_count>0,JSON.stringify(w.last_decisions));
  assert.ok(w.last_decisions.every(d=>d.source==='ai'||(d.source==='rules'&&d.fallback_reason)));
  assert.equal(w.last_decisions.find(d=>d.npc_id==='wise').source,'ai');
  assert.ok(w.festival.prepared_by.includes('wise'),'Wise should honour preparation request');
  await suggest(ai,'wise','host_talk','library');
  await suggest(ai,'joe','attend_talk','library');
  await ai.locator('.advance-button').click();await ready(ai);
  w=await state(ai);report.sharing={decisions:w.last_decisions,festival:w.festival};
  assert.ok(w.festival.talk_completed,'Actual host and listener should meet');
  assert.ok(w.festival.ledger.some(e=>e.npc_id==='wise'&&e.kind==='talk'&&e.points===4));
  await ai.locator('.festival-panel').screenshot({path:'test-results/ai-contributions.png'});
  // 从真实产生的两个承诺验证指定撤回；已开始的长椅承诺不会被误删。
  const cancellation=await open(base);
  await cancellation.getByRole('button',{name:'观察林间长椅',exact:true}).click();await ready(cancellation);
  await suggest(cancellation,'stead','attend_talk','library');
  await suggest(cancellation,'stead','repair_bench','forest');
  await cancellation.locator('.advance-button').click();await ready(cancellation);
  await cancellation.getByRole('switch',{name:'AI模式'}).click();await ready(cancellation);
  report.cancel=await say(cancellation,'stead','参加读书分享的邀请先取消，修椅子的约定保留。');
  const stead=(await state(cancellation)).npcs.find(n=>n.id==='stead');
  assert.equal(report.cancel.source,'ai');assert.ok(!stead.agenda.some(t=>t.activity==='attend_talk'));assert.ok(stead.agenda.some(t=>t.activity==='repair_bench'));
  // 完整六回合与结局；真实AI允许选择差异，不要求特定冠军。
  for(let i=w.turn;i<6;i++){await ai.locator('.advance-button').click();await ready(ai);}
  await ai.locator('.ending-panel').waitFor();
  report.ending=(await state(ai)).ending;
  assert.ok(report.ending.festival.winners.length);
  await ai.locator('.ending-panel').screenshot({path:'test-results/ai-ending.png'});
  fs.writeFileSync('test-results/live-demo-report.json',JSON.stringify(report,null,2));
  console.log(`Live demo passed: same-state semantic difference, ${report.first_turn_ai_count}/4 real AI choices (other choices explicitly downgraded), sharing contributions, targeted cancellation and six-turn ending.`);
 }catch(error){fs.writeFileSync('test-results/live-demo-report.json',JSON.stringify(report,null,2));throw error;}
 finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
