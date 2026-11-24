# Decisions

From Brief 07 (decided):

- The entry is the Bluehost AI Builder app; this repo is the Stage on Vercel, embedded by iframe. URLs only between them. No Supabase; no backend beyond Vercel functions.
- Slots: top, outerwear, bottom, footwear, headwear, eyewear, watch, neckwear; top, bottom, footwear required. Garments hide covered body regions instead of fighting offsets.
- GLB frame: metres, Y up, avatar faces +Z, feet at origin. Static A-pose, no rig.
- Catalog: 7 fictional merchants, 43 products, INR whole rupees. CSVs for the Bluehost prompts.
- Stylist model from STYLIST_MODEL, default claude-haiku-5-5, fallback claude-sonnet-5-5; keyword matcher fallback on the client.
- Cuts if something stalls: faceless head, fewer meshes with more colours, Rehearsal lighting only, keyword stylist.

Coordinator, 24 Nov:

- 11:10 Deadline is 1:00 PM and setup started at 11:02, so lanes push straight to main (rebase on origin/main, build, push) instead of waiting for the Coordinator to merge. Disjoint folders make this safe; the build check keeps main deploying.
- 11:10 The Coordinator wrote catalog.json and the placeholder generator (blender/render/build_catalog.py) so the CSVs reach the Bluehost prompts immediately. Lane E owns it from here.
- 11:10 Stage hooks: each camera is a pair of empties, cam_X (position) and cam_X_target (look-at). Spots are spot_L/R/C aimed at spot_target_L/R/C. avatar_fit is the turntable spot, mark_center the Showtime mark. stage.glb carries no lights; the web builds both lighting states in code.
- 11:10 Garment materials are replaced at runtime from catalog material fields; pattern masks are /textures/PATTERN.png, 1 UV unit = 1 metre, 0.25 m per repeat.
- 11:10 Persona default look: KC-001 white tee, RS-001 charcoal blazer, IL-005 charcoal wide trousers, KB-001 white sneakers. Eyewear added once we know if he wears glasses.
- 11:10 None of the newest Downloads images are of the founder (a whiteboard and phone screenshots); Lane A starts with the designer-toy figure and personalises when photos arrive.
- 11:10 web stack as installed by npm today: react 19.3, three 0.187, @react-three/fiber 9.8, drei 10.7, @react-three/postprocessing 3.2, zustand 5.1, motion 14.14, vite 8.3, typescript 7.0. Unverified by the scout.
- 11:16 Commit signing is off in this repo's local git config: the SSH signing key isn't in the agent, so signed commits hang. The Innodata repo's commits are unsigned too.
- 11:22 Vercel project hrishikesh-stage (team hrizzup), root directory web, framework vite, ANTHROPIC_API_KEY and STYLIST_MODEL set. Live at https://hrishikesh-stage.vercel.app. `vercel git connect` failed (the Vercel GitHub app probably can't see the new repo), so a Coordinator watcher deploys origin/main to production within a minute of every push until the founder adds the repo to the Vercel GitHub app.
- 11:22 Commits use the GitHub noreply email (repo-local config); the private email blocks pushes.
- 11:35 Stylist (Lane D2, done): claude-haiku-5-5 from STYLIST_MODEL with low effort and thinking disabled; one retry on claude-sonnet-5-5 (thinking left unset, it rejects disabled) if 2.5 s remain of an 8.3 s budget. Structured output verified on Haiku 5.5 with SDK 1.13 via `output_config.format` json_schema (`output_format` is deprecated); slot SKUs are enums, required slots non-null. Forced tool calls (`tool_choice` any/tool) return 400 on these models, so structured output is the only JSON guarantee. Functions are single-file `(req, res)` Node handlers that read the live /catalog/catalog.json with an embedded snapshot fallback, and cache identical requests for 15 minutes on a warm instance. Stage check swaps are computed in code and the model picks one or null. Live latency 3–4 s end to end.
- 11:37 web/tsconfig.tsbuildinfo untracked (the build rewrites it).

Brief 08 (SHOP-UNI-FY), 24 Nov:

- 11:48 Catalog replaced: SHOP-UNI-FY, 5 Instagram thrift stores (kaapi-thrift, stonewash-society, kerbside-kicks, lids-and-lenses, second-hand), 31 one-of-one pieces. Bluehost is built against these slugs, SKUs and URLs; never rename them. Old seven merchants' files deleted. The render manifest was reset and every old product image deleted, because LL- and SH- SKUs were reused with different meanings (old LL-001 was a tortoise frame, new LL-001 is the red cap).
- 11:48 New catalog fields: product category, size, condition, era, oneOfOne (always true; demo mode keeps pieces available); merchant instagram; material.soleColor (KK-002 gum sole). catalog.json also carries defaultLook (his outfit today: KT-002, KT-006, SW-001, KK-001, LL-006, SH-001) and looks[0] Stage Ready (KT-001, KT-006, SW-001, KK-001, LL-001, LL-006, SH-001).
- 11:48 CSV columns now: merchants slug, name, code, instagram, tagline, category, story, colours, logo/banner URLs, store_url (/m/SLUG), merchant_app_url (/m/SLUG/app), piece_count; products sku, name, store, category, slot, price, size, condition, era, one_of_one, color, description, tags, image_url, try_on_path (/experience?try=SKU), viewer_url (STAGE/product?sku=SKU&embed=1). Copies on the founder's Desktop.
- 11:48 Brand logo is a SHOP-UNI-FY wordmark in Anton (bone letters, signal-red hyphens). Portfolio photos IMG_5043, IMG_6967, IMG_5378, IMG_1642 published as /portfolio/01–04.webp (long edge 1600, EXIF and GPS stripped). Face references, the stage photo and the layout sketches live only in private/ (EXIF-stripped copies, smaller ones in private/refs/).
- 11:45 The founder wears thin gold hexagonal frames: LL-006 (mesh eye_round, reshaped to a hex frame by Lane B) is in his default look; glasses never come from the head scan.
- 11:45 Avatar likeness: the brief's primary path (Hyper3D Rodin through Blender MCP) is unavailable because this session has no Blender MCP, so Lane A uses the fallback, Hunyuan3D-2 or TRELLIS on a Hugging Face Space with HF_TOKEN (copied into the gitignored .env). Two attempts, then the stylised head personalised from the photos. A scanned head is exported as body_head with hair included and no hair_full/hair_capped; headwear is sized over the hair and hides nothing.
- 11:45 Lane F (email) cancelled: Bluehost shows an in-app pop-up instead. The orbit ring is replaced by the sketch layout (M1/M2 left, M3/M4 right, M5 under the stage). Add look to bag is now Lock the look, target _parent, HOST + CART_PATH (default /cart, cartPath param) + ?add=…&look=….
- 11:45 New Stage modes: mode=persona, mode=locked&look=…, and /product?sku=… (SPA rewrite in vercel.json).
- 11:52 Stylist (D2, done): the demo prompt returns Stage Ready exactly from Haiku 5.5 and from the keyword fallback. House rules (white shirt → KT-001, red cap → LL-001, baggy/my jeans → SW-001, stage/presenting adds KT-006 and SH-001 unless he names a layer or watch, eyewear stays LL-006 unless he asks for shades) run in the keyword path and again on the server after the model; responses list any corrected slots in `guarded`. The stage score is anchored within ±6 of a code-computed score. Defaults come from the live catalog's defaultLook and looks. Stylist 2.8–3.1 s, stage check 2.2–2.6 s.
- 11:56 Avatar likeness v1 (A): built in code from his photos (skin #A06C52 sampled from colour photos, curly dark hair, light stubble as the beard node with its own material, slim athletic build); faceless. Landmarks unchanged.
- 11:58 Image-to-3D head: authorised by the founder's Brief 08, but the input is limited to the already-public portfolio photo (/portfolio/01.webp); the private face references are never uploaded. Two attempts, hard stop 12:30, ship only if it beats the stylised head.
