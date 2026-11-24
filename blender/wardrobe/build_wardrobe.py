"""Lane B Wardrobe: builds every garment/accessory in code and exports web/public/models/wardrobe.glb.

Run headless from the repo root:
    /opt/homebrew/bin/blender -b --python blender/wardrobe/build_wardrobe.py

Frame: metres, Y up (glTF), figure faces +Z, feet on y=0, figure's LEFT is +X.
Inside Blender we work in Blender's Z-up frame and convert: blender (x, y, z) = gltf (x, -z, y).
All helpers below take glTF-frame coordinates (G(x, y, z)) so the numbers match the shared landmarks.

If web/public/models/avatar.glb exists, its body_* meshes are used as the fit target
(garments are pushed outside the body by their offset); otherwise a proxy body from the landmarks is used.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "web", "public", "models", "wardrobe.glb")
AVATAR = os.environ.get("AVATAR_GLB", os.path.join(REPO, "web", "public", "models", "avatar.glb"))
ONLY = [s for s in os.environ.get("ONLY", "").split(",") if s]


def G(x, y, z):
    """glTF-frame point -> Blender vector."""
    return Vector((x, -z, y))


def gy(v):  # glTF y of a blender vector
    return v.z


# ---------------------------------------------------------------- scene utils
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def new_obj(name, me):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bm_to_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return new_obj(name, me)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    me.name = ob.name


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def delete(ob):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me and me.users == 0:
        bpy.data.meshes.remove(me)


def join(name, obs):
    bm = bmesh.new()
    for ob in obs:
        tmp = bmesh.new()
        tmp.from_mesh(ob.data)
        tmp.transform(ob.matrix_world)
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for ob in obs:
        delete(ob)
    return bm_to_obj(name, bm)


# ---------------------------------------------------------------- primitives
def superellipse(t, a, b, n):
    c, s = math.cos(t), math.sin(t)
    x = a * math.copysign(abs(c) ** (2.0 / n), c)
    y = b * math.copysign(abs(s) ** (2.0 / n), s)
    return x, y


def loft(bm, rings, seg=40, cap0=True, cap1=True):
    """rings: list of (center, u, v, a, b, n) in blender space. Returns ring vert lists."""
    vrings = []
    for (c, u, v, a, b, n) in rings:
        ring = []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            x, y = superellipse(t, a, b, n)
            ring.append(bm.verts.new(c + u * x + v * y))
        vrings.append(ring)
    for r0, r1 in zip(vrings[:-1], vrings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if cap0:
        bm.faces.new(list(reversed(vrings[0])))
    if cap1:
        bm.faces.new(vrings[-1])
    return vrings


def hring(x, y, z, a, b, n=2.0):
    """Horizontal ring (glTF): half-width a along X, half-depth b along Z."""
    return (G(x, y, z), Vector((1, 0, 0)), Vector((0, -1, 0)), a, b, n)


def arm_frame(side):
    """side +1 = figure's left (+X). Returns shoulder joint, axis dir, two perpendiculars (blender)."""
    s = G(0.19 * side, 1.42, 0.0)
    ang = math.radians(30)
    d = G(math.sin(ang) * side, -math.cos(ang), 0.0)
    w = G(0, 0, 1)  # front/back
    v = d.cross(w).normalized()
    return s, d, w, v


def arm_point(side, t):
    s, d, _, _ = arm_frame(side)
    return s + d * t


def tube_along(bm, p0, d, w, v, stations, seg=32, n=2.0, cap=True):
    """stations: list of (t, ra, rb): ring at p0 + d*t, radius ra along w, rb along v."""
    rings = [(p0 + d * t, w, v, ra, rb, n) for (t, ra, rb) in stations]
    return loft(bm, rings, seg, cap, cap)


def sphere(bm, c, rx, ry, rz, seg=24, rings=12):
    """Ellipsoid in glTF radii (rx along X, ry along Y-up, rz along Z-front)."""
    m = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for vert in m["verts"]:
        co = vert.co.copy()
        vert.co = c + Vector((co.x * rx, co.y * rz, co.z * ry))


def capsule(bm, a, b, r, seg=20):
    d = (b - a)
    L = d.length
    d.normalize()
    w = d.cross(Vector((0, 0, 1)))
    if w.length < 1e-4:
        w = d.cross(Vector((1, 0, 0)))
    w.normalize()
    v = d.cross(w).normalized()
    st = []
    k = 6
    for i in range(k + 1):  # hemisphere a
        ang = -math.pi / 2 + (math.pi / 2) * i / k
        st.append((r * math.sin(ang) + 0.0, r * math.cos(ang) + 1e-4))
    for i in range(k + 1):
        ang = (math.pi / 2) * i / k
        st.append((L + r * math.sin(ang), r * math.cos(ang) + 1e-4))
    tube_along(bm, a, d, w, v, [(t, rr, rr) for (t, rr) in st], seg=seg)


# ---------------------------------------------------------------- body (proxy or real)
def proxy_body():
    bm = bmesh.new()
    # torso + hips
    loft(bm, [hring(0, 0.80, 0, 0.17, 0.115, 2.4), hring(0, 0.92, 0, 0.18, 0.12, 2.4),
              hring(0, 1.05, 0, 0.15, 0.105, 2.4), hring(0, 1.25, 0, 0.18, 0.12, 2.4),
              hring(0, 1.38, 0, 0.19, 0.11, 2.6), hring(0, 1.43, 0, 0.14, 0.085, 2.4),
              hring(0, 1.45, 0, 0.06, 0.06, 2.0), hring(0, 1.55, 0.0, 0.055, 0.055, 2.0)], 40)
    sphere(bm, G(0, 1.625, 0.01), 0.08, 0.125, 0.10)
    for side in (1, -1):
        s, d, w, v = arm_frame(side)
        tube_along(bm, s, d, w, v, [(-0.03, 0.045, 0.045), (0.0, 0.05, 0.05), (0.29, 0.04, 0.04),
                                    (0.55, 0.028, 0.032), (0.62, 0.02, 0.045), (0.74, 0.012, 0.035)], seg=20)
        x = 0.095 * side
        loft(bm, [hring(x, 0.86, 0.0, 0.085, 0.09), hring(0.1 * side, 0.70, 0.0, 0.075, 0.08),
                  hring(0.103 * side, 0.49, 0.0, 0.05, 0.055), hring(0.106 * side, 0.35, -0.01, 0.05, 0.055),
                  hring(0.11 * side, 0.10, 0.0, 0.035, 0.04)], 24)
    ob = bm_to_obj("fit_body", bm)
    m = ob.modifiers.new("r", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = 0.01
    apply_mods(ob)
    return ob


def real_body():
    if not os.path.exists(AVATAR):
        return None
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=AVATAR)
    except Exception as e:
        print("WARDROBE: avatar import failed", e)
        return None
    new = [o for o in bpy.data.objects if o not in before]
    bodies = [o for o in new if o.type == "MESH" and ((o.name.startswith("body_") and not o.name.startswith("body_foot"))
                                                     or o.name.startswith("hair_capped"))]
    if not bodies:
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
        return None
    copies = []
    for o in bodies:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        c = new_obj("bodypart", me)
        c.matrix_world = o.matrix_world.copy()
        copies.append(c)
    for o in new:
        if o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    ob = join("fit_body", copies)
    print("WARDROBE: using real avatar body,", len(ob.data.vertices), "verts")
    return ob


# ---------------------------------------------------------------- garment pipeline
def region_faces(bm, pred):
    faces = [f for f in bm.faces if pred(f.calc_center_median())]
    verts = {v for f in faces for v in f.verts}
    edges = {e for f in faces for e in f.edges}
    return list(verts) + list(edges) + faces


def bisect(bm, co, no, pred=None):
    """Remove geometry on the +no side of the plane, limited to faces whose centre passes pred."""
    geom = region_faces(bm, pred) if pred else bm.verts[:] + bm.edges[:] + bm.faces[:]
    if not geom:
        return
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no.normalized(), clear_outer=True)


def remove_faces(bm, pred):
    dead = [f for f in bm.faces if pred(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=dead, context="FACES")


def clean_loose(bm):
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")


def keep_largest(bm):
    """Drop small floating islands left by cuts."""
    seen = set()
    islands = []
    for f in bm.faces:
        if f in seen:
            continue
        stack = [f]
        isl = []
        seen.add(f)
        while stack:
            g = stack.pop()
            isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen:
                        seen.add(h)
                        stack.append(h)
        islands.append(isl)
    islands.sort(key=len, reverse=True)
    return islands


def drop_small_islands(bm, min_frac=0.03):
    isl = keep_largest(bm)
    if not isl:
        return
    big = len(isl[0])
    dead = [f for i in isl if len(i) < big * min_frac for f in i]
    if dead:
        bmesh.ops.delete(bm, geom=dead, context="FACES")
    clean_loose(bm)


def volume_to_shell(name, build, voxel, smooth_iter, cuts, keep_islands_frac=0.03):
    bm = bmesh.new()
    build(bm)
    ob = bm_to_obj(name, bm)
    m = ob.modifiers.new("r", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.adaptivity = 0.0
    if smooth_iter:
        s = ob.modifiers.new("s", "SMOOTH")
        s.factor = 0.9
        s.iterations = smooth_iter
    apply_mods(ob)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    cuts(bm)
    clean_loose(bm)
    drop_small_islands(bm, keep_islands_frac)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def fit_outside(ob, targets, offset=None, maxdist=0.06, ymin=None, passes=2):
    """Push garment verts outside each target by its offset. Only targets within maxdist count,
    so far-away rims/edges never drag geometry (no fins)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for t, off in targets:
        if t is None:
            continue
        me_t = t.data
        bfaces = set()
        if len(me_t.polygons) < 200000:
            import bmesh as _bm
            tb = _bm.new()
            tb.from_mesh(me_t)
            for e in tb.edges:
                if e.is_boundary:
                    for f in e.link_faces:
                        bfaces.add(f.index)
            tb.free()
        trees.append((BVHTree.FromObject(t, dg), off, bfaces))
    if not trees:
        return
    me = ob.data
    mw = ob.matrix_world
    moved = 0
    for _ in range(passes):
        for v in me.vertices:
            co = v.co.copy()
            if ymin is not None and co.z < ymin:
                continue
            for tree, off, bfaces in trees:
                loc, nrm, idx, dist = tree.find_nearest(co, maxdist)
                if loc is None or idx in bfaces:
                    continue
                d = (co - loc).dot(nrm)
                if d < off:
                    co = loc + nrm * off if d < 0 or (co - loc).length < 1e-6 else co + nrm * (off - d)
                    moved += 1
            v.co = co
    me.update()
    sm = ob.modifiers.new("relax", "SMOOTH")  # soften the push-out creases a touch
    sm.factor = 0.25
    sm.iterations = 1
    apply_mods(ob)
    print(f"WARDROBE:   fit {ob.name}: moved {moved}")


SHELLS = {}


def finish(ob, target_tris, thickness, solid_offset=1.0, sharp_deg=None):
    tris = tri_count(ob)
    if tris > target_tris:
        d = ob.modifiers.new("d", "DECIMATE")
        d.decimate_type = "COLLAPSE"
        d.ratio = target_tris / tris
        apply_mods(ob)
    shell = new_obj(ob.name + "__shell", ob.data.copy())
    shell.hide_render = True
    SHELLS[ob.name] = shell
    if thickness:
        so = ob.modifiers.new("t", "SOLIDIFY")
        so.thickness = thickness
        so.offset = solid_offset
        so.use_rim = True
        so.use_even_offset = False
        apply_mods(ob)
    tri = ob.modifiers.new("tri", "TRIANGULATE")
    apply_mods(ob)
    me = ob.data
    me.shade_smooth()
    if sharp_deg:
        bm = bmesh.new()
        bm.from_mesh(me)
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(sharp_deg):
                e.smooth = False
        bm.to_mesh(me)
        bm.free()
    cube_uv(ob)
    set_material(ob)
    print(f"WARDROBE: {ob.name}: {tri_count(ob)} tris")
    return ob


def cube_uv(ob):
    """Cube projection in glTF metres: 1 UV unit = 1 m."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            co = l.vert.co  # blender: x=gx, y=-gz, z=gy
            gx, gyy, gz = co.x, co.z, -co.y
            if ax == 0:      # facing +-X (gltf X)
                l[uv].uv = (gz * (1 if n.x < 0 else -1), gyy)
            elif ax == 2:    # facing +-Y gltf (up/down)
                l[uv].uv = (gx, gz)
            else:            # facing +-Z gltf (front/back)
                l[uv].uv = (gx * (1 if n.y < 0 else -1), gyy)
    bm.to_mesh(me)
    bm.free()


def set_material(ob):
    name = "mat_" + ob.name
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
        bsdf.inputs["Metallic"].default_value = 0.0
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ---------------------------------------------------------------- garments
def torso_rings(extra, hem=0.88, top_neck=1.56, neck_r=(0.078, 0.075), shoulder=0.0, n=2.6):
    """Shirt-like torso (glTF). extra = looseness added to the body numbers."""
    e = extra
    return [
        hring(0, hem, 0, 0.185 + e, 0.125 + e, n),
        hring(0, 1.00, 0, 0.18 + e, 0.122 + e, n),
        hring(0, 1.12, 0, 0.18 + e, 0.122 + e, n),
        hring(0, 1.25, 0, 0.185 + e, 0.127 + e, n),
        hring(0, 1.36, 0, 0.195 + e + shoulder, 0.122 + e, n),
        hring(0, 1.42, 0, 0.185 + e + shoulder, 0.112 + e, n),
        hring(0, 1.445, 0, 0.15 + e * 0.6, 0.10 + e * 0.5, 2.4),
        hring(0, 1.458, 0, 0.11 + e * 0.3, 0.09 + e * 0.3, 2.2),
        hring(0, 1.466, 0, neck_r[0], neck_r[1], 2.0),
        hring(0, top_neck, 0, neck_r[0], neck_r[1], 2.0),
    ]


def sleeve(bm, side, stations, n=2.0):
    s, d, w, v = arm_frame(side)
    tube_along(bm, s, d, w, v, stations, seg=28, n=n)


def sleeve_cut(bm, side, t_end, r_reg):
    s, d, w, v = arm_frame(side)
    P = s + d * t_end

    def pred(c, s=s, d=d):
        rel = c - s
        t = rel.dot(d)
        dist = (rel - d * t).length
        return t > t_end - 0.08 and dist < r_reg

    bisect(bm, P, d, pred)


def neck_cut(bm, y_back, y_front, r_reg=0.1):
    # plane through back point and front point, normal mostly +Y, tilted so front is lower
    tilt = (y_back - y_front) / 0.16
    no = G(0, 1, tilt) - G(0, 0, 0)
    co = G(0, (y_back + y_front) / 2, 0)
    bisect(bm, co, no, lambda c: math.hypot(c.x, c.y) < r_reg and gy(c) > 1.40)


def hem_cut(bm, y):
    bisect(bm, G(0, y, 0), Vector((0, 0, -1)), lambda c: gy(c) < y + 0.12 and abs(c.x) < 0.32)


def build_top_tee(body, under):
    extra = 0.022

    def build(bm):
        loft(bm, torso_rings(extra), 44)
        for side in (1, -1):
            sleeve(bm, side, [(-0.02, 0.07, 0.07), (0.0, 0.074, 0.074), (0.12, 0.07, 0.07), (0.26, 0.066, 0.066)])

    def cuts(bm):
        hem_cut(bm, 0.93)
        neck_cut(bm, 1.478, 1.462)
        for side in (1, -1):
            sleeve_cut(bm, side, 0.20, 0.085)

    ob = volume_to_shell("top_tee", build, 0.008, 6, cuts)
    fit_outside(ob, [(body, 0.012)] + [(u, 0.009) for u in under])
    return finish(ob, 3600, 0.004)


def build_top_oversized(body, under):
    extra = 0.035

    def build(bm):
        loft(bm, torso_rings(extra, hem=0.84, shoulder=0.025), 44)
        for side in (1, -1):
            s, d, w, v = arm_frame(side)
            tube_along(bm, s + G(0.03 * side, -0.02, 0) - G(0, 0, 0), d, w, v,
                       [(-0.02, 0.082, 0.082), (0.0, 0.085, 0.085), (0.15, 0.08, 0.08), (0.32, 0.074, 0.074)], seg=28)

    def cuts(bm):
        hem_cut(bm, 0.90)
        neck_cut(bm, 1.478, 1.46)
        for side in (1, -1):
            sleeve_cut(bm, side, 0.26, 0.10)

    ob = volume_to_shell("top_oversized", build, 0.008, 6, cuts)
    fit_outside(ob, [(body, 0.014)] + [(u, 0.009) for u in under])
    return finish(ob, 3600, 0.004)


def build_top_shirt(body, under):
    extra = 0.018

    def build(bm):
        loft(bm, torso_rings(extra, top_neck=1.56, neck_r=(0.074, 0.072)), 44)
        for side in (1, -1):
            sleeve(bm, side, [(-0.02, 0.066, 0.066), (0.0, 0.07, 0.07), (0.15, 0.06, 0.06), (0.29, 0.052, 0.052),
                              (0.50, 0.045, 0.048), (0.60, 0.045, 0.048)])
        # collar band: slightly flared ring standing up the neck
        loft(bm, [hring(0, 1.455, 0, 0.085, 0.083), hring(0, 1.50, -0.005, 0.083, 0.08),
                  hring(0, 1.53, -0.01, 0.09, 0.088)], 36)

    def cuts(bm):
        hem_cut(bm, 0.93)
        neck_cut(bm, 1.52, 1.475)
        for side in (1, -1):
            sleeve_cut(bm, side, 0.56, 0.08)

    ob = volume_to_shell("top_shirt", build, 0.007, 5, cuts)
    fit_outside(ob, [(body, 0.012)] + [(u, 0.009) for u in under])
    return finish(ob, 4000, 0.004)


def front_open_cut(bm, button_y, top_y, top_half, hem_y, hem_half):
    """Open front: V from the collar down to the button, cutaway below. Removes |x| < f(y) on the front."""
    def f(y):
        if y >= button_y:
            return top_half * (y - button_y) / (top_y - button_y)
        return hem_half * (button_y - y) / (button_y - hem_y)

    def pred(c):
        y = gy(c)
        z = -c.y
        return z > 0.02 and abs(c.x) < f(y) + 0.003

    remove_faces(bm, pred)
    clean_loose(bm)
    for v in bm.verts:
        if v.is_boundary and -v.co.y > 0.015 and hem_y + 0.006 < gy(v.co) < 1.53 and abs(v.co.x) < f(gy(v.co)) + 0.04:
            v.co.x = math.copysign(f(gy(v.co)), v.co.x if abs(v.co.x) > 1e-6 else 1.0)


def build_outer(name, body, under, length_y, extra, lapel):
    def build(bm):
        loft(bm, torso_rings(extra, hem=length_y - 0.04, top_neck=1.58, neck_r=(0.095, 0.092), shoulder=0.012), 44)
        for side in (1, -1):
            sleeve(bm, side, [(-0.02, 0.095, 0.095), (0.0, 0.098, 0.098), (0.15, 0.092, 0.092), (0.29, 0.076, 0.076),
                              (0.50, 0.06, 0.062), (0.60, 0.06, 0.062)])

    def cuts(bm):
        hem_cut(bm, length_y)
        neck_cut(bm, 1.545, 1.50, r_reg=0.12)
        for side in (1, -1):
            sleeve_cut(bm, side, 0.555, 0.09)
        front_open_cut(bm, 1.05 if lapel else 0.90, 1.50, 0.105 if lapel else 0.075, length_y, 0.07 if lapel else 0.01)

    ob = volume_to_shell(name, build, 0.008, 6, cuts)
    fit_outside(ob, [(body, 0.025)] + [(u, 0.011) for u in under])
    if lapel:
        add_lapels(ob)
    return finish(ob, 5000, 0.006)


def add_lapels(ob):
    """Lapels: the band of faces next to the V opening is extruded outward and folded over."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    band = []
    for f in bm.faces:
        c = f.calc_center_median()
        y = gy(c)
        z = -c.y
        if z > 0.03 and 1.07 < y < 1.47:
            lim = 0.105 * (y - 1.05) / 0.45
            if lim < abs(c.x) < lim + 0.055 * min(1.0, (y - 1.05) / 0.2):
                band.append(f)
    if band:
        res = bmesh.ops.extrude_face_region(bm, geom=band)
        verts = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
        for v in verts:
            r = Vector((v.co.x, v.co.y, 0.0))
            v.co += r.normalized() * 0.006
        bmesh.ops.delete(bm, geom=band, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def build_outer_blazer(body, under):
    return build_outer("outer_blazer", body, under, 0.78, 0.047, lapel=True)


def build_outer_overshirt(body, under):
    return build_outer("outer_overshirt", body, under, 0.86, 0.05, lapel=False)


def build_bottom(name, body, wide):
    def build(bm):
        loft(bm, [hring(0, 1.06, 0, 0.165, 0.115, 2.4), hring(0, 1.00, 0, 0.17, 0.12, 2.4),
                  hring(0, 0.92, 0, 0.19 + (0.01 if wide else 0), 0.13, 2.4), hring(0, 0.84, 0, 0.18, 0.125, 2.4),
                  hring(0, 0.78, 0, 0.14, 0.10, 2.2)], 44)
        for side in (1, -1):
            if wide:
                st = [(0.095, 0.86, 0.0, 0.094, 0.104), (0.10, 0.70, 0.0, 0.09, 0.10), (0.106, 0.49, 0.0, 0.088, 0.10),
                      (0.115, 0.25, 0.0, 0.094, 0.108), (0.122, 0.05, 0.0, 0.10, 0.12), (0.124, 0.0, 0.0, 0.10, 0.12)]
            else:
                st = [(0.095, 0.86, 0.0, 0.092, 0.10), (0.10, 0.70, 0.0, 0.08, 0.088), (0.103, 0.49, 0.0, 0.06, 0.066),
                      (0.106, 0.35, -0.01, 0.06, 0.066), (0.11, 0.12, 0.0, 0.05, 0.056), (0.11, 0.04, 0.0, 0.052, 0.058)]
            loft(bm, [hring(x * side, y, z, a, b, 2.2) for (x, y, z, a, b) in st], 32)

    hem = 0.035 if wide else 0.075

    def cuts(bm):
        bisect(bm, G(0, 1.035, 0), Vector((0, 0, 1)), lambda c: gy(c) > 0.98)
        for side in (1, -1):
            bisect(bm, G(0, hem, 0), Vector((0, 0, -1)), lambda c, side=side: gy(c) < 0.2 and c.x * side > 0)

    ob = volume_to_shell(name, build, 0.006, 6, cuts)
    fit_outside(ob, [(body, 0.008)], ymin=0.16)
    return finish(ob, 3200, 0.004)


def build_bottom_wide(body, under):
    return build_bottom("bottom_wide", body, True)


def build_bottom_slim(body, under):
    return build_bottom("bottom_slim", body, False)


# ---------------------------------------------------------------- shoes
def shoe_rings(side, kind):
    x = 0.11 * side
    if kind == "sneaker":
        prof = [  # y, z-centre, half-length, half-width, exponent
            (0.000, 0.080, 0.150, 0.060, 2.6),
            (0.012, 0.080, 0.154, 0.062, 2.6),
            (0.030, 0.080, 0.152, 0.061, 2.6),
            (0.034, 0.079, 0.146, 0.057, 2.5),
            (0.060, 0.074, 0.138, 0.055, 2.4),
            (0.082, 0.050, 0.108, 0.052, 2.3),
            (0.102, 0.012, 0.072, 0.049, 2.2),
            (0.122, -0.006, 0.058, 0.047, 2.1),
            (0.132, -0.012, 0.054, 0.047, 2.0),
        ]
    else:  # loafer: low, sleek, thin sole, low vamp
        prof = [
            (0.000, 0.082, 0.147, 0.055, 2.8),
            (0.014, 0.082, 0.150, 0.057, 2.8),
            (0.018, 0.082, 0.145, 0.054, 2.6),
            (0.045, 0.078, 0.140, 0.052, 2.4),
            (0.068, 0.058, 0.115, 0.049, 2.2),
            (0.090, 0.018, 0.080, 0.046, 2.1),
            (0.100, 0.000, 0.068, 0.045, 2.0),
        ]
    rings = []
    for (y, zc, L, W, n) in prof:
        rings.append(hring(x, y, zc, W, L, n))
    return rings


def build_shoe(name, body, kind):
    bm = bmesh.new()
    for side in (1, -1):
        vr = loft(bm, shoe_rings(side, kind), 40, cap0=True, cap1=False)
    ob = bm_to_obj(name, bm)
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.006
    so.offset = -1.0
    so.use_rim = True
    ss = ob.modifiers.new("s", "SUBSURF")
    ss.levels = 1
    ss.render_levels = 1
    apply_mods(ob)
    # keep the sole flat on y = 0
    for v in ob.data.vertices:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return finish(ob, 7000, 0.0, sharp_deg=None)


def build_shoe_sneaker(body, under):
    return build_shoe("shoe_sneaker", body, "sneaker")


def build_shoe_loafer(body, under):
    return build_shoe("shoe_loafer", body, "loafer")


# ---------------------------------------------------------------- headwear
HEAD_C = (0.0, 1.625, 0.01)
HAT_TILT = {"head_cap": 13.0, "head_beanie": 9.0, "head_bucket": 7.0}


def dome(bm, c, rx, ry, rz, y_cut_frac=0.0, seg=40, rings=14):
    """Upper part of an ellipsoid (glTF radii), open at the bottom."""
    cx, cy, cz = c
    vr = []
    for i in range(rings + 1):
        phi = (math.pi / 2) * (1 - i / rings)  # from equator to pole
        y = math.sin(phi)
        r = math.cos(phi)
        vr.append((cy + ry * (y_cut_frac + (1 - y_cut_frac) * y), r))
    rings_l = [hring(cx, yy, cz, max(rx * r, 1e-4), max(rz * r, 1e-4), 2.0) for (yy, r) in vr]
    return loft(bm, rings_l, seg, cap0=False, cap1=True)


def tilt(ob, deg, pivot_y=1.70):
    """Rotate about the glTF X axis so the front rises and the back drops (hats sit back on the head)."""
    th = math.radians(deg)
    c, s_ = math.cos(th), math.sin(th)
    for v in ob.data.vertices:
        y, z = v.co.z - pivot_y, -v.co.y  # glTF y (rel), z
        y2 = y * c + z * s_
        z2 = -y * s_ + z * c
        v.co.z = y2 + pivot_y
        v.co.y = -z2
    ob.data.update()


def build_head_cap(body, under):
    bm = bmesh.new()
    dome(bm, (0.0, 1.615, 0.003), 0.099, 0.155, 0.114)
    # brim: flat-ish curved visor at the front
    seg = 24
    rows = []
    for j in range(4):
        r = j / 3.0
        row = []
        for i in range(seg + 1):
            a = math.radians(-70 + 140 * i / seg)
            rr = 0.097 + r * 0.075 * math.cos(a * 0.9) ** 0.6
            x = math.sin(a) * rr
            z = 0.003 + math.cos(a) * (0.114 / 0.099) * rr
            y = 1.628 - 0.012 * r - 0.004 * r * r
            row.append(bm.verts.new(G(x, y, z)))
        rows.append(row)
    for r0, r1 in zip(rows[:-1], rows[1:]):
        for i in range(seg):
            bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
    ob = bm_to_obj("head_cap", bm)
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.006
    so.offset = 1.0
    so.use_rim = True
    ss = ob.modifiers.new("s", "SUBSURF")
    ss.levels = 1
    apply_mods(ob)
    # button on top
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    sphere(bm, G(0, 1.770, 0.003), 0.012, 0.007, 0.012, 12, 6)
    bm.to_mesh(ob.data)
    bm.free()
    tilt(ob, HAT_TILT[ob.name])
    fit_outside(ob, [(body, 0.006)], maxdist=0.04)
    return finish(ob, 6000, 0.0)


def build_head_beanie(body, under):
    bm = bmesh.new()
    dome(bm, (0.0, 1.605, 0.003), 0.1, 0.19, 0.115)
    # folded cuff
    loft(bm, [hring(0, 1.598, 0.003, 0.105, 0.119), hring(0, 1.665, 0.003, 0.105, 0.118)], 40, False, False)
    ob = bm_to_obj("head_beanie", bm)
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.008
    so.offset = 1.0
    ss = ob.modifiers.new("s", "SUBSURF")
    ss.levels = 1
    apply_mods(ob)
    tilt(ob, HAT_TILT[ob.name])
    fit_outside(ob, [(body, 0.006)], maxdist=0.04)
    return finish(ob, 6000, 0.0)


def build_head_bucket(body, under):
    bm = bmesh.new()
    dome(bm, (0.0, 1.64, 0.003), 0.101, 0.13, 0.116, y_cut_frac=0.0)
    loft(bm, [hring(0, 1.64, 0.003, 0.101, 0.116), hring(0, 1.622, 0.003, 0.15, 0.162), hring(0, 1.605, 0.003, 0.172, 0.182)],
         40, False, False)
    ob = bm_to_obj("head_bucket", bm)
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.006
    so.offset = 1.0
    ss = ob.modifiers.new("s", "SUBSURF")
    ss.levels = 1
    apply_mods(ob)
    tilt(ob, HAT_TILT[ob.name])
    fit_outside(ob, [(body, 0.006)], maxdist=0.04)
    return finish(ob, 6000, 0.0)


# ---------------------------------------------------------------- eyewear, watch, chain
def torus_ring(bm, c, u, v, R, r, seg=32, rseg=8, sx=1.0, sy=1.0):
    vr = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        dirv = u * (math.cos(a) * sx) + v * (math.sin(a) * sy)
        rad = (u * math.cos(a) + v * math.sin(a))
        ring = []
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            n = u.cross(v).normalized()
            p = c + dirv * R + rad * (r * math.cos(b)) + n * (r * math.sin(b))
            ring.append(bm.verts.new(p))
        vr.append(ring)
    for i in range(seg):
        r0, r1 = vr[i], vr[(i + 1) % seg]
        for j in range(rseg):
            k = (j + 1) % rseg
            bm.faces.new((r0[j], r1[j], r1[k], r0[k]))


def bar(bm, a, b, r, seg=8):
    capsule(bm, a, b, r, seg)


def build_glasses(name, shades):
    bm = bmesh.new()
    ey, fz = 1.63, 0.118
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))
    for side in (1, -1):
        cx = 0.033 * side
        if shades:
            torus_ring(bm, G(cx, ey, fz), X, Y, 0.028, 0.0035, 36, 8, sx=1.15, sy=0.85)
            # lens: flat disc
            seg = 32
            ring = [bm.verts.new(G(cx + math.cos(2 * math.pi * i / seg) * 0.031, ey + math.sin(2 * math.pi * i / seg) * 0.023,
                                   fz)) for i in range(seg)]
            bm.faces.new(ring)
        else:
            torus_ring(bm, G(cx, ey, fz), X, Y, 0.022, 0.0025, 36, 8)
        # temple arm back to the ear
        bar(bm, G((0.062 if shades else 0.056) * side, ey + 0.004, fz - 0.004), G(0.074 * side, ey + 0.004, fz - 0.03), 0.0025)
        bar(bm, G(0.074 * side, ey + 0.004, fz - 0.03), G(0.088 * side, ey + 0.004, -0.04), 0.0025)
    bar(bm, G(-0.012, ey + 0.006, fz + 0.002), G(0.012, ey + 0.006, fz + 0.002), 0.0022)  # bridge
    ob = bm_to_obj(name, bm)
    return finish(ob, 4000, 0.0)


def build_eye_round(body, under):
    return build_glasses("eye_round", False)


def build_eye_shades(body, under):
    return build_glasses("eye_shades", True)


def build_watch(name, digital):
    s, d, w, v = arm_frame(1)  # figure's LEFT arm (+X)
    t = 0.535
    c = s + d * t
    bm = bmesh.new()
    # strap: thin elliptical band around the wrist
    tube_along(bm, s, d, w, v, [(t - 0.011, 0.034, 0.038), (t + 0.011, 0.034, 0.038)], seg=32, cap=False)
    ob = bm_to_obj(name, bm)
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.004
    so.offset = 1.0
    apply_mods(ob)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    # face on the back of the wrist (outward = +Z front? use the top: -v points down/in); put it facing +Z (front)
    nrm = (w * 0.8 - v).normalized()  # outward + toward the front, readable from the audience
    face_c = c + nrm * 0.036
    e2 = nrm.cross(d).normalized()
    if digital:
        loft(bm, [(face_c, d, e2, 0.017, 0.015, 4.0), (face_c + nrm * 0.009, d, e2, 0.017, 0.015, 4.0)], 24)
    else:
        loft(bm, [(face_c, d, e2, 0.019, 0.019, 2.0), (face_c + nrm * 0.008, d, e2, 0.019, 0.019, 2.0)], 32)
    bm.to_mesh(ob.data)
    bm.free()
    return finish(ob, 3000, 0.0)


def build_watch_analog(body, under):
    return build_watch("watch_analog", False)


def build_watch_digital(body, under):
    return build_watch("watch_digital", True)


def build_neck_chain(body, under):
    bm = bmesh.new()
    # chain around the neck base, dipping onto the upper chest (glTF)
    n = 64
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = math.sin(a) * 0.082
        zf = math.cos(a)
        z = zf * 0.085 + 0.005
        y = 1.452 - 0.07 * max(0.0, zf) ** 2.2
        z += 0.03 * max(0.0, zf) ** 2  # sit out over the chest
        pts.append(G(x, y, z))
    rseg = 6
    r = 0.0028
    rings = []
    for i in range(n):
        p = pts[i]
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        a = t.cross(Vector((0, 0, 1)))
        if a.length < 1e-4:
            a = Vector((1, 0, 0))
        a.normalize()
        b = t.cross(a).normalized()
        rings.append([bm.verts.new(p + a * (r * math.cos(2 * math.pi * j / rseg)) + b * (r * math.sin(2 * math.pi * j / rseg)))
                      for j in range(rseg)])
    for i in range(n):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for j in range(rseg):
            k = (j + 1) % rseg
            bm.faces.new((r0[j], r1[j], r1[k], r0[k]))
    ob = bm_to_obj("neck_chain", bm)
    fit_outside(ob, [(body, 0.016)] + [(u, 0.007) for u in under])
    return finish(ob, 3000, 0.0)


# ---------------------------------------------------------------- main
ORDER = [
    ("bottom_wide", build_bottom_wide, []),
    ("bottom_slim", build_bottom_slim, []),
    ("top_tee", build_top_tee, ["bottom_wide", "bottom_slim"]),
    ("top_shirt", build_top_shirt, ["bottom_wide", "bottom_slim"]),
    ("top_oversized", build_top_oversized, ["bottom_wide", "bottom_slim"]),
    ("outer_blazer", build_outer_blazer, ["top_tee", "top_shirt", "top_oversized", "bottom_wide", "bottom_slim"]),
    ("outer_overshirt", build_outer_overshirt, ["top_tee", "top_shirt", "top_oversized", "bottom_wide", "bottom_slim"]),
    ("shoe_sneaker", build_shoe_sneaker, []),
    ("shoe_loafer", build_shoe_loafer, []),
    ("head_cap", build_head_cap, []),
    ("head_beanie", build_head_beanie, []),
    ("head_bucket", build_head_bucket, []),
    ("eye_round", build_eye_round, []),
    ("eye_shades", build_eye_shades, []),
    ("watch_analog", build_watch_analog, []),
    ("watch_digital", build_watch_digital, []),
    ("neck_chain", build_neck_chain, ["top_tee", "top_shirt", "top_oversized"]),
]


def main():
    reset()
    body = real_body() or proxy_body()
    built = {}
    for name, fn, under_names in ORDER:
        if ONLY and name not in ONLY:
            continue
        under = [SHELLS[u] for u in under_names if u in SHELLS]
        try:
            built[name] = fn(body, under)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("WARDROBE: FAILED", name, e)
    keep_body = os.environ.get("KEEP_BODY")
    bpy.ops.object.select_all(action="DESELECT")
    for ob in built.values():
        ob.select_set(True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_texcoords=True, export_normals=True,
                              export_materials="EXPORT", export_animations=False,
                              export_draco_mesh_compression_enable=False)
    print("WARDROBE: exported", OUT, os.path.getsize(OUT), "bytes;", ", ".join(built))
    if keep_body:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join("/tmp", "wardrobe_debug.blend"))


if __name__ == "__main__":
    main()
