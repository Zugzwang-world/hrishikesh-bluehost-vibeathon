# Avatar (Lane A)

Designer-toy man, ~7 heads tall, matte vinyl, faceless head. The founder's likeness is carried by the
stylised features, all generated in code (no scan, no downloaded assets): curly dark hair with volume on the
top and sides, light stubble (`beard` node, own `stubble` material) with a mouth opening, skin tone sampled
from his photos (#A06C52), and a slim athletic build (narrower waist and hips, lean limbs, same landmarks).
His gold hex frames come from the wardrobe (`eye_round`), not from the avatar. Static relaxed A-pose, no rig.

## Rebuild

From the repo root:

```
/opt/homebrew/bin/blender -b --python blender/avatar/build_avatar.py          # writes web/public/models/avatar.glb
/opt/homebrew/bin/blender -b --python blender/avatar/render_persona.py        # writes web/public/brand/persona.png
# persona options (env): PERSONA_LIGHT=stage (cobalt/violet stage check), PERSONA_TOP=tee (no wardrobe),
# PERSONA_TY / PERSONA_DIST / PERSONA_AZ for framing. Default: today's outfit from wardrobe.glb.
/opt/homebrew/bin/blender -b --python blender/avatar/preview.py -- OUTDIR     # quick Workbench check renders
```

Add `-- --save` to the build to also write `blender/avatar/avatar.blend` (not committed).

## Method

1. Body: torso loft (Catmull-Rom resampled superellipse rings), tapered tubes for limbs, ellipsoids for head,
   ears, subtle nose, deltoids, trapezius, calves, mitten hands and feet. All unioned with a voxel remesh
   (5.5 mm), smoothed, decimated to ~23k triangles, sole clipped flat at y = 0.
2. Region cuts: clean planar bisects at each region boundary, faces labelled by region, then split into
   separate nodes. Neighbours share their boundary edges exactly (no holes when both are shown).
   Vertex normals are taken from the unsplit body, so seams do not show in shading.
3. Hair: a shell offset from the head surface over an (azimuth, polar) patch with a hairline table, plus a
   few hundred seeded spheres scattered over it (and a loose fringe on the forehead), unioned by a voxel
   remesh into a mop of curls, then decimated. `hair_capped` is a thin band below the cap line with curls
   behind the ears only. Stubble is a thin sheet 1.6 to 2.8 mm off the skin; the mouth sinks under the skin.

## Output (glTF frame: metres, Y up, faces +Z, feet on y = 0)

Nodes: `body_head body_neck body_torso body_hips body_upperarm_L/R body_forearm_L/R body_hand_L/R
body_thigh_L/R body_shin_L/R body_foot_L/R hair_full hair_capped beard`. `_L` is the figure's left (+X).
Materials: `skin` (#A06C52, roughness 0.55), `hair` (#1C1512) and `stubble` (#725041, used by `beard`).
Draco compressed, ~41k triangles, ~160 KB.

Bounding boxes for headwear and eyewear fits (metres, glTF frame):
`body_head` x ±0.095, y 1.50 to 1.744, z -0.093 to 0.113; `hair_full` x ±0.118, y 1.554 to 1.784,
z -0.120 to 0.130; `hair_capped` x ±0.091, y 1.553 to 1.622, z -0.106 to 0.100; `beard` y 1.502 to 1.603.

## Landmarks (shared with Lane B)

| Landmark | Value |
| --- | --- |
| Height | 1.75 (skull top 1.745, curly hair top ~1.784) |
| Chin / neck | chin 1.50, neck 1.44 to 1.50 |
| Shoulder joints | x ±0.19, y 1.42 |
| Chest | y 1.25, width 0.36, depth 0.24 |
| Waist | y 1.05, width 0.30, depth 0.21 |
| Hips | y 0.92, width 0.36, depth 0.24; crotch 0.82 |
| Arms | XY plane, 30° from vertical; elbow 0.29, wrist 0.55, fingertips 0.74 m from the shoulder joint; palms face the thighs |
| Legs | hip joints x ±0.095 y 0.88; knee 0.49; ankle 0.08 |
| Feet | centred x ±0.11, heel z -0.06, toe z +0.21, width 0.10 |

Region cuts: head above y 1.50; neck 1.44–1.50; torso 1.44 to 1.00 (arms excluded at the shoulder);
hips 1.00 to 0.80; thigh 0.80–0.49; shin 0.49–0.10; foot below 0.10; upper arm from the shoulder to
0.18 m along the arm; forearm 0.18–0.55 m; hand beyond the wrist (0.55 m).

`hair_capped` is only the hair below the cap line (y ≤ 1.62): sideburns and the band at the back.
