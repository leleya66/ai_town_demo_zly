// 在真实页面验证四条任务、角色限制、广播回应与实际贡献，独立世界不读写个人存档。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const reports=[];
 try{
  for(const ai of [false,true]){
   const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
   page.setDefaultTimeout(125000);
   await page.route('https://fonts.googleapis.com/**',r=>r.abort());
   const ready=()=>page.waitForFunction(()=>document.querySelector('.game-shell')?.getAttribute('aria-busy')==='false'&&!!document.querySelector('.suggestion-panel'),null,{timeout:125000});
   await page.goto(process.env.DEMO_URL || 'http://127.0.0.1:5174/');await ready();
   const state=()=>page.evaluate(async()=> (await fetch('/api/worlds/'+sessionStorage.getItem('town-world-id'))).json());
   assert.equal(await page.locator('.event-task').count(),4);
   await page.locator('.npc-card[data-npc="calm"]').click();
   assert.equal(await page.locator('select[aria-label="建议活动"] option[value="prepare_talk"]').count(),0);
   await page.locator('.npc-card[data-npc="wise"]').click();
   if(ai){await page.getByRole('switch',{name:'AI模式'}).click();await ready();}
   await page.getByLabel('建议活动',{exact:true}).selectOption('prepare_talk');
   await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
   await page.locator('.advance-button').click();await ready();
   let w=await state();assert.ok(w.festival.prepared_by.includes('wise'),'Wise需要实际完成准备');
   await page.getByLabel('建议活动',{exact:true}).selectOption('invite_event');
   await page.getByRole('button',{name:'提出建议',exact:true}).click();await ready();
   await page.locator('.advance-button').click();await ready();
   w=await state();
   assert.equal(w.invitations.filter(i=>i.event==='talk').length,3,'分享广播给其他三人');
   assert.ok(w.invitations.filter(i=>i.event==='talk').every(i=>i.status==='pending'),'刚广播不能强迫接受');
   assert.equal(w.festival.ledger.filter(e=>e.npc_id==='wise').length,0,'邀请本身不计分');
   fs.mkdirSync('test-results',{recursive:true});
   await page.getByRole('button',{name:'邀请链路',exact:true}).click();
   await page.locator('.invitation-panel').screenshot({path:`test-results/${ai?'ai':'mock'}-invitations.png`});
   await page.getByRole('button',{name:'关闭弹窗',exact:true}).click();
   const turns=[];
   while(w.turn<6){await page.locator('.advance-button').click();await ready();w=await state();turns.push(w.last_decisions);}
   const completed=w.invitations.filter(i=>i.event==='talk'&&i.status==='completed');
   assert.ok(completed.length>0,'六回合内应有实际听众，不能只有广播');
   assert.equal(w.festival.ranking.find(r=>r.npc_id==='wise').score,Math.min(6,completed.length*2));
   assert.ok(w.festival.ranking.every(r=>r.score<=6));
   if(ai)assert.ok(turns.flat().some(d=>d.source==='ai'));
   reports.push({ai,festival:w.festival,invitations:w.invitations,turns});
   fs.writeFileSync('test-results/event-routes.json',JSON.stringify(reports,null,2));
   await page.locator('.ending-panel').screenshot({path:`test-results/${ai?'ai':'mock'}-four-events-ending.png`});
   console.log(JSON.stringify({ai,listeners:completed.length,ranking:w.festival.ranking}));
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
