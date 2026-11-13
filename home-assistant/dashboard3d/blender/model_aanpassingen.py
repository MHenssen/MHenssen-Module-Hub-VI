"""
Correcties op het Floorplanner-model, zodat het lijkt op het echte huis.
Wordt aangeroepen door render_lampgroepen.py, hotspots.py en fml_naar_glb.py,
direct na het laden van de verdiepingen.

  - Zonnepanelen kantelen: Floorplanner bewaart de kanteling als rotation_x /
    rotation_y in de FML, maar fml2blender negeert die. We lezen ze uit de FML
    (env FML_ALLE="a.fml:b.fml:c.fml") en zoeken het bijbehorende paneel op positie.
  - De losse balk die uit de zolder steekt weghalen (bestaat in het echt niet).
  - Bovenkant van het dakkapel wit.
  - Auto's in de lak van onze eigen auto's: zilvergrijze VW T4, donkerblauwe
    BMW iX3 (op straat) en grijsmetallic Audi Q4 (op de oprit, bij de laadpaal).
    Elke auto krijgt eigen materialen, zodat twee gelijke modellen een andere
    kleur kunnen krijgen.
"""
import json
import math
import os

import bpy
from mathutils import Vector

PANEEL_NAAM = "Solar panel"
WIT = (0.92, 0.92, 0.90)

# kleur, metaalachtig, ruwheid
LAK = {
    "t4": ((0.50, 0.52, 0.54), 0.85, 0.28),   # zilvergrijs metallic
    "ix3": ((0.010, 0.022, 0.065), 0.75, 0.22),  # donkerblauw metallic
    "q4": ((0.20, 0.21, 0.22), 0.85, 0.25),   # grijsmetallic
}
# welke materialen van een model de carrosserie zijn
CARROSSERIE = {
    "Vanagon": ("Material__3", "_6_-_Default"),
    "SUV": ("FINISH_Car_DarkBlue",),
}


def _wortel(o):
    while o.parent:
        o = o.parent
    return o


def _wereld_bbox(root):
    pts = [c.matrix_world @ Vector(b) for c in [root, *root.children_recursive] if c.type == "MESH" for b in c.bound_box]
    if not pts:
        return None, None
    return (Vector([min(p[i] for p in pts) for i in range(3)]),
            Vector([max(p[i] for p in pts) for i in range(3)]))


def _fml_items(paden):
    items = []

    def loop(o):
        if isinstance(o, dict):
            if "refid" in o and "x" in o:
                items.append(o)
            for v in o.values():
                loop(v)
        elif isinstance(o, list):
            for v in o:
                loop(v)

    for p in paden:
        try:
            loop(json.load(open(p, encoding="utf-8")))
        except OSError:
            print("FML niet gevonden:", p, flush=True)
    return items


def kantel_panelen(fml_paden):
    kantel = [i for i in _fml_items(fml_paden) if i.get("rotation_x") or i.get("rotation_y")]
    gedaan = 0
    for o in bpy.data.objects:
        if o.parent is not None or not o.name.startswith(PANEEL_NAAM):
            continue
        x, y = o.location.x, o.location.y
        # FML: cm, y naar beneden; Blender: m, y naar boven
        best = min(kantel, key=lambda i: (i["x"] / 100 - x) ** 2 + (-i["y"] / 100 - y) ** 2, default=None)
        if not best or math.hypot(best["x"] / 100 - x, -best["y"] / 100 - y) > 0.3:
            continue
        o.rotation_mode = "XYZ"
        o.rotation_euler.x = math.radians(best.get("rotation_x") or 0)
        o.rotation_euler.y = math.radians(best.get("rotation_y") or 0)
        gedaan += 1
    print("PANELEN GEKANTELD", gedaan, flush=True)


def verwijder_balk():
    """De lange balk (>5 m) die door de zoldergevel naar buiten steekt."""
    weg = 0
    for o in list(bpy.data.objects):
        if o.parent is None and "Beam" in o.name:
            mn, mx = _wereld_bbox(o)
            if mn is not None and max(mx.x - mn.x, mx.y - mn.y) > 5.0:
                for c in [*o.children_recursive, o]:
                    bpy.data.objects.remove(c, do_unlink=True)
                weg += 1
    print("BALK VERWIJDERD", weg, flush=True)


def _maak_wit(m):
    if not m or not m.use_nodes:
        return
    for b in m.node_tree.nodes:
        if b.type == "BSDF_PRINCIPLED":
            for link in list(b.inputs["Base Color"].links):
                m.node_tree.links.remove(link)
            b.inputs["Base Color"].default_value = (*WIT, 1)


def dakkapel_wit():
    """Het dakkapel en alles wat er bovenop ligt (dakbedekking, randen) wit."""
    dk = bpy.data.objects.get("dakkapel")
    if not dk:
        return
    mn, mx = _wereld_bbox(dk)
    n = 0
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        a, b = _wereld_bbox(o)
        if a is None:
            continue
        # vlak object dat binnen de voetafdruk van het dakkapel op of boven de bovenkant ligt
        if (a.x >= mn.x - 0.3 and b.x <= mx.x + 0.3 and a.y >= mn.y - 0.3 and b.y <= mx.y + 0.3
                and a.z >= mn.z - 0.25 and (b.z - a.z) < 0.6):
            for s in o.material_slots:
                if s.material:
                    s.material = s.material.copy()
                    _maak_wit(s.material)
            n += 1
    print("DAKKAPEL WIT", n, flush=True)


def _lak(m, kleur, metaal, ruw):
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not b:
        return
    for link in list(b.inputs["Base Color"].links):
        m.node_tree.links.remove(link)
    b.inputs["Base Color"].default_value = (*kleur, 1)
    b.inputs["Metallic"].default_value = metaal
    b.inputs["Roughness"].default_value = ruw
    if "Coat Weight" in b.inputs:  # blanke lak
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Coat Roughness"].default_value = 0.05


def auto_lak():
    for root in [o for o in bpy.data.objects if o.parent is None and o.name.startswith("CAR - ")]:
        if "Vanagon" in root.name:
            soort, sleutel = "t4", "Vanagon"
        elif "SUV" in root.name:
            # de SUV op de oprit (links, bij de laadpaal) is de Q4, die op straat de iX3
            soort, sleutel = ("q4" if root.matrix_world.translation.x < -10 else "ix3"), "SUV"
        else:
            continue
        kopie = {}
        for o in [root, *root.children_recursive]:
            if o.type != "MESH":
                continue
            for s in o.material_slots:
                m = s.material
                if m and m.node_tree and m.name.startswith(CARROSSERIE[sleutel]):
                    if m.name not in kopie:
                        kopie[m.name] = m.copy()
                        _lak(kopie[m.name], *LAK[soort])
                    s.link = "OBJECT"
                    s.material = kopie[m.name]
        print("AUTO", root.name, soort, len(kopie), flush=True)


def pas_toe():
    fml = [p for p in os.environ.get("FML_ALLE", "").split(":") if p]
    if fml:
        kantel_panelen(fml)
    verwijder_balk()
    dakkapel_wit()
    auto_lak()
    bpy.context.view_layer.update()
