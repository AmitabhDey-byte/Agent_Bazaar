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

test("reduced motion provides the complete readable story without a long scroll stage",async({page})=>{
 await page.emulateMedia({reducedMotion:"reduce"});
 await page.goto("/");
 await expect(page.locator(".journey-stage")).not.toBeVisible();
 await expect(page.locator(".reduced-story")).toBeVisible();
 await expect(page.locator(".reduced-story article")).toHaveCount(5);
 await page.locator(".reduced-story").getByRole("link",{name:"Put them to work"}).click();
 await expect(page.getByLabel("Your goal",{exact:true})).toBeInViewport();
});
