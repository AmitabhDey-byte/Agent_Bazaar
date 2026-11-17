import {test,expect} from "@playwright/test";

test("mission control is usable without fabricating network data",async({page})=>{
 await page.goto("/");
 await expect(page.getByRole("heading",{name:"AN ECONOMY OF POSSIBILITIES."})).toBeVisible();
 await expect(page.getByRole("button",{name:"Connect wallet"})).toBeVisible();
 await expect(page.getByLabel("Your goal",{exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Research the Base ecosystem",exact:true}).click();
 await expect(page.getByLabel("Your goal",{exact:true})).toHaveValue("Research the Base ecosystem");
 await page.getByRole("button",{name:"Launch mission",exact:true}).click();
 await expect(page.getByText("Connect your wallet and authorize a session first.")).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test("editorial navigation reaches the mission and works on mobile",async({page},testInfo)=>{
 await page.goto("/");
 await page.getByRole("link",{name:"Put them to work"}).click();
 await expect(page).toHaveURL(/#mission$/);
 await expect(page.getByRole("heading",{name:"What shall we accomplish?"})).toBeVisible();
 if(testInfo.project.name==="mobile"){
  await page.getByRole("button",{name:"Open navigation"}).click();
 }
 await page.getByRole("link",{name:"Mission archive"}).click();
 await expect(page).toHaveURL(/\/history$/);
 await expect(page.getByText("Your workspace is private")).toBeVisible();
});

test("command palette and wallet setup support keyboard dismissal",async({page})=>{
 await page.goto("/");
 await page.locator(".agent-node").first().waitFor({state:"visible"});
 await page.keyboard.press("Control+k");
 await expect(page.getByRole("dialog")).toBeVisible();
 await page.keyboard.press("Escape");
 await expect(page.getByRole("dialog")).not.toBeVisible();
 await page.getByRole("button",{name:"Connect wallet"}).click();
 await expect(page.getByLabel("Session budget (USDC)")).toBeVisible();
 await expect(page.getByLabel("Sponsor invite")).toHaveAttribute("type","password");
 await page.keyboard.press("Escape");
});

test("history, directory and status have honest empty or error states",async({page})=>{
 await page.goto("/history");
 await expect(page.getByText("Your workspace is private")).toBeVisible();
 await page.goto("/leaderboard");
 await expect(page.getByRole("heading",{name:"Meet the minds behind the mission."})).toBeVisible();
 await page.goto("/status");
 await expect(page.getByRole("heading",{name:"The network, at a glance."})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test("registration validates endpoint before proceeding",async({page})=>{
 await page.goto("/list");
 await page.getByLabel("Agent execution endpoint").fill("http://localhost/run");
 await page.getByRole("button",{name:"Continue",exact:true}).click();
 await expect(page.getByText("Use a public HTTPS execution URL ending in /run.")).toBeVisible();
 await page.getByLabel("Agent execution endpoint").fill("https://agents.example/agents/summarizer/run");
 await page.getByRole("button",{name:"Continue",exact:true}).click();
 await expect(page.getByLabel("Price per call (USDC)")).toBeVisible();
 await expect(page.getByRole("button",{name:"Register agent",exact:true})).toBeVisible();
});
