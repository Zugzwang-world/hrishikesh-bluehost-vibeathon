# Stage (Lane C)

`build_stage.py` builds the keynote stage in code and exports `web/public/models/stage.glb`.

    /opt/homebrew/bin/blender -b --python blender/stage/build_stage.py
    python3 blender/stage/check_glb.py          # lists hooks, materials, size

`render_hero.py` renders `web/public/brand/hero.jpg` (Cycles, Showtime lighting) from stage.glb,
plus avatar.glb and wardrobe.glb when both exist.

    /opt/homebrew/bin/blender -b --python blender/stage/render_hero.py
    # previews: -- --res 40 --samples 16 --cam cam_wide [--rehearsal] [--stage-only] --out /tmp/x.jpg

## Format

- glTF binary, **Draco compressed** (`KHR_draco_mesh_compression`), plus `KHR_materials_emissive_strength`.
  The web GLTFLoader needs a DRACOLoader (the web ships three's decoder at /draco/). About 175 KB, about 37k triangles.
- Metres, Y up, audience toward +Z. All transforms applied (meshes sit at identity).
- No lights, no cameras. Hooks are empty nodes (plain `Object3D` in three.js).

## Layout

- Riser top surface at y = 0, 10 m wide (x -5..5), z -4..2.6, 0.6 m tall. House floor at y -0.6.
- LED wall screen: 6.4 x 3.6 m, x -3.2..3.2, y 0.5..4.1, at z -3.6, facing +Z.
- Truss towers at x = ±5.2, z = 1.0, top span at y 6.1..6.4. Upstage flown span at y 6.9, z -2.6.
- Podium at x 2.6, z -0.6 (turned 14° toward centre). Floor wedges at x ±2.2 and ±3.7, z 2.15.
- Seats: 9 rows, z 4.5..12 (slight arc), centre aisle at x -0.7..0.7.
- x -1.5..1.5 on the riser is kept clear for the avatar.
- Hall: side walls at x ±12, back wall at z 18, black drape at z -5.2, side masking at x ±8.5.
  Exit signs on the back and side walls, warm sconces, aisle step lights (all emissive, always on).

## Hooks (empties, web coordinates)

| Name | Position | Notes |
| --- | --- | --- |
| mark_center | (0, 0, 0) | Showtime mark, centre of the glowing centre mark |
| avatar_fit | (0, 0, 1.6) | Fitting mode turntable spot |
| cam_fit / cam_fit_target | (0, 1.15, 5.6) / (0, 0.95, 1.6) | Frames a 1.75 m person at avatar_fit |
| cam_wide / cam_wide_target | (0, 3.2, 14) / (0, 1.4, -1) | Back of the house |
| cam_audience / cam_audience_target | (0.7, 1.8, -1.6) / (0, 0.6, 8) | Over the presenter's shoulder, out to the house |
| cam_close / cam_close_target | (0.35, 1.5, 1.7) / (0, 1.45, 0) | Close on the presenter at mark_center |
| spot_L / spot_target_L | (-2.92, 5.48, 0.97) / (0, 0, 0) | Lens of the left front-truss spot |
| spot_C / spot_target_C | (0, 5.46, 0.97) / (0, 0, 0) | Lens of the centre front-truss spot |
| spot_R / spot_target_R | (2.92, 5.48, 0.97) / (0, 0, 0) | Lens of the right front-truss spot |

Spot positions sit at the fixture lens; check_glb.py prints the exact values.

## Materials the web drives

| Material | Mesh | Use |
| --- | --- | --- |
| led_wall | led_wall | Single quad, UV 0..1 over the full screen. Set map/emissiveMap at runtime. glTF UV convention: use `texture.flipY = false` for a canvas texture to read upright. |
| led_strip | led_edge_strip, led_pillars, podium accent | Emissive blue (#1A6BFF-ish); turn up in Showtime |
| center_mark | center_mark | Glowing ring, dot and ticks at mark_center |
| turntable_ring | turntable | Faint ring at avatar_fit (the turntable disc itself is `turntable`, flush at y 0.0015) |
| light_cone | light_cones | Open cones from every moving head, UV v = 0 at the lens, 1 at the far end (use it to fade). Make additive + transparent in the web |

Other materials (dark, static): stage_deck, stage_fascia, floor_house, drape, bezel, truss,
fixture_metal, fixture_lens, podium, podium_top, mic_metal, monitor, monitor_grille, seat, audience,
turntable, house_wall, exit_sign (emissive green), aisle_light (emissive warm).

## Meshes

riser, led_edge_strip, stairs, house_floor, drape, center_mark, turntable, led_wall, led_wall_frame,
led_pillars, truss, fixtures, light_cones, podium, floor_monitors, audience_seats, audience_people,
house_walls, house_lights. light_cones holds 12 beams: 3 hero spots + 4 washes on the front truss,
5 back lights on the upstage span raking onto the deck.

## Hero render

render_hero.py imports the three GLBs, hides `defaultHidden` plus the `hides` of each worn garment
that is present (top_tee, outer_blazer, bottom_wide, shoe_sneaker), colours them from the brief,
puts HRISHIKESH on the LED wall as emissive text, lights with warm front-truss spots, a front-of-house
follow spot, blue/violet washes and coloured beams, then adds compositor bloom. About 1 minute on
the M4 GPU at 128 samples. With `--stage-only` (or when avatar/wardrobe are missing) it renders the
empty stage with the spots on the centre mark.
Audience seats and people are each one merged mesh (one draw call each).
