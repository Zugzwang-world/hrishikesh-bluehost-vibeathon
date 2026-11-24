"""Inspect stage.glb: node names, hooks, materials, extensions, size.

    python3 blender/stage/check_glb.py [path]
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "web", "public", "models", "stage.glb")
data = open(path, "rb").read()
magic, ver, length = struct.unpack("<III", data[:12])
clen, ctype = struct.unpack("<II", data[12:20])
gltf = json.loads(data[20:20 + clen])

nodes = {n.get("name"): n for n in gltf.get("nodes", [])}
mats = [m.get("name") for m in gltf.get("materials", [])]
HOOKS = ["cam_fit", "cam_wide", "cam_audience", "cam_close",
         "cam_fit_target", "cam_wide_target", "cam_audience_target", "cam_close_target",
         "spot_L", "spot_R", "spot_C", "spot_target_L", "spot_target_R", "spot_target_C",
         "avatar_fit", "mark_center"]
REQ_MATS = ["led_wall", "led_strip", "center_mark", "light_cone"]

print("size bytes", os.path.getsize(path))
print("extensionsUsed", gltf.get("extensionsUsed"))
print("materials", mats)
missing = [h for h in HOOKS if h not in nodes]
print("missing hooks", missing)
print("missing materials", [m for m in REQ_MATS if m not in mats])
for h in HOOKS:
    n = nodes.get(h)
    if n:
        print(f"  {h:22s} {[round(v, 3) for v in n.get('translation', [0, 0, 0])]} mesh={'mesh' in n}")
print("mesh nodes", [n for n, v in nodes.items() if "mesh" in v])
lights = gltf.get("extensions", {}).get("KHR_lights_punctual")
print("lights", bool(lights), "cameras", len(gltf.get("cameras", [])))
sys.exit(1 if missing else 0)
