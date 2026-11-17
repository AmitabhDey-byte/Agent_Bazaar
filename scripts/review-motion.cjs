async(page)=>{
 const shots=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:width===1440?1000:844});
  await page.goto('http://localhost:3001/',{waitUntil:'networkidle'});
  await page.locator('.journey-enhanced').waitFor();
  await page.evaluate(()=>document.fonts.ready);
  for(const progress of [0,.28,.55,.75,.95]){
   await page.evaluate(p=>{const el=document.querySelector('.scroll-journey');window.scrollTo({top:el.getBoundingClientRect().top+scrollY+(el.offsetHeight-innerHeight)*p,behavior:'instant'});},progress);
   await page.waitForTimeout(650);
   await page.waitForFunction(percent=>document.querySelector('.journey-percent')?.textContent===percent,`${Math.round(progress*100).toString().padStart(2,'0')}%`);
   if(progress===.28)await page.locator('.passport-portrait img').evaluateAll(images=>Promise.all(images.map(image=>image.decode())));
   await page.screenshot({path:`D:/MVP/docs/screenshots/motion-${width}-${Math.round(progress*100)}.png`});
   shots.push({width,progress,chapter:await page.locator('.journey-stage').getAttribute('data-chapter'),overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
  }
 }
 return shots;
}
