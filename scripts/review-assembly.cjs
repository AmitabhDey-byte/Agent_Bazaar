async(page)=>{
 const results=[];
 for(const width of [1440,1024,768,390,320]){
  await page.setViewportSize({width,height:width>760?1000:844});
  await page.goto('http://localhost:3001/',{waitUntil:'networkidle'});
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('.assembly-desk').scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>document.querySelector('.assembly-registry')?.getAttribute('aria-busy')==='false');
  await page.locator('.assembly-desk img').evaluateAll(images=>Promise.all(images.map(image=>image.decode())));
  await page.locator('.assembly-desk').screenshot({path:`D:/MVP/docs/screenshots/assembly-${width}.png`,style:'.site-header{visibility:hidden!important}'});
  results.push({width,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),registryState:await page.locator('.assembly-registry').innerText()});
 }
 return results;
}
