#!/usr/bin/env python3
"""Bounded final repair for the R28 office/Terminal-Dogma review."""

from __future__ import annotations
from collections import defaultdict
import argparse, csv, json, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_s20_approved_semantic_repairs import Change, atomic_replace, rewrite_region
from query_blocks import dimension_dir, read_box

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run/saves/SEELE_S20_RECOVERY_R28"
HISTORY = ROOT / "backups/SEELE_R28_PRE_COMMANDER_OFFICE_20260811_212555"
DIM = "projectseele:geofront"
AIR = "minecraft:air"
PACKET = "S23-OFFICE-DOGMA-FINAL-R01"

def bare(s): return s.split("[", 1)[0]

def plan():
    lo, hi = (-80,-590,210), (90,-310,350)
    cur = read_box(WORLD,DIM,lo,hi)
    old = read_box(HISTORY,DIM,(-75,-452,215),(-29,-436,248))
    out = {}
    def put(p, state, why):
        before=cur.get(p,AIR)
        if before != state: out[p]=Change(PACKET,*p,before,state,"bounded_exact_repair",why)

    # Undo only the later north-west stone accretion where the earlier
    # authoritative save proves the cell was air.
    for p, before in old.items():
        now=cur.get(p,AIR)
        if bare(before)==AIR and bare(now) in {"minecraft:stone","minecraft:dirt","minecraft:grass_block"}:
            put(p,AIR,"restore_northwest_pyramid_exterior")

    # Flatten the obsolete square installation into the accepted pyramid
    # base: buried fill, one clean polished-deepslate surface, air above.
    for x in range(-48,-3):
      for z in range(288,328):
        for y in range(-470,-466): put((x,y,z),"minecraft:stone","restore_pyramid_buried_fill")
        put((x,-466,z),"minecraft:polished_deepslate","restore_flat_pyramid_base")
        for y in range(-465,-457): put((x,y,z),AIR,"remove_obsolete_square_installation")

    # Three explicitly rejected local structures. The boxes are intentionally
    # disjoint from the south-wall cross and the retained lift axis.
    for box,why in [(((46,-566,300),(60,-554,316)),"remove_redundant_dogma_gallery"),
                    (((10,-575,239),(34,-555,258)),"remove_redundant_west_dogma_structure"),
                    (((67,-527,268),(77,-500,278)),"remove_redundant_deep_column")]:
      a,b=box
      for x in range(a[0],b[0]+1):
       for y in range(a[1],b[1]+1):
        for z in range(a[2],b[2]+1):
         if bare(cur.get((x,y,z),AIR)) != AIR: put((x,y,z),AIR,why)

    # Missing complete crucifix course at y=-567.
    for x in range(26,35):
      put((x,-567,319),"minecraft:red_stained_glass", "restore_missing_cross_course")
      for z in range(320,323): put((x,-567,z),"minecraft:redstone_block","restore_missing_cross_course")

    # North-facing secure lift: 7x7 shaft shell, clean 5x5 sweep, route
    # thresholds, and a complete lower cabin that runtime can recover.
    cx,cz=28,321
    for y in range(-390,-335):
      for x in range(cx-3,cx+4):
       for z in range(cz-3,cz+4):
        edge=abs(x-cx)==3 or abs(z-cz)==3
        put((x,y,z),"minecraft:reinforced_deepslate" if edge else AIR,
            "build_commander_office_lift_shaft")
    for wy in (-388,-340):
      # North landing aperture and supported seven-block handoff.
      for y in range(wy,wy+3):
       for x in range(cx-2,cx+3): put((x,y,cz-3),AIR,"open_north_lift_landing")
      for z in range(cz-7,cz-2):
       for x in range(cx-2,cx+3):
        put((x,wy-1,z),"minecraft:polished_deepslate","build_north_lift_handoff")
        put((x,wy,z),AIR,"clear_north_lift_handoff")
        put((x,wy+1,z),AIR,"clear_north_lift_handoff")
    # Recoverable lower 5x5 block cabin, initially open north.
    wy=-388
    for x in range(cx-2,cx+3):
     for z in range(cz-2,cz+3):
      put((x,wy-1,z),"minecraft:polished_deepslate","build_commander_lift_cabin")
      put((x,wy+4,z),"minecraft:smooth_quartz","build_commander_lift_cabin")
      if abs(x-cx)==2 or abs(z-cz)==2:
       for y in range(wy,wy+4):
        door=(z==cz-2 and abs(x-cx)<=1)
        put((x,y,z), AIR if door else "minecraft:iron_block","build_commander_lift_cabin")
    return sorted(out.values(),key=lambda c:(c.y,c.z,c.x))

def apply(changes):
    stamp=time.strftime("%Y%m%d_%H%M%S"); art=ROOT/"artifacts"/f"s23_office_dogma_final_{stamp}"
    (art/"region_before").mkdir(parents=True)
    rd=dimension_dir(WORLD,DIM)/"region"; groups=defaultdict(lambda:defaultdict(list))
    for c in changes:
      ch=(c.x>>4,c.z>>4); groups[(ch[0]>>5,ch[1]>>5)][ch].append(c)
    originals={}
    try:
      for (rx,rz),chunks in groups.items():
       p=rd/f"r.{rx}.{rz}.mca"; originals[p]=p.read_bytes(); shutil.copy2(p,art/"region_before"/p.name)
       removals={(c.x,c.y,c.z) for rows in chunks.values() for c in rows
                 if c.after == AIR}
       atomic_replace(p,rewrite_region(p,chunks,removals))
      lo=tuple(min(getattr(c,a) for c in changes) for a in ('x','y','z')); hi=tuple(max(getattr(c,a) for c in changes) for a in ('x','y','z'))
      got=read_box(WORLD,DIM,lo,hi); bad=[c for c in changes if got.get((c.x,c.y,c.z),AIR)!=c.after]
      if bad: raise RuntimeError(f"readback failed: {len(bad)}")
    except Exception:
      for p,data in originals.items(): atomic_replace(p,data)
      raise
    with (art/"block_diff.csv").open('w',newline='',encoding='utf-8') as f:
      w=csv.writer(f); w.writerow(('x','y','z','before','after','reason'))
      for c in changes:w.writerow((c.x,c.y,c.z,c.before,c.after,c.reason))
    (art/"receipt.json").write_text(json.dumps({'status':'APPLIED_AND_READ_BACK_VERIFIED','writes':len(changes)},indent=2)+'\n')
    return art

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--apply',action='store_true'); a=ap.parse_args()
    c=plan(); print(f"planned={len(c)}")
    if a: print(apply(c))
