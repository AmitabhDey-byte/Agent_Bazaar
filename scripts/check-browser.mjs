// Toolchain launch verification only; this is not an application smoke test.
import { chromium } from "@playwright/test";

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    const page = await browser.newPage({ viewport });
    await page.goto("about:blank");
    const actual = await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
    if (actual.width !== viewport.width || actual.height !== viewport.height) throw new Error("Viewport mismatch");
    console.log(`Chromium ${browser.version()}: launch + ${viewport.width}x${viewport.height} viewport OK`);
    await page.close();
  }
} finally {
  await browser.close();
}
