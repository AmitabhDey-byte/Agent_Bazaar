# Scroll-driven landing experience

This revision replaces the static editorial front page with a native-scroll, viewport-pinned story. The original reference was revisited in Playwright MCP at 11 positions across its full 22,659px document, including the aperture zoom, character assembly, launch, orbital sequence, diagonal transition and landing.

Agent Bazaar uses its own five-part narrative:

1. **The possibility:** oversized type and the engraved engine; scroll moves the headline away and zooms through the illustration.
2. **The assembly:** a circular aperture reveals a night scene; six illustrated specialist dossiers assemble around a rotating orbital diagram.
3. **The selection:** dossiers move apart, the chosen discipline comes forward, and a selection stamp appears.
4. **The exchange:** a payment coin moves and rotates through drawn orbital paths while the background changes again.
5. **The return:** the paper scene returns and a receipt arrives; a direct action takes the visitor into the real mission workspace.

The sequence is explanatory artwork, not simulated agent activity or payment evidence. No fabricated live bids, balances, agents, or receipts were added to the application.

## Interaction

- One sticky viewport over a native document scroll range; no wheel interception, forced scrolling, autoplay or scroll lock.
- Every major scene is driven by scroll position and reverses when the user scrolls upward.
- Chapter controls jump to the appropriate point and show progress.
- “Start a mission” skips the entire illustrated sequence.
- Wallet and application navigation remain reachable through the fixed header.
- Mobile has a separately composed stage, lower chapter controls, and readable captions.
- Reduced-motion preference and JavaScript-disabled browsing receive a readable linear story with direct access to the mission desk.

Implementation: `web/src/components/scroll-journey.tsx` and `web/src/app/journey.css`. Motion is already an application dependency. Function-based interpolation keeps the layered tracks synchronized instead of allowing browser acceleration to stretch individual track durations.

Evidence: `docs/screenshots/motion-*.png`, `docs/motion-accessibility.json`, and the actual browser recording `docs/video/agent-bazaar-scroll.webm`. The dedicated browser tests check scene pinning, opacity isolation, forward and reverse travel, chapter jumps, skip-to-workspace, and reduced motion on desktop and mobile.

Earlier `editorial-*` screenshots document the superseded static design. The current artwork integration, mobile corrections, production measurements, and verification results are recorded in [frontend-review.md](frontend-review.md). `docs/lighthouse.json` now measures the current scroll experience. Frontend deployment settings remain in `DEPLOY-FRONTEND.md`.
