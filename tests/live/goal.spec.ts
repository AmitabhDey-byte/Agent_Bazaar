import {test,expect} from "@playwright/test";
test("a full goal executes against the real deployed backend",async({page,request})=>{
 const token=process.env.LIVE_E2E_SESSION_TOKEN;
 const goal=process.env.LIVE_E2E_GOAL;
 const endpoint=process.env.NEXT_PUBLIC_API_URL;
 test.skip(!token||!goal||!endpoint,"Requires a live funded deployment and authorized session; no payment mock is used.");
 test.setTimeout(300000);
 const response=await request.get(`${endpoint}/session`,{headers:{Authorization:`Bearer ${token}`}});
 expect(response.ok()).toBeTruthy();
 const session=await response.json();
 await page.goto("/");
 await page.evaluate(({token,cap,wallet})=>sessionStorage.setItem("agent-bazaar-session",JSON.stringify({state:{token,cap,wallet},version:0})),{token,cap:session.cap,wallet:session.wallet});
 await page.reload();
 await page.getByLabel("Your goal",{exact:true}).fill(goal!);
 await page.getByRole("button",{name:"Launch mission",exact:true}).click();
 await expect(page).toHaveURL(/\/runs\//,{timeout:45000});
 await expect(page.getByText("Mission outcome",{exact:false})).toBeVisible({timeout:240000});
 await expect(page.getByRole("link",{name:"View receipt",exact:false}).first()).toHaveAttribute("href",/sepolia.basescan.org\/tx\/0x[\da-f]{64}/i);
});
