"""
Floorplanner (.fml) -> Blender -> huis.glb voor het 3D-dashboard.

Bouwt een licht model (geen meubelmodellen van Floorplanner nodig):
- muren met uitsparingen voor ramen en deuren
- vloeren per kamer (kamernaam uit Floorplanner)
- lampen als kleine bolletjes met een vaste naam (lamp_v1_01, ...)
- zonnepanelen als losse platen (pv_v2_01, ...)
- meubels als eenvoudige blokken (optioneel)
- daken, schoorsteen en terrein

Elke verdieping is een eigen hoofdnode in de glb (verdieping_1, verdieping_2,
verdieping_3) met daaronder groepen (muren, vloeren, lampen, ...), zodat het
dashboard verdiepingen los kan tonen of verbergen.

Gebruik (Blender als Python-module, of in Blender zelf):
    python fml_naar_glb.py --uit huis.glb [--blend huis.blend] [--geen-meubels] \
        verdieping1.fml verdieping2.fml verdieping3.fml

Volgorde van de bestanden = volgorde van de verdiepingen (onder naar boven).
"""

import argparse
import json
import math
import os
import sys
from collections import Counter

import bpy  # eerst bpy: daarmee komt bmesh beschikbaar
import bmesh
from mathutils import Matrix, Vector

SCALE = 0.01  # Floorplanner rekent in cm
PV_REFID = "4746e6e09e4687d649122db82dd2dcc6b67cecc9"  # zonnepaneel 99x165 cm
FLOOR_NAMES = {1: "begane_grond", 2: "eerste_verdieping", 3: "zolder"}


# --------------------------------------------------------------------------
# hulpfuncties
# --------------------------------------------------------------------------

def to_bl(x, y, z=0.0, base=0.0):
    """Floorplanner (cm, y naar beneden) -> Blender (m, z omhoog)."""
    return Vector((x * SCALE, -y * SCALE, base + z * SCALE))


def slug(text):
    out = "".join(c.lower() if c.isalnum() else "_" for c in (text or "ruimte"))
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "ruimte"


def material(name, rgba, emission=None):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.8
    if rgba[3] < 1.0:
        bsdf.inputs["Alpha"].default_value = rgba[3]
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
    if emission:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = 1.0
    mat.diffuse_color = rgba
    return mat


def hex_rgba(hex_color, alpha=1.0, fallback=(0.9, 0.9, 0.9)):
    try:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
        return (*lin, alpha)
    except Exception:
        return (*fallback, alpha)


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def link(obj, parent):
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def mesh_obj(name, verts, faces, mat, parent):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    return link(obj, parent)


def prism(name, poly2d, z0, z1, mat, parent):
    """Verticaal geëxtrudeerde (concave) polygoon, netjes getrianguleerd."""
    bm = bmesh.new()
    bottom = [bm.verts.new((p.x, p.y, z0)) for p in poly2d]
    try:
        face = bm.faces.new(bottom)
    except ValueError:
        bm.free()
        return None
    bmesh.ops.recalc_face_normals(bm, faces=[face])
    if face.normal.z > 0:
        face.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=top, vec=(0, 0, z1 - z0))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    return link(obj, parent)


def slab_from_points(name, pts3d, thickness, mat, parent):
    """Schuine plaat (dakvlak): punten met eigen hoogte, dikte omhoog."""
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(p)) for p in pts3d]
    try:
        face = bm.faces.new(vs)
    except ValueError:
        bm.free()
        return None
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=top, vec=(0, 0, max(thickness, 0.01)))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    return link(obj, parent)


def box(name, center, size, rot_z, mat, parent):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    obj.scale = size
    obj.rotation_euler = (0, 0, rot_z)
    obj.location = center
    return link(obj, parent)


def point_in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]["x"], poly[i]["y"]
        xj, yj = poly[j]["x"], poly[j]["y"]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def room_of(x, y, areas):
    for a in areas:
        if a.get("name") and point_in_poly(x, y, a["poly"]):
            return a["name"]
    return ""


# --------------------------------------------------------------------------
# bouwen per verdieping
# --------------------------------------------------------------------------

def build_walls(design, base, parent, mats):
    cutters = []
    for i, w in enumerate(design.get("walls", []), 1):
        a, b = to_bl(w["a"]["x"], w["a"]["y"], 0, base), to_bl(w["b"]["x"], w["b"]["y"], 0, base)
        d = b - a
        if d.length < 0.01:
            continue
        h1 = max(w.get("az", {}).get("h", 0) * SCALE - 0.01, 0)
        h2 = max(w.get("bz", {}).get("h", 0) * SCALE - 0.01, 0)
        if h1 < 0.02 and h2 < 0.02:
            continue
        t = w.get("thickness", 15) * SCALE
        bal = w.get("balance", 0.5)
        perp = Vector((-d.y, d.x, 0)).normalized()
        b1, b2 = a + perp * t * bal, a - perp * t * (1 - bal)
        b3, b4 = b - perp * t * (1 - bal), b + perp * t * bal
        up1, up2 = Vector((0, 0, h1)), Vector((0, 0, h2))
        verts = [b1, b2, b3, b4, b1 + up1, b2 + up1, b3 + up2, b4 + up2]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)]
        wall = mesh_obj(f"{parent.name}_muur_{i:02d}", verts, faces, mats["muur"], parent)

        angle = math.atan2(d.y, d.x)
        for o in w.get("openings", []):
            tt = o.get("t", 0.5)
            cx = w["a"]["x"] + tt * (w["b"]["x"] - w["a"]["x"])
            cy = w["a"]["y"] + tt * (w["b"]["y"] - w["a"]["y"])
            z = o.get("z", 0)
            hh = o.get("z_height", 200)
            ww = o.get("width", 90)
            c = to_bl(cx, cy, z + hh / 2, base)
            cutter = box("cutter", c, (ww * SCALE, t * 3, hh * SCALE), angle, mats["muur"],
                         None)
            bpy.context.view_layer.update()
            mod = wall.modifiers.new("opening", "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.solver = "EXACT"
            mod.object = cutter
            cutters.append(cutter)
            if o.get("type") == "window":
                glass_c = to_bl(cx, cy, z + hh / 2, base)
                box(f"{parent.name}_raam_{i:02d}", glass_c,
                    (ww * SCALE, 0.02, hh * SCALE), angle, mats["glas"], wall.parent)
        if wall.modifiers:
            # modifier_apply via context override (werkt ook in achtergrondmodus)
            with bpy.context.temp_override(object=wall, active_object=wall,
                                           selected_objects=[wall], selected_editable_objects=[wall]):
                for m in list(wall.modifiers):
                    bpy.ops.object.modifier_apply(modifier=m.name)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)


def build_floors(design, base, parent, mats, level):
    names = Counter()
    for a in design.get("areas", []):
        poly = [to_bl(p["x"], p["y"], 0, base) for p in a.get("poly", [])]
        if len(poly) < 3:
            continue
        nm = slug(a.get("name"))
        names[nm] += 1
        suffix = f"_{names[nm]}" if names[nm] > 1 else ""
        mat = material(f"vloer_{a.get('color', 'x')}", hex_rgba(a.get("color", "#dddddd")))
        obj = prism(f"kamer_v{level}_{nm}{suffix}", poly, base - 0.05, base, mat, parent)
        if obj:
            obj["kamer"] = a.get("name") or ""
            obj["verdieping"] = level


def build_surfaces(design, base, parents, mats, level):
    n = Counter()
    for s in design.get("surfaces", []):
        if s.get("isCutout"):
            continue
        pts = [to_bl(p["x"], p["y"], p.get("z", 0), base) for p in s.get("poly", [])]
        if len(pts) < 3:
            continue
        th = (s.get("thickness") or 2) * SCALE
        if s.get("isRoof"):
            n["dak"] += 1
            alpha = 1.0 - (s.get("transparency", 0) or 0) / 100
            if (s.get("customName") or "").lower() == "dakkapel":
                alpha = 1.0  # dakkapel is in het echt wit en dicht, niet doorzichtig
            mat = material(f"dak_{s.get('color', 'x')}_{int(alpha * 100)}",
                           hex_rgba(s.get("color", "#9a9a9a"), max(alpha, 0.15)))
            slab_from_points(f"dak_v{level}_{n['dak']:02d}", pts, th, mat, parents["daken"])
        elif th > 0.5:  # schoorsteen e.d.
            n["blok"] += 1
            prism(f"schoorsteen_v{level}_{n['blok']}", pts, pts[0].z, pts[0].z + th,
                  material("schoorsteen", hex_rgba(s.get("color", "#ababac"))), parents["daken"])
        else:  # terras, paden, gras
            n["terrein"] += 1
            mat = material(f"terrein_{s.get('color', 'x')}", hex_rgba(s.get("color", "#b8c4a8")))
            prism(f"terrein_v{level}_{n['terrein']:02d}", pts, pts[0].z - 0.02, pts[0].z + 0.005,
                  mat, parents["terrein"])


def build_items(design, base, parents, mats, level, meubels=True):
    areas = design.get("areas", [])
    lamps, pv, furn = [], 0, 0
    for it in design.get("items", []):
        x, y = it.get("x", 0), it.get("y", 0)
        z = it.get("z", 0)
        w, d, h = it.get("width", 10), it.get("height", 10), it.get("z_height", 10)
        rot = math.radians(-(it.get("rotation", 0) or 0))
        if "light" in it:
            lamps.append((it, room_of(x, y, areas)))
            continue
        if it.get("refid") == PV_REFID:
            pv += 1
            tilt = math.radians(it.get("rotation_y", 0) or 0)
            c = to_bl(x, y, z + h / 2, base)
            obj = box(f"pv_v{level}_{pv:02d}", c, (w * SCALE, d * SCALE, 0.04), rot,
                      mats["pv"], parents["zonnepanelen"])
            # Floorplanner kantelt panelen om hun eigen Y-as (rotation_y)
            obj.rotation_euler = (0, tilt, rot)
            continue
        if not meubels or w * d * h <= 0:
            continue
        # lange balken (> 5 m) steken in het model door de gevel; in het echt bestaan ze niet
        if max(w, d) > 500 and h < 40:
            continue
        # alleen binnenmeubels: bomen, auto's en tuinspullen weglaten
        if h > 260 or not any(point_in_poly(x, y, a["poly"]) for a in areas):
            continue
        furn += 1
        c = to_bl(x, y, z + h / 2, base)
        box(f"meubel_v{level}_{furn:03d}", c, (w * SCALE, d * SCALE, h * SCALE), rot,
            mats["meubel"], parents["meubels"])

    # lampen sorteren per kamer zodat de nummering voorspelbaar is
    lamps.sort(key=lambda t: (t[1], t[0].get("y", 0), t[0].get("x", 0)))
    for i, (it, room) in enumerate(lamps, 1):
        x, y = it["x"], it["y"]
        z = min(it.get("z", 0) + it.get("z_height", 10) / 2, 300)
        name = f"lamp_v{level}_{i:02d}"
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.07)
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(name, me)
        obj.data.materials.append(mats["lamp"])
        obj.location = to_bl(x, y, z, base)
        obj["kamer"] = room
        obj["verdieping"] = level
        obj["fp_guid"] = it.get("guid", "")
        obj["groep"] = nearest_group(obj.location, GROEPEN.get(f"v{level}", {}))
        link(obj, parents["lampen"])
    return len(lamps), pv, furn


GROEPEN = {}


def nearest_group(loc, groepen, straal=0.6):
    """Lampgroep (uit groepen.json) waar deze lamp het dichtst bij hangt."""
    best, bd = "", straal
    for g, posities in groepen.items():
        for x, y in posities:
            d = ((loc.x - x) ** 2 + (loc.y - y) ** 2) ** 0.5
            if d < bd:
                best, bd = g, d
    return best


def level_height(design, default=2.8):
    hs = Counter(round(w.get("az", {}).get("h", 0)) for w in design.get("walls", []))
    hs = {h: c for h, c in hs.items() if h >= 200}
    return max(hs, key=lambda h: (hs[h], h)) * SCALE if hs else default


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("fml", nargs="+")
    ap.add_argument("--uit", default="huis.glb")
    ap.add_argument("--blend")
    ap.add_argument("--geen-meubels", action="store_true")
    ap.add_argument("--hoogtes", help="vaste verdiepingshoogtes in m, bv. 2.97,2.8")
    ap.add_argument("--groepen", help="groepen.json met lampgroep-posities per verdieping")
    args = ap.parse_args(argv)
    if args.groepen:
        with open(args.groepen, encoding="utf-8") as f:
            GROEPEN.update(json.load(f))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {
        "muur": material("muur", (0.92, 0.91, 0.88, 1)),
        "glas": material("glas", (0.55, 0.75, 0.9, 0.35)),
        "pv": material("zonnepaneel", (0.03, 0.05, 0.12, 1)),
        "meubel": material("meubel", (0.75, 0.72, 0.68, 1)),
        "lamp": material("lamp", (1.0, 0.85, 0.5, 1), emission=(1.0, 0.85, 0.5, 1)),
    }
    fixed = [float(h) for h in args.hoogtes.split(",")] if args.hoogtes else None
    base = 0.0
    report = []
    for idx, path in enumerate(args.fml, 1):
        with open(path, encoding="utf-8") as f:
            design = json.load(f)
        root = empty(f"verdieping_{idx}")
        root["naam"] = FLOOR_NAMES.get(idx, f"verdieping_{idx}")
        root["fp_design"] = design.get("name", "")
        root["basis_hoogte_m"] = round(base, 3)
        parents = {k: empty(f"v{idx}_{k}", root) for k in
                   ("muren", "vloeren", "lampen", "zonnepanelen", "meubels", "daken", "terrein")}
        build_walls(design, base, parents["muren"], mats)
        build_floors(design, base, parents["vloeren"], mats, idx)
        build_surfaces(design, base, parents, mats, idx)
        nl, npv, nf = build_items(design, base, parents, mats, idx, not args.geen_meubels)
        report.append(f"verdieping {idx} ({design.get('name')}): basis {base:.2f} m, "
                      f"{nl} lampen, {npv} zonnepanelen, {nf} meubels")
        step = fixed[idx - 1] if fixed and idx - 1 < len(fixed) else level_height(design)
        base += step

    # lege groepen opruimen
    for obj in list(bpy.data.objects):
        if obj.type == "EMPTY" and obj.parent and not obj.children:
            bpy.data.objects.remove(obj, do_unlink=True)

    # lampenlijst om straks aan Home Assistant-entities te koppelen
    csv_path = os.path.splitext(os.path.abspath(args.uit))[0] + "_lampen.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("object;verdieping;kamer;groep\n")
        for obj in sorted(bpy.data.objects, key=lambda o: o.name):
            if obj.name.startswith("lamp_"):
                f.write(f"{obj.name};{obj['verdieping']};{obj['kamer']};{obj['groep']}\n")

    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(args.uit), export_format="GLB",
                              export_extras=True, export_yup=True, export_apply=True)
    print("\n".join(report))
    print("geschreven:", args.uit, os.path.getsize(args.uit) // 1024, "KB")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv)
