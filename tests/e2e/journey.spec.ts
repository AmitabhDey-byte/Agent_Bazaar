import {test,expect} from "@playwright/test";

test("scroll scrubs and reverses the pinned scenes",async({page})=>{
 await page.goto("/");
 await page.locator(".journey-enhanced").waitFor();
 const stage=page.locator(".journey-stage");
 async function seek(progress:number){
  await page.evaluate(p=>{const el=document.querySelector<HTMLElement>(".scroll-journey")!;window.scrollTo({top:el.offsetTop+(el.offsetHeight-innerHeight)*p,behavior:"instant"});},progress);
 }
 const initial=await page.locator(".journey-engine").evaluate(el=>getComputedStyle(el).transform);
 await seek(.28);
 await expect(stage).toHaveAttribute("data-chapter","1");
 await expect(page.locator(".journey-opening")).toHaveCSS("opacity","0");
 await expect(page.locator(".passport-0")).toHaveCSS("opacity","1");
 await expect.poll(()=>page.locator(".passport-portrait img").evaluateAll(images=>images.filter(image=>(image as HTMLImageElement).complete&&(image as HTMLImageElement).naturalWidth>0).length)).toBe(6);
 expect(await stage.evaluate(el=>Math.abs(el.getBoundingClientRect().top))).toBeLessThan(2);
 expect(await page.locator(".journey-engine").evaluate(el=>getComputedStyle(el).transform)).not.toBe(initial);
 await seek(.75);
 await expect(stage).toHaveAttribute("data-chapter","3");
 await expect(page.locator(".exchange-scene")).toHaveCSS("opacity","1");
 await expect(page.locator(".passport-0")).toHaveCSS("opacity","0");
 await seek(.95);
 await expect(stage).toHaveAttribute("data-chapter","4");
 await expect(page.locator(".journey-receipt")).toHaveCSS("opacity","1");
 await page.getByRole("button",{name:"01 The possibility"}).click();
 await expect(stage).toHaveAttribute("data-chapter","0");
 await expect(page.locator(".journey-opening")).toHaveCSS("opacity","1");
 await expect(page.locator(".journey-receipt")).toHaveCSS("opacity","0");
 await page.getByRole("link",{name:"Start a mission",exact:true}).click();
 await expect(page).toHaveURL(/#mission$/);
 await expect(page.getByLabel("Your goal",{exact:true})).toBeInViewport();
});

test("narrow screens keep wallet and navigation reachable",async({page})=>{
 await page.setViewportSize({width:320,height:700});
 await page.goto("/");
 const menu=page.getByRole("button",{name:"Open navigation"});
 await expect(menu).toBeInViewport({ratio:1});
 await expect(page.getByRole("button",{name:"Connect wallet"})).toBeInViewport({ratio:1});
 await menu.click();
 await page.getByRole("link",{name:"Mission archive"}).click();
 await expect(page).toHaveURL(/\/history$/);
 await expect(page.getByRole("button",{name:"Open navigation"})).toBeInViewport({ratio:1});
});

test("short landscape screens get a readable complete field guide",async({page})=>{
 await page.setViewportSize({width:844,height:390});
 await page.goto("/");
 await expect(page.locator(".journey-stage")).not.toBeVisible();
 await expect(page.locator(".reduced-story article")).toHaveCount(5);
 await page.locator(".reduced-story").getByRole("link",{name:"Put them to work"}).click();
 await expect(page.getByLabel("Your goal",{exact:true})).toBeInViewport();
});

test("reduced motion provides the complete readable story without a long scroll stage",async({page})=>{
 await page.emulateMedia({reducedMotion:"reduce"});
 await page.goto("/");
 await expect(page.locator(".journey-stage")).not.toBeVisible();
 await expect(page.locator(".reduced-story")).toBeVisible();
 await expect(page.locator(".reduced-story article")).toHaveCount(5);
 await page.locator(".reduced-story").getByRole("link",{name:"Put them to work"}).click();
 await expect(page.getByLabel("Your goal",{exact:true})).toBeInViewport();
});
