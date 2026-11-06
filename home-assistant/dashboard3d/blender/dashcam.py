"""
Gedeelde dashboardcamera voor render_lampgroepen.py en hotspots.py.
Beide scripts moeten exact dezelfde camera gebruiken, anders kloppen de
hotspots (klikpunten) niet met de render.

soort:
  boven   schuin van boven, orthografisch, één verdieping (isometrisch)
  achter  perspectief vanaf de tuinkant, hele huis
  voor    perspectief vanaf de straatkant (-y), hele huis
"""
import math

import bpy
from mathutils import Vector

DAK_WOORDEN = ("roof", "dak")


def huis_bounds(min_x=-6.5):
    """Bounding box van de muren van het hoofdhuis (schuur/garage links vallen erbuiten)."""
    walls = [o for o in bpy.data.objects if o.type == "MESH" and "Wall" in o.name]
    pts = [o.matrix_world @ Vector(c) for o in walls for c in o.bound_box]
    pts = [p for p in pts if p.x > min_x] or pts
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def _namen(o):
    """Naam van het object en van al zijn ouders (meubels zijn vaak een boom van meshes)."""
    while o is not None:
        yield o.name.lower()
        o = o.parent


def verberg_daken():
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if any(w in n for n in _namen(o) for w in DAK_WOORDEN):
            o.hide_render = True
        # schuine dakvlakken van fml2blender heten "Surface.xxx" en zijn meters hoog
        elif o.name.startswith("Surface") and o.dimensions.z > 1.5 and o.parent is None:
            o.hide_render = True


def _hoeken(mn, mx):
    return [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]


def maak_camera(sc, soort="boven", marge=1.06):
    """Maakt de camera, past hem passend om het huis en geeft (camera_object, vloerhoogte)."""
    # Voor: ook de garage links in beeld (daar staat de laadpaal op de oprit)
    mn, mx = huis_bounds(min_x=-30 if soort == "voor" else -6.5)
    vloer = mn.z
    if soort == "boven":
        mx = Vector((mx.x, mx.y, vloer + 2.6))  # alleen deze verdieping, tot net onder het plafond
    breed, hoog = sc.render.resolution_x, sc.render.resolution_y
    mid = (mn + mx) / 2
    cam = bpy.data.cameras.new("dashboard_cam")
    co = bpy.data.objects.new("dashboard_cam", cam)
    sc.collection.objects.link(co)
    sc.camera = co
    cam.sensor_fit = "HORIZONTAL"
    hoeken = _hoeken(mn, mx)

    if soort == "boven":
        cam.type = "ORTHO"
        richting = Vector((8, -8, 11)).normalized()
        co.location = mid + richting * 40
        co.rotation_euler = (-richting).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        inv = co.matrix_world.inverted()
        lok = [inv @ p for p in hoeken]
        x0, x1 = min(p.x for p in lok), max(p.x for p in lok)
        y0, y1 = min(p.y for p in lok), max(p.y for p in lok)
        # camera verschuiven naar het midden van het huis in beeld
        rot = co.matrix_world.to_3x3()
        co.location += rot @ Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
        cam.ortho_scale = max(x1 - x0, (y1 - y0) * breed / hoog) * marge
    else:
        cam.lens = 35
        richting = Vector((0.55, -1.0, 0.75)) if soort == "voor" else Vector((0.6, 1.0, 0.8))
        richting.normalize()
        doel = mid
        tan_h = (cam.sensor_width / 2) / cam.lens
        tan_v = tan_h * hoog / breed
        afstand = 5.0
        while afstand < 200:
            co.location = doel + richting * afstand
            co.rotation_euler = (-richting).to_track_quat("-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            inv = co.matrix_world.inverted()
            past = True
            for p in hoeken:
                q = inv @ p
                diepte = -q.z
                if diepte <= 0.1 or abs(q.x) / diepte > tan_h / marge or abs(q.y) / diepte > tan_v / marge:
                    past = False
                    break
            if past:
                break
            afstand += 0.25
    bpy.context.view_layer.update()
    return co, vloer
