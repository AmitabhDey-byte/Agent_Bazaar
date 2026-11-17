async (page) => {
 const results=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  await page.goto('http://localhost:3001/',{waitUntil:'networkidle'});
  await page.locator('.hero-art img').evaluate(image=>image.decode());
  await page.screenshot({path:`D:/MVP/docs/screenshots/editorial-${width}.png`,fullPage:true,animations:'disabled'});
  await page.screenshot({path:`D:/MVP/docs/screenshots/editorial-fold-${width}.png`,animations:'disabled'});
  results.push({width,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
 }
 return results;
}
