"""Coverage check: for outfits, cast rays from every hidden body region vertex towards plausible camera
directions; a ray that escapes without hitting a garment or a visible body part is a gap the audience could see.
    /opt/homebrew/bin/blender -b --python blender/wardrobe/check_cover.py
"""
import bpy, os, sys, json, math, random
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
contract = json.load(open(os.path.join(REPO, "contract", "meshes.json")))
MESHES = contract["meshes"]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(REPO, "web/public/models/avatar.glb"))
bpy.ops.import_scene.gltf(filepath=os.path.join(REPO, "web/public/models/wardrobe.glb"))
objs = {o.name.split(".")[0]: o for o in bpy.data.objects if o.type == "MESH"}
dg = bpy.context.evaluated_depsgraph_get()


def world_mesh(o):
    me = o.evaluated_get(dg).to_mesh()
    verts = [o.matrix_world @ v.co for v in me.vertices]
    nrm = [(o.matrix_world.to_3x3() @ v.normal).normalized() for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    o.evaluated_get(dg).to_mesh_clear()
    return verts, nrm, polys


cache = {n: world_mesh(o) for n, o in objs.items()}
random.seed(1)
DIRS = []
for i in range(400):
    v = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
    if -0.35 < v.z < 0.75:  # blender z = up; cameras sit around and slightly above
        DIRS.append(v)

OUTFITS = [
    ["top_tee", "bottom_wide", "shoe_sneaker"],
    ["top_shirt", "bottom_slim", "shoe_loafer"],
    ["top_oversized", "bottom_slim", "shoe_sneaker"],
    ["top_tee", "outer_blazer", "bottom_slim", "shoe_loafer"],
    ["top_shirt", "outer_overshirt", "bottom_wide", "shoe_sneaker", "head_cap"],
    ["top_tee", "bottom_wide", "shoe_sneaker", "head_beanie"],
    ["top_tee", "bottom_wide", "shoe_sneaker", "head_bucket"],
]
only = os.environ.get("OUTFIT")
for outfit in OUTFITS:
    if only and only not in ",".join(outfit):
        continue
    hidden = set(contract["defaultHidden"])
    shows = set()
    for g in outfit:
        hidden |= set(MESHES[g]["hides"])
        shows |= set(MESHES[g]["shows"])
    hidden -= shows
    obst = []
    for n in objs:
        if n in outfit or ((n.startswith("body_") or n.startswith("hair_") or n in ("beard",)) and n not in hidden):
            obst.append(n)
    V, P = [], []
    for n in obst:
        verts, _, polys = cache[n]
        off = len(V)
        V += verts
        P += [tuple(i + off for i in p) for p in polys]
    tree = BVHTree.FromPolygons(V, P)
    report = {}
    for n in hidden:
        if n not in cache or not n.startswith("body_"):
            continue
        verts, nrms, _ = cache[n]
        leaks, tot = 0, 0
        worst = []
        for i in range(0, len(verts), 3):
            p, nm = verts[i], nrms[i]
            if p.z < 0.01:  # sole on the floor
                continue
            tot += 1
            esc = 0
            for d in DIRS:
                if d.dot(nm) < 0.1:
                    continue
                hit = tree.ray_cast(p + d * 0.0005, d, 5.0)
                if hit[0] is None:
                    esc += 1
            if esc:
                leaks += 1
                worst.append((esc, p))
        worst.sort(key=lambda t: -t[0])
        report[n] = (leaks, tot, [(e, round(p.x, 3), round(p.z, 3), round(-p.y, 3)) for e, p in worst[:4]])
    print("OUTFIT", "+".join(outfit))
    for n, (l, t, w) in sorted(report.items()):
        print(f"   {n:16s} leaking {l:4d}/{t:4d}  worst (rays, gx, gy, gz): {w}")
