"""Eevee product shots for every catalog SKU, one Blender process.

  /opt/homebrew/bin/blender -b --python blender/render/render_products.py -- [options]

Options (after the lone --):
  --glb PATH        wardrobe GLB (default web/public/models/wardrobe.glb)
  --only SKU,SKU    render only these SKUs
  --merchant SLUG   render only this merchant's SKUs
  --samples N       Eevee samples (default 20)
  --out DIR         PNG output dir (default blender/render/out)
  --res WxH         default 800x1000

Renders PNGs into --out; then run:  uv run --with pillow python blender/render/convert_renders.py
(converts to web/public/products/SKU.webp and records the SKUs in blender/render/rendered.json).

Each garment (node = the product's mesh name) is shown alone (the avatar body is invisible), three-quarter view,
on a merchant brand-colour backdrop with a soft gradient and soft studio light. Material from the catalog:
colour, roughness, metalness, pattern mask from web/public/textures (0.25 m per tile, 1 m = 4 repeats) and the
print texture for printText. Lane E owns this script.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(bpy.data.filepath).resolve().parents[0] if False else Path(__file__).resolve().parents[2]
PUB = ROOT / "web" / "public"
TEX = PUB / "textures"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) else default
    return default


GLB = Path(opt("--glb", str(PUB / "models" / "wardrobe.glb")))
ONLY = set(opt("--only", "").split(",")) - {""}
MERCHANT = opt("--merchant")
SAMPLES = int(opt("--samples", "20"))
OUT = Path(opt("--out", str(ROOT / "blender" / "render" / "out")))
RES = [int(v) for v in opt("--res", "800x1000").split("x")]
OUT.mkdir(parents=True, exist_ok=True)

catalog = json.loads((PUB / "catalog" / "catalog.json").read_text())
merchants = {m["slug"]: m for m in catalog["merchants"]}
products = [p for p in catalog["products"]
            if (not ONLY or p["sku"] in ONLY) and (not MERCHANT or p["merchant"] == MERCHANT)]


def srgb2lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexlin(h, a=1.0):
    h = h.lstrip("#")
    return tuple(srgb2lin(int(h[i:i + 2], 16)) for i in (0, 2, 4)) + (a,)


def mixc(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3)) + (1.0,)


# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.film_transparent = False
try:
    scene.view_settings.view_transform = "Standard"
except TypeError:
    pass
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
try:
    scene.eevee.taa_render_samples = SAMPLES
    scene.eevee.taa_samples = SAMPLES
except Exception:
    pass
for attr, val in (("use_gtao", True), ("use_soft_shadows", True), ("use_raytracing", False),
                  ("use_shadows", True), ("gtao_distance", 0.4)):
    if hasattr(scene.eevee, attr):
        try:
            setattr(scene.eevee, attr, val)
        except Exception:
            pass

if not GLB.exists():
    print(f"[render_products] {GLB} not found")
    sys.exit(1)
bpy.ops.import_scene.gltf(filepath=str(GLB))
all_objs = list(bpy.context.scene.objects)
mesh_objs = [o for o in all_objs if o.type == "MESH"]
print(f"[render_products] imported {len(all_objs)} objects, {len(mesh_objs)} meshes from {GLB.name}")


def descendants(o):
    for c in o.children:
        yield c
        yield from descendants(c)


def garment_objects(meshname):
    """Mesh objects that belong to the glTF node `meshname` (the node itself and its mesh children)."""
    roots = [o for o in all_objs if o.name == meshname or o.name.startswith(meshname + ".")]
    roots = [o for o in roots if o.name == meshname] or roots
    found = []
    for r in roots:
        if r.type == "MESH":
            found.append(r)
        for c in descendants(r):
            if c.type == "MESH":
                found.append(c)
    return found


for o in all_objs:
    if o.type == "MESH":
        o.hide_render = True
        o.hide_viewport = True
        if hasattr(o, "visible_shadow"):
            pass

# ---------------------------------------------------------------- camera, lights
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 70
cam_data.sensor_width = 36
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = size
    ld.energy = energy
    ld.color = color
    lo = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(lo)
    lo.location = loc
    return lo, target


light_rig = []  # (obj, offset, size scale)


def build_world(brand, accent):
    """Backdrop = screen-space brand gradient for camera rays; studio softbox environment for light and reflections."""
    w = bpy.data.worlds.new("w")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    mixsh = nt.nodes.new("ShaderNodeMixShader")
    lp = nt.nodes.new("ShaderNodeLightPath")
    # backdrop gradient (window space)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[0].color = hexlin(brand, 1)  # placeholder, set per product
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    # radial spotlight in window space
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = (0.5, 0.62, 0)
    nt.links.new(tc.outputs["Window"], sub.inputs[0])
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(sub.outputs[0], ln.inputs[0])
    sp = nt.nodes.new("ShaderNodeMapRange")
    sp.inputs["From Min"].default_value = 0.0
    sp.inputs["From Max"].default_value = 0.85
    sp.inputs["To Min"].default_value = 1.0
    sp.inputs["To Max"].default_value = 0.0
    sp.clamp = True
    nt.links.new(ln.outputs["Value"], sp.inputs["Value"])
    spot_col = nt.nodes.new("ShaderNodeMath")
    spot_col.operation = "MULTIPLY_ADD"
    spot_col.inputs[1].default_value = 1.05
    spot_col.inputs[2].default_value = 1.0
    nt.links.new(sp.outputs["Result"], spot_col.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        nt.links.new(spot_col.outputs[0], comb.inputs[k])
    addc = nt.nodes.new("ShaderNodeMixRGB")
    addc.blend_type = "MULTIPLY"  # brightens the brand tone without washing out its hue
    addc.inputs["Fac"].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], addc.inputs["Color1"])
    nt.links.new(comb.outputs["Color"], addc.inputs["Color2"])
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(addc.outputs["Color"], bg_cam.inputs["Color"])
    bg_cam.inputs["Strength"].default_value = 1.0
    # studio environment: soft overhead box + warm kicker, dim elsewhere
    tc2 = nt.nodes.new("ShaderNodeTexCoord")
    sep2 = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc2.outputs["Generated"], sep2.inputs[0])
    ramp2 = nt.nodes.new("ShaderNodeValToRGB")
    ramp2.color_ramp.elements[0].position = 0.35
    ramp2.color_ramp.elements[0].color = (0.18, 0.18, 0.2, 1)
    ramp2.color_ramp.elements[1].position = 0.9
    ramp2.color_ramp.elements[1].color = (1.5, 1.5, 1.55, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.3
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep2.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp2.inputs["Fac"])
    # tint env a little with brand colour so garments pick up a tasteful bounce
    tint = nt.nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MIX"
    tint.inputs["Fac"].default_value = 0.22
    nt.links.new(ramp2.outputs["Color"], tint.inputs["Color1"])
    tint.inputs["Color2"].default_value = hexlin(brand, 1)
    bg_env = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(tint.outputs["Color"], bg_env.inputs["Color"])
    bg_env.inputs["Strength"].default_value = 0.4
    nt.links.new(lp.outputs["Is Camera Ray"], mixsh.inputs["Fac"])
    nt.links.new(bg_env.outputs[0], mixsh.inputs[1])
    nt.links.new(bg_cam.outputs[0], mixsh.inputs[2])
    nt.links.new(mixsh.outputs[0], out.inputs["Surface"])
    return dict(ramp=ramp, tint=tint)


world_nodes = build_world("#444444", "#ffffff")
key = area("key", (0, 0, 0), None, (2.4, 2.4), 260, (1.0, 0.97, 0.92))
fill = area("fill", (0, 0, 0), None, (3.0, 3.0), 90, (0.92, 0.95, 1.0))
rim = area("rim", (0, 0, 0), None, (1.2, 2.2), 160, (1, 1, 1))
light_rig = [key, fill, rim]
KEY_W, FILL_W, RIM_W = 70.0, 22.0, 35.0  # watts at 2.5 m; scaled with distance squared per product


def point_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- materials
_img = {}


def image(name):
    if name not in _img:
        im = bpy.data.images.load(str(TEX / f"{name}.png"))
        im.colorspace_settings.name = "Non-Color" if not name.startswith("print-") else "sRGB"
        if name.startswith("print-"):
            im.alpha_mode = "STRAIGHT"
        _img[name] = im
    return _img[name]


def make_material(p, objs, bbox):
    mat = p["material"]
    m = bpy.data.materials.new(p["sku"])
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = float(mat.get("roughness", 0.85))
    bsdf.inputs["Metallic"].default_value = float(mat.get("metalness", 0.0))
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.35 if mat.get("metalness", 0) < 0.5 else 0.5
    base = hexlin(mat["color"])
    pcol = hexlin(mat.get("patternColor") or mat["color"])
    bsdf.inputs["Base Color"].default_value = base
    colour_out = None
    pat = mat.get("pattern", "solid")
    has_uv = all(len(o.data.uv_layers) > 0 for o in objs)

    # position in world space (metres)
    geo = nt.nodes.new("ShaderNodeNewGeometry")

    def tex_node(name, scale_per_m=4.0, bump=False):
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = image(name)
        tn.interpolation = "Smart"
        tn.extension = "REPEAT"
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale_per_m,) * 3
        if has_uv:
            uv = nt.nodes.new("ShaderNodeUVMap")
            uv.uv_map = objs[0].data.uv_layers[0].name
            nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
        else:
            tn.projection = "BOX"
            tn.projection_blend = 0.25
            nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tn.inputs["Vector"])
        return tn

    mask_val = None
    if pat in ("stripe", "check", "denim", "melange", "corduroy"):
        tn = tex_node(pat)
        mixn = nt.nodes.new("ShaderNodeMix")
        mixn.data_type = "RGBA"
        mixn.inputs["A"].default_value = base
        mixn.inputs["B"].default_value = pcol
        nt.links.new(tn.outputs["Color"], mixn.inputs["Factor"])
        colour_out = mixn.outputs["Result"]
        mask_val = tn.outputs["Color"]
    else:
        # solid cloth gets a whisper of heather so it never reads as a flat fill
        if mat.get("metalness", 0) < 0.5 and mat.get("roughness", 0.85) >= 0.5:
            tn = tex_node("melange")
            mixn = nt.nodes.new("ShaderNodeMix")
            mixn.data_type = "RGBA"
            mixn.inputs["A"].default_value = mixc(base[:3], (1, 1, 1), 0.0)
            mixn.inputs["A"].default_value = tuple(min(1.0, c * 1.035) for c in base[:3]) + (1.0,)
            mixn.inputs["B"].default_value = tuple(c * 0.965 for c in base[:3]) + (1.0,)
            nt.links.new(tn.outputs["Color"], mixn.inputs["Factor"])
            colour_out = mixn.outputs["Result"]
            mask_val = tn.outputs["Color"]
    # relief for woven surfaces
    if mask_val is not None and pat in ("corduroy", "denim", "check", "stripe"):
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = {"corduroy": 0.9, "denim": 0.35, "check": 0.18, "stripe": 0.2}[pat]
        bn.inputs["Distance"].default_value = 0.002
        nt.links.new(mask_val, bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])

    # print: a flat decal projected from the front, placed on the chest (tops) or the crown front (caps)
    if pat == "print" and mat.get("printText"):
        slug = "blr" if mat["printText"].upper() == "BLR" else "ship-it"
        (x0, y0, z0), (x1, y1, z1) = bbox
        cx, cz = (x0 + x1) / 2, None
        h = z1 - z0
        w = x1 - x0
        if p["slot"] == "headwear":
            cz, width = z0 + 0.62 * h, min(0.075, 0.6 * w)
        else:
            cz, width = z0 + 0.64 * h, min(0.26, 0.5 * w)
        hgt = width / 2.0
        # world position: (x, y, z); decal uses x and z (front is -Y in Blender)
        sepx = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sepx.inputs[0])
        com = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(sepx.outputs["X"], com.inputs["X"])
        nt.links.new(sepx.outputs["Z"], com.inputs["Y"])
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (0.5 - cx / width, 0.5 - cz / hgt, 0)
        mp.inputs["Scale"].default_value = (1.0 / width, 1.0 / hgt, 1.0)
        nt.links.new(com.outputs["Vector"], mp.inputs["Vector"])
        pr = nt.nodes.new("ShaderNodeTexImage")
        pr.image = image(f"print-{slug}")
        pr.extension = "CLIP"
        pr.interpolation = "Cubic"
        nt.links.new(mp.outputs["Vector"], pr.inputs["Vector"])
        # front-facing only (normal points toward -Y)
        ny = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], ny.inputs[0])
        neg = nt.nodes.new("ShaderNodeMath")
        neg.operation = "MULTIPLY"
        neg.inputs[1].default_value = -1.0
        nt.links.new(ny.outputs["Y"], neg.inputs[0])
        front = nt.nodes.new("ShaderNodeMath")
        front.operation = "GREATER_THAN"
        front.inputs[1].default_value = 0.2
        nt.links.new(neg.outputs[0], front.inputs[0])
        amul = nt.nodes.new("ShaderNodeMath")
        amul.operation = "MULTIPLY"
        nt.links.new(pr.outputs["Alpha"], amul.inputs[0])
        nt.links.new(front.outputs[0], amul.inputs[1])
        pmix = nt.nodes.new("ShaderNodeMix")
        pmix.data_type = "RGBA"
        if colour_out is not None:
            nt.links.new(colour_out, pmix.inputs["A"])
        else:
            pmix.inputs["A"].default_value = base
        pmix.inputs["B"].default_value = pcol
        nt.links.new(amul.outputs[0], pmix.inputs["Factor"])
        colour_out = pmix.outputs["Result"]
    if colour_out is not None:
        nt.links.new(colour_out, bsdf.inputs["Base Color"])
    return m


# ---------------------------------------------------------------- framing
def world_bbox(objs):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for corner in o.bound_box:
            v = o.matrix_world @ Vector(corner)
            for i in range(3):
                mn[i] = min(mn[i], v[i])
                mx[i] = max(mx[i], v[i])
    return (tuple(mn), tuple(mx))


def frame(objs, p):
    (x0, y0, z0), (x1, y1, z1) = world_bbox(objs)
    centre = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    corners = [Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    low = p["slot"] in ("footwear", "headwear", "eyewear", "watch", "neckwear")
    yaw = math.radians(-34 if p["slot"] != "watch" else -28)  # camera swings toward +X from the front (-Y)
    elev = math.radians(20 if low else 9)
    d = Vector((math.sin(-yaw) * math.cos(elev), -math.cos(yaw) * math.cos(elev), math.sin(elev)))
    dist = 2.0
    margin = 0.90  # garment fills this fraction of the frame
    lo_d, hi_d = 0.05, 20.0
    for _ in range(26):
        dist = (lo_d + hi_d) / 2
        cam.location = centre + d * dist
        point_at(cam, centre)
        bpy.context.view_layer.update()
        xs, ys = [], []
        for c in corners:
            ndc = world_to_camera_view(scene, cam, c)
            xs.append(ndc.x)
            ys.append(ndc.y)
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        if span_x > margin or span_y > margin * 0.92:
            lo_d = dist
        else:
            hi_d = dist
    dist = hi_d
    cam.location = centre + d * dist
    point_at(cam, centre)
    # nudge: centre the projected bbox in frame
    bpy.context.view_layer.update()
    xs, ys = [], []
    for c in corners:
        ndc = world_to_camera_view(scene, cam, c)
        xs.append(ndc.x)
        ys.append(ndc.y)
    cam_data.shift_x = -((max(xs) + min(xs)) / 2 - 0.5) * (cam_data.sensor_width / cam_data.lens) * (RES[0] / max(RES)) * 1.0
    cam_data.shift_y = -((max(ys) + min(ys)) / 2 - 0.5) * (cam_data.sensor_width / cam_data.lens) * (RES[1] / max(RES)) * 1.0
    size = max(x1 - x0, z1 - z0, 0.05)
    # lights relative to the garment
    placements = {
        "key": (centre + Vector((-1.1, -1.5, 1.0)) * (0.6 + size), 4.0 + 18 * size * size),
        "fill": (centre + Vector((1.6, -1.2, 0.2)) * (0.6 + size), 2.5 + 8 * size * size),
        "rim": (centre + Vector((0.9, 1.6, 0.9)) * (0.6 + size), 3.0 + 10 * size * size),
    }
    for lo, (loc, scale) in zip(light_rig, placements.values()):
        lo[0].location = loc
        point_at(lo[0], centre)
        lo[0].data.size = lo[0].data.size_y = max(0.4, size * 2.2)
    # dark garments get more light, and a stronger rim, so they separate from a dark backdrop
    c = hexlin(p["material"]["color"])
    glum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    dark = max(0.0, min(1.0, 1.0 - glum / 0.18))
    boost = 1.0 + 0.9 * dark
    for lo, base_w, extra in ((key, KEY_W, 1.0), (fill, FILL_W, 1.0), (rim, RIM_W, 1.0 + 0.8 * dark)):
        dd = (lo[0].location - centre).length
        lo[0].data.energy = base_w * (dd / 2.5) ** 2 * boost * extra
    return centre, size


# ---------------------------------------------------------------- render loop
done, skipped = [], []
for i, p in enumerate(products):
    objs = garment_objects(p["mesh"])
    if not objs:
        skipped.append(p["sku"])
        print(f"[render_products] {p['sku']}: mesh {p['mesh']} not in {GLB.name}, keeping placeholder")
        continue
    mer = merchants[p["merchant"]]
    # backdrop colours
    bgc = mer["brandColor"]
    top = mixc(hexlin(bgc)[:3], (1, 1, 1), 0.03)
    bot = mixc(hexlin(bgc)[:3], (0, 0, 0), 0.62)
    r = world_nodes["ramp"].color_ramp
    r.elements[0].color = bot  # bottom of frame
    r.elements[1].color = top  # top of frame
    world_nodes["tint"].inputs["Color2"].default_value = hexlin(bgc)
    for o in objs:
        o.hide_render = False
        o.hide_viewport = False
    bbox = world_bbox(objs)
    mat = make_material(p, objs, bbox)
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)
        for poly in o.data.polygons:
            poly.use_smooth = True
    frame(objs, p)
    scene.render.filepath = str(OUT / f"{p['sku']}.png")
    bpy.ops.render.render(write_still=True)
    done.append(p["sku"])
    print(f"[render_products] {i + 1}/{len(products)} {p['sku']} -> {scene.render.filepath}")
    for o in objs:
        o.hide_render = True
        o.hide_viewport = True

(OUT / "last_run.json").write_text(json.dumps({"rendered": done, "skipped": skipped}))
print(f"[render_products] done: {len(done)} rendered, {len(skipped)} skipped (no mesh)")
