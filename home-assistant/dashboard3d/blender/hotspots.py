"""
Berekent waar elke lampgroep (en elk energielabel) op de render staat, in %
van breedte/hoogte, met exact dezelfde camera als render_lampgroepen.py.

  CAMERA=boven|achter|voor [EXTRA_BLENDS=a.blend:b.blend] \
  python hotspots.py -- huis_v1.blend groepen.json v1 uitmap/ weergave_id

Schrijft uitmap/<weergave_id>.json (groepen) en uitmap/<weergave_id>_labels.json.
"""
import json
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashcam import huis_bounds, maak_camera  # noqa: E402

blend, groepen_pad, sleutel, uitmap, wid = sys.argv[sys.argv.index("--") + 1:][:5]
CAMERA = os.environ.get("CAMERA", "boven")
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for extra in filter(None, os.environ.get("EXTRA_BLENDS", "").split(":")):
    with bpy.data.libraries.load(extra, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None and o.type != "CAMERA":
            sc.collection.objects.link(o)
sc.render.resolution_x = int(os.environ.get("RES_X", "1600"))
sc.render.resolution_y = int(os.environ.get("RES_Y", "1067"))
groepen = json.load(open(groepen_pad)).get(sleutel, {})
co, vloer = maak_camera(sc, CAMERA)


def scherm(p):
    v = world_to_camera_view(sc, co, p)
    return {"x": round(min(97, max(3, v.x * 100)), 1), "y": round(min(95, max(5, (1 - v.y) * 100)), 1)}


res = {}
for g, posities in groepen.items():
    x = sum(p[0] for p in posities) / len(posities)
    y = sum(p[1] for p in posities) / len(posities)
    res[g] = scherm(Vector((x, y, vloer + 1.0)))

# energielabels: zon boven de zonnepanelen, net/laadpaal aan de straatkant, huis in het midden
mn, mx = huis_bounds(min_x=-30 if CAMERA == "voor" else -6.5)
mid = (mn + mx) / 2
pv = [o for o in bpy.data.objects if o.type == "MESH"
      and any(w in o.name.lower() for w in ("solar", "pv", "zonnepan", "paneel"))]
if pv:
    zon = sum((o.matrix_world.translation for o in pv), Vector()) / len(pv) + Vector((0, 0, 1.5))
else:
    zon = Vector((mid.x, mid.y, mx.z + 1.0))
punten = {
    "zon": zon,
    "huis": Vector((mid.x, mid.y, mn.z + 2.0)),
    "net": Vector((mid.x + 2.0, mn.y, mn.z + 1.0)),
    "laadpaal": Vector((mn.x + 1.5, mn.y - 2.0, mn.z + 1.0)),
}
# LABELS=labels.json overschrijft punten: {"zon": [x, y, z], ...} in Blender-meters
if os.environ.get("LABELS"):
    for k, v in json.load(open(os.environ["LABELS"])).items():
        punten[k] = Vector(v)
labels = {k: scherm(v) for k, v in punten.items()}
os.makedirs(uitmap, exist_ok=True)
json.dump(res, open(os.path.join(uitmap, f"{wid}.json"), "w"), indent=1)
json.dump(labels, open(os.path.join(uitmap, f"{wid}_labels.json"), "w"), indent=1)
print("HOTSPOTS", wid, res, labels)
