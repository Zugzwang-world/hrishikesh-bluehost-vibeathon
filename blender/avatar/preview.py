"""Quick Workbench preview renders of avatar.glb (front, 3/4, side, head close-up).

    /opt/homebrew/bin/blender -b --python blender/avatar/preview.py -- OUTDIR [hide1,hide2]
"""
import bpy
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GLB = os.path.join(ROOT, "web", "public", "models", "avatar.glb")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else "/tmp"
HIDE = set(args[1].split(",")) if len(args) > 1 else {"hair_capped"}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in bpy.context.scene.objects:
    if o.name.split(".")[0] in HIDE:
        o.hide_render = True

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_cavity = False
sc.render.resolution_x = 700
sc.render.resolution_y = 1000
sc.render.film_transparent = False
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam


def shoot(name, az_deg, target, dist, lens=50, elev=0.0):
    # glTF frame: target (x, y, z); camera on a circle around Y. Blender = (x, -z, y)
    az = math.radians(az_deg)
    tx, ty, tz = target
    cx = tx + dist * math.sin(az)
    cz = tz + dist * math.cos(az)
    cy = ty + elev
    cam.location = (cx, -cz, cy)
    d = Vector((tx, -tz, ty)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)


shoot("front", 0, (0, 0.9, 0), 4.2)
shoot("threeq", 35, (0, 0.9, 0), 4.2)
shoot("side", 90, (0, 0.9, 0), 4.2)
shoot("back", 180, (0, 0.9, 0), 4.2)
sc.render.resolution_x = 800
sc.render.resolution_y = 800
shoot("head_threeq", 35, (0, 1.6, 0), 1.1)
shoot("head_front", 0, (0, 1.6, 0), 1.1)
shoot("head_side", 90, (0, 1.6, 0), 1.1)
