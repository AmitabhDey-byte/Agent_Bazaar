import {chromium} from "@playwright/test";
import {AxeBuilder} from "@axe-core/playwright";
import {writeFile} from "node:fs/promises";
const browser=await chromium.launch({headless:true});
const reports=[];
try{
 for(const width of [1440,390]){
  const context=await browser.newContext({viewport:{width,height:900}});
  const page=await context.newPage();
  await page.goto(process.env.AUDIT_URL || "http://localhost:3001/",{waitUntil:"networkidle"});
  await page.locator(".agent-node").first().waitFor({state:"visible"});
  const result=await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21aa","wcag21a"]).analyze();
  reports.push({width,violations:result.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
  console.log(JSON.stringify(reports.at(-1)));
  await context.close();
 }
 await writeFile("docs/accessibility.json",JSON.stringify(reports,null,2));
 process.exitCode=reports.some(r=>r.violations.length)?1:0;
}finally{await browser.close();}
