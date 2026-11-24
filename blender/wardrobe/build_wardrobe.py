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


HEAD = {"obj": None}


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
    heads = []
    for o in new:
        # what stays visible under a hat: the head (which may carry baked hair) and hair_capped; hair_full is hidden
        if o.type == "MESH" and (o.name.startswith("body_head") or o.name.startswith("hair")):
            me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
            c = new_obj("headpart", me)
            c.matrix_world = o.matrix_world.copy()
            heads.append(c)
    if heads:
        HEAD["obj"] = join("head_vol", heads)
    for o in new:
        if o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in copies:  # close the region cuts so the joined body is watertight
        bm = bmesh.new()
        bm.from_mesh(c.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bnd = [e for e in bm.edges if e.is_boundary]
        if bnd:
            bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
        bm.to_mesh(c.data)
        bm.free()
    ob = join("fit_body", copies)
    raw = ob.data.copy()
    m = ob.modifiers.new("r", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = 0.005
    apply_mods(ob)
    if len(ob.data.vertices) < 20000:  # remesh failed: fall back to the raw parts
        old = ob.data
        ob.data = raw
        bpy.data.meshes.remove(old)
        print("WARDROBE: body remesh failed, using raw parts")
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


def cinch(ob, body, pred, offset, falloff=0.045, maxdist=0.25):
    """Pull open boundary loops (neckline, cuffs) snug to the body so no gap shows, blending inwards."""
    if body is None:
        return
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree
    tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    B = [v for v in bm.verts if v.is_boundary and pred(v.co)]
    if not B:
        bm.free()
        return
    Bset = set(B)
    for _ in range(6):  # relax the stair-stepped voxel edge along the loop first
        newco = {}
        for v in B:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary and e.other_vert(v) in Bset]
            if len(nb) == 2:
                newco[v] = (v.co * 2 + nb[0].co + nb[1].co) / 4
        for v, c in newco.items():
            v.co = c
    disp = []
    for v in B:
        loc, nrm, idx, dist = tree.find_nearest(v.co, maxdist)
        if loc is None:
            disp.append(Vector())
            continue
        disp.append((loc + nrm * offset) - v.co)
    idx_of = {v: i for i, v in enumerate(B)}
    for _ in range(4):  # smooth the pull along the loop so the edge stays even
        nd = []
        for i, v in enumerate(B):
            nb = [idx_of[e.other_vert(v)] for e in v.link_edges if e.is_boundary and e.other_vert(v) in idx_of]
            nd.append((disp[i] * 2 + sum((disp[j] for j in nb), Vector())) / (2 + len(nb)))
        disp = nd
    kd = KDTree(len(B))
    for i, v in enumerate(B):
        kd.insert(v.co, i)
    kd.balance()
    moves = []
    for v in bm.verts:
        co, i, d = kd.find(v.co)
        if d is None or d > falloff:
            continue
        # average the displacement of nearby boundary verts for smoothness
        acc, wsum = Vector(), 0.0
        for co2, j, d2 in kd.find_range(v.co, max(0.012, d + 0.01)):
            w = 1.0 / (d2 + 0.003)
            acc += disp[j] * w
            wsum += w
        w = (1.0 - d / falloff) ** 2 * (3 - 2 * (1.0 - d / falloff)) if d > 0 else 1.0
        moves.append((v, acc / wsum * w))
    for v, m in moves:
        v.co += m
    bm.to_mesh(ob.data)
    bm.free()
    print(f"WARDROBE:   cinch {ob.name}: {len(B)} boundary verts")


def is_neck(c):
    return gy(c) > 1.38 and math.hypot(c.x, c.y) < 0.16


def is_cuff(c):
    return abs(c.x) > 0.2 and gy(c) > 0.85


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
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
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
    cinch(ob, body, is_neck, 0.003)
    cinch(ob, body, is_cuff, 0.01, falloff=0.05)
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
    cinch(ob, body, is_neck, 0.006)
    cinch(ob, body, is_cuff, 0.02, falloff=0.05)
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
            sleeve_cut(bm, side, SLEEVE_T, 0.08)

    ob = volume_to_shell("top_shirt", build, 0.007, 5, cuts)
    fit_outside(ob, [(body, 0.012)] + [(u, 0.009) for u in under])
    cinch(ob, body, is_neck, 0.01, falloff=0.03)
    cinch(ob, body, is_cuff, 0.006, falloff=0.06)
    return finish(ob, 4000, 0.004)


def front_open_cut(bm, button_y, top_y, top_half, hem_y, hem_half):
    """Open front with clean straight edges: a V from the collar to the button, a cutaway below it."""
    k = top_half / (top_y - button_y)
    k2 = hem_half / max(1e-3, button_y - hem_y)
    co = G(0, button_y, 0)
    for side in (1, -1):
        # above the button: remove side*x < k (y - yb)
        n_up = G(-side, k, 0) - G(0, 0, 0)
        bisect(bm, co, n_up, lambda c, side=side: -c.y > 0.02 and c.x * side > -0.012 and gy(c) > button_y - 0.03)
        n_dn = G(-side, -k2, 0) - G(0, 0, 0)
        bisect(bm, co, n_dn, lambda c, side=side: -c.y > 0.02 and c.x * side > -0.012 and gy(c) < button_y + 0.03)
    clean_loose(bm)


def opening_half(y, button_y, top_y, top_half, hem_y, hem_half):
    if y >= button_y:
        return top_half * (y - button_y) / (top_y - button_y)
    return hem_half * (button_y - y) / max(1e-3, button_y - hem_y)


def build_outer(name, body, under, length_y, extra, lapel):
    def build(bm):
        loft(bm, torso_rings(extra, hem=length_y - 0.04, top_neck=1.58, neck_r=(0.095, 0.092), shoulder=0.012), 44)
        for side in (1, -1):
            sleeve(bm, side, [(-0.02, 0.095, 0.095), (0.0, 0.098, 0.098), (0.15, 0.092, 0.092), (0.29, 0.076, 0.076),
                              (0.50, 0.06, 0.062), (0.60, 0.06, 0.062)])

    def cuts(bm):
        hem_cut(bm, length_y)
        neck_cut(bm, 1.53, 1.49, r_reg=0.12)
        for side in (1, -1):
            sleeve_cut(bm, side, SLEEVE_T, 0.09)
        front_open_cut(bm, 1.05 if lapel else 0.90, 1.50, 0.105 if lapel else 0.075, length_y, 0.07 if lapel else 0.01)

    ob = volume_to_shell(name, build, 0.008, 6, cuts)
    fit_outside(ob, [(body, 0.025)] + [(u, 0.011) for u in under])
    cinch(ob, body, lambda c: is_cuff(c) and gy(c) < 1.05, 0.013, falloff=0.07)
    if lapel:
        add_lapels(ob, 1.05, 1.50, 0.105, length_y, 0.07)
    return finish(ob, 3700, 0.006)


def add_lapels(ob, button_y, top_y, top_half, hem_y, hem_half):
    """Lapels: a smooth panel lying on the chest along each edge of the V, widening up to a notch."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    rows, cols = 26, 6
    y0, y1 = button_y + 0.01, 1.47
    for side in (1, -1):
        grid = []
        for i in range(rows + 1):
            y = y0 + (y1 - y0) * i / rows
            xin = opening_half(y, button_y, top_y, top_half, hem_y, hem_half) - 0.002
            if y < 1.40:
                w = 0.078 * min(1.0, (y - button_y) / 0.28) ** 0.8
            else:
                w = 0.078 - 0.04 * (y - 1.40) / (y1 - 1.40)
            row = []
            for j in range(cols + 1):
                x = (xin + w * j / cols) * side
                org = G(x, y, 0.5)
                hit, nrm, idx, dist = tree.ray_cast(org, Vector((0, 1, 0)), 1.0)
                if hit is None:
                    hit, nrm = G(x, y, 0.16), Vector((0, -1, 0))
                lift = 0.004 + 0.003 * (j / cols)  # roll: outer edge stands off a touch
                row.append(bm.verts.new(hit + nrm * lift))
            grid.append(row)
        for i in range(rows):
            for j in range(cols):
                q = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
                bm.faces.new(q if side > 0 else tuple(reversed(q)))
    bm.to_mesh(ob.data)
    bm.free()


def build_outer_blazer(body, under):
    return build_outer("outer_blazer", body, under, 0.78, 0.047, lapel=True)


def build_outer_overshirt(body, under):
    return build_outer("outer_overshirt", body, under, 0.86, 0.05, lapel=False)


def build_bottom(name, body, wide, under=()):
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
                      (0.106, 0.35, -0.01, 0.06, 0.066), (0.11, 0.17, -0.005, 0.056, 0.07), (0.11, 0.11, -0.006, 0.059, 0.08),
                      (0.11, 0.04, -0.006, 0.059, 0.082)]
            loft(bm, [hring(x * side, y, z, a, b, 2.2) for (x, y, z, a, b) in st], 32)

    hem = 0.035 if wide else 0.075

    def cuts(bm):
        bisect(bm, G(0, 1.035, 0), Vector((0, 0, 1)), lambda c: gy(c) > 0.98)
        for side in (1, -1):
            bisect(bm, G(0, hem, 0), Vector((0, 0, -1)), lambda c, side=side: gy(c) < 0.2 and c.x * side > 0)

    ob = volume_to_shell(name, build, 0.006, 6, cuts)
    fit_outside(ob, [(body, 0.008)], ymin=0.16)
    # hems are cut wide enough to swallow both shoe collars, so no push against the shoes is needed
    return finish(ob, 3200, 0.004)


def build_bottom_wide(body, under):
    return build_bottom("bottom_wide", body, True, under)


def build_bottom_slim(body, under):
    return build_bottom("bottom_slim", body, False, under)


# ---------------------------------------------------------------- shoes
def shoe_ring(bm, side, y, zc, L, W, n, seg=48, spring=0.0, tilt=0.0):
    """One ring of a foot-shaped outline (narrow heel, wide ball, round toe), tilted so it drops toward the toe."""
    ring = []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        u, s_ = math.cos(t), math.sin(t)
        z = zc + L * math.copysign(abs(u) ** (2.0 / n), u)
        g = 0.80 + 0.22 * min(1.0, max(0.0, (u + 1.0) / 1.3)) - 0.06 * max(0.0, u - 0.7) / 0.3
        x = 0.11 * side + W * g * math.copysign(abs(s_) ** (2.0 / n), s_) - 0.006 * side * max(0.0, u)
        yy = y + spring * max(0.0, (z - 0.13) / 0.10) ** 2 + tilt * (z - zc)
        ring.append(bm.verts.new(G(x, yy, z)))
    return ring


def shoe_volume(bm, side, prof, seg=48):
    rings = [shoe_ring(bm, side, y, zc, L, W, n, seg=seg, spring=sp, tilt=tl) for (y, zc, L, W, n, sp, tl) in prof]
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(list(reversed(rings[0])))  # sole closed, collar open


SNEAKER = [  # y, z-centre, half-length, half-width, exponent, toe spring, tilt
    (0.000, 0.081, 0.146, 0.056, 2.8, 0.016, 0.0),
    (0.004, 0.081, 0.150, 0.058, 2.8, 0.016, 0.0),
    (0.024, 0.081, 0.153, 0.060, 2.8, 0.016, 0.0),
    (0.029, 0.081, 0.153, 0.060, 2.8, 0.014, 0.0),
    (0.031, 0.080, 0.146, 0.054, 2.6, 0.012, 0.0),
    (0.050, 0.078, 0.143, 0.054, 2.5, 0.008, -0.03),
    (0.068, 0.066, 0.128, 0.052, 2.3, 0.0, -0.10),
    (0.085, 0.040, 0.100, 0.050, 2.2, 0.0, -0.22),
    (0.100, 0.015, 0.078, 0.048, 2.1, 0.0, -0.30),
    (0.112, 0.000, 0.066, 0.047, 2.0, 0.0, -0.35),
]
LOAFER = [
    (0.000, 0.082, 0.146, 0.053, 3.0, 0.008, 0.0),
    (0.010, 0.082, 0.150, 0.055, 3.0, 0.008, 0.0),
    (0.014, 0.082, 0.150, 0.055, 3.0, 0.008, 0.0),
    (0.016, 0.082, 0.146, 0.052, 2.8, 0.006, 0.0),
    (0.040, 0.079, 0.142, 0.051, 2.5, 0.004, -0.03),
    (0.058, 0.062, 0.124, 0.049, 2.3, 0.0, -0.12),
    (0.072, 0.030, 0.094, 0.047, 2.2, 0.0, -0.22),
    (0.084, 0.008, 0.074, 0.046, 2.0, 0.0, -0.25),
]


def build_shoe(name, body, kind):
    bm = bmesh.new()
    prof = SNEAKER if kind == "sneaker" else LOAFER
    for side in (1, -1):
        shoe_volume(bm, side, prof)
        if kind == "sneaker":  # padded tongue rising out of the throat
            loft(bm, [hring(0.11 * side, 0.080, 0.072, 0.028, 0.008, 3), hring(0.11 * side, 0.104, 0.056, 0.029, 0.009, 3),
                      hring(0.11 * side, 0.124, 0.040, 0.028, 0.008, 3)], 24)
    ob = bm_to_obj(name, bm)
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.005
    so.offset = 1.0  # ring winding is inward, so +1 grows inside the shoe
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
    ob = build_shoe("shoe_sneaker", body, "sneaker")
    # separate sole material so a product can have a gum sole; neutral white by default
    sole = bpy.data.materials.get("mat_shoe_sneaker_sole") or bpy.data.materials.new("mat_shoe_sneaker_sole")
    sole.use_nodes = True
    bsdf = sole.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.88, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.7
    ob.data.materials.append(sole)
    n = 0
    for poly in ob.data.polygons:
        if poly.center.z < 0.0295:
            poly.material_index = 1
            n += 1
    print(f"WARDROBE:   shoe_sneaker sole faces {n}")
    return ob


def build_shoe_loafer(body, under):
    return build_shoe("shoe_loafer", body, "loafer")


# ---------------------------------------------------------------- headwear
HAT_TILT = {"head_cap": 13.0, "head_beanie": 9.0, "head_bucket": 7.0}
HEAD_P = 2.6  # super-ellipsoid exponent of the head+hair volume (curly hair is boxier than an ellipsoid)


def head_volume():
    """Ellipsoid the headwear must clear: a curly-hair allowance (~+2 cm, top ~1.79) grown to contain the
    avatar's real head + hair above the brow. Returns (cx, cy, cz, rx, ry, rz) in glTF metres."""
    cx, cy, cz, rx, ry, rz = 0.0, 1.635, 0.005, 0.112, 0.155, 0.122
    P = HEAD_P
    ob = HEAD["obj"]
    if ob is not None:
        sc = 1.0
        worst = None
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            x, y, z = w.x, w.z, -w.y
            if y < 1.62 or (z > 0.085 and y < 1.69):  # face, beard, ears below the hat line
                continue
            q = (abs((x - cx) / rx) ** P + abs((y - cy) / ry) ** P + abs((z - cz) / rz) ** P) ** (1.0 / P)
            if q > sc:
                sc, worst = q, (round(x, 3), round(y, 3), round(z, 3))
        rx, ry, rz = rx * sc, ry * sc, rz * sc
        print(f"WARDROBE:   head volume scale {sc:.3f}", worst if sc > 1 else "")
    return cx, cy, cz, rx, ry, rz


def head_proxy_obj(hv, pad=0.0):
    cx, cy, cz, rx, ry, rz = hv
    bm = bmesh.new()
    m = bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.0)
    e = 2.0 / HEAD_P
    for vert in m["verts"]:  # super-ellipsoid, same metric as head_volume()
        a, b, c = vert.co  # blender x, y(-gz), z(gy)
        vert.co = G(cx + math.copysign(abs(a) ** e, a) * (rx + pad), cy + math.copysign(abs(c) ** e, c) * (ry + pad),
                    cz - math.copysign(abs(b) ** e, b) * (rz + pad))
    ob = bm_to_obj("head_proxy", bm)
    ob.hide_render = True
    return ob


def dome(bm, c, rx, ry, rz, y_cut_frac=0.0, seg=40, rings=14, p=2.0):
    """Upper part of a super-ellipsoid (glTF radii), open at the bottom; p > 2 gives a fuller, rounder crown."""
    cx, cy, cz = c
    vr = []
    for i in range(rings + 1):
        phi = (math.pi / 2) * (1 - i / rings)  # from equator to pole
        y = math.sin(phi) ** (2.0 / p)
        r = math.cos(phi) ** (2.0 / p)
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


def hat_finish(ob, body, hv):
    tilt(ob, HAT_TILT[ob.name])
    prox = head_proxy_obj(hv)
    targets = [(body, 0.006), (prox, 0.006)]
    if HEAD["obj"] is not None:
        targets.append((HEAD["obj"], 0.006))
    fit_outside(ob, targets, maxdist=0.05)
    delete(prox)
    return finish(ob, 6000, 0.0)


def solidify_subsurf(ob, th, levels=1):
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = th
    so.offset = 1.0
    so.use_rim = True
    ss = ob.modifiers.new("s", "SUBSURF")
    ss.levels = levels
    apply_mods(ob)


def build_head_cap(body, under):
    hv = head_volume()
    cx, cy, cz, rx, ry, rz = hv
    base = cy + 0.006
    top = cy + ry + 0.008
    RX, RZ = rx + 0.008, rz + 0.008
    bm = bmesh.new()
    dome(bm, (cx, base, cz), RX, top - base, RZ, p=2.7)
    # brim: curved visor at the front
    seg = 24
    rows = []
    for j in range(4):
        r = j / 3.0
        row = []
        for i in range(seg + 1):
            a = math.radians(-70 + 140 * i / seg)
            rr = RX * 0.985 + r * 0.078 * math.cos(a * 0.9) ** 0.6
            x = math.sin(a) * rr
            z = cz + math.cos(a) * (RZ / RX) * rr
            y = base + 0.012 - 0.012 * r - 0.004 * r * r
            row.append(bm.verts.new(G(x, y, z)))
        rows.append(row)
    for r0, r1 in zip(rows[:-1], rows[1:]):
        for i in range(seg):
            bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
    ob = bm_to_obj("head_cap", bm)
    solidify_subsurf(ob, 0.006)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    sphere(bm, G(cx, top + 0.004, cz), 0.012, 0.007, 0.012, 12, 6)  # button
    bm.to_mesh(ob.data)
    bm.free()
    return hat_finish(ob, body, hv)


def build_head_beanie(body, under):
    hv = head_volume()
    cx, cy, cz, rx, ry, rz = hv
    base = cy + 0.012
    top = cy + ry + 0.02
    bm = bmesh.new()
    dome(bm, (cx, base, cz), rx + 0.01, top - base, rz + 0.01, p=2.3)
    loft(bm, [hring(cx, base - 0.006, cz, rx + 0.016, rz + 0.016), hring(cx, base + 0.06, cz, rx + 0.016, rz + 0.016)],
         40, False, False)  # folded cuff
    ob = bm_to_obj("head_beanie", bm)
    solidify_subsurf(ob, 0.008)
    return hat_finish(ob, body, hv)


def build_head_bucket(body, under):
    hv = head_volume()
    cx, cy, cz, rx, ry, rz = hv
    base = cy + 0.02
    top = cy + ry + 0.012
    RX, RZ = rx + 0.01, rz + 0.01
    bm = bmesh.new()
    rings = [hring(cx, base - 0.032, cz, RX + 0.07, RZ + 0.066), hring(cx, base - 0.016, cz, RX + 0.048, RZ + 0.046),
             hring(cx, base - 0.002, cz, RX + 0.006, RZ + 0.006)]
    k, p_ = 12, 3.0
    for i in range(k + 1):  # crown, one continuous surface with the brim
        phi = (math.pi / 2) * i / k
        yy = base + (top - base) * math.sin(phi) ** (2.0 / p_)
        r = max(math.cos(phi) ** (2.0 / p_), 1e-3)
        rings.append(hring(cx, yy, cz, RX * r, RZ * r))
    loft(bm, rings, 40, cap0=False, cap1=True)
    ob = bm_to_obj("head_bucket", bm)
    solidify_subsurf(ob, 0.006)
    return hat_finish(ob, body, hv)


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


def tube_path(bm, pts, r, rseg=6, closed=True):
    n = len(pts)
    rings = []
    for i in range(n):
        p = pts[i]
        if closed:
            t = (pts[(i + 1) % n] - pts[i - 1])
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        a = t.cross(Vector((0, 0, 1)))
        if a.length < 1e-4:
            a = t.cross(Vector((1, 0, 0)))
        a.normalize()
        b = t.cross(a).normalized()
        rings.append([bm.verts.new(p + a * (r * math.cos(2 * math.pi * j / rseg)) + b * (r * math.sin(2 * math.pi * j / rseg)))
                      for j in range(rseg)])
    m = n if closed else n - 1
    for i in range(m):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for j in range(rseg):
            k = (j + 1) % rseg
            bm.faces.new((r0[j], r1[j], r1[k], r0[k]))
    if not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])


def face_measure():
    """Front of the face at the eyes and the bridge, and head half-width at the temples (glTF)."""
    ey, ex = 1.63, 0.033
    z_eye, z_bridge, half_w = 0.10, 0.105, 0.09
    ob = HEAD["obj"]
    if ob is not None:
        from mathutils.bvhtree import BVHTree
        tree = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
        zs = []
        for x in (ex, -ex):
            hit = tree.ray_cast(G(x, ey, 0.5), Vector((0, 1, 0)), 1.0)[0]
            if hit is not None:
                zs.append(-hit.y)
        if zs:
            z_eye = max(zs)
        hit = tree.ray_cast(G(0, ey + 0.008, 0.5), Vector((0, 1, 0)), 1.0)[0]
        if hit is not None:
            z_bridge = -hit.y
        ws = []
        for sd in (1, -1):
            hit = tree.ray_cast(G(sd * 0.5, ey + 0.005, 0.0), G(-sd, 0, 0) - G(0, 0, 0), 1.0)[0]
            if hit is not None:
                ws.append(abs(hit.x))
        if ws:
            half_w = max(ws)
    print(f"WARDROBE:   face z_eye {z_eye:.3f} z_bridge {z_bridge:.3f} half_w {half_w:.3f}")
    return ey, ex, z_eye, z_bridge, half_w


def build_glasses(name, shades):
    ey, ex, z_eye, z_bridge, half_w = face_measure()
    fz = max(z_eye + 0.016, z_bridge + 0.006)
    bm = bmesh.new()
    if shades:  # bold square shades: thick rounded-square rims, dark lens slabs, heavy temples
        W, H, rr = 0.030, 0.023, 0.0032
        for side in (1, -1):
            cx = (ex + 0.002) * side
            pts = []
            for i in range(48):
                t = 2 * math.pi * i / 48
                x, y = superellipse(t, W, H, 5.0)
                pts.append(G(cx + x, ey + y, fz))
            tube_path(bm, pts, rr, 8)
            X, Y = Vector((1, 0, 0)), Vector((0, 0, 1))
            loft(bm, [(G(cx, ey, fz + 0.0012), X, Y, W - 0.001, H - 0.001, 5.0),
                      (G(cx, ey, fz - 0.0012), X, Y, W - 0.001, H - 0.001, 5.0)], 48)
            ox = cx + W * side
            tube_path(bm, [G(ox, ey + H * 0.6, fz - 0.002), G((half_w + 0.004) * side, ey + 0.012, fz - 0.03),
                           G((half_w + 0.004) * side, ey + 0.01, -0.035)], 0.0028, 8, closed=False)
        tube_path(bm, [G(-(ex + 0.002 - W), ey + H * 0.55, fz + 0.001), G(0, ey + H * 0.62, fz + 0.002),
                       G(ex + 0.002 - W, ey + H * 0.55, fz + 0.001)], 0.0032, 8, closed=False)
    else:  # thin metal hexagonal frames
        R, rr = 0.026, 0.0011
        for side in (1, -1):
            cx = (ex + 0.001) * side
            corners = [(R * math.cos(math.radians(a)), R * 0.92 * math.sin(math.radians(a))) for a in range(0, 360, 60)]
            pts = []
            for i in range(6):  # 6 edges, slightly rounded corners
                (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 6]
                for k in range(1, 7):
                    f = 0.08 + 0.84 * k / 7
                    pts.append(G(cx + x0 + (x1 - x0) * f, ey + y0 + (y1 - y0) * f, fz))
            tube_path(bm, pts, rr, 6)
            ox = cx + R * side
            tube_path(bm, [G(ox, ey, fz), G(ox + 0.004 * side, ey + 0.002, fz - 0.004),
                           G((half_w + 0.003) * side, ey + 0.006, fz - 0.03), G((half_w + 0.003) * side, ey + 0.005, -0.035)],
                      0.0012, 6, closed=False)
            # nose pad arm
            tube_path(bm, [G((ex + 0.001 - R * 0.55) * side, ey - 0.012, fz), G(0.008 * side, ey - 0.006, fz - 0.008)],
                      0.0008, 6, closed=False)
        ix = ex + 0.001 - R * 0.5
        tube_path(bm, [G(-ix, ey + R * 0.8, fz), G(-0.006, ey + R * 0.78 + 0.003, fz + 0.002),
                       G(0.006, ey + R * 0.78 + 0.003, fz + 0.002), G(ix, ey + R * 0.8, fz)], 0.0011, 6, closed=False)
    ob = bm_to_obj(name, bm)
    return finish(ob, 4000, 0.0)


def build_eye_round(body, under):
    return build_glasses("eye_round", False)


def build_eye_shades(body, under):
    return build_glasses("eye_shades", True)


WATCH_T = 0.574  # along the left arm from the shoulder joint; long sleeves end at SLEEVE_T
SLEEVE_T = 0.562


def build_watch(name, digital, body=None):
    """Watch on the figure's LEFT wrist (+X), just past the long-sleeve cuffs so it shows with every top.
    The strap is shrunk onto the real wrist; the case faces out and a little forward."""
    from mathutils.bvhtree import BVHTree
    s, d, w, v = arm_frame(1)
    t = WATCH_T
    c = s + d * t
    tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get()) if body is not None else None
    bm = bmesh.new()
    tube_along(bm, s, d, w, v, [(t - 0.010, 0.05, 0.05), (t + 0.010, 0.05, 0.05)], seg=40, cap=False)
    if tree is not None:  # snug the strap onto the wrist
        for vert in bm.verts:
            loc, nrm, idx, dist = tree.find_nearest(vert.co, 0.08)
            if loc is not None:
                vert.co = loc + nrm * 0.003
    ob = bm_to_obj(name, bm)
    so = ob.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.0035
    so.offset = 0.0
    so.use_rim = True
    apply_mods(ob)
    nrm = (w * 0.8 - v).normalized()  # outward + toward the front, readable from the audience
    surf = 0.03
    if tree is not None:
        hit = tree.ray_cast(c + nrm * 0.12, -nrm, 0.2)[0]
        if hit is not None:
            surf = (hit - c).dot(nrm)
    face_c = c + nrm * (surf + 0.004)
    e2 = nrm.cross(d).normalized()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    if digital:
        loft(bm, [(face_c, d, e2, 0.017, 0.015, 4.0), (face_c + nrm * 0.009, d, e2, 0.017, 0.015, 4.0)], 24)
    else:
        loft(bm, [(face_c, d, e2, 0.019, 0.019, 2.0), (face_c + nrm * 0.008, d, e2, 0.019, 0.019, 2.0),
                  (face_c + nrm * 0.0095, d, e2, 0.016, 0.016, 2.0)], 32)
    bm.to_mesh(ob.data)
    bm.free()
    return finish(ob, 3000, 0.0)


def build_watch_analog(body, under):
    return build_watch("watch_analog", False, body)


def build_watch_digital(body, under):
    return build_watch("watch_digital", True, body)


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
    # push the centreline (not the tube) outside the neck/chest and any top, so the tube keeps its round section
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    trees = [(BVHTree.FromObject(t, dg), off) for t, off in [(body, 0.008)] + [(u, 0.0075) for u in under] if t]
    for _ in range(3):
        for i, p in enumerate(pts):
            for tree, off in trees:
                loc, nrm, idx, dist = tree.find_nearest(p, 0.08)
                if loc is not None and (p - loc).dot(nrm) < off:
                    p = loc + nrm * off
            pts[i] = p
        pts = [(pts[i - 1] + pts[i] * 2 + pts[(i + 1) % n]) / 4 for i in range(n)]
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
    return finish(ob, 3000, 0.0)


# ---------------------------------------------------------------- main
ORDER = [
    ("shoe_sneaker", build_shoe_sneaker, []),
    ("shoe_loafer", build_shoe_loafer, []),
    ("bottom_wide", build_bottom_wide, ["shoe_sneaker", "shoe_loafer"]),
    ("bottom_slim", build_bottom_slim, ["shoe_sneaker", "shoe_loafer"]),
    ("top_tee", build_top_tee, ["bottom_wide", "bottom_slim"]),
    ("top_shirt", build_top_shirt, ["bottom_wide", "bottom_slim"]),
    ("top_oversized", build_top_oversized, ["bottom_wide", "bottom_slim"]),
    ("outer_blazer", build_outer_blazer, ["top_tee", "top_shirt", "top_oversized", "bottom_wide", "bottom_slim"]),
    ("outer_overshirt", build_outer_overshirt, ["top_tee", "top_shirt", "top_oversized", "bottom_wide", "bottom_slim"]),
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
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                              export_draco_position_quantization=14, export_draco_normal_quantization=10,
                              export_draco_texcoord_quantization=12)
    print("WARDROBE: exported", OUT, os.path.getsize(OUT), "bytes;", ", ".join(built))
    if keep_body:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join("/tmp", "wardrobe_debug.blend"))


if __name__ == "__main__":
    main()
