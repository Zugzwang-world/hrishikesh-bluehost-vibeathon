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

# Dress the portrait in a simple crew-neck tee made here from the body's own region cuts
# (torso + upper arms, offset outward), so the portrait never depends on another lane's asset.
import bmesh  # noqa: E402

# Today's outfit from main's wardrobe.glb (read-only), colours from the catalog items:
# KT-002 black poplin shirt, KT-006 beige linen overshirt, SW-001 light-wash baggy jeans,
# KK-001 white sneakers, LL-006 gold hex frames, SH-001 gold digital watch.
OUTFIT = {
    "top_shirt": ((0x12, 0x12, 0x12), 0.75, 0.0),
    "outer_overshirt": ((0xCD, 0xBA, 0x9A), 0.85, 0.0),
    "bottom_wide": ((0x9F, 0xB7, 0xCC), 0.8, 0.0),
    "shoe_sneaker": ((0xF4, 0xF4, 0xF2), 0.6, 0.0),
    "eye_round": ((0xC9, 0xA5, 0x5A), 0.28, 1.0),
    "watch_digital": ((0xD4, 0xAF, 0x37), 0.3, 1.0),
}
WARDROBE = os.path.join(ROOT, "web", "public", "models", "wardrobe.glb")
MODE = os.environ.get("PERSONA_TOP", "outfit")


def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


if MODE == "outfit" and os.path.exists(WARDROBE):
    import json
    contract = json.load(open(os.path.join(ROOT, "contract", "meshes.json")))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=WARDROBE)
    hide = set()
    for o in set(bpy.data.objects) - before:
        base = o.name.split(".")[0]
        if o.type != "MESH":
            continue
        if base not in OUTFIT:
            bpy.data.objects.remove(o)
            continue
        col, rough, metal = OUTFIT[base]
        m = bpy.data.materials.new("persona_" + base)
        m.use_nodes = True
        b_ = m.node_tree.nodes.get("Principled BSDF")
        b_.inputs["Base Color"].default_value = tuple(lin(c) for c in col) + (1.0,)
        b_.inputs["Roughness"].default_value = rough
        b_.inputs["Metallic"].default_value = metal
        o.data.materials.clear()
        o.data.materials.append(m)
        hide |= set(contract["meshes"][base]["hides"])
    for o in list(bpy.data.objects):
        if o.name.split(".")[0] in hide:
            bpy.data.objects.remove(o)
elif MODE == "tee":
    parts = [o for o in bpy.data.objects
             if o.name.split(".")[0] in ("body_neck", "body_torso", "body_upperarm_L", "body_upperarm_R",
                                         "body_hips")]
    bm = bmesh.new()
    for o in parts:
        me = o.data.copy()
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=6e-4)
    # drop the lower hips so the hem sits at ~0.93 (Blender Z is up)
    kill = [f for f in bm.faces if f.calc_center_median().z < 0.93]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    # planar crew neckline
    def near_neck(co):
        return math.hypot(co.x, -co.y + 0.01) < 0.16

    nf = [f for f in bm.faces if near_neck(f.calc_center_median())]
    ne = list({e for f in nf for e in f.edges})
    nv = list({v for f in nf for v in f.verts})
    bmesh.ops.bisect_plane(bm, geom=nv + ne + nf, dist=1e-6, plane_co=(0, 0, 1.455), plane_no=(0, 0, 1))
    kill = [f for f in bm.faces if near_neck(f.calc_center_median()) and f.calc_center_median().z > 1.455]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.010
    tee_me = bpy.data.meshes.new("persona_tee")
    bm.to_mesh(tee_me)
    bm.free()
    tee_me.shade_smooth()
    tee = bpy.data.objects.new("persona_tee", tee_me)
    sc0 = bpy.context.scene
    sc0.collection.objects.link(tee)
    sm = tee.modifiers.new("smooth", "SMOOTH")
    sm.factor, sm.iterations = 0.5, 6
    so = tee.modifiers.new("solid", "SOLIDIFY")
    so.thickness, so.offset = 0.004, 1.0
    tee_mat = bpy.data.materials.new("persona_top")
    tb_ = tee_mat.node_tree.nodes.get("Principled BSDF") if tee_mat.node_tree else None
    if tb_ is None:
        tee_mat.use_nodes = True
        tb_ = tee_mat.node_tree.nodes.get("Principled BSDF")
    tb_.inputs["Base Color"].default_value = (0.022, 0.024, 0.030, 1.0)
    tb_.inputs["Roughness"].default_value = 0.9
    tee_me.materials.append(tee_mat)

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


LIGHT = os.environ.get("PERSONA_LIGHT", "studio")
face = B(0, 1.50, 0.02)
if LIGHT == "stage":
    # on-stage check: dark house, white follow spot, cobalt and violet washes
    bg.inputs["Strength"].default_value = 0.02
    area("spot", B(-0.6, 3.2, 2.2), face, 0.6, 260, (1.0, 0.97, 0.93))
    area("cobalt", B(-1.8, 1.8, 0.6), face, 1.5, 220, (0x2D / 255, 0x4B / 255, 1.0))
    area("violet", B(1.6, 2.2, -1.3), face, 1.2, 260, (0x7A / 255, 0x5C / 255, 1.0))
    area("cobalt_rim", B(-0.9, 2.0, -1.6), face, 1.0, 160, (0x2D / 255, 0x4B / 255, 1.0))
else:
    area("key", B(-1.1, 2.3, 1.5), face, 2.2, 80, (1.0, 0.96, 0.92))
    area("fill", B(1.6, 1.6, 1.2), face, 3.0, 24, (0.92, 0.95, 1.0))
    area("rim", B(0.9, 2.2, -1.4), face, 1.2, 70, (1.0, 0.98, 0.95))
    area("rim2", B(-1.0, 1.9, -1.2), face, 1.2, 35, (0.95, 0.97, 1.0))
    # a whisper of the stage colours on the edges
    area("cobalt_kiss", B(-1.4, 1.7, -0.9), face, 1.0, 25, (0x2D / 255, 0x4B / 255, 1.0))
    area("violet_kiss", B(1.3, 1.9, -1.0), face, 1.0, 25, (0x7A / 255, 0x5C / 255, 1.0))

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 85
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
az = math.radians(float(os.environ.get("PERSONA_AZ", "26")))
# waist-up framing so the outfit (overshirt, shirt, frames, watch) reads
target = Vector((0.04, float(os.environ.get("PERSONA_TY", "1.38")), 0.0))
dist = float(os.environ.get("PERSONA_DIST", "2.45"))
cam.location = B(target.x + dist * math.sin(az), target.y + 0.12, target.z + dist * math.cos(az))
tb = B(target.x, target.y, target.z)
cam.rotation_euler = (tb - cam.location).to_track_quat("-Z", "Y").to_euler()

sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
