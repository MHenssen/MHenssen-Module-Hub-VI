"""
Maakt www/verdiepingen.json voor de dashboardkaart uit:
  - lampgroepen.yaml   (welke HA-entities bij welke groep horen)
  - hotspots_*.json    (positie van elke groep op de render, uit hotspots.py)
  - de lijst renders   (welke <weergave>_<groep>.jpg bestaan)

  python maak_verdiepingen_json.py lampgroepen.yaml hotspots_map/ renders_map/ uit.json
"""
import json
import os
import sys

import yaml

groepen_yaml, hotspots_dir, renders_dir, uit = sys.argv[1:5]
cfg = yaml.safe_load(open(groepen_yaml, encoding="utf-8"))
renders = set(os.listdir(renders_dir))

# kamer per groep (voor het kamerpaneel rechts)
KAMER = {
    "woonkamer_plafond": "woonkamer", "woonkamer_sfeer": "woonkamer", "tv_ambilight": "woonkamer",
    "keuken_tafel": "keuken", "keuken_bar": "keuken", "leeshoek": "leeshoek", "speelhoek": "speelhoek",
    "toilet": "hal", "entree": "hal", "bijkeuken": "bijkeuken",
    "voordeur": "buiten", "overkapping": "buiten", "tuin": "buiten", "tuin_feest": "buiten",
    "voortuin_slingers": "buiten", "tuinhuis_garage": "buiten",
    "slaapkamer": "slaapkamer", "badkamer": "badkamer", "floris": "floris", "olivier": "olivier",
}
KAMERNAMEN = [
    ("woonkamer", "Woonkamer", "Begane grond"), ("keuken", "Keuken", "Begane grond"),
    ("leeshoek", "Leeshoek", "Begane grond"), ("speelhoek", "Speelhoek", "Begane grond"),
    ("hal", "Hal & toilet", "Begane grond"), ("bijkeuken", "Bijkeuken", "Begane grond"),
    ("buiten", "Buiten", "Tuin"), ("slaapkamer", "Slaapkamer", "1e verdieping"),
    ("badkamer", "Badkamer", "1e verdieping"), ("floris", "Floris", "1e verdieping"),
    ("olivier", "Olivier", "1e verdieping"),
]
NAAM = lambda g: g.replace("_", " ").capitalize()

alle = {}
for verdieping in cfg.values():
    for gid, g in (verdieping or {}).items():
        alle[gid] = g


def groepen_voor(weergave, gids):
    hs_pad = os.path.join(hotspots_dir, f"{weergave}.json")
    hs = json.load(open(hs_pad)) if os.path.exists(hs_pad) else {}
    res = []
    for gid in gids:
        g = alle.get(gid, {})
        render = f"{weergave}_{gid}.jpg"
        item = {"id": gid, "naam": NAAM(gid), "kamer": KAMER.get(gid),
                "bediening": g.get("bediening"), "lampen": g.get("lampen", [])}
        if render in renders:
            item["render"] = render
        if gid in hs:
            item.update(hs[gid])
        res.append(item)
    return res


weergaven = []
for wid, naam, gids, labels in [
    ("achter", "Achter", ["tuin", "overkapping"], [{"type": "zon"}, {"type": "huis"}]),
    ("voor", "Voor", ["voordeur"], [{"type": "zon"}, {"type": "net"}, {"type": "laadpaal"}]),
    ("begane_grond", "Begane grond", list((cfg.get("begane_grond") or {}).keys()), [{"type": "huis"}]),
    ("eerste_verdieping", "1e verdieping", list((cfg.get("eerste_verdieping") or {}).keys()), []),
    ("zolder", "Zolder", [], []),
]:
    if f"{wid}_dag.jpg" not in renders:
        continue
    lab_pad = os.path.join(hotspots_dir, f"{wid}_labels.json")
    lab_pos = json.load(open(lab_pad)) if os.path.exists(lab_pad) else {}
    weergaven.append({
        "id": wid, "naam": naam, "dag": f"{wid}_dag.jpg", "basis": f"{wid}_basis.jpg",
        "groepen": groepen_voor(wid, gids),
        "labels": [dict(l, **lab_pos.get(l["type"], {"x": 50, "y": 20 + 12 * i})) for i, l in enumerate(labels)],
    })

kamers = []
for kid, knaam, verd in KAMERNAMEN:
    ids = []
    for gid, k in KAMER.items():
        if k != kid or gid not in alle:
            continue
        g = alle[gid]
        for e in ([g["bediening"]] if g.get("bediening") else []) + g.get("lampen", []):
            if e not in ids:
                ids.append(e)
    if ids:
        kamers.append({"id": kid, "naam": knaam, "verdieping": verd, "lampen": ids})

json.dump({"beeld": {"breedte": 1600, "hoogte": 1067}, "weergaven": weergaven, "kamers": kamers},
          open(uit, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("weergaven:", [w["id"] for w in weergaven], "kamers:", len(kamers))
