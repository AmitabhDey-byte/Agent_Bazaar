import {chromium} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
await mkdir('docs/video',{recursive:true});
const browser=await chromium.launch();
const context=await browser.newContext({viewport:{width:1440,height:900},recordVideo:{dir:'.local/video',size:{width:1440,height:900}}});
const page=await context.newPage();const video=page.video();
await page.goto('http://localhost:3001/',{waitUntil:'networkidle'});
await page.locator('.journey-enhanced').waitFor();
await page.waitForTimeout(900);
const distance=await page.locator('.scroll-journey').evaluate(el=>el.offsetHeight-innerHeight);
for(let i=0;i<180;i++){await page.mouse.wheel(0,distance/180);await page.waitForTimeout(90);}
await page.waitForTimeout(900);
await page.getByRole('link',{name:'Make your first move'}).click();
await page.waitForTimeout(1200);
await context.close();await video.saveAs('docs/video/agent-bazaar-scroll.webm');await browser.close();
console.log('Recorded docs/video/agent-bazaar-scroll.webm');
