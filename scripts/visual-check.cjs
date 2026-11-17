async (page) => {
  const results = [];
  for (const viewport of [{width:1440,height:1080},{width:390,height:844}]) {
    await page.setViewportSize(viewport);
    await page.goto('http://localhost:3000/', {waitUntil:'networkidle'});
    await page.getByRole('heading',{name:'AN ECONOMY OF POSSIBILITIES.'}).waitFor();
    await page.getByRole('button',{name:'Open command palette'}).click();
    await page.getByRole('dialog').waitFor();
    await page.keyboard.press('Escape');
    await page.locator('.agent-node').first().waitFor({state:'visible'});
    await page.waitForFunction(() => document.querySelector('.cost span') && getComputedStyle(document.querySelector('.cost span')).opacity === '1');
    await page.screenshot({path:`D:/MVP/docs/screenshots/mission-${viewport.width}.png`,fullPage:true,animations:'disabled'});
    results.push({width:viewport.width,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
  }
  return results;
}
