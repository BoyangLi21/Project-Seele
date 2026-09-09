"""Geometry preview of the downloaded build; never a substitute for in-game evidence."""
import sys,importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'.Codex/3d-sections'))
import export_sections as g
g.OUT=ROOT/'artifacts/world_refinement_r08/ships'
d=np.load(g.OUT/'dd6_02_source.npz');a=d['blocks'];p=d['palette'];keep=np.array([s.split('[')[0] not in ('minecraft:water','minecraft:barrier') for s in p])[a]
g.mesh(a,p,d['lo'],keep,'author_destroyer');g.save('author_destroyer')
