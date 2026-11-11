"""
Fotorealistische renders per verdieping voor het dashboard (Blender/Cycles).

Per verdieping:
  <naam>_dag.jpg     overdag, zon, alle lampen uit
  <naam>_basis.jpg   avond, alle lampen uit (ondergrond voor de lampen)
  <naam>_<groep>.jpg alleen het licht van die lampgroep op zwart; het dashboard
                     telt dit op bij de basis (CSS mix-blend-mode: screen),
                     met dekking = helderheid van de HA-entity.

Gebruik:
  python render_lampgroepen.py -- huis_v1.blend begane_grond groepen.json v1 uitmap/
groepen.json: {"v1": {"woonkamer_plafond": [[x, y], ...], ...}} in Blender-meters.
"""
import json
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashcam import maak_camera, verberg_daken  # noqa: E402

blend, naam, groepen_pad, sleutel, uit = sys.argv[sys.argv.index("--") + 1:][:5]
SAMPLES = int(os.environ.get("SAMPLES", "96"))
RES = (int(os.environ.get("RES_X", "1600")), int(os.environ.get("RES_Y", "1067")))
STRAAL = 0.6  # m: licht hoort bij een groepslamp als het binnen deze afstand hangt

bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
os.makedirs(uit, exist_ok=True)
CAMERA = os.environ.get("CAMERA", "boven")  # boven | achter | voor

# andere verdiepingen erbij laden (voor de buitenaanzichten van het hele huis)
for extra in filter(None, os.environ.get("EXTRA_BLENDS", "").split(":")):
    with bpy.data.libraries.load(extra, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None and o.type != "CAMERA":
            sc.collection.objects.link(o)
# groepen.json: {"v1": {"groep": [[x, y], ...]}} of, uitgebreid,
# {"groep": {"posities": [[x, y], ...], "nieuw": [[x, y, z, watt, "kleur"], ...]}}
# "posities" koppelt bestaande Floorplanner-lampen; "nieuw" zet een extra lamp neer
# (bv. een ledstrip of ambilight die niet in Floorplanner staat). z is t.o.v. de vloer.
groepen = {}
nieuwe_lampen = {}
for g, spec in json.load(open(groepen_pad)).get(sleutel, {}).items():
    if isinstance(spec, dict):
        groepen[g] = spec.get("posities", [])
        nieuwe_lampen[g] = spec.get("nieuw", [])
    else:
        groepen[g] = spec
KLEUREN = {"warm": (1.0, 0.72, 0.45), "neutraal": (1.0, 0.9, 0.8), "paars": (0.55, 0.3, 1.0),
           "roze": (1.0, 0.35, 0.6), "blauw": (0.4, 0.6, 1.0)}

# bomen e.d. (hoger dan 4 m) verbergen: die blokkeren het zicht van bovenaf
for o in bpy.data.objects:
    if o.type == "MESH" and o.dimensions.z > 4.0:
        o.hide_render = True

# camera (gedeeld met hotspots.py); bij bovenaanzicht de daken weg
sc.render.resolution_x, sc.render.resolution_y = RES
if CAMERA == "boven":
    verberg_daken()
co, vloer = maak_camera(sc, CAMERA)

# auto's in de kleuren van onze eigen auto's (iX3 zwart, Q4 grijs, T4-busje grijs)
def wortel(o):
    while o.parent:
        o = o.parent
    return o


def lak(m, kleur, metaal=0.6):
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not b:
        return
    for link in list(b.inputs["Base Color"].links):
        m.node_tree.links.remove(link)
    b.inputs["Base Color"].default_value = (*kleur, 1)
    b.inputs["Metallic"].default_value = metaal
    b.inputs["Roughness"].default_value = 0.25


geverfd = set()
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    r = wortel(o)
    for slot in o.material_slots:
        m = slot.material
        if not m or m.name in geverfd or not m.node_tree:
            continue
        if "Vanagon" in r.name and m.name.startswith(("Material__3", "_6_-_Default")):
            lak(m, (0.22, 0.23, 0.24)); geverfd.add(m.name)
        elif "SUV" in r.name and m.name.startswith("FINISH_Car_DarkBlue"):
            # de SUV op de oprit (bij de laadpaal) is de grijze Q4, die op straat de zwarte iX3
            lak(m, (0.32, 0.33, 0.34) if r.matrix_world.translation.x < -10 else (0.015, 0.015, 0.017))
            geverfd.add(m.name)

# muren per kamer in de echte kleur (uit de foto's): KAMERKLEUREN='{"Woonkamer": "#B5A999"}'
# en FML=verdieping1.fml. Alleen muurvlakken die naar die kamer kijken, krijgen de kleur.
def _in_poly(x, y, poly):
    binnen = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            binnen = not binnen
        j = i
    return binnen


def verf_kamers(fml_pad, kleuren):
    fml = json.load(open(fml_pad))
    kamers = [(a.get("name"), [(p["x"] / 100, -p["y"] / 100) for p in a["poly"]])
              for a in fml.get("areas", []) if a.get("name") in kleuren]
    mats = {}
    for naam_k, hexkleur in kleuren.items():
        m = bpy.data.materials.new(f"verf_{naam_k}")
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        h = hexkleur.lstrip("#")
        srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        b.inputs["Base Color"].default_value = (*[c ** 2.2 for c in srgb], 1)
        b.inputs["Roughness"].default_value = 0.8
        mats[naam_k] = m
    geverfd_vlakken = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or "Wall" not in o.name or not o.data:
            continue
        mw = o.matrix_world
        rot = mw.to_3x3()
        idx = {}
        for poly in o.data.polygons:
            n = (rot @ poly.normal).normalized()
            if abs(n.z) > 0.3:
                continue
            c = mw @ poly.center
            px, py = c.x + n.x * 0.15, c.y + n.y * 0.15
            for naam_k, pts in kamers:
                if _in_poly(px, py, pts):
                    if naam_k not in idx:
                        o.data.materials.append(mats[naam_k])
                        idx[naam_k] = len(o.data.materials) - 1
                    poly.material_index = idx[naam_k]
                    geverfd_vlakken += 1
                    break
    print("GEVERFD", geverfd_vlakken, flush=True)


if os.environ.get("KAMERKLEUREN") and os.environ.get("FML"):
    verf_kamers(os.environ["FML"], json.loads(os.environ["KAMERKLEUREN"]))

# extra lampen (ledstrips, ambilight) toevoegen
for g, lijst in nieuwe_lampen.items():
    for i, (x, y, z, watt, kleur) in enumerate(lijst):
        ld = bpy.data.lights.new(f"extra_{g}_{i}", "POINT")
        ld.energy = watt
        ld.color = KLEUREN.get(kleur, KLEUREN["warm"])
        ld.shadow_soft_size = 0.15
        lo = bpy.data.objects.new(f"extra_{g}_{i}", ld)
        lo["groep"] = g
        sc.collection.objects.link(lo)
        lo.location = (x, y, vloer + z)

# lichtbronnen en gloeiende lampkappen verzamelen
lights = [o for o in bpy.data.objects if o.type == "LIGHT"]
emitters = []
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    for slot in o.material_slots:
        m = slot.material
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED" and n.inputs["Emission Strength"].default_value > 0:
                    emitters.append((o, n, n.inputs["Emission Strength"].default_value))
                elif n.type == "EMISSION":
                    emitters.append((o, n, n.inputs["Strength"].default_value))


def groep_van(obj):
    if obj.get("groep"):
        return obj["groep"]
    p = obj.matrix_world.translation
    best, bd = None, STRAAL
    for g, posities in groepen.items():
        for x, y in posities:
            d = ((p.x - x) ** 2 + (p.y - y) ** 2) ** 0.5
            if d < bd:
                best, bd = g, d
    return best


light_groep = {o.name: groep_van(o) for o in lights}


def onder_plaat_zetten():
    """Floorplanner zet sommige plafondspots ín de dakrand of luifel; dan komt er
    geen licht uit. Zulke lampen verschuiven we net onder de plaat."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    verplaatst = 0
    for o in lights:
        if not light_groep[o.name]:
            continue
        p = o.matrix_world.translation.copy()
        start = p - Vector((0, 0, 1.2))
        geraakt, plek, *_ = sc.ray_cast(dg, start, Vector((0, 0, 1)), distance=1.19)
        if geraakt and plek.z < p.z - 0.01:
            o.matrix_world.translation = Vector((p.x, p.y, plek.z - 0.05))
            verplaatst += 1
    print("VERPLAATST", verplaatst, flush=True)


onder_plaat_zetten()
emit_groep = [(o, n, s, groep_van(o)) for o, n, s in emitters]


def zet(aan):
    """aan: set van groepsnamen die aan staan (None = alles uit)."""
    for o in lights:
        o.hide_render = light_groep[o.name] not in aan
    for o, n, s, g in emit_groep:
        key = "Emission Strength" if n.type == "BSDF_PRINCIPLED" else "Strength"
        n.inputs[key].default_value = s if g in aan else 0.0


if not sc.world:
    sc.world = bpy.data.worlds.new("wereld")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
# de camera ziet een donkere achtergrond (past bij de kaart), de verlichting blijft de lucht
nt = sc.world.node_tree
pad = nt.nodes.new("ShaderNodeLightPath")
donker = nt.nodes.new("ShaderNodeBackground")
donker.inputs[0].default_value = (0.006, 0.007, 0.008, 1)
mix = nt.nodes.new("ShaderNodeMixShader")
uitvoer = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
nt.links.new(pad.outputs["Is Camera Ray"], mix.inputs[0])
nt.links.new(bg.outputs[0], mix.inputs[1])
nt.links.new(donker.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], uitvoer.inputs["Surface"])
# daglicht: zachte zon (iets warm) plus een blauwe lucht als omgevingslicht
zon_data = bpy.data.lights.new("zon", "SUN")
zon_data.energy = 5.0
zon_data.angle = 0.02
zon_data.color = (1.0, 0.92, 0.82)
zon = bpy.data.objects.new("zon", zon_data)
sc.collection.objects.link(zon)
zon.rotation_euler = (0.75, 0.15, 0.9)
LUCHT_DAG = (0.5, 0.62, 0.9, 1)
LUCHT_AVOND = (0.06, 0.09, 0.22, 1)  # blauw uur

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = True
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.cycles.blur_glossy = 1.0
sc.render.resolution_x, sc.render.resolution_y = RES
sc.view_settings.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
    try:
        sc.view_settings.look = look
        break
    except TypeError:
        pass
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 88


def render(bestand):
    sc.render.filepath = os.path.join(uit, bestand)
    bpy.ops.render.render(write_still=True)
    print("RENDER", bestand, flush=True)


ALLEEN_GROEPEN = [g for g in os.environ.get("ALLEEN_GROEPEN", "").split(",") if g]
if ALLEEN_GROEPEN:  # alleen deze lichtlagen opnieuw renderen
    groepen = {g: v for g, v in groepen.items() if g in ALLEEN_GROEPEN}
else:
    zet(set()); zon.hide_render = False
    bg.inputs[0].default_value = LUCHT_DAG; bg.inputs[1].default_value = 0.45
    render(f"{naam}_dag.jpg")
if os.environ.get("ALLEEN_DAG"):  # snelle proef van de camera
    sys.exit(0)
zon.hide_render = True
# avond: blauw uur met wat maanlicht, zodat het huis nog zichtbaar is
bg.inputs[0].default_value = LUCHT_AVOND
bg.inputs[1].default_value = 0.6 if CAMERA == "boven" else 0.9
maan_data = bpy.data.lights.new("maan", "SUN")
maan_data.energy = 0.35
maan_data.color = (0.6, 0.7, 1.0)
maan = bpy.data.objects.new("maan", maan_data)
sc.collection.objects.link(maan)
maan.rotation_euler = (0.9, -0.3, 2.2)
if not ALLEEN_GROEPEN:
    render(f"{naam}_basis.jpg")
maan.hide_render = True
bg.inputs[1].default_value = 0.0
donker.inputs[1].default_value = 0.0  # lichtlagen op echt zwart
sc.cycles.samples = int(os.environ.get("SAMPLES_LAAG", SAMPLES))
for g in groepen:
    zet({g})
    render(f"{naam}_{g}.jpg")
print("TELLING", {g: sum(1 for v in light_groep.values() if v == g) for g in groepen})
