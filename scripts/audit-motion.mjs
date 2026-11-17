import {chromium} from '@playwright/test';
import {AxeBuilder} from '@axe-core/playwright';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.launch();const reports=[];
try{
 for(const width of [1440,390]){
  const context=await browser.newContext({viewport:{width,height:844}});const page=await context.newPage();
  await page.goto(process.env.AUDIT_URL||'http://localhost:3001/',{waitUntil:'networkidle'});
  for(const progress of [0,.28,.55,.75,.95]){
   await page.evaluate(p=>{const el=document.querySelector('.scroll-journey');scrollTo({top:el.offsetTop+(el.offsetHeight-innerHeight)*p,behavior:'instant'});},progress);
   await page.waitForTimeout(600);
   const report=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
   reports.push({width,progress,violations:report.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
  }
  await context.close();
 }
 await writeFile('docs/motion-accessibility.json',JSON.stringify(reports,null,2));
 console.log(JSON.stringify(reports));process.exitCode=reports.some(r=>r.violations.length)?1:0;
}finally{await browser.close();}
