#!/usr/bin/env python3
"""Install EUD's Longinus model into the LOCAL-ONLY development pack."""
import json
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "eud-1.1.0-forge-1.20.1.jar"
OUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"


def read_unique(archive, suffix):
    matches = [entry for entry in archive.namelist() if entry.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {suffix}, found {len(matches)}")
    return archive.read(matches[0])


with zipfile.ZipFile(SOURCE) as archive:
    model = json.loads(read_unique(archive, "assets/eud/models/custom/lanzadelonginusmodel.json"))
    model["textures"] = {
        "0": "projectseele:item/lance_of_longinus_local",
        "particle": "projectseele:item/lance_of_longinus_local",
    }
    texture = read_unique(archive, "assets/eud/textures/block/.png")

model_path = OUT / "models/item/lance_of_longinus.json"
texture_path = OUT / "textures/item/lance_of_longinus_local.png"
model_path.parent.mkdir(parents=True, exist_ok=True)
texture_path.parent.mkdir(parents=True, exist_ok=True)
model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
texture_path.write_bytes(texture)

note = REPO / "run/resourcepacks/eva_real_model/_SOURCE.txt"
text = note.read_text(encoding="utf-8") if note.exists() else ""
line = "EUD Longinus model: local testing only; CC BY-NC 4.0 attribution required."
if line not in text:
    note.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")
print("Installed local EUD Lance of Longinus model")
