# Wardrobe hides/shows: measured corrections

Lane B does not edit contract/. These are the lists the wardrobe is built for; the Coordinator decides.

## Headwear: keep the curly hair visible

The headwear (head_cap, head_beanie, head_bucket) is sized to sit ON TOP of the avatar's curly hair_full
(and of a curly-hair allowance of about +2 cm, top about 1.80 m), so nothing clips with the hair visible.
With the contract lists (hide hair_full, show hair_capped) the hats float over a near-bald head.

Recommended:

| mesh | hides | shows |
| --- | --- | --- |
| head_cap | [] | [] |
| head_beanie | [] | [] |
| head_bucket | [] | [] |

The contract lists still work without clipping (hair_capped stays inside every hat); they just look less natural.

## Everything else

All other meshes match contract/meshes.json. Checked with blender/wardrobe/check_cover.py (rays cast from
every hidden body region towards camera directions): hips, thighs and shins are fully covered by both bottoms;
torso and arm regions show only small slivers at the neckline and cuff edges.
