"""Build the keynote stage and export web/public/models/stage.glb.

Run headless from the repo root:
    /opt/homebrew/bin/blender -b --python blender/stage/build_stage.py

Everything is generated here in code. Re-runnable: starts from an empty scene.

Coordinates: helpers take WEB coordinates (metres, Y up, audience toward +Z)
and convert to Blender (Z up): web (x, y, z) -> blender (x, -z, y). The glTF
exporter converts back to Y up. Riser top is web y = 0.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
sys.path.insert(0, HERE)
import stage_textures as stx  # noqa: E402
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "web", "public", "models", "stage.glb")

random.seed(7)


# ---------------------------------------------------------------- helpers
def W(x, y, z):
    """Web coordinate -> Blender vector."""
    return Vector((x, -z, y))


def WS(sx, sy, sz):
    """Web size -> Blender size."""
    return Vector((sx, sz, sy))


def rot_y_web(deg):
    """Rotation about the web vertical axis (blender Z)."""
    return Matrix.Rotation(math.radians(deg), 4, "Z")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.objects, bpy.data.images):
        for item in list(coll):
            coll.remove(item)


# ---------------------------------------------------------------- materials
MATS = {}


def mat(name, color=(0.02, 0.02, 0.02), rough=0.8, metal=0.0, emit=None,
        strength=1.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            m.blend_method = "BLEND"
        m.use_backface_culling = False
    m.diffuse_color = (*color, alpha)
    MATS[name] = m
    return m


def deck_texture():
    """512 px tile = 2 x 2 m of stage deck: two 2 x 1 m platforms, fine seams, faint scuffs."""
    import numpy as np
    n = 512
    rng = np.random.default_rng(3)
    base = 34.0 / 255.0
    img = np.full((n, n), base, dtype=np.float32)
    # low-frequency mottling + fine grain
    lo = rng.normal(0, 1, (16, 16)).astype(np.float32)
    lo = np.kron(lo, np.ones((n // 16, n // 16), dtype=np.float32))
    k = np.ones(31, dtype=np.float32) / 31
    lo = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 0, lo)
    lo = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, lo)
    img += lo * (3.0 / 255.0) + rng.normal(0, 1.2 / 255.0, (n, n)).astype(np.float32)
    seam = 18.0 / 255.0
    for t in (0, 1):                          # platform edges: tile border + mid line (2 x 1 m panels)
        img[t, :] = seam
        img[:, t] = seam
        img[n // 2 + t - 1, :] = seam
    img = np.clip(img, 0, 1)
    rgba = np.ones((n, n, 4), dtype=np.float32)
    rgba[..., 0] = img
    rgba[..., 1] = img
    rgba[..., 2] = np.clip(img * 1.04, 0, 1)
    im = bpy.data.images.new("stage_deck_tex", n, n, alpha=False)
    im.pixels.foreach_set(rgba.ravel())
    im.update()
    im.pack()
    return im


def make_image(name, arr):
    """arr: float sRGB (H, W, 3), row 0 = top. Packed into the .blend, exported as JPEG."""
    import numpy as np
    h, w, _ = arr.shape
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = arr[::-1]          # blender rows start at the bottom
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.pixels.foreach_set(rgba.ravel())
    im.update()
    im.pack()
    return im


def textured(name, arr, rough=0.8, emissive=False, strength=1.0, base_dark=None):
    """Material whose base colour (and optionally emission) is a generated image."""
    m = mat(name, (1, 1, 1), rough=rough)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = make_image(name + "_tex", arr)
    if base_dark is not None:
        b.inputs["Base Color"].default_value = (*base_dark, 1)
    else:
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    if emissive:
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = strength
    return m


def build_materials():
    m = mat("stage_deck", (1.0, 1.0, 1.0), rough=0.72)
    try:
        nt = m.node_tree
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = deck_texture()
        nt.links.new(tex.outputs["Color"], nt.nodes.get("Principled BSDF").inputs["Base Color"])
    except Exception as e:   # fall back to a flat colour
        print("DECK TEXTURE FAILED", e)
        m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.016, 0.016, 0.018, 1)
    mat("stage_deck_edge", (0.012, 0.012, 0.014), rough=0.72)
    mat("stage_fascia", (0.006, 0.006, 0.007), rough=0.45)
    mat("floor_house", (0.016, 0.016, 0.018), rough=0.92)
    mat("drape", (0.004, 0.004, 0.005), rough=1.0)
    mat("bezel", (0.012, 0.012, 0.013), rough=0.4, metal=0.5)
    textured("led_wall", stx.led_wall_tex(), rough=0.3, emissive=True, strength=1.0)
    textured("led_wall_side", stx.side_panel_tex(), rough=0.3, emissive=True, strength=1.0)
    textured("ceiling_gobo", stx.gobo_tex(), rough=0.95, emissive=True, strength=1.0, base_dark=(0.004, 0.006, 0.02))
    textured("qr_card", stx.qr_tex(), rough=0.6)
    mat("ceiling_beam", (0.008, 0.01, 0.025), rough=0.8)
    mat("cove_light", (0.05, 0.2, 0.5), rough=0.5, emit=(0.15, 0.55, 1.0), strength=2.0)
    mat("fixture_lens_blue", (0.3, 0.4, 0.8), rough=0.1, emit=(0.35, 0.6, 1.0), strength=4.0)
    mat("led_strip", (0.02, 0.06, 0.15), rough=0.4, emit=(0.10, 0.42, 1.0), strength=3.0)
    mat("center_mark", (0.05, 0.10, 0.20), rough=0.4, emit=(0.35, 0.65, 1.0), strength=2.5)
    mat("turntable", (0.022, 0.022, 0.025), rough=0.35, metal=0.2)
    mat("turntable_ring", (0.10, 0.12, 0.16), rough=0.4, emit=(0.30, 0.45, 0.75), strength=0.8)
    mat("truss", (0.07, 0.07, 0.075), rough=0.42, metal=0.85)
    mat("fixture_metal", (0.025, 0.025, 0.028), rough=0.35, metal=0.9)
    mat("fixture_lens", (0.6, 0.6, 0.6), rough=0.1, emit=(1.0, 0.95, 0.88), strength=4.0)
    mat("light_cone", (1.0, 0.97, 0.92), rough=1.0, emit=(1.0, 0.97, 0.92), strength=1.0, alpha=0.12)
    mat("podium", (0.018, 0.018, 0.02), rough=0.5, metal=0.1)
    mat("podium_top", (0.05, 0.035, 0.025), rough=0.55)
    mat("mic_metal", (0.3, 0.3, 0.32), rough=0.25, metal=1.0)
    mat("monitor", (0.012, 0.012, 0.013), rough=0.7)
    mat("monitor_grille", (0.03, 0.03, 0.032), rough=0.9, metal=0.4)
    mat("seat", (0.012, 0.02, 0.09), rough=0.95)          # navy banquet chairs
    mat("audience", (0.006, 0.006, 0.008), rough=0.9)
    mat("house_wall", (0.014, 0.014, 0.017), rough=0.95)
    mat("exit_sign", (0.05, 0.4, 0.12), rough=0.5, emit=(0.15, 1.0, 0.35), strength=2.0)
    mat("aisle_light", (0.3, 0.25, 0.18), rough=0.5, emit=(1.0, 0.72, 0.42), strength=1.5)


# ---------------------------------------------------------------- mesh builder
class Part:
    """Accumulates geometry for one object, one bmesh, several materials."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.mats = []

    def mi(self, material_name):
        m = MATS[material_name]
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _tag(self, geom, material_name, smooth=False):
        idx = self.mi(material_name)
        for f in [g for g in geom if isinstance(g, bmesh.types.BMFace)]:
            f.material_index = idx
            f.smooth = smooth

    def _new_geom(self, before):
        return [f for f in self.bm.faces if f.index == -1 or f not in before]

    def box(self, center, size, material, rot=None):
        """center/size in web coords. rot: 4x4 blender matrix around center."""
        m = Matrix.Translation(W(*center))
        if rot is not None:
            m = m @ rot
        m = m @ Matrix.Diagonal((*WS(*size), 1.0))
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._tag(self._faces_of(res["verts"]), material)
        return res

    def box_minmax(self, lo, hi, material):
        c = [(a + b) / 2 for a, b in zip(lo, hi)]
        s = [abs(b - a) for a, b in zip(lo, hi)]
        return self.box(c, s, material)

    def _faces_of(self, verts):
        fs = set()
        for v in verts:
            fs.update(v.link_faces)
        return list(fs)

    def cyl(self, a, b, r, material, segs=8, caps=True, smooth=False, r2=None):
        """Cylinder between web points a and b."""
        A, B = W(*a), W(*b)
        d = B - A
        L = d.length
        q = d.normalized().to_track_quat("Z", "Y")
        m = Matrix.Translation((A + B) / 2) @ q.to_matrix().to_4x4()
        res = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=segs,
                                    radius1=r, radius2=r if r2 is None else r2,
                                    depth=L, matrix=m)
        self._tag(self._faces_of(res["verts"]), material, smooth)
        return res

    def disc(self, center, r_in, r_out, material, segs=48, lift=0.0):
        """Flat ring (or disc if r_in == 0) on a horizontal plane, web coords."""
        cx, cy, cz = center
        cy += lift
        idx = self.mi(material)
        outer, inner = [], []
        for i in range(segs):
            t = 2 * math.pi * i / segs
            outer.append(self.bm.verts.new(W(cx + r_out * math.cos(t), cy, cz + r_out * math.sin(t))))
            if r_in > 0:
                inner.append(self.bm.verts.new(W(cx + r_in * math.cos(t), cy, cz + r_in * math.sin(t))))
        if r_in > 0:
            for i in range(segs):
                j = (i + 1) % segs
                f = self.bm.faces.new((outer[i], inner[i], inner[j], outer[j]))
                f.material_index = idx
        else:
            f = self.bm.faces.new(outer[::-1])
            f.material_index = idx

    def quad(self, corners, material, uvs=None):
        """corners: 4 web points CCW as seen from the front."""
        vs = [self.bm.verts.new(W(*c)) for c in corners]
        f = self.bm.faces.new(vs)
        f.material_index = self.mi(material)
        if uvs:
            for loop, uv in zip(f.loops, uvs):
                loop[self.uv].uv = uv
        return f

    def open_cone(self, apex, target, r0, r1, material, segs=20, length=None):
        """Open cone (no caps) from apex toward target. UV v: 0 at apex, 1 at far end."""
        A, T = W(*apex), W(*target)
        d = (T - A)
        L = length if length else d.length
        d.normalize()
        q = d.to_track_quat("Z", "Y").to_matrix()
        ex, ey = q.col[0], q.col[1]
        rings = []
        steps = 4
        for k in range(steps + 1):
            t = k / steps
            r = r0 + (r1 - r0) * t
            c = A + d * (L * t)
            ring = [self.bm.verts.new(c + (ex * math.cos(2 * math.pi * i / segs) +
                                           ey * math.sin(2 * math.pi * i / segs)) * r)
                    for i in range(segs)]
            rings.append((ring, t))
        idx = self.mi(material)
        for k in range(steps):
            (ra, ta), (rb, tb) = rings[k], rings[k + 1]
            for i in range(segs):
                j = (i + 1) % segs
                f = self.bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
                f.material_index = idx
                f.smooth = True
                for loop, uv in zip(f.loops, ((i / segs, ta), ((i + 1) / segs, ta),
                                              ((i + 1) / segs, tb), (i / segs, tb))):
                    loop[self.uv].uv = uv

    def vcyl(self, center, height, rx, rz, material, rot=None, top=1.0, segs=8):
        """Vertical elliptical (optionally tapered) open tube, web coords."""
        m = Matrix.Translation(W(*center))
        if rot is not None:
            m = m @ rot
        m = m @ Matrix.Diagonal((rx, rz, 1.0, 1.0))
        res = bmesh.ops.create_cone(self.bm, cap_ends=False, cap_tris=False, segments=segs,
                                    radius1=1.0, radius2=top, depth=height, matrix=m)
        self._tag(self._faces_of(res["verts"]), material, smooth=True)
        return res

    def sphere(self, center, radii, material, segs=8, rings=5, rot=None):
        m = Matrix.Translation(W(*center))
        if rot is not None:
            m = m @ rot
        m = m @ Matrix.Diagonal((*WS(*radii), 1.0))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings,
                                        radius=1.0, matrix=m)
        self._tag(self._faces_of(res["verts"]), material, smooth=True)
        return res

    def finish(self, collection=None):
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        return ob


def empty(name, pos, size=0.25, kind="PLAIN_AXES"):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = kind
    ob.empty_display_size = size
    ob.location = W(*pos)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- layout
RISER_X = 6.0          # half width (12 m riser)
RISER_Z0, RISER_Z1 = -4.0, 2.6
RISER_H = 0.6
FLOOR_Y = -RISER_H
WALL_Z = -3.6
WALL_W, WALL_H, WALL_Y0 = 8.64, 3.6, 0.5   # 2.4 : 1 main screen
CEIL_Y = 7.4
ROW0_Z = 6.0           # first audience row (behind cam_fit at z 5.6 so the fitting shot stays clean)
TRUSS_X = 5.2
TRUSS_Z = 1.3          # front (lower) truss line
TRUSS_TOP = 6.2        # top of the front span
BACK_Z, BACK_Y = -1.1, 6.75   # back (upper) truss line, centre height
TRUSS_W = 0.3


def build_riser():
    p = Part("riser")
    # deck slab just under y = 0, then the textured deck surface quad at y = 0 (UV: 1 unit = 2 m)
    p.box_minmax((-RISER_X, -0.04, RISER_Z0), (RISER_X, -0.002, RISER_Z1), "stage_deck_edge")
    x0, x1, z0, z1 = -RISER_X, RISER_X, RISER_Z0, RISER_Z1
    p.quad([(x0, 0.0, z1), (x1, 0.0, z1), (x1, 0.0, z0), (x0, 0.0, z0)], "stage_deck",
           uvs=[(x0 / 2, -z1 / 2), (x1 / 2, -z1 / 2), (x1 / 2, -z0 / 2), (x0 / 2, -z0 / 2)])
    # body / fascia
    p.box_minmax((-RISER_X + 0.02, FLOOR_Y, RISER_Z0 + 0.02), (RISER_X - 0.02, -0.04, RISER_Z1 - 0.02), "stage_fascia")
    # deck board seams: subtle raised lines would cost tris; instead a thin lip on the front edge
    p.box_minmax((-RISER_X, -0.10, RISER_Z1 - 0.01), (RISER_X, -0.04, RISER_Z1 + 0.02), "stage_fascia")
    p.finish()

    s = Part("led_edge_strip")
    s.box_minmax((-RISER_X, -0.085, RISER_Z1 + 0.012), (RISER_X, -0.055, RISER_Z1 + 0.03), "led_strip")
    # toe strip along the bottom of the fascia
    s.box_minmax((-RISER_X, FLOOR_Y + 0.02, RISER_Z1 - 0.005), (RISER_X, FLOOR_Y + 0.04, RISER_Z1 + 0.005), "led_strip")
    s.finish()

    # stairs at both front corners
    st = Part("stairs")
    for sx in (-1, 1):
        x0 = sx * (RISER_X - 0.75)
        for k in range(2):
            top = -(k + 1) * 0.2
            z0 = RISER_Z1 + k * 0.32
            st.box_minmax((x0 - 0.5, FLOOR_Y, z0), (x0 + 0.5, top, z0 + 0.32), "stage_fascia")
    st.finish()

    # house floor and black drape
    f = Part("house_floor")
    f.box_minmax((-16, FLOOR_Y - 0.05, -9), (16, FLOOR_Y, 18), "floor_house")
    f.finish()
    d = Part("drape")
    d.quad([(-12, FLOOR_Y, -5.2), (12, FLOOR_Y, -5.2), (12, CEIL_Y, -5.2), (-12, CEIL_Y, -5.2)], "drape")
    # side masking legs (facing inward, angled)
    d.quad([(-8.5, FLOOR_Y, 2.0), (-8.5, FLOOR_Y, -5.2), (-8.5, CEIL_Y, -5.2), (-8.5, CEIL_Y, 2.0)], "drape")
    d.quad([(8.5, FLOOR_Y, -5.2), (8.5, FLOOR_Y, 2.0), (8.5, CEIL_Y, 2.0), (8.5, CEIL_Y, -5.2)], "drape")
    d.finish()


def build_marks():
    c = Part("center_mark")
    c.disc((0, 0, 0), 0.30, 0.36, "center_mark", segs=64, lift=0.003)
    c.disc((0, 0, 0), 0.0, 0.045, "center_mark", segs=24, lift=0.003)
    # four short ticks
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        cx, cz = 0.46 * math.cos(a), 0.46 * math.sin(a)
        size = (0.12, 0.004, 0.02) if ang in (0, 180) else (0.02, 0.004, 0.12)
        c.box((cx, 0.002, cz), size, "center_mark")
    c.finish()

    t = Part("turntable")
    t.disc((0, 0, 1.6), 0.0, 0.62, "turntable", segs=64, lift=0.0015)
    t.disc((0, 0, 1.6), 0.60, 0.635, "turntable_ring", segs=64, lift=0.002)
    t.finish()


def build_led_wall():
    x0, x1 = -WALL_W / 2, WALL_W / 2
    y0, y1 = WALL_Y0, WALL_Y0 + WALL_H
    z = WALL_Z
    scr = Part("led_wall")
    scr.quad([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], "led_wall",
             uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    scr.finish()

    b = Part("led_wall_frame")
    t, dep = 0.06, 0.16
    zc = z - dep / 2 + 0.03
    b.box((0, y1 + t / 2, zc), (WALL_W + 2 * t, t, dep), "bezel")
    b.box((0, y0 - t / 2, zc), (WALL_W + 2 * t, t, dep), "bezel")
    b.box((x0 - t / 2, (y0 + y1) / 2, zc), (t, WALL_H, dep), "bezel")
    b.box((x1 + t / 2, (y0 + y1) / 2, zc), (t, WALL_H, dep), "bezel")
    b.box((0, (y0 + y1) / 2, z - 0.12), (WALL_W, WALL_H, 0.08), "bezel")
    b.box_minmax((x0 - 0.1, 0.0, z - 0.35), (x1 + 0.1, y0 - t, z + 0.05), "bezel")   # plinth
    for lx in (-3.6, -1.2, 1.2, 3.6):
        b.box((lx, (y0 + y1) / 2, z - 0.4), (0.08, WALL_H + 0.4, 0.08), "truss")
    b.finish()

    # narrower side LED panels, set slightly forward and turned toward the house
    sp = Part("led_side_panels")
    pw, ph, py0 = 2.1, 3.0, 0.55
    for sx in (-1, 1):
        th = 14.0 * -sx
        a = math.radians(th)
        c = Vector((sx * (WALL_W / 2 + 0.35 + pw / 2), py0 + ph / 2, z + 0.25))
        r = Vector((math.cos(a), 0, -math.sin(a)))
        n = Vector((math.sin(a), 0, math.cos(a)))
        up = Vector((0, 1, 0))
        bl, br = c - r * pw / 2 - up * ph / 2, c + r * pw / 2 - up * ph / 2
        tr, tl = c + r * pw / 2 + up * ph / 2, c - r * pw / 2 + up * ph / 2
        sp.quad([tuple(bl), tuple(br), tuple(tr), tuple(tl)], "led_wall_side",
                uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        sp.box(tuple(c - n * 0.07), (pw + 0.1, ph + 0.1, 0.1), "bezel", rot=rot_y_web(th))
        sp.box((c.x, (py0 - 0.05) / 2, c.z - 0.07), (pw * 0.9, py0 - 0.05, 0.3), "bezel")
    sp.finish()


def build_side_screens():
    """IMAG side screens (16:9, 3.2 x 1.8 m) flown outside the truss towers, angled to the house.
    Material led_wall_side: UV 0..1 like led_wall, so the web can mirror the main wall content."""
    p = Part("led_side_screens")
    sw, sh = 3.2, 1.8
    for sx in (-1, 1):
        th = 25.0 * -sx                     # left screen turns toward +x, right toward -x
        a = math.radians(th)
        c = Vector((sx * 6.9, 3.1, 0.0))
        r = Vector((math.cos(a), 0, -math.sin(a)))
        n = Vector((math.sin(a), 0, math.cos(a)))
        up = Vector((0, 1, 0))
        bl, br = c - r * sw / 2 - up * sh / 2, c + r * sw / 2 - up * sh / 2
        tr, tl = c + r * sw / 2 + up * sh / 2, c - r * sw / 2 + up * sh / 2
        p.quad([tuple(bl), tuple(br), tuple(tr), tuple(tl)], "led_wall_side",
               uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        p.box(tuple(c - n * 0.06), (sw + 0.12, sh + 0.12, 0.1), "bezel", rot=rot_y_web(th))
        for k in (-1, 1):
            top = c + r * (k * sw * 0.4) + up * (sh / 2 + 0.06) - n * 0.06
            p.cyl(tuple(top), (top.x, 12.0, top.z), 0.008, "fixture_metal", segs=4, caps=False)
    p.finish()


def truss_run(p, a, b, w=TRUSS_W, rc=0.024, rb=0.011, pitch=0.5):
    """Box truss between web points a, b: 4 chords and zig-zag braces on 4 faces."""
    A, B = Vector(a), Vector(b)
    d = B - A
    L = d.length
    dn = d.normalized()
    up = Vector((0, 1, 0)) if abs(dn.y) < 0.9 else Vector((1, 0, 0))
    u = dn.cross(up).normalized()
    v = dn.cross(u).normalized()
    h = w / 2
    corners = [u * h + v * h, -u * h + v * h, -u * h - v * h, u * h - v * h]
    for c in corners:
        p.cyl(tuple(A + c), tuple(B + c), rc, "truss", segs=6, caps=False)
    n = max(1, int(L / pitch))
    for f in range(4):
        c0, c1 = corners[f], corners[(f + 1) % 4]
        for k in range(n):
            s0 = A + dn * (L * k / n)
            s1 = A + dn * (L * (k + 1) / n)
            if k % 2 == 0:
                p.cyl(tuple(s0 + c0), tuple(s1 + c1), rb, "truss", segs=4, caps=False)
            else:
                p.cyl(tuple(s0 + c1), tuple(s1 + c0), rb, "truss", segs=4, caps=False)


def build_truss():
    p = Part("truss")
    span = 6.6
    front_c = TRUSS_TOP - TRUSS_W / 2
    for (zc, yc) in ((TRUSS_Z, front_c), (BACK_Z, BACK_Y)):
        truss_run(p, (-span, yc, zc), (span, yc, zc))
        for cx in (-5.0, 0.0, 5.0):
            p.box((cx, yc + TRUSS_W / 2 + 0.17, zc), (0.22, 0.3, 0.22), "fixture_metal")   # chain hoist
            p.cyl((cx, yc + TRUSS_W / 2 + 0.32, zc), (cx, CEIL_Y, zc), 0.008, "fixture_metal", segs=4, caps=False)
        for ex in (-span, span):
            p.box((ex, yc, zc), (0.12, TRUSS_W + 0.04, TRUSS_W + 0.04), "truss")              # end plates
    p.finish()


def moving_head(p, mount, target, cones, cone_len=None, r1=0.75, lens="fixture_lens"):
    """Hanging moving-head: clamp, base, yoke, head aimed at target, lens and cone."""
    mx, my, mz = mount
    p.box((mx, my - 0.05, mz), (0.08, 0.1, 0.08), "fixture_metal")               # clamp
    p.box((mx, my - 0.16, mz), (0.34, 0.12, 0.28), "fixture_metal")              # base
    yoke_y = my - 0.22
    p.box((mx - 0.17, yoke_y - 0.15, mz), (0.04, 0.3, 0.12), "fixture_metal")
    p.box((mx + 0.17, yoke_y - 0.15, mz), (0.04, 0.3, 0.12), "fixture_metal")
    pivot = Vector((mx, yoke_y - 0.25, mz))
    T = Vector(target)
    d = (T - pivot).normalized()
    back = pivot - d * 0.16
    front = pivot + d * 0.16
    p.cyl(tuple(back), tuple(front), 0.13, "fixture_metal", segs=12, smooth=True, r2=0.15)
    lens0 = front
    lens1 = front + d * 0.012
    p.cyl(tuple(lens0), tuple(lens1), 0.11, lens, segs=12)
    if cones is not None:
        L = cone_len if cone_len else (T - lens1).length
        cones.open_cone(tuple(lens1), tuple(T), 0.1, r1, "light_cone", length=L)
    return tuple(lens1)


def build_fixtures():
    p = Part("fixtures")
    cones = Part("light_cones")
    spots = {}
    # front (lower) row: hero spots L / C / R plus washes, warm lenses
    hang_y = TRUSS_TOP - TRUSS_W
    spot_x = {"L": -3.0, "C": 0.0, "R": 3.0}
    wash = {-4.5: (-2.8, 0, -1.6), -1.5: (-1.2, 0, 1.2), 1.5: (1.2, 0, 1.2), 4.5: (2.8, 0, -1.6)}
    for x in (-6.0, -4.5, -3.0, -1.5, 0.0, 1.5, 3.0, 4.5, 6.0):
        key = next((k for k, v in spot_x.items() if v == x), None)
        if key:
            lens = moving_head(p, (x, hang_y, TRUSS_Z), (0, 0, 0), cones, r1=0.6)
            spots[key] = (lens, (0, 0, 0))
        elif x in wash:
            moving_head(p, (x, hang_y, TRUSS_Z), wash[x], cones, r1=0.5)
        else:
            moving_head(p, (x, hang_y, TRUSS_Z), (x * 0.6, 0, 1.5), None)
    # back (upper) row: cool lenses, beams raking onto the deck toward the front edge
    by = BACK_Y - TRUSS_W / 2
    for x in (-6.0, -4.5, -3.0, -1.5, 0.0, 1.5, 3.0, 4.5, 6.0):
        tgt = (x * 0.55, 0.0, 1.0 + abs(x) * 0.2)
        if x in (-6.0, -3.0, 0.0, 3.0, 6.0):
            moving_head(p, (x, by, BACK_Z), tgt, cones, r1=0.45, lens="fixture_lens_blue")
        else:
            moving_head(p, (x, by, BACK_Z), tgt, None, lens="fixture_lens_blue")
    p.finish()
    cones.finish()
    return spots


def build_podium():
    p = Part("podium")
    px, pz = 2.6, -0.6
    rot = rot_y_web(-14)   # turn slightly toward centre stage
    def R(lx, ly, lz):
        v = rot @ Vector((lx, -lz, ly))
        return (px + v.x, ly, pz - v.y)
    # body: tapered stack
    p.box(R(0, 0.03, 0), (0.62, 0.06, 0.48), "podium", rot=rot)
    p.box(R(0, 0.52, 0), (0.54, 0.92, 0.40), "podium", rot=rot)
    # slanted reading desk
    desk_rot = rot @ Matrix.Rotation(math.radians(-14), 4, "X")
    p.box(R(0, 1.03, -0.02), (0.64, 0.05, 0.50), "podium_top", rot=desk_rot)
    # front accent strip (led_strip so Showtime lights it)
    p.box(R(0, 0.55, 0.205), (0.04, 0.78, 0.01), "led_strip", rot=rot)
    p.box(R(0, 0.12, 0.245), (0.50, 0.015, 0.01), "led_strip", rot=rot)
    # gooseneck mic
    pts = [R(0.14, 1.06, -0.18), R(0.14, 1.18, -0.20), R(0.12, 1.28, -0.26), R(0.10, 1.33, -0.34)]
    for a, b in zip(pts, pts[1:]):
        p.cyl(a, b, 0.006, "mic_metal", segs=6, caps=False)
    head_end = R(0.09, 1.34, -0.42)
    p.cyl(pts[-1], head_end, 0.014, "audience", segs=8, smooth=True, r2=0.018)
    p.finish()


def build_monitors():
    p = Part("floor_monitors")
    for x in (-3.7, -2.2, 2.2, 3.7):
        yaw = -math.degrees(math.atan2(x, 3.0)) * 0.4
        rot = rot_y_web(yaw)
        cx, cz = x, 2.15
        # wedge cross-section in local (z, y): back tall at +z (downstage), front low at -z
        prof = [(-0.24, 0.0), (0.24, 0.0), (0.24, 0.36), (0.02, 0.36), (-0.24, 0.12)]
        hw = 0.32
        vs_l, vs_r = [], []
        for lz, ly in prof:
            for side, store in ((-hw, vs_l), (hw, vs_r)):
                v = rot @ Vector((side, -lz, 0))
                store.append(p.bm.verts.new(W(cx + v.x, ly, cz - v.y)))
        im, ig = p.mi("monitor"), p.mi("monitor_grille")
        f = p.bm.faces.new(vs_l[::-1]); f.material_index = im
        f = p.bm.faces.new(vs_r); f.material_index = im
        n = len(prof)
        for i in range(n):
            j = (i + 1) % n
            f = p.bm.faces.new((vs_l[i], vs_l[j], vs_r[j], vs_r[i]))
            f.material_index = ig if i == 4 else im
    bmesh.ops.recalc_face_normals(p.bm, faces=p.bm.faces[:])
    p.finish()


def build_audience():
    seats = Part("audience_seats")
    people = Part("audience_people")
    row_z = [ROW0_Z + i * 0.92 for i in range(9)]
    for ri, z0 in enumerate(row_z):
        floor = FLOOR_Y
        xs = [0.95 + 0.58 * k for k in range(11)]
        for sx in (-1, 1):
            for x in xs:
                x = sx * x
                z = z0 + 0.010 * x * x          # gentle arc toward the stage
                yaw = math.degrees(math.atan2(x, z + 2.0)) * 0.9
                rot = rot_y_web(yaw)
                def R(lx, ly, lz, rot=rot, x=x, z=z):
                    v = rot @ Vector((lx, -lz, ly))
                    return (x + v.x, floor + ly, z - v.y)
                seats.box(R(0, 0.20, 0.02), (0.08, 0.40, 0.08), "seat", rot=rot)
                seats.box(R(0, 0.44, 0.0), (0.50, 0.08, 0.46), "seat", rot=rot)
                seats.box(R(0, 0.76, 0.24), (0.50, 0.64, 0.08), "seat", rot=rot)
                bl_, br_ = R(0.07, 0.78, 0.285), R(-0.07, 0.78, 0.285)
                tr_, tl_ = R(-0.07, 0.92, 0.285), R(0.07, 0.92, 0.285)
                seats.quad([bl_, br_, tr_, tl_], "qr_card", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
                if random.random() < 0.78:
                    s = random.uniform(0.92, 1.08)
                    lean = random.uniform(-0.03, 0.03)
                    # torso (tapered elliptical tube), shoulders, upper arms, neck, head
                    people.vcyl(R(lean, 0.76 * s, 0.07), 0.48 * s, 0.165 * s, 0.11, "audience", rot=rot, top=1.15, segs=8)
                    people.sphere(R(lean, 1.0 * s, 0.07), (0.215 * s, 0.075, 0.125), "audience", segs=10, rings=5, rot=rot)
                    for side in (-1, 1):
                        people.cyl(R(lean + side * 0.2 * s, 0.98 * s, 0.07), R(lean + side * 0.22 * s, 0.68 * s, 0.0),
                                   0.05 * s, "audience", segs=5, caps=False)
                    people.cyl(R(lean, 1.0 * s, 0.07), R(lean, 1.15 * s, 0.075), 0.05, "audience", segs=6, caps=False)
                    hr = 0.105 * s
                    people.sphere(R(lean + random.uniform(-0.02, 0.02), 1.26 * s, 0.06), (hr * 0.86, hr * 1.12, hr * 0.98),
                                  "audience", segs=10, rings=7, rot=rot)
    seats.finish()
    people.finish()


def build_house():
    """Side and back walls of the hall, pilasters, exit signs, aisle and wall lights."""
    h = Part("house_walls")
    top = CEIL_Y
    # side walls (inner faces) and back wall
    h.quad([(-12, FLOOR_Y, 18), (-12, FLOOR_Y, 2.0), (-12, top, 2.0), (-12, top, 18)], "house_wall")
    h.quad([(12, FLOOR_Y, 2.0), (12, FLOOR_Y, 18), (12, top, 18), (12, top, 2.0)], "house_wall")
    h.quad([(12, FLOOR_Y, 18), (-12, FLOOR_Y, 18), (-12, top, 18), (12, top, 18)], "house_wall")
    # proscenium returns joining the side masking to the walls
    h.quad([(-12, FLOOR_Y, 2.0), (-8.5, FLOOR_Y, 2.0), (-8.5, top, 2.0), (-12, top, 2.0)], "house_wall")
    h.quad([(8.5, FLOOR_Y, 2.0), (12, FLOOR_Y, 2.0), (12, top, 2.0), (8.5, top, 2.0)], "house_wall")
    for sx in (-1, 1):
        for z in (5.0, 8.5, 12.0, 15.5):
            h.box((sx * 11.85, (FLOOR_Y + top) / 2, z), (0.3, top - FLOOR_Y, 0.5), "house_wall")
    h.finish()

    l = Part("house_lights")
    # exit signs on the back wall and on the side walls near the stage
    for x in (-7.0, 7.0):
        l.box((x, 2.6, 17.94), (0.42, 0.18, 0.06), "exit_sign")
    for sx in (-1, 1):
        l.box((sx * 11.95, 2.6, 3.2), (0.06, 0.18, 0.42), "exit_sign")
        # warm wall sconces between pilasters
        for z in (6.75, 10.25, 13.75):
            l.box((sx * 11.93, 2.2, z), (0.05, 0.9, 0.08), "aisle_light")
    # aisle step lights along the centre aisle
    for i in range(9):
        z = ROW0_Z + i * 0.92 + 0.3
        for sx in (-1, 1):
            l.box((sx * 0.62, FLOOR_Y + 0.12, z), (0.04, 0.05, 0.1), "aisle_light")
    l.finish()


def build_ceiling():
    c = Part("ceiling")
    x0, x1, z0, z1, y = -12, 12, -5.2, 18, CEIL_Y
    t = 7.0   # metres per gobo tile
    c.quad([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], "ceiling_gobo",
           uvs=[(x0 / t, z0 / t), (x1 / t, z0 / t), (x1 / t, z1 / t), (x0 / t, z1 / t)])
    for bz in (-3.0, 1.5, 6.0, 10.5, 15.0):
        c.box((0, y - 0.18, bz), (24, 0.36, 0.45), "ceiling_beam")
        c.box((0, y - 0.37, bz), (24, 0.025, 0.06), "cove_light")
    c.finish()


def build_empties(spots):
    empty("mark_center", (0, 0, 0), 0.4, "CIRCLE")
    empty("avatar_fit", (0, 0, 1.6), 0.4, "CIRCLE")
    cams = {
        "cam_fit": ((0, 1.15, 5.6), (0, 0.95, 1.6)),
        "cam_wide": ((0, 3.2, 14.0), (0, 1.4, -1.0)),
        "cam_audience": ((0.7, 1.8, -1.6), (0, 0.6, 8.0)),
        "cam_close": ((0.35, 1.5, 1.7), (0, 1.45, 0.0)),
    }
    for name, (pos, tgt) in cams.items():
        empty(name, pos, 0.3, "CUBE")
        empty(name + "_target", tgt, 0.15, "SPHERE")
    for key, (lens, tgt) in spots.items():
        empty("spot_" + key, lens, 0.3, "SINGLE_ARROW")
        empty("spot_target_" + key, tgt, 0.15, "SPHERE")


def export():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=OUT,
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        export_extras=False,
        use_selection=False,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=7,
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12,
        export_image_format="JPEG",
        export_image_quality=88,
    )
    print("EXPORTED", OUT, os.path.getsize(OUT))


def main():
    reset_scene()
    build_materials()
    build_riser()
    build_marks()
    build_led_wall()
    build_ceiling()
    build_truss()
    spots = build_fixtures()
    build_podium()
    build_monitors()
    build_audience()
    build_house()
    build_empties(spots)
    tris = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            ob.data.calc_loop_triangles()
            tris += len(ob.data.loop_triangles)
    print("TRIANGLES", tris)
    blend = os.path.join(HERE, "stage.blend")
    if os.environ.get("STAGE_SAVE_BLEND"):
        bpy.ops.wm.save_as_mainfile(filepath=blend)
    export()


if __name__ == "__main__":
    main()
