# Stage (Lane C)

`build_stage.py` builds the keynote stage in code and exports `web/public/models/stage.glb`.
It is modelled on today's event stage (Small Business AI Builder Tour, Bengaluru): a very wide
cobalt-to-violet LED wall with outlined-square clusters, narrower side LED panels, two flown truss
rows of moving heads, a blue gobo wash on the ceiling, a lit stage lip and rows of navy chairs.
`stage_textures.py` generates every texture with numpy (no downloaded assets).

    /opt/homebrew/bin/blender -b --python blender/stage/build_stage.py
    python3 blender/stage/check_glb.py          # lists hooks, materials, size

`render_hero.py` renders `web/public/brand/hero.jpg` (Cycles, blue Showtime light) from stage.glb,
plus avatar.glb and wardrobe.glb when present.

    /opt/homebrew/bin/blender -b --python blender/stage/render_hero.py
    # previews: -- --res 40 --samples 16 [--cam cam_wide | --pos x,y,z --tgt x,y,z --lens 18]
    #              [--rehearsal] [--stage-only] [--view AgX --look "AgX - Punchy"] --out /tmp/x.jpg

## Format

- glTF binary, **Draco compressed** (`KHR_draco_mesh_compression`), plus `KHR_materials_emissive_strength`.
  The web GLTFLoader needs a DRACOLoader (the web ships three's decoder at /draco/).
  About 400 KB, about 52k triangles, five small JPEG textures.
- Metres, Y up, audience toward +Z. All transforms applied (meshes sit at identity).
- No lights, no cameras. Hooks are empty nodes (plain `Object3D` in three.js).

## Layout

- Riser top surface at y = 0, 12 m wide (x -6..6), z -4..2.6, 0.6 m tall. House floor at y -0.6.
- Main LED wall (led_wall): 8.64 x 3.6 m (**2.4 : 1**), x -4.32..4.32, y 0.5..4.1, z -3.6, facing +Z.
- Side LED panels (led_wall_side): 2.1 x 3.0 m each, centred x ±5.72, y 0.55..3.55, z -3.35, turned 14° to the house.
- Two flown truss rows hung from the ceiling on chain hoists, x -6.6..6.6:
  front (lower) row at z 1.3, y ~6.05, 9 heads, warm lenses; back (upper) row at z -1.1, y ~6.75, 9 heads, blue lenses.
- Ceiling at y 7.4 over the whole hall with a tileable blue gobo texture (7 m tile) and beams with cyan cove lines.
- Podium at x 2.6, z -0.6 (turned 14° toward centre). Floor wedges at x ±2.2 and ±3.7, z 2.15.
- Seats: 9 rows, z 4.5..12 (slight arc), navy banquet chairs with a QR card on each back, centre aisle at x -0.7..0.7.
- x -1.5..1.5 on the riser is kept clear for the avatar.
- Hall: side walls at x ±12, back wall at z 18, black drape at z -5.2, side masking at x ±8.5.
  Exit signs, warm sconces, aisle step lights (all emissive, always on).

## Hooks (empties, web coordinates)

| Name | Position | Notes |
| --- | --- | --- |
| mark_center | (0, 0, 0) | Showtime mark, centre of the glowing centre mark |
| avatar_fit | (0, 0, 1.6) | Fitting mode turntable spot |
| cam_fit / cam_fit_target | (0, 1.15, 5.6) / (0, 0.95, 1.6) | Frames a 1.75 m person at avatar_fit |
| cam_wide / cam_wide_target | (0, 3.2, 14) / (0, 1.4, -1) | Back of the house |
| cam_audience / cam_audience_target | (0.7, 1.8, -1.6) / (0, 0.6, 8) | Over the presenter's shoulder, out to the house |
| cam_close / cam_close_target | (0.35, 1.5, 1.7) / (0, 1.45, 0) | Close on the presenter at mark_center |
| spot_L / spot_target_L | (-2.92, 5.28, 1.27) / (0, 0, 0) | Lens of the left front-row spot |
| spot_C / spot_target_C | (0, 5.26, 1.26) / (0, 0, 0) | Lens of the centre front-row spot |
| spot_R / spot_target_R | (2.92, 5.28, 1.27) / (0, 0, 0) | Lens of the right front-row spot |

Spot positions sit at the fixture lens; check_glb.py prints the exact values.

## Materials the web drives

| Material | Mesh | Use |
| --- | --- | --- |
| led_wall | led_wall | Single quad, UV 0..1 over the full 2.4 : 1 screen. Baked base look (gradient #2D4BFF to #7A5CFF plus outlined squares, clear centre band) on map and emissiveMap; the web may replace or overlay it at runtime. glTF UV convention: `texture.flipY = false` for a canvas texture. A 16:9 canvas will stretch 1.35x wide; draw at 2.4 : 1 (e.g. 2304 x 960). |
| led_wall_side | led_side_panels | Two side panels, UV 0..1 each (0.7 : 1 portrait), baked gradient plus squares. Note the web's `startsWith('led_wall')` also paints the main canvas onto these |
| led_strip | led_edge_strip, podium accent | Lit stage lip; turn up in Showtime |
| center_mark | center_mark | Glowing ring, dot and ticks at mark_center |
| turntable_ring | turntable | Faint ring at avatar_fit (the turntable disc itself is `turntable`, flush at y 0.0015) |
| light_cone | light_cones | 12 open cones, UV v = 0 at the lens, 1 at the far end (use it to fade). Additive + transparent in the web |

Textured static materials: stage_deck (2 x 1 m platform seams, UV 1 unit = 2 m), ceiling_gobo
(emissive blue gobo shapes on navy), qr_card (chair-back QR stickers). Emissive static:
cove_light, fixture_lens (warm), fixture_lens_blue, exit_sign, aisle_light.
Other dark materials: stage_deck_edge, stage_fascia, floor_house, drape, bezel, truss, fixture_metal,
podium, podium_top, mic_metal, monitor, monitor_grille, seat (navy), audience, turntable, house_wall, ceiling_beam.

## Meshes

riser, led_edge_strip, stairs, house_floor, drape, center_mark, turntable, led_wall, led_wall_frame,
led_side_panels, ceiling, truss, fixtures, light_cones, podium, floor_monitors, audience_seats,
audience_people, house_walls, house_lights. light_cones: 3 hero spots + 4 washes on the front row,
5 back-row beams raking onto the deck. Audience seats and people are each one merged mesh.

## Hero render

render_hero.py imports the three GLBs, hides `defaultHidden` plus the `hides` of each worn garment
that is present (and un-hides its `shows`, e.g. hair_capped under the cap), colours the Stage Ready look
(top_shirt, outer_overshirt, bottom_wide with the denim mask, shoe_sneaker, head_cap, eye_round and
watch_digital as metal), writes HRISHIKESH HUNDEKARI and the tour line on the wall as emissive text,
lights it with cool front-row spots, a follow spot, blue/violet back washes and beams, then adds
compositor bloom and a soft vignette (Standard view, exposure -0.4). About 1 minute on the M4 GPU at
128 samples. With `--stage-only` (or without the avatar) it renders the empty stage.
