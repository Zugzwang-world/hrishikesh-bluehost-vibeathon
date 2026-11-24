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
