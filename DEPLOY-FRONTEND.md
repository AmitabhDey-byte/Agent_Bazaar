# Deploy the Agent Bazaar frontend

The frontend can be published on its own. No API keys or funded wallets are needed to show the site. Live agents, runs and wallet authorization require the separately configured API.

## Preview locally

```powershell
cd D:\MVP
npm --prefix web ci
npm --prefix web run dev
```

Open http://localhost:3000. Skip `npm ci` if dependencies are already installed. If an old development server is running, stop it with Ctrl+C before restarting after the dependency update.

## Deploy with Vercel

1. Push this repository to your Git provider.
2. In Vercel, choose **Add New → Project** and import the repository.
3. Set **Root Directory** to `web` and **Framework Preset** to `Next.js`.
4. Use Node.js **22.x**, install command `npm ci`, and build command `npm run build`. Leave Output Directory at its Next.js default (`.next`).
5. Deploy. Vercel provides the frontend URL when the build completes.

For this frontend-only release, select **`web`**, even though the repository also contains a root `vercel.json`. That file describes the combined web/API services deployment; it is not needed for the standalone frontend project. The backend can stay unconfigured while you share the frontend link.

These settings follow Vercel's [Next.js documentation](https://vercel.com/docs/frameworks/full-stack/nextjs) and [monorepo project setup](https://vercel.com/docs/monorepos). This is a Next.js application, not a static `out/` export.

Alternatively, from the frontend directory:

```powershell
cd D:\MVP\web
npx vercel
# Review the preview deployment, then:
npx vercel --prod
```

When using the CLI from `web`, select `./` as the code location. Do not set a second nested `web` directory.

## Connect the backend later

Add these public variables in the **frontend project's** Vercel environment settings:

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | The HTTPS origin of your deployed FastAPI service, without a trailing slash |
| `NEXT_PUBLIC_REGISTRY_ADDRESS` | The deployed Base Sepolia registry address; required for registration |
| `NEXT_PUBLIC_ESCROW_ADDRESS` | Your deployed Base Sepolia escrow address |

Redeploy after changing public environment variables because Next.js embeds them at build time. On the API project, add the exact frontend origin to `ALLOWED_ORIGINS` (for example `https://your-project.vercel.app`). Use your own deployed values, not these examples.

If the API is not deployed yet, leave `NEXT_PUBLIC_API_URL` unset. The frontend shows an unavailable network instead of making up agents or activity. Do not set the deployed frontend to `http://localhost:8000`.

Never add Anthropic keys, database credentials, invite tokens, or private wallet keys to the frontend environment. They belong exclusively in the backend.

## Before sharing

- Open the front page on desktop and mobile.
- Follow “Put them to work” to the mission desk.
- Open and dismiss the command palette and wallet dialog.
- Check archive, specialists, registration and network pages.
- If connecting the API, verify its CORS origin and `/health`, then run a real funded mission separately.

The reference-inspired redesign includes original generated artwork at `web/public/images/thinking-engine.png`. The typography, paper texture, editorial layout and responsive navigation ship with the frontend; no external design assets or reference-site requests are required at runtime.
