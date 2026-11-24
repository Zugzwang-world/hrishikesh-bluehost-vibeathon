"""Render web/public/brand/persona.png (1200 x 1500, transparent) from avatar.glb.

    /opt/homebrew/bin/blender -b --python blender/avatar/render_persona.py [-- OUT.png]
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
OUT = args[0] if args else os.path.join(ROOT, "web", "public", "brand", "persona.png")


def B(x, y, z):
    """glTF (Y up, +Z front) to Blender (Z up, -Y front)."""
    return Vector((x, -z, y))


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in list(bpy.context.scene.objects):
    if o.name.startswith("hair_capped"):
        bpy.data.objects.remove(o)

# Dress the portrait in Lane B's tee when wardrobe.glb is present (read-only use of their asset).
WARDROBE = os.path.join(ROOT, "web", "public", "models", "wardrobe.glb")
TOP = os.environ.get("PERSONA_TOP", "top_tee")
if TOP and os.path.exists(WARDROBE):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=WARDROBE)
    tee_mat = bpy.data.materials.new("persona_top")
    tee_mat.use_nodes = True
    tb_ = tee_mat.node_tree.nodes.get("Principled BSDF")
    tb_.inputs["Base Color"].default_value = (0.024, 0.026, 0.032, 1.0)
    tb_.inputs["Roughness"].default_value = 0.85
    for o in set(bpy.data.objects) - before:
        if o.type != "MESH":
            continue
        if o.name.split(".")[0] != TOP:
            bpy.data.objects.remove(o)
        else:
            o.data.materials.clear()
            o.data.materials.append(tee_mat)
    for o in list(bpy.data.objects):
        if o.name.split(".")[0] in ("body_torso", "body_upperarm_L", "body_upperarm_R"):
            bpy.data.objects.remove(o)

sc = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
print("engine", sc.render.engine)
if sc.render.engine == "CYCLES":
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
else:
    try:
        sc.eevee.taa_render_samples = 128
        sc.eevee.use_shadows = True
    except AttributeError:
        pass
    for attr, val in (("use_raytracing", True), ("use_gtao", True)):
        if hasattr(sc.eevee, attr):
            setattr(sc.eevee, attr, val)

sc.render.resolution_x = 1200
sc.render.resolution_y = 1500
sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "8"
sc.render.image_settings.compression = 100
try:
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
except TypeError:
    pass

# soften the vinyl a touch: slight sheen-free coat for a premium toy read
for m in bpy.data.materials:
    if not m.node_tree:
        continue
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf and m.name.startswith("hair"):
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    if bsdf and m.name.startswith("skin"):
        bsdf.inputs["Coat Weight"].default_value = 0.12
        bsdf.inputs["Coat Roughness"].default_value = 0.35
        if "Subsurface Weight" in bsdf.inputs:
            bsdf.inputs["Subsurface Weight"].default_value = 0.0

world = bpy.data.worlds.new("studio")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.42, 0.42, 0.45, 1.0)
bg.inputs["Strength"].default_value = 0.18
sc.world = world


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "DISK"
    ld.size = size
    ld.energy = energy
    ld.color = color
    lo = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(lo)
    lo.location = loc
    lo.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    return lo


face = B(0, 1.58, 0.02)
area("key", B(-1.1, 2.3, 1.5), face, 2.2, 75, (1.0, 0.96, 0.92))
area("fill", B(1.6, 1.6, 1.2), face, 3.0, 22, (0.92, 0.95, 1.0))
area("rim", B(0.9, 2.2, -1.4), face, 1.2, 70, (1.0, 0.98, 0.95))
area("rim2", B(-1.0, 1.9, -1.2), face, 1.2, 35, (0.95, 0.97, 1.0))

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 85
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
az = math.radians(28)
target = Vector((0.0, 1.545, 0.0))
dist = 1.5
cam.location = B(target.x + dist * math.sin(az), 1.62, target.z + dist * math.cos(az))
tb = B(target.x, target.y, target.z)
cam.rotation_euler = (tb - cam.location).to_track_quat("-Z", "Y").to_euler()

sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
