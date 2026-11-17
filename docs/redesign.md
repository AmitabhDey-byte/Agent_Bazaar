# Editorial frontend redesign

Reference: https://belka-stelka.ava-case.site/ — inspected through Playwright MCP, including the loaded opening spread and a scrolled chapter. The reference informed the paper, typography, ink palette and editorial hierarchy; its code, text and artwork were not copied.

## Delivered

- Cream paper background, Bodoni display typography, vermilion accents and ruled newspaper columns.
- Original engraved thinking-engine illustration, editorial stamp, numbered navigation, and chapter transitions.
- Responsive front page explaining the product, with direct links into the functional mission workspace.
- Matching treatments across archive, directory, status, registration, run pages, wallet dialogs and command palette.
- Existing real API, wallet, auction, payment and streaming integrations preserved.
- Mobile navigation, keyboard controls and reduced-motion support.

The artwork was generated using the built-in image generation tool and copied to `web/public/images/thinking-engine.png`. Prompt: premium scientific-newspaper copperplate engraving of a spherical mechanical thinking engine, brass gears and orbital instruments, ivory paper, sparse vermilion details, no text or interface. The original remains in the Codex generated-images folder. CSS blends the supplied raster into the page; no reference-site assets are fetched at runtime.

Playwright MCP screenshots are stored in `docs/screenshots/editorial-1440.png`, `editorial-390.png`, and the corresponding `editorial-fold-*` images. The preview is the real frontend with an unconfigured API, not a fabricated active run.

See `DEPLOY-FRONTEND.md` for local preview and frontend-only Vercel deployment.

## Verification

- Next.js 15 production build, TypeScript and ESLint pass.
- Playwright: 10 desktop/mobile interaction tests pass.
- Axe: zero WCAG A/AA violations at 1440px and 390px after contrast and accessible-name corrections.
- Playwright MCP: screenshots reviewed at both widths; no horizontal overflow.
- Local development server returns HTTP 200 after a clean restart.
- Frontend npm audit: zero reported vulnerabilities after compatible dependency fixes; Next.js remains on major version 15.
- Lighthouse mobile: performance 87, accessibility 100, best practices 100, SEO 100. The measured performance target of over 90 is not met; remaining work is primarily initial JavaScript and image delivery. The font-related layout shift was removed.
- Regression checks: 20 API tests and 8 contract tests pass, including fuzz and invariant coverage.

No deployment or real funded goal was executed. The user is handling deployment. The numbers above describe the earlier static redesign. The current pinned scroll frontend and updated measurements are recorded in [frontend-review.md](frontend-review.md); `lighthouse.json` has been refreshed for that revision.
