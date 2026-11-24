"""Render web/public/brand/hero.jpg: the avatar on the keynote stage, Showtime lighting.

    /opt/homebrew/bin/blender -b --python blender/stage/render_hero.py -- [options]

Options (after --):
    --stage-only        do not import avatar/wardrobe even if present
    --res PCT           resolution percentage of 1920x1080 (default 100)
    --samples N         Cycles samples (default 96)
    --cam NAME          render from a stage camera empty (cam_wide, cam_fit...) instead of the hero camera
    --out PATH          output path (default web/public/brand/hero.jpg)
    --eevee             use Eevee instead of Cycles

Imports web/public/models/stage.glb (+ avatar.glb, wardrobe.glb when present), hides the
body_* regions listed in contract/meshes.json for the worn garments, colours them, then
lights the scene in code. Everything procedural; no downloaded assets.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODELS = os.path.join(ROOT, "web", "public", "models")
CONTRACT = os.path.join(ROOT, "contract", "meshes.json")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None, cast=str):
    if name in argv:
        i = argv.index(name)
        if cast is bool:
            return True
        return cast(argv[i + 1])
    return False if cast is bool else default


STAGE_ONLY = opt("--stage-only", cast=bool)
RES = opt("--res", 100, int)
SAMPLES = opt("--samples", 96, int)
CAM = opt("--cam", None)
OUT = opt("--out", os.path.join(ROOT, "web", "public", "brand", "hero.jpg"))
EEVEE = opt("--eevee", cast=bool)
REHEARSAL = opt("--rehearsal", cast=bool)   # neutral bright preview for checking geometry

WORN = {
    "top_tee": (0xF4, 0xF2, 0xEE),
    "outer_blazer": (0x3A, 0x3B, 0x3F),
    "bottom_wide": (0x3A, 0x3A, 0x3E),
    "shoe_sneaker": (0xF5, 0xF5, 0xF2),
}


def W(x, y, z):
    return Vector((x, -z, y))


def srgb(c):
    def f(u):
        u = u / 255.0
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    return tuple(f(u) for u in c)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


# ---------------------------------------------------------------- materials
def emission_only(m, color, strength):
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return nt, em, out


def led_wall_material(m):
    """Deep blue-violet gradient with a soft glow band and fine LED rows."""
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.004, 0.012, 0.06, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.035, 0.01, 0.09, 1)
    mid = cr.elements.new(0.55)
    mid.color = (0.01, 0.06, 0.22, 1)
    nt.links.new(sep.outputs["Y"], ramp.inputs[0])
    # horizontal radial falloff toward edges
    grad = nt.nodes.new("ShaderNodeMath"); grad.operation = "SUBTRACT"
    grad.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs["X"], grad.inputs[0])
    sq = nt.nodes.new("ShaderNodeMath"); sq.operation = "MULTIPLY"
    nt.links.new(grad.outputs[0], sq.inputs[0]); nt.links.new(grad.outputs[0], sq.inputs[1])
    vig = nt.nodes.new("ShaderNodeMath"); vig.operation = "MULTIPLY_ADD"
    vig.inputs[1].default_value = -2.2
    vig.inputs[2].default_value = 1.0
    nt.links.new(sq.outputs[0], vig.inputs[0])
    # LED pixel rows (subtle)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"; wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 90.0
    nt.links.new(tc.outputs["UV"], wave.inputs["Vector"])
    rows = nt.nodes.new("ShaderNodeMapRange")
    rows.inputs["To Min"].default_value = 0.82
    rows.inputs["To Max"].default_value = 1.0
    nt.links.new(wave.outputs["Fac"], rows.inputs["Value"])
    m1 = nt.nodes.new("ShaderNodeMix"); m1.data_type = "RGBA"; m1.blend_type = "MULTIPLY"
    m1.inputs["Factor"].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], m1.inputs["A"])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    nt.links.new(vig.outputs[0], mul.inputs[0]); nt.links.new(rows.outputs["Result"], mul.inputs[1])
    for k in ("X", "Y", "Z"):
        nt.links.new(mul.outputs[0], comb.inputs[k])
    nt.links.new(comb.outputs[0], m1.inputs["B"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 3.0
    nt.links.new(m1.outputs["Result"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])


def cone_material(m, color=(1.0, 0.96, 0.9), strength=0.5):
    """Additive beam: transparent + emission fading along UV v (0 at lens)."""
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs["Y"], inv.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"
    pw.inputs[1].default_value = 1.6
    nt.links.new(inv.outputs[0], pw.inputs[0])
    # fresnel-ish: beams look denser at the silhouette
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.4
    edge = nt.nodes.new("ShaderNodeMath"); edge.operation = "MULTIPLY_ADD"
    edge.inputs[1].default_value = 0.8
    edge.inputs[2].default_value = 0.25
    nt.links.new(lw.outputs["Facing"], edge.inputs[0])
    k = nt.nodes.new("ShaderNodeMath"); k.operation = "MULTIPLY"
    nt.links.new(pw.outputs[0], k.inputs[0]); nt.links.new(edge.outputs[0], k.inputs[1])
    s = nt.nodes.new("ShaderNodeMath"); s.operation = "MULTIPLY"
    s.inputs[1].default_value = strength
    nt.links.new(k.outputs[0], s.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    nt.links.new(s.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass


def tune_stage_materials():
    for m in bpy.data.materials:
        n = m.name
        if n == "led_wall":
            led_wall_material(m)
        elif n == "light_cone":
            cone_material(m)
        elif n == "led_strip":
            emission_only(m, (0.12, 0.45, 1.0), 9.0)
        elif n == "center_mark":
            emission_only(m, (0.45, 0.72, 1.0), 6.0)
        elif n == "fixture_lens":
            emission_only(m, (1.0, 0.95, 0.88), 25.0)


# ---------------------------------------------------------------- avatar + wardrobe
def dress_avatar():
    av = os.path.join(MODELS, "avatar.glb")
    wd = os.path.join(MODELS, "wardrobe.glb")
    if STAGE_ONLY or not (os.path.exists(av) and os.path.exists(wd)):
        print("HERO: stage only")
        return False
    contract = json.load(open(CONTRACT))
    meshes = contract["meshes"]
    import_glb(av)
    import_glb(wd)
    hide = set(contract.get("defaultHidden", []))
    for g in WORN:
        hide.update(meshes.get(g, {}).get("hides", []))
    garments = set(meshes.keys())
    for ob in bpy.data.objects:
        base = ob.name.split(".")[0]
        if base in garments and base not in WORN:
            ob.hide_render = True
        if base in hide:
            ob.hide_render = True
        if base in WORN and ob.type == "MESH":
            col = srgb(WORN[base])
            m = bpy.data.materials.new("hero_" + base)
            m.use_nodes = True
            b = m.node_tree.nodes.get("Principled BSDF")
            b.inputs["Base Color"].default_value = (*col, 1)
            rough = {"top_tee": 0.85, "outer_blazer": 0.7, "bottom_wide": 0.75, "shoe_sneaker": 0.5}[base]
            b.inputs["Roughness"].default_value = rough
            try:
                b.inputs["Sheen Weight"].default_value = 0.3 if base != "shoe_sneaker" else 0.0
            except Exception:
                pass
            ob.data.materials.clear()
            ob.data.materials.append(m)
    print("HERO: avatar dressed")
    return True


# ---------------------------------------------------------------- scene dressing
def wall_text():
    bpy.ops.object.text_add(location=(0, 0, 0))
    t = bpy.context.object
    t.name = "hero_wall_text"
    t.data.body = "HRISHIKESH"
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.data.space_character = 1.12
    t.data.offset = 0.012
    t.data.extrude = 0.0
    bpy.context.view_layer.update()
    width = t.dimensions.x
    s = 5.0 / max(width, 1e-3)
    t.scale = (s, s, s)
    t.rotation_euler = (math.radians(90), 0, 0)
    t.location = W(0, 3.05, -3.585)
    m = bpy.data.materials.new("hero_text")
    emission_only(m, (0.92, 0.96, 1.0), 6.0)
    t.data.materials.append(m)
    # thin accent line under the name
    bpy.ops.mesh.primitive_plane_add(size=1, location=W(0, 2.42, -3.586))
    ln = bpy.context.object
    ln.name = "hero_wall_line"
    ln.rotation_euler = (math.radians(90), 0, 0)
    ln.scale = (1.4, 0.022, 1)
    m2 = bpy.data.materials.new("hero_line")
    emission_only(m2, (0.15, 0.5, 1.0), 8.0)
    ln.data.materials.append(m2)


def find(name):
    return bpy.data.objects.get(name)


def spot(name, pos, target, color, energy, angle_deg, blend=0.25, radius=0.08):
    ld = bpy.data.lights.new(name, "SPOT")
    ld.energy = energy
    ld.color = color
    ld.spot_size = math.radians(angle_deg)
    ld.spot_blend = blend
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = pos
    d = (target - pos).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def area(name, pos, target, color, energy, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = pos
    d = (target - pos).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def showtime_lights(has_avatar):
    mark = find("mark_center").matrix_world.translation.copy()
    chest = mark + Vector((0, 0, 1.1))
    for key in ("L", "C", "R"):
        s = find("spot_" + key).matrix_world.translation.copy()
        energy = 2600 if key == "C" else 1800
        spot("hero_spot_" + key, s, mark + Vector((0, 0, 0.9 if has_avatar else 0.0)),
             (1.0, 0.94, 0.86), energy, 17 if key == "C" else 15, blend=0.35)
    # colour washes from the upstage flown span (back light) and the side towers
    for x, col in ((-4.0, (0.25, 0.35, 1.0)), (-2.0, (0.75, 0.2, 1.0)), (0.0, (0.2, 0.45, 1.0)),
                   (2.0, (0.75, 0.2, 1.0)), (4.0, (0.25, 0.35, 1.0))):
        spot("hero_back_%d" % x, W(x, 6.6, -2.6), W(x * 0.5, 0.0, 0.8), col, 2200, 30, blend=0.6)
    spot("hero_side_L", W(-5.2, 3.5, 1.0), W(0, 1.0, 0.0), (0.35, 0.3, 1.0), 900, 25, blend=0.6)
    spot("hero_side_R", W(5.2, 3.5, 1.0), W(0, 1.0, 0.0), (0.85, 0.25, 0.9), 900, 25, blend=0.6)
    # soft front key so the face reads (from the front-of-house position)
    area("hero_key", W(-2.5, 4.5, 9.0), chest, (1.0, 0.93, 0.85), 900 if has_avatar else 200, 2.5)
    # faint house spill on the audience
    area("hero_house", W(0, 7.0, 9.0), W(0, -0.6, 8.0), (0.3, 0.4, 0.9), 120, 10.0)


def camera():
    cam_data = bpy.data.cameras.new("hero_cam")
    cam = bpy.data.objects.new("hero_cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    if CAM and find(CAM) and find(CAM + "_target"):
        pos = find(CAM).matrix_world.translation.copy()
        tgt = find(CAM + "_target").matrix_world.translation.copy()
        cam_data.lens = 30
    else:
        pos = W(0.0, 1.05, 7.6)
        tgt = W(0.0, 1.95, -2.0)
        cam_data.lens = 31
    cam.location = pos
    cam.rotation_euler = (tgt - pos).normalized().to_track_quat("-Z", "Y").to_euler()
    cam_data.clip_end = 200
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = (pos - find("mark_center").matrix_world.translation).length
    cam_data.dof.aperture_fstop = 4.0
    bpy.context.scene.camera = cam


def world():
    w = bpy.data.worlds.new("hero_world")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.0015, 0.002, 0.004, 1)
    bg.inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = w


def render_settings():
    sc = bpy.context.scene
    r = sc.render
    r.resolution_x, r.resolution_y = 1920, 1080
    r.resolution_percentage = RES
    r.image_settings.file_format = "JPEG"
    r.image_settings.quality = 90
    if EEVEE:
        r.engine = "BLENDER_EEVEE"
    else:
        r.engine = "CYCLES"
        c = sc.cycles
        c.samples = SAMPLES
        c.use_denoising = True
        c.max_bounces = 6
        c.transparent_max_bounces = 16
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            c.device = "GPU"
            print("HERO: GPU", [d.name for d in prefs.devices])
        except Exception as e:
            print("HERO: CPU", e)
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0


def main():
    reset()
    import_glb(os.path.join(MODELS, "stage.glb"))
    tune_stage_materials()
    has_avatar = dress_avatar()
    wall_text()
    if REHEARSAL:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(50), 0, math.radians(20))
        bpy.context.scene.collection.objects.link(sun)
    else:
        showtime_lights(has_avatar)
    camera()
    world()
    if REHEARSAL:
        bpy.context.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.25, 0.25, 0.27, 1)
    render_settings()
    bpy.context.scene.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    print("HERO: wrote", OUT)


if __name__ == "__main__":
    main()
