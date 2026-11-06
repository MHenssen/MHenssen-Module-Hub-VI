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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashcam import maak_camera, verberg_daken  # noqa: E402

blend, naam, groepen_pad, sleutel, uit = sys.argv[sys.argv.index("--") + 1:][:5]
SAMPLES = int(os.environ.get("SAMPLES", "64"))
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
groepen = json.load(open(groepen_pad)).get(sleutel, {})

# bomen e.d. (hoger dan 4 m) verbergen: die blokkeren het zicht van bovenaf
for o in bpy.data.objects:
    if o.type == "MESH" and o.dimensions.z > 4.0:
        o.hide_render = True

# camera (gedeeld met hotspots.py); bij bovenaanzicht de daken weg
sc.render.resolution_x, sc.render.resolution_y = RES
if CAMERA == "boven":
    verberg_daken()
co, vloer = maak_camera(sc, CAMERA)

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
    p = obj.matrix_world.translation
    best, bd = None, STRAAL
    for g, posities in groepen.items():
        for x, y in posities:
            d = ((p.x - x) ** 2 + (p.y - y) ** 2) ** 0.5
            if d < bd:
                best, bd = g, d
    return best


light_groep = {o.name: groep_van(o) for o in lights}
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
zon_data = bpy.data.lights.new("zon", "SUN")
zon_data.energy = 3.5
zon = bpy.data.objects.new("zon", zon_data)
sc.collection.objects.link(zon)
zon.rotation_euler = (0.8, 0.2, 0.6)

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = RES
sc.view_settings.view_transform = "AgX"
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 88


def render(bestand):
    sc.render.filepath = os.path.join(uit, bestand)
    bpy.ops.render.render(write_still=True)
    print("RENDER", bestand, flush=True)


zet(set()); zon.hide_render = False; bg.inputs[1].default_value = 1.0
render(f"{naam}_dag.jpg")
if os.environ.get("ALLEEN_DAG"):  # snelle proef van de camera
    sys.exit(0)
# avond: zwak blauwig maanlicht, zodat het huis nog net zichtbaar is
zon.hide_render = True; bg.inputs[1].default_value = 0.12
maan_data = bpy.data.lights.new("maan", "SUN")
maan_data.energy = 0.25
maan_data.color = (0.6, 0.7, 1.0)
maan = bpy.data.objects.new("maan", maan_data)
sc.collection.objects.link(maan)
maan.rotation_euler = (0.9, -0.3, 2.2)
render(f"{naam}_basis.jpg")
maan.hide_render = True
bg.inputs[1].default_value = 0.0
for g in groepen:
    zet({g})
    render(f"{naam}_{g}.jpg")
print("TELLING", {g: sum(1 for v in light_groep.values() if v == g) for g in groepen})
