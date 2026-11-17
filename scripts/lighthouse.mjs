import { chromium } from '@playwright/test';
import lighthouse from 'lighthouse';
import { writeFile } from 'node:fs/promises';

const port = 9223;
const browser = await chromium.launch({ headless: true, args: [`--remote-debugging-port=${port}`] });
try {
  const result = await lighthouse(process.env.AUDIT_URL || 'http://localhost:3001', {
    port, output: 'json', logLevel: 'error', onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
  });
  await writeFile('docs/lighthouse.json', result.report);
  console.log(JSON.stringify(Object.fromEntries(Object.entries(result.lhr.categories).map(([k,v]) => [k, Math.round(v.score*100)]))));
  console.log(JSON.stringify(Object.values(result.lhr.audits).filter(a => a.score !== null && a.score < 0.9).map(a => ({id:a.id, title:a.title, value:a.displayValue}))));
} finally { await browser.close(); }
