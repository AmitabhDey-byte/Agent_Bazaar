# Frontend review — 17 November 2026

Scope: review the user's latest frontend changes and supplied assembly assets, finish integration, and prepare the frontend for the user's own deployment. No backend implementation or deployment was changed.

## Completed

- Preserved the new assembly desk, registry state handling, auction ledger, bookplate, balance-scale engraving, and six specialist WebP illustrations.
- Replaced the old Lucide portraits in the pinned assembly/selection chapters with the supplied specialist artwork. A shared capability-to-artwork map keeps the story and live registry consistent. The story remains explanatory illustration, not registry records or payment evidence.
- Kept native reversible scrolling, camera zoom, spatial assembly, chapter navigation, and the mission shortcut.
- Fixed the wallet trigger's mobile styling: Radix's dialog trigger slot had overwritten the button slot used by the responsive selectors. Wallet and navigation now fit at 320px on the landing and inside pages.
- Sized the illustrated dossiers for narrow/short phones. Short landscape windows use the complete linear field guide. Reduced-motion behavior remains supported.
- Corrected mission anchor clearance below the fixed header and tightened the short-landscape mission layout so the goal field is reachable on arrival.
- Replaced the landing route's dashboard loading skeleton with a paper field-guide loading state that reserves the story's height. This removed the visible footer jump while the page streamed in.
- Clarified frontend-only Vercel setup: project Root Directory is `web`. The user's root multi-service `vercel.json` remains available for their separate combined deployment plan.

## Verified

| Check | Result |
| --- | --- |
| Next.js 15.5.29 production build, including TypeScript | Passed |
| Frontend ESLint | Passed |
| Playwright smoke/motion/keyboard/navigation | 18 passed |
| API regression suite in `api/.venv` | 20 passed |
| Forge regression suite | 8 passed, including 256-run fuzz tests and a 128-run/4,096-call invariant |
| Axe WCAG A/AA | No violations in five scroll chapters at 1440px and 390px |
| Playwright MCP visual review | Five chapters at 1440px/390px; assembly desk at 1440px/1024px/768px/390px/320px; no horizontal document overflow |
| Lighthouse mobile, local production build | Performance 87, accessibility 100, best practices 100, SEO 100 |

The final Lighthouse report measured LCP at 3.7s and CLS at 0.00047 (down from 0.133 before the loading-state correction). Performance above 90 is **not** claimed; initial JavaScript and image delivery remain optimization opportunities. These are local measurements, not deployed-service performance guarantees.

The repository's updated setup uses `api/.venv` for API dependencies. The root tooling `.venv` lacks `httpx` and cannot collect the API suite; the existing API environment passed it. No dependency manifests were changed.

Evidence: [scroll screenshots](screenshots/motion-1440-28.png), [mobile scroll screenshot](screenshots/motion-390-28.png), [assembly desk](screenshots/assembly-1440.png), [mobile assembly desk](screenshots/assembly-390.png), [scroll recording](video/agent-bazaar-scroll.webm), [accessibility report](motion-accessibility.json), and [Lighthouse report](lighthouse.json). `scripts/review-motion.cjs` and `scripts/review-assembly.cjs` run through Playwright MCP. The latter captures the assembly element with the fixed header hidden only for the isolated screenshot.

Live authenticated registry/auction data, wallet signatures, payments, and funded runs still require the separately configured backend and testnet services. The production preview displayed the actual unavailable registry state. No runtime mocks or fabricated activity were introduced.

## Documentation checked

- Context7: [Next.js 15 Image API](https://github.com/vercel/next.js/blob/v15.5.28/docs/01-app/03-api-reference/02-components/image.mdx), for local artwork dimensions, responsive sizes, and loading priority.
- Context7 and official docs: [Vercel monorepos](https://vercel.com/docs/monorepos) and [Services](https://vercel.com/docs/services), to distinguish a separate frontend project from the supplied root service configuration.

Preview and deployment commands are in [DEPLOY-FRONTEND.md](../DEPLOY-FRONTEND.md). No deployment was attempted.
