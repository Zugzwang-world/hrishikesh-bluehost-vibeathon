# Bluehost Vibeathon: Stage component

Working name Ensemble (may change; keep code, repo and URLs neutral). Shoppers who buy one outfit from several independent stores never see the whole look together. The Stage puts the shopper's own 3D avatar at the centre with merchant shops around it: describe a look and an occasion, flip through each merchant's collection on the avatar, run an on-stage simulation, then send the whole look to the Bluehost cart in one bag. Demo persona: Hrishikesh, presenting on stage at the Bluehost event in Bangalore.

The entry is the Bluehost AI Builder app (built by prompts, never edited here). This repo is the Stage, hosted on Vercel and embedded in the Bluehost /stage page by iframe. They talk by URL only (contract/url-contract.md).

## Read first

- Entries are due at 1:00 PM IST, 24 Nov 2026. Whatever is live at the deadline is the entry. **Main must deploy cleanly at all times.** Get it working end to end with placeholders, then improve in place.
- Originality: make every 3D asset here (Blender Python, code, generated textures). Never download 3D models, characters, HDRIs or texture packs. Google Fonts are fine.
- Prototype, speed and demo reliability. No tests, reviews or gates beyond what the demo needs. When unsure, pick the sensible default, tell the Coordinator for DECISIONS.md, keep moving.
- The founder works by voice and does no coding. Ask him only for logins, approvals, photos and keys, one line each. Reports are short and voice-friendly.
- Never use Fable or Mythos models. The founder's photos live in private/ (gitignored) and never go into git or onto Vercel.

## Contract first

contract/meshes.json (slots, mesh node names, hides/shows, stage hooks), contract/catalog.schema.json, contract/url-contract.md. Only the Coordinator edits contract/, docs/vibeathon/ and this file. Stable asset URLs are listed in url-contract.md; never rename them.

## Lanes (each edits only its own folders)

| Lane | Folders |
| --- | --- |
| A Avatar | blender/avatar, web/public/models/avatar.glb, web/public/brand/persona.png |
| B Wardrobe | blender/wardrobe, web/public/models/wardrobe.glb, web/public/textures |
| C Stage | blender/stage, web/public/models/stage.glb, web/public/brand/hero.jpg |
| D Web | web/src, web/api, web/index.html, web/package.json, web/vite.config.ts, web/vercel.json |
| E Catalog and renders | web/public/catalog, web/public/products, web/public/merchants, web/public/brand/logo.png, blender/render |
| Coordinator | contract/, docs/vibeathon/, CLAUDE.md, .claude/ |

## Shipping

- Lanes work in their own worktree and commit small working increments.
- Ship = `git fetch origin && git rebase origin/main`, then `cd web && npm run build` must pass, then `git push origin HEAD:main`. Push rejected: fetch, rebase, build, push again.
- Every push to main deploys to Vercel (project hrishikesh-stage, root directory web).
- Blender: `/opt/homebrew/bin/blender -b --python SCRIPT.py` (Blender 5.3). Scripts live in the lane's blender/ folder and run headless; GLBs are exported straight into web/public/models.
- After every merge the Coordinator rewrites docs/vibeathon/NOW.md and pushes, so the claude.ai Project sync stays fresh.
