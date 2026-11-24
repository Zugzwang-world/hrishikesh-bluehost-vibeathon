"""Every visible hit from outside must hit a front face (three.js culls back faces).
    /opt/homebrew/bin/blender -b --python blender/wardrobe/check_normals.py
"""
import bpy, os, random
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(REPO, "web/public/models/wardrobe.glb"))
dg = bpy.context.evaluated_depsgraph_get()
random.seed(2)
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type != "MESH":
        continue
    tree = BVHTree.FromObject(o, dg)
    me = o.data
    verts = [o.matrix_world @ v.co for v in me.vertices]
    lo = Vector([min(v[i] for v in verts) for i in range(3)])
    hi = Vector([max(v[i] for v in verts) for i in range(3)])
    c = (lo + hi) / 2
    front = back = 0
    for _ in range(300):
        d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
        tgt = Vector([random.uniform(lo[i], hi[i]) for i in range(3)])
        org = tgt - d * 3.0
        loc, nrm, idx, dist = tree.ray_cast(org, d, 6.0)
        if loc is None:
            continue
        if nrm.dot(d) < 0:
            front += 1
        else:
            back += 1
    flag = "  <-- BACKFACES" if back > front * 0.1 else ""
    print(f"NORMALS {o.name:16s} front {front:3d} back {back:3d}  tris {sum(len(p.vertices)-2 for p in me.polygons)}{flag}")
