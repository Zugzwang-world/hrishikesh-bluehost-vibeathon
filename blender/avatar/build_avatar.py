"""Build the designer-toy avatar and export web/public/models/avatar.glb.

Run headless from the repo root:
    /opt/homebrew/bin/blender -b --python blender/avatar/build_avatar.py

Everything is generated in code (no downloaded assets). All geometry is authored
in glTF coordinates (metres, Y up, figure faces +Z) and converted to Blender's
Z-up frame on the way in; the glTF exporter converts back.
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_GLB = os.path.join(ROOT, "web", "public", "models", "avatar.glb")
OUT_BLEND = os.path.join(HERE, "avatar.blend")

# ---------------------------------------------------------------- look
SKIN_SRGB = (0x8A, 0x5A, 0x3C)
HAIR_SRGB = (0x17, 0x13, 0x12)
SKIN_ROUGH = 0.55
HAIR_ROUGH = 0.78

# ---------------------------------------------------------------- budgets
BODY_TRIS = 23000
HAIR_TRIS = 6500
CAPPED_TRIS = 1800
BEARD_TRIS = 2600

# ---------------------------------------------------------------- landmarks (glTF frame)
SH_X, SH_Y = 0.19, 1.42
ARM_ANGLE = math.radians(30.0)
ELBOW_T, WRIST_T, TIP_T = 0.29, 0.55, 0.74
SLEEVE_T = 0.18

HEAD_C = Vector((0.0, 1.6225, 0.008))
HEAD_R = Vector((0.0865, 0.1225, 0.102))


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def g2b(p):
    return (p[0], -p[2], p[1])


def arm_frame(s):
    J = Vector((SH_X * s, SH_Y, 0.0))
    d = Vector((math.sin(ARM_ANGLE) * s, -math.cos(ARM_ANGLE), 0.0))
    n = Vector((-math.cos(ARM_ANGLE) * s, -math.sin(ARM_ANGLE), 0.0))  # palm normal, toward thigh
    return J, d, n


# ---------------------------------------------------------------- mesh builder
class MB:
    def __init__(self):
        self.v = []
        self.f = []

    def loft(self, rows, cap0=None, cap1=None, closed=True):
        n = len(rows[0])
        base = len(self.v)
        for r in rows:
            self.v.extend([tuple(p) for p in r])
        m = n if closed else n - 1
        for j in range(len(rows) - 1):
            for i in range(m):
                a = base + j * n + i
                b = base + j * n + (i + 1) % n
                self.f.append((a, b, b + n, a + n))
        if cap0 is not None:
            ci = len(self.v)
            self.v.append(tuple(cap0))
            for i in range(m):
                self.f.append((base + (i + 1) % n, base + i, ci))
        if cap1 is not None:
            ci = len(self.v)
            self.v.append(tuple(cap1))
            last = base + (len(rows) - 1) * n
            for i in range(m):
                self.f.append((last + i, last + (i + 1) % n, ci))

    def ellipsoid(self, c, a0, a1, a2, nu=32, nv=18, fn=None):
        """a1 is the pole axis. fn(point, unit) may deform a point."""
        c = Vector(c)
        a0, a1, a2 = Vector(a0), Vector(a1), Vector(a2)
        rows = []
        for j in range(1, nv):
            v = math.pi * j / nv
            row = []
            for i in range(nu):
                u = 2 * math.pi * i / nu
                un = (math.sin(v) * math.cos(u), math.cos(v), math.sin(v) * math.sin(u))
                p = c + a0 * un[0] + a1 * un[1] + a2 * un[2]
                if fn:
                    p = fn(p, un)
                row.append(p)
            rows.append(row)
        top = c + a1
        bot = c - a1
        if fn:
            top = fn(top, (0, 1, 0))
            bot = fn(bot, (0, -1, 0))
        self.loft(rows, cap0=top, cap1=bot)

    def sphere(self, c, r, nu=28, nv=14):
        self.ellipsoid(c, (r, 0, 0), (0, r, 0), (0, 0, r), nu, nv)

    def tube(self, A, B, prof, n=32):
        A, B = Vector(A), Vector(B)
        d = B - A
        L = d.length
        d.normalize()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        e1 = d.cross(ref).normalized()
        e2 = d.cross(e1).normalized()
        rows = []
        for t, r in prof:
            c = A + d * (L * t)
            rows.append([c + (e1 * math.cos(2 * math.pi * i / n) + e2 * math.sin(2 * math.pi * i / n)) * r
                         for i in range(n)])
        self.loft(rows, cap0=A, cap1=B)

    def to_object(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata([g2b(p) for p in self.v], [], self.f)
        me.validate(clean_customdata=False)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def catmull(keys, step):
    """Resample (y, a, b, c) keys with a Catmull-Rom spline every `step` in y."""
    out = []
    k = [keys[0]] + list(keys) + [keys[-1]]
    for i in range(1, len(k) - 2):
        p0, p1, p2, p3 = k[i - 1], k[i], k[i + 1], k[i + 2]
        n = max(1, int(round((p2[0] - p1[0]) / step)))
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[q]) + (-p0[q] + p2[q]) * t + (2 * p0[q] - 5 * p1[q] + 4 * p2[q] - p3[q]) * t2
                                    + (-p0[q] + 3 * p1[q] - 3 * p2[q] + p3[q]) * t3) for q in range(4)))
    out.append(keys[-1])
    return out


def superellipse_ring(y, hw, hd, cz=0.0, n=56, e=2.5):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        x = hw * math.copysign(abs(c) ** (2 / e), c)
        z = hd * math.copysign(abs(s) ** (2 / e), s)
        pts.append(Vector((x, y, cz + z)))
    return pts


# ---------------------------------------------------------------- head surface
def head_point(u, v, off=0.0):
    """u: azimuth from +Z toward +X, v: polar angle from top. Returns glTF point."""
    un = Vector((math.sin(v) * math.sin(u), math.cos(v), math.sin(v) * math.cos(u)))
    p = Vector((HEAD_R.x * un.x, HEAD_R.y * un.y, HEAD_R.z * un.z))
    nrm = Vector((un.x / HEAD_R.x, un.y / HEAD_R.y, un.z / HEAD_R.z)).normalized()
    s = max(0.0, -un.y)
    p.x *= 1.0 - 0.13 * s * s
    p.z += 0.016 * s * s
    # slightly flatter face plane, fuller back of skull
    if un.z > 0:
        p.z *= 1.0 - 0.04 * un.z * (1 - s)
    return HEAD_C + p + nrm * off


def head_deform(p, un):
    return head_point(math.atan2(un[0], un[2]), math.acos(max(-1, min(1, un[1]))))


# ---------------------------------------------------------------- body primitives
def build_body_mb():
    mb = MB()
    # torso loft: (y, half width, half depth, z centre), Catmull-Rom resampled
    rings = [
        (0.830, 0.100, 0.075, -0.005),
        (0.865, 0.160, 0.112, -0.010),
        (0.920, 0.180, 0.120, -0.012),
        (0.975, 0.170, 0.112, -0.006),
        (1.050, 0.150, 0.105, 0.000),
        (1.150, 0.163, 0.113, 0.006),
        (1.250, 0.180, 0.120, 0.010),
        (1.330, 0.186, 0.115, 0.004),
        (1.390, 0.182, 0.100, -0.004),
        (1.430, 0.160, 0.082, -0.010),
        (1.460, 0.095, 0.065, -0.012),
        (1.470, 0.040, 0.040, -0.012),
    ]
    rows = [superellipse_ring(y, hw, hd, cz) for (y, hw, hd, cz) in catmull(rings, 0.008)]
    mb.loft(rows, cap0=(0, 0.828, -0.005), cap1=(0, 1.472, -0.012))
    # trapezius: soften the neck-to-shoulder line
    for s in (1, -1):
        mb.ellipsoid((0.10 * s, 1.425, -0.012), (0.095, 0, 0), (0, 0.040, 0), (0, 0, 0.070), nu=32, nv=14)
    # neck
    mb.tube((0, 1.40, -0.014), (0, 1.60, -0.006), [(0, 0.068), (0.3, 0.063), (0.6, 0.061), (1, 0.060)], n=32)
    # head
    mb.ellipsoid(HEAD_C, (HEAD_R.x, 0, 0), (0, HEAD_R.y, 0), (0, 0, HEAD_R.z), nu=64, nv=40, fn=head_deform)
    for s in (1, -1):
        # ears
        mb.ellipsoid((0.080 * s, 1.612, -0.008), (0.013, 0, 0), (0, 0.030, 0), (0, 0, 0.020), nu=20, nv=12)
    # nose bump (subtle)
    mb.ellipsoid((0, 1.597, 0.101), (0.0135, 0, 0), (0, 0.018, 0), (0, 0, 0.015), nu=20, nv=12)

    for s in (1, -1):
        J, d, n = arm_frame(s)
        E = J + d * ELBOW_T
        W = J + d * WRIST_T
        mb.sphere(J + Vector((0.004 * s, -0.004, 0)), 0.054)
        mb.tube(J, E, [(0, 0.052), (0.35, 0.049), (0.75, 0.043), (1, 0.040)])
        mb.sphere(E, 0.040, 24, 12)
        mb.tube(E, W, [(0, 0.040), (0.25, 0.042), (0.7, 0.035), (1, 0.029)])
        mb.sphere(W, 0.029, 24, 12)
        # mitten hand: palm faces the thigh
        z = Vector((0, 0, 1))
        hc = J + d * 0.645
        mb.ellipsoid(hc, d * 0.097, n * 0.023, z * 0.047, nu=28, nv=16)
        tdir = (d * 0.85 + z * 0.5).normalized()
        tc = J + d * 0.60 + z * 0.040 + n * 0.006
        mb.ellipsoid(tc, tdir * 0.040, n * 0.015, n.cross(tdir).normalized() * 0.016, nu=20, nv=12)

        # legs
        hip = Vector((0.096 * s, 0.90, -0.006))
        K = Vector((0.100 * s, 0.49, 0.008))
        A = Vector((0.105 * s, 0.085, -0.008))
        mb.tube(hip, K, [(0, 0.090), (0.25, 0.085), (0.6, 0.070), (0.9, 0.058), (1, 0.056)])
        mb.sphere(K, 0.055, 24, 12)
        mb.tube(K, A, [(0, 0.053), (0.18, 0.057), (0.35, 0.055), (0.7, 0.043), (1, 0.036)])
        mb.ellipsoid((0.102 * s, 0.37, -0.016), (0.050, 0, 0), (0, 0.10, 0), (0, 0, 0.050), nu=24, nv=12)
        mb.sphere(A, 0.037, 24, 12)
        # feet: heel z -0.06, toe z +0.21, width 0.10, sole clipped at y = 0
        mb.ellipsoid((0.110 * s, 0.040, -0.012), (0.043, 0, 0), (0, 0.050, 0), (0, 0, 0.048), nu=24, nv=12)
        mb.ellipsoid((0.110 * s, 0.033, 0.070), (0.049, 0, 0), (0, 0.043, 0), (0, 0, 0.095), nu=28, nv=12)
        mb.ellipsoid((0.113 * s, 0.024, 0.150), (0.050, 0, 0), (0, 0.034, 0), (0, 0, 0.060), nu=24, nv=12)
    return mb


# ---------------------------------------------------------------- hair / beard shells
def lerp_table(tab, x):
    x = abs(x)
    for (x0, y0), (x1, y1) in zip(tab, tab[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * t
    return tab[-1][1]


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def shell(mb, u0, u1, nu, vmin_fn, vmax_fn, nv, off_fn, inner=-0.006, closed=False):
    outer_rows, inner_rows = [], []
    count = nu if closed else nu + 1
    for i in range(count):
        u = u0 + (u1 - u0) * i / nu
        va, vb = vmin_fn(u), vmax_fn(u)
        orow, irow = [], []
        for j in range(nv + 1):
            v = va + (vb - va) * j / nv
            orow.append(head_point(u, v, off_fn(u, v, va, vb)))
            irow.append(head_point(u, v, inner))
        outer_rows.append(orow)
        inner_rows.append(irow)
    # outer and inner sheets as lofts along u
    base = len(mb.v)
    cols = count
    for r in outer_rows:
        mb.v.extend(r)
    for r in inner_rows:
        mb.v.extend(r)
    m = nv + 1
    ib = base + cols * m

    def O(i, j):
        return base + (i % cols) * m + j

    def I(i, j):
        return ib + (i % cols) * m + j

    ilim = cols if closed else cols - 1
    for i in range(ilim):
        for j in range(nv):
            mb.f.append((O(i, j), O(i, j + 1), O(i + 1, j + 1), O(i + 1, j)))
            mb.f.append((I(i, j), I(i + 1, j), I(i + 1, j + 1), I(i, j + 1)))
        # walls at v boundaries
        mb.f.append((O(i, 0), O(i + 1, 0), I(i + 1, 0), I(i, 0)))
        mb.f.append((O(i, nv), I(i, nv), I(i + 1, nv), O(i + 1, nv)))
    if not closed:
        for j in range(nv):
            mb.f.append((O(0, j), I(0, j), I(0, j + 1), O(0, j + 1)))
            mb.f.append((O(cols - 1, j), O(cols - 1, j + 1), I(cols - 1, j + 1), I(cols - 1, j)))


D = math.radians
HAIRLINE = [(0, 70), (25, 70), (45, 75), (60, 84), (68, 100), (80, 100), (86, 80), (110, 78),
            (122, 94), (145, 113), (180, 121)]
PART_X = 0.034  # side part on the figure's left (+X)


def hair_full_off(u, v, va, vb):
    p = head_point(u, v)
    rel = p - HEAD_C
    off = 0.0065 + 0.0045 * smoothstep(-0.02, 0.08, rel.y)
    # volume on top, heavier toward the sweep side (-X) and front
    top = math.exp(-((v - D(15)) / D(40)) ** 2)
    off += 0.030 * top * (1.0 + 0.40 * max(-1.0, min(1.0, -rel.x / HEAD_R.x)))
    front = math.exp(-((u) / D(45)) ** 2) * math.exp(-((v - D(40)) / D(22)) ** 2)
    off += 0.024 * front
    # side part groove, front to crown
    if rel.y > 0.06 and rel.z > -0.06:
        g = math.exp(-((rel.x - PART_X) / 0.005) ** 2)
        off -= 0.009 * g * smoothstep(0.06, 0.09, rel.y)
    # swept strand clumps: on top they fan back from the front part, on the sides they run back
    if rel.y > 0.0:
        ang = math.atan2(rel.x - PART_X, rel.z + 0.16)
        off -= 0.0055 * (0.5 + 0.5 * math.cos(ang * 16)) ** 3 * smoothstep(0.0, 0.07, rel.y)
    side = 1.0 - smoothstep(0.02, 0.08, rel.y)
    if side > 0:
        off -= 0.0022 * side * (0.5 + 0.5 * math.cos(rel.y * 260 + rel.z * 40)) ** 2
    # taper to the hairline
    t = smoothstep(0.0, D(18), vb - v)
    return 0.0008 + (off - 0.0008) * t


def hair_capped_off(u, v, va, vb):
    # where the hairline sits above the cap line (forehead, over the ears) there is no hair: sink it
    hl = D(lerp_table(HAIRLINE, math.degrees(u)))
    sink = smoothstep(CAP_V + D(2), CAP_V + D(7), hl)
    t = smoothstep(0.0, D(10), vb - v) * smoothstep(0.0, D(6), v - va)
    return (0.002 + 0.0045 * t) * sink - 0.0045 * (1 - sink)


CAP_V = math.acos((1.62 - HEAD_C.y) / HEAD_R.y)  # polar angle of the cap line


BEARD_TOP = [(0, 106), (16, 107), (28, 111), (42, 113), (58, 108), (72, 101), (84, 98)]
BEARD_BOT = [(0, 164), (30, 157), (55, 145), (70, 131), (84, 118)]


def beard_off(u, v, va, vb):
    off = 0.0062
    chin = math.exp(-(u / D(26)) ** 2) * math.exp(-((v - D(142)) / D(16)) ** 2)
    off += 0.0045 * chin
    must = math.exp(-(u / D(20)) ** 2) * math.exp(-((v - D(111)) / D(5)) ** 2)
    off += 0.0025 * must
    t = smoothstep(0.0, D(8), vb - v) * smoothstep(0.0, D(6), v - va)
    tu = smoothstep(0.0, D(10), D(84) - abs(u))
    off = 0.002 + (off - 0.002) * t * tu
    # mouth opening: skin shows through, so the shape reads as moustache + beard
    m = math.exp(-(u / D(17)) ** 4) * math.exp(-((v - D(118.5)) / D(4.2)) ** 4)
    return off * (1 - m) - 0.0045 * m


def build_hair_full():
    mb = MB()
    shell(mb, -math.pi, math.pi, 120, lambda u: 0.0, lambda u: D(lerp_table(HAIRLINE, math.degrees(u))),
          36, hair_full_off, inner=-0.004, closed=True)
    return mb


def build_hair_capped():
    mb = MB()
    shell(mb, -math.pi, math.pi, 120, lambda u: CAP_V,
          lambda u: max(CAP_V + D(1), D(lerp_table(HAIRLINE, math.degrees(u)))),
          12, hair_capped_off, closed=True)
    return mb


def build_beard():
    mb = MB()
    shell(mb, -D(84), D(84), 64, lambda u: D(lerp_table(BEARD_TOP, math.degrees(u))),
          lambda u: D(lerp_table(BEARD_BOT, math.degrees(u))), 28, beard_off, closed=False)
    return mb


# ---------------------------------------------------------------- modifier baking
def bake(ob, mods):
    for i, (typ, props) in enumerate(mods):
        md = ob.modifiers.new("m%d" % i, typ)
        for k, val in props.items():
            setattr(md, k, val)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    ob.modifiers.clear()
    old = ob.data
    me.validate()
    ob.data = me
    bpy.data.meshes.remove(old)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def remesh_smooth_decimate(ob, voxel, smooth_iter, smooth_fac, target):
    bake(ob, [("REMESH", dict(mode="VOXEL", voxel_size=voxel, adaptivity=0.0)),
              ("SMOOTH", dict(factor=smooth_fac, iterations=smooth_iter))])
    tc = tri_count(ob)
    if tc > target:
        bake(ob, [("DECIMATE", dict(decimate_type="COLLAPSE", ratio=target / tc))])


# ---------------------------------------------------------------- region split
REGIONS = ["body_head", "body_neck", "body_torso", "body_hips",
           "body_upperarm_L", "body_upperarm_R", "body_forearm_L", "body_forearm_R",
           "body_hand_L", "body_hand_R", "body_thigh_L", "body_thigh_R",
           "body_shin_L", "body_shin_R", "body_foot_L", "body_foot_R"]


def arm_radius(t):
    tab = [(0.0, 0.056), (0.10, 0.052), (0.29, 0.042), (0.42, 0.042), (0.55, 0.031), (0.60, 0.05), (0.74, 0.05),
           (1.0, 0.05)]
    return lerp_table(tab, max(0.0, t))


def arm_info(c):
    s = 1 if c.x >= 0 else -1
    J, d, n = arm_frame(s)
    v = c - J
    t = v.dot(d)
    perp = (v - d * t).length
    is_arm = t > 0.02 and perp < arm_radius(t) + (0.035 if t > 0.5 else 0.012)
    return s, t, is_arm


def classify(c):
    """c: glTF-space face centre."""
    s, t, is_arm = arm_info(c)
    side = "L" if s > 0 else "R"
    rn = math.hypot(c.x, c.z + 0.01)
    if c.y > 1.50 and rn < 0.17:
        return "body_head"
    if c.y > 1.44 and rn < 0.09:
        return "body_neck"
    if is_arm:
        if t < SLEEVE_T:
            return "body_upperarm_" + side
        if t < WRIST_T:
            return "body_forearm_" + side
        return "body_hand_" + side
    if c.y > 1.00:
        return "body_torso"
    if c.y > 0.80:
        return "body_hips"
    if c.y > 0.49:
        return "body_thigh_" + side
    if c.y > 0.10:
        return "body_shin_" + side
    return "body_foot_" + side


def b2g(co):
    return Vector((co.x, co.z, -co.y))


def split_body(ob, skin):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    # flat sole
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                           plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)
    holes = [e for e in bm.edges if e.is_boundary]
    if holes:
        bmesh.ops.holes_fill(bm, edges=holes, sides=0)

    def faces_where(pred):
        out = []
        for f in bm.faces:
            if pred(b2g(f.calc_center_median())):
                out.append(f)
        return out

    def cut(faces, co_g, no_g):
        if not faces:
            return
        es = set()
        vs = set()
        for f in faces:
            es.update(f.edges)
            vs.update(f.verts)
        bmesh.ops.bisect_plane(bm, geom=list(vs) + list(es) + faces, dist=1e-6,
                               plane_co=g2b(co_g), plane_no=g2b(no_g))

    # neck / head cuts
    for y in (1.50, 1.44):
        cut(faces_where(lambda c, y=y: abs(c.y - y) < 0.03 and math.hypot(c.x, c.z + 0.01) < 0.1),
            (0, y, 0), (0, 1, 0))
    # trunk and leg cuts
    for y in (1.00, 0.80, 0.49, 0.10):
        cut(faces_where(lambda c, y=y: abs(c.y - y) < 0.03 and not arm_info(c)[2]), (0, y, 0), (0, 1, 0))
    # arm cuts
    for s in (1, -1):
        J, d, n = arm_frame(s)
        for tc in (SLEEVE_T, WRIST_T):
            def pred(c, s=s, tc=tc):
                ss, t, isa = arm_info(c)
                return ss == s and isa and abs(t - tc) < 0.03
            cut(faces_where(pred), J + d * tc, d)

    bm.normal_update()
    lay = bm.faces.layers.int.new("region")
    lx = bm.verts.layers.float.new("nx")
    ly = bm.verts.layers.float.new("ny")
    lz = bm.verts.layers.float.new("nz")
    for v in bm.verts:
        v[lx], v[ly], v[lz] = v.normal
    for f in bm.faces:
        f[lay] = REGIONS.index(classify(b2g(f.calc_center_median())))

    objs = []
    for ri, name in enumerate(REGIONS):
        b = bm.copy()
        l2 = b.faces.layers.int["region"]
        kill = [f for f in b.faces if f[l2] != ri]
        bmesh.ops.delete(b, geom=kill, context="FACES")
        loose = [v for v in b.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(b, geom=loose, context="VERTS")
        b.verts.index_update()
        x2, y2, z2 = (b.verts.layers.float["nx"], b.verts.layers.float["ny"], b.verts.layers.float["nz"])
        normals = [(v[x2], v[y2], v[z2]) for v in b.verts]
        me = bpy.data.meshes.new(name)
        b.to_mesh(me)
        b.free()
        for an in ("nx", "ny", "nz", "region"):
            a = me.attributes.get(an)
            if a:
                me.attributes.remove(a)
        me.shade_smooth()
        try:
            me.normals_split_custom_set_from_vertices(normals)
        except Exception as ex:  # pragma: no cover
            print("custom normals failed", ex)
        me.materials.append(skin)
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        objs.append(o)
        print("region", name, len(me.polygons))
    bm.free()
    bpy.data.objects.remove(ob)
    return objs


# ---------------------------------------------------------------- materials
def make_material(name, srgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    col = tuple(srgb_to_linear(c) for c in srgb) + (1.0,)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    m.diffuse_color = col
    return m


# ---------------------------------------------------------------- main
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    skin = make_material("skin", SKIN_SRGB, SKIN_ROUGH)
    hair = make_material("hair", HAIR_SRGB, HAIR_ROUGH)

    body = build_body_mb().to_object("body_tmp")
    remesh_smooth_decimate(body, 0.0055, 20, 0.7, BODY_TRIS)
    split_body(body, skin)

    for name, builder, target, voxel in (("hair_full", build_hair_full, HAIR_TRIS, 0.0028),
                                          ("hair_capped", build_hair_capped, CAPPED_TRIS, 0.0025),
                                          ("beard", build_beard, BEARD_TRIS, 0.0025)):
        ob = builder().to_object(name)
        remesh_smooth_decimate(ob, voxel, 4, 0.5, target)
        ob.data.shade_smooth()
        ob.data.materials.append(hair)
        print(name, tri_count(ob))

    total = sum(tri_count(o) for o in bpy.context.scene.objects if o.type == "MESH")
    print("TOTAL TRIS", total)

    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    kw = dict(filepath=OUT_GLB, export_format="GLB", export_yup=True, export_apply=True,
              export_texcoords=False, export_normals=True, export_materials="EXPORT")
    try:
        bpy.ops.export_scene.gltf(export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=14,
                                  export_draco_normal_quantization=12, **kw)
    except Exception as ex:
        print("Draco export failed, exporting uncompressed:", ex)
        bpy.ops.export_scene.gltf(**kw)
    print("GLB bytes", os.path.getsize(OUT_GLB))
    if "--save" in sys.argv:
        bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


main()
