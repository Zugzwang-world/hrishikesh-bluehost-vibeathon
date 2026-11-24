"""Quick workbench previews of wardrobe.glb on the fit body (or avatar.glb).
    /opt/homebrew/bin/blender -b --python blender/wardrobe/preview.py -- OUTDIR [mesh,mesh,...]
"""
import bpy, os, sys, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_wardrobe as W

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = argv[0] if argv else "/tmp"
SHOW = argv[1].split(",") if len(argv) > 1 and argv[1] else None

W.reset()
before = set(bpy.data.objects)
if os.path.exists(W.AVATAR):
    bpy.ops.import_scene.gltf(filepath=W.AVATAR)
    for o in bpy.data.objects:
        if o.type == "MESH" and (o.name.startswith("hair_capped")):
            o.hide_render = True
    body_objs = [o for o in bpy.data.objects if o not in before]
else:
    body_objs = [W.proxy_body()]
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=W.OUT)
gar = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
hides = set()
import json
meshes = json.load(open(os.path.join(W.REPO, "contract", "meshes.json")))["meshes"]
for o in gar:
    base = o.name.split(".")[0]
    if SHOW and base not in SHOW:
        o.hide_render = True
    else:
        hides |= set(meshes.get(base, {}).get("hides", []))
        for s in meshes.get(base, {}).get("shows", []):
            for b in body_objs:
                if b.name.startswith(s):
                    b.hide_render = False
if os.environ.get("KEEP_HAIR"):
    hides.discard("hair_full")
for b in body_objs:
    if any(b.name.startswith(h) for h in hides):
        b.hide_render = True
    if b.type == "MESH" and b.name.startswith("fit_body") and SHOW:
        pass

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "OBJECT"
import random
random.seed(3)
for o in bpy.data.objects:
    if o.type == "MESH":
        o.color = (0.85, 0.65, 0.5, 1) if (o in body_objs) else (random.random()*0.6+0.2, random.random()*0.6+0.2, random.random()*0.6+0.3, 1)
sc.display.shading.show_cavity = True
sc.render.resolution_x = 700
sc.render.resolution_y = 1000
cam_d = bpy.data.cameras.new("c")
cam_d.type = "ORTHO"
cam_d.ortho_scale = float(os.environ.get("ORTHO", "1.95"))
cam = bpy.data.objects.new("c", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
cy = float(os.environ.get("CY", "0.9"))
views = {"front": (0, -4, 0), "side": (4, 0, 0), "back": (0, 4, 0), "q34": (2.8, -2.8, 0.6), "top": (0.0, -0.01, 4)}
for name, (x, y, z) in views.items():
    if os.environ.get("VIEWS") and name not in os.environ["VIEWS"].split(","):
        continue
    cam.location = Vector((x, y, cy + z))
    d = Vector((0, 0, cy)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUTDIR, f"pv_{name}.png")
    bpy.ops.render.render(write_still=True)
print("PREVIEW done", OUTDIR)
