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
REHEARSAL = opt("--rehearsal", cast=bool)
PARTIAL = opt("--allow-partial", cast=bool)  # preview: avatar without wardrobe   # neutral bright preview for checking geometry

# Stage Ready look: (colour, roughness, metallic, pattern mask)
WORN = {
    "top_shirt": (0xF4F3EE, 0.8, 0.0, None),          # white Oxford
    "outer_overshirt": (0xCDBA9A, 0.85, 0.0, None),   # beige linen, open
    "bottom_wide": (0x9FB7CC, 0.85, 0.0, "denim"),    # light-wash baggy jeans
    "shoe_sneaker": (0xF4F4F2, 0.5, 0.0, None),
    "head_cap": (0xC62828, 0.7, 0.0, None),           # red cap
    "eye_round": (0xC9A55A, 0.3, 1.0, None),          # gold hex frames
    "watch_digital": (0xD4AF37, 0.3, 1.0, None),
}
TEXTURES = os.path.join(ROOT, "web", "public", "textures")


def W(x, y, z):
    return Vector((x, -z, y))


def srgb(c):
    if isinstance(c, int):
        c = ((c >> 16) & 255, (c >> 8) & 255, c & 255)

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


def colour_cones():
    """Split the cone mesh into beams and colour them: warm hero spots, blue/violet washes."""
    ob = bpy.data.objects.get("light_cones")
    if not ob:
        return
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [o for o in bpy.data.objects if o.name.startswith("light_cones")]
    palette = {
        "warm": (0.82, 0.88, 1.0),
        "blue": (0.25, 0.45, 1.0),
        "violet": (0.62, 0.3, 1.0),
    }
    mats = {}
    for k, col in palette.items():
        m = bpy.data.materials.new("hero_cone_" + k)
        cone_material(m, col, 0.12 if k == "warm" else 0.30)
        mats[k] = m
    for o in parts:
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        apex = max(ws, key=lambda v: v.z)
        x, back = apex.x, apex.y > 0.0   # blender y = -web z; upper (back) row hangs at web z -1.1
        if back:
            key = "violet" if abs(round(x)) in (2,) else "blue"
        elif abs(x) < 0.3 or abs(abs(x) - 2.92) < 0.3:
            key = "warm"
        else:
            key = "blue"
        o.data.materials.clear()
        o.data.materials.append(mats[key])
    print("HERO: cones", len(parts))


def tune_stage_materials():
    for m in bpy.data.materials:
        n = m.name
        if n.startswith("led_wall") or n == "ceiling_gobo":
            # keep the baked texture from stage.glb, just push the glow
            b = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
            if b:
                b.inputs["Emission Strength"].default_value = 0.8 if n.startswith("led_wall") else 1.3
            else:
                led_wall_material(m)
        elif n == "light_cone":
            cone_material(m, strength=0.22)
        elif n == "led_strip":
            emission_only(m, (0.12, 0.45, 1.0), 9.0)
        elif n == "center_mark":
            emission_only(m, (0.45, 0.72, 1.0), 6.0)
        elif n == "fixture_lens":
            emission_only(m, (1.0, 0.95, 0.88), 25.0)
        elif n == "fixture_lens_blue":
            emission_only(m, (0.35, 0.6, 1.0), 25.0)
        elif n == "cove_light":
            emission_only(m, (0.2, 0.6, 1.0), 6.0)


# ---------------------------------------------------------------- avatar + wardrobe
def garment_material(base):
    hexcol, rough, metal, mask = WORN[base]
    col = srgb(hexcol)
    m = bpy.data.materials.new("hero_" + base)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    try:
        b.inputs["Sheen Weight"].default_value = 0.1 if metal == 0 and base != "shoe_sneaker" else 0.0
    except Exception:
        pass
    path = os.path.join(TEXTURES, (mask or "") + ".png")
    if mask and os.path.exists(path):
        # grayscale mask tiled at 0.25 m on the garment's cube-projected UVs (1 UV unit = 1 m)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (4, 4, 4)
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = bpy.data.images.load(path)
        tx.image.colorspace_settings.name = "Non-Color"
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*[c * 0.72 for c in col], 1)
        mix.inputs["B"].default_value = (*[min(1, c * 1.15) for c in col], 1)
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
        nt.links.new(tx.outputs["Color"], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def dress_avatar():
    av = os.path.join(MODELS, "avatar.glb")
    wd = os.path.join(MODELS, "wardrobe.glb")
    have_wd = os.path.exists(wd)
    if STAGE_ONLY or not os.path.exists(av) or not (have_wd or PARTIAL):
        print("HERO: stage only")
        return False
    contract = json.load(open(CONTRACT))
    meshes = contract["meshes"]
    import_glb(av)
    if have_wd:
        import_glb(wd)
    present = {o.name.split(".")[0] for o in bpy.data.objects}
    hide = set(contract.get("defaultHidden", []))
    show = set()
    for g in WORN:
        if g in present:   # only apply hides/shows for garments that actually exist
            hide.update(meshes.get(g, {}).get("hides", []))
            show.update(meshes.get(g, {}).get("shows", []))
        else:
            print("HERO: missing garment", g)
    hide -= show
    garments = set(meshes.keys())
    for ob in bpy.data.objects:
        base = ob.name.split(".")[0]
        if base in garments and base not in WORN:
            ob.hide_render = True
        if base in hide:
            ob.hide_render = True
        if base in WORN and ob.type == "MESH":
            ob.data.materials.clear()
            ob.data.materials.append(garment_material(base))
    print("HERO: avatar dressed; hidden", sorted(hide & present))
    return True


# ---------------------------------------------------------------- scene dressing
def text_obj(name, body, width, y, strength, color=(0.94, 0.96, 1.0), spacing=1.06, bold=0.012):
    bpy.ops.object.text_add(location=(0, 0, 0))
    t = bpy.context.object
    t.name = name
    t.data.body = body
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.data.space_character = spacing
    t.data.offset = bold
    bpy.context.view_layer.update()
    s = width / max(t.dimensions.x, 1e-3)
    t.scale = (s, s, s)
    t.rotation_euler = (math.radians(90), 0, 0)
    t.location = W(0, y, -3.585)
    m = bpy.data.materials.new(name + "_mat")
    emission_only(m, color, strength)
    t.data.materials.append(m)
    return t


def wall_text():
    """What the web paints on the LED wall at the event (text only, no logos)."""
    text_obj("hero_wall_name", "HRISHIKESH HUNDEKARI", 6.6, 3.35, 6.0)
    text_obj("hero_wall_sub", "SHOP-UNI-FY  \u00b7  Small Business AI Builder Tour  \u00b7  Bengaluru",
             5.4, 2.72, 4.0, color=(0.85, 0.9, 1.0), spacing=1.0, bold=0.004)


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
    # light on the presenter is scaled down so the white tee holds detail and charcoal reads charcoal
    k = opt("--avlight", 0.22, float) if has_avatar else 1.0
    mark = find("mark_center").matrix_world.translation.copy()
    chest = mark + Vector((0, 0, 1.1))
    for key in ("L", "C", "R"):
        s = find("spot_" + key).matrix_world.translation.copy()
        energy = (2600 if key == "C" else 1800) * k
        spot("hero_spot_" + key, s, mark + Vector((0, 0, 0.9 if has_avatar else 0.0)),
             (0.86, 0.91, 1.0), energy, 17 if key == "C" else 15, blend=0.35)
    # colour washes from the upstage flown span (back light) and the side towers
    for x, col in ((-4.5, (0.18, 0.32, 1.0)), (-1.5, (0.4, 0.3, 1.0)), (1.5, (0.4, 0.3, 1.0)),
                   (4.5, (0.18, 0.32, 1.0))):
        spot("hero_back_%d" % x, W(x, 6.6, -1.1), W(x * 0.5, 0.0, 0.8), col, 2600, 30, blend=0.6)
    spot("hero_side_L", W(-5.2, 3.5, 1.0), W(0, 1.0, 0.0), (0.35, 0.3, 1.0), 900 * k, 25, blend=0.6)
    spot("hero_side_R", W(5.2, 3.5, 1.0), W(0, 1.0, 0.0), (0.85, 0.25, 0.9), 900 * k, 25, blend=0.6)
    # soft front key so the face reads (from the front-of-house position)
    area("hero_key", W(-2.5, 4.5, 9.0), chest, (0.92, 0.94, 1.0), 2500 * k if has_avatar else 200, 2.5)
    if has_avatar:
        # front-of-house follow spot on the presenter, slightly off axis
        spot("hero_follow", W(1.8, 6.5, 15.0), mark + Vector((0, 0, 1.15)), (0.95, 0.96, 1.0),
             40000 * k, 6.5, blend=0.6, radius=0.3)
        # tight soft face light so the face reads against the bright wall
        head = mark + Vector((0, 0, 1.62))
        spot("hero_face", W(0.5, 1.9, 5.5), head, (1.0, 0.9, 0.8), opt("--face", 900, float), 4.0, blend=0.9, radius=0.4)
        # cool rim from upstage high
        spot("hero_rim", W(0.0, 6.5, -2.6), mark + Vector((0, 0, 1.4)), (0.55, 0.7, 1.0), 5000 * k, 14, blend=0.5)
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
        pos = W(0.0, 0.95, 6.3)
        tgt = W(0.0, 1.85, -2.0)
        cam_data.lens = 30
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
        sc.view_settings.view_transform = opt("--view", "Standard")
        sc.view_settings.look = opt("--look", "None")
        print("HERO: look", sc.view_settings.look)
    except Exception:
        pass
    sc.view_settings.exposure = opt("--exposure", -0.4, float)


def bloom():
    """Compositor bloom so LED strips, text and lenses glow (Blender 5 node-group compositor)."""
    try:
        sc = bpy.context.scene
        ng = bpy.data.node_groups.new("hero_comp", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        gl = ng.nodes.new("CompositorNodeGlare")
        out = ng.nodes.new("NodeGroupOutput")
        gl.inputs["Type"].default_value = "Bloom"
        gl.inputs["Quality"].default_value = "High"
        gl.inputs["Threshold"].default_value = 0.9
        gl.inputs["Strength"].default_value = 0.55
        gl.inputs["Size"].default_value = 0.6
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        last = gl.outputs["Image"]
        try:   # soft vignette: ellipse mask (0.55 outside), blurred, multiplied in
            el = ng.nodes.new("CompositorNodeEllipseMask")
            el.inputs["Mask"].default_value = 0.55
            el.inputs["Value"].default_value = 1.0
            el.inputs["Size"].default_value = (0.95, 0.9)
            bl = ng.nodes.new("CompositorNodeBlur")
            px = 320 * RES / 100
            bl.inputs["Size"].default_value = (px, px)
            mx = ng.nodes.new("ShaderNodeMix")
            mx.data_type = "RGBA"
            mx.blend_type = "MULTIPLY"
            mx.inputs[0].default_value = 1.0
            ng.links.new(el.outputs["Mask"], bl.inputs["Image"])
            ng.links.new(last, mx.inputs[6])
            ng.links.new(bl.outputs["Image"], mx.inputs[7])
            last = mx.outputs[2]
        except Exception as e:
            print("HERO: vignette skipped", e)
        ng.links.new(last, out.inputs[0])
        sc.compositing_node_group = ng
        sc.render.use_compositing = True
        print("HERO: bloom on")
    except Exception as e:
        print("HERO: bloom skipped", e)


def main():
    reset()
    import_glb(os.path.join(MODELS, "stage.glb"))
    tune_stage_materials()
    colour_cones()
    for name in ("turntable",):
        if bpy.data.objects.get(name):
            bpy.data.objects[name].hide_render = True
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
    if not opt("--no-bloom", cast=bool):
        bloom()
    bpy.context.scene.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    print("HERO: wrote", OUT)


if __name__ == "__main__":
    main()
