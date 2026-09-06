"""Measured plans and sections of the private preview; no game renderer or writes.

All block access goes through query_blocks. A map pixel is an exact sampled
column, not an interpolated or generated prediction. Unknown chunks stay pink.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from query_blocks import iter_box_cells, AIR

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / 'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
OUT = ROOT / 'artifacts/tv_world_preview_20260906/scans'
DIM = 'projectseele:geofront'
FONT = 'C:/Windows/Fonts/consola.ttf'
UNKNOWN = (115, 62, 91)


def colour(state):
    name = state.split('[')[0].split(':')[-1]
    if name in ('air', 'cave_air', 'void_air'): return (218, 229, 230)
    if 'water' == name: return (60, 122, 158)
    if 'lcl' in name: return (214, 122, 38)
    if 'leaves' in name: return (57, 101, 64)
    if name == 'grass_block': return (112, 139, 89)
    if name in ('dirt', 'coarse_dirt', 'rooted_dirt'): return (130, 107, 83)
    if 'sand' in name: return (187, 178, 139)
    if 'gravel' in name: return (144, 145, 140)
    if 'log' in name or 'planks' in name: return (137, 114, 77)
    if 'orange' in name: return (187, 116, 52)
    if 'yellow' in name: return (185, 164, 69)
    if 'red' in name: return (141, 78, 70)
    if 'glass' in name: return (87, 125, 134)
    if 'black' in name or 'deepslate' in name: return (68, 76, 85)
    if 'white' in name or 'quartz' in name or 'iron_block' in name: return (199, 204, 202)
    if 'light' in name or 'lantern' in name or 'lamp' in name: return (222, 219, 167)
    if 'stone' in name or 'andesite' in name or 'concrete' in name: return (139, 150, 156)
    return (106, 123, 137)


def frame(image, title, subtitle, filename, labels=()):
    scale = min(3, max(1, 1400 // image.width))
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new('RGB', (max(image.width + 70, 940), image.height + 145), (239, 239, 232))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 20)
    small = ImageFont.truetype(FONT, 15)
    draw.text((28, 18), title, fill=(25, 38, 45), font=font)
    draw.text((28, 47), subtitle, fill=(56, 71, 76), font=small)
    canvas.paste(image, (35, 82))
    for x, y, text in labels:
        px, py = 35 + x * scale, 82 + y * scale
        draw.ellipse((px-4, py-4, px+4, py+4), fill=(245, 220, 112), outline=(15, 20, 24))
        draw.text((px + 7, py - 17), text, fill=(15, 20, 24), stroke_width=2,
                  stroke_fill=(241, 241, 230), font=small)
    draw.text((28, image.height + 99), 'Pink = unmeasured | blue = water | green = vegetation | gray = structures/rock',
              fill=(56, 71, 76), font=small)
    canvas.save(OUT / filename)


def plan(name, bounds, stride, labels):
    x0, y0, z0, x1, y1, z1 = bounds
    shape = ((z1-z0)//stride+1, (x1-x0)//stride+1)
    top = np.full(shape, -32768, dtype=np.int16)
    rgb = np.full((*shape, 3), UNKNOWN, dtype=np.uint8)
    sampled = set()
    counts = Counter()
    start = time.monotonic()
    for (x, y, z), state in iter_box_cells(WORLD, DIM, (x0,y0,z0), (x1,y1,z1),
                                          step=(stride,1,stride), include_air=False, full_chunks_only=True):
        ix, iz = (x-x0)//stride, (z-z0)//stride
        sampled.add((x>>4,z>>4))
        # Invisible gameplay markers must not hide the physical terrain.
        if any(marker in state for marker in ('minecraft:light[', 'minecraft:barrier', 'minecraft:structure_void')):
            continue
        if y > top[iz,ix]:
            top[iz,ix] = y
            rgb[iz,ix] = colour(state)
        counts[state.split('[')[0]] += 1
    known = top > -32768
    safe = np.where(known, top, y0).astype(float)
    dz, dx = np.gradient(safe, stride)
    shade = np.clip(1 - .025*dx - .035*dz, .68, 1.16)
    rgb[known] = np.clip(rgb[known].astype(float)*shade[known,None], 0, 255).astype(np.uint8)
    image = Image.fromarray(rgb)
    transformed = [((x-x0)/stride, (z-z0)/stride, text) for x,z,text in labels]
    frame(image, name.replace('_',' ').upper(),
          f'X {x0}..{x1} | Z {z0}..{z1} | Y {y0}..{y1} | exact columns every {stride} blocks | NORTH ^',
          name+'.png', transformed)
    np.savez_compressed(OUT / (name+'.npz'), height=top, rgb=rgb, bounds=bounds, stride=stride)
    receipt = dict(bounds=bounds, stride=stride, sampled_columns=int(known.sum()),
                   known_fraction=float(known.mean()), chunks_with_measured_solids=len(sampled),
                   measured_top_range=[int(top[known].min()),int(top[known].max())],
                   top_states=counts.most_common(15), seconds=round(time.monotonic()-start,2))
    (OUT / (name+'.json')).write_text(json.dumps(receipt, indent=2))
    print(name, receipt, flush=True)


def section(name, z, x0=-700, x1=1800, y0=-620, y1=130):
    start = time.monotonic()
    rgb = np.full((y1-y0+1,x1-x0+1,3), UNKNOWN, dtype=np.uint8)
    known = 0
    for (x,y,_),state in iter_box_cells(WORLD,DIM,(x0,y0,z),(x1,y1,z),include_air=True,full_chunks_only=True):
        rgb[y1-y,x-x0] = colour(state)
        known += 1
    frame(Image.fromarray(rgb), name.replace('_',' ').upper(),
          f'EXACT vertical section at Z={z} | X {x0}..{x1} | Y {y0}..{y1} | no vertical exaggeration', name+'.png')
    (OUT/(name+'.json')).write_text(json.dumps(dict(z=z,bounds=[x0,y0,x1,y1],
        measured_cells=known,seconds=round(time.monotonic()-start,2)),indent=2))
    print(name, 'measured_cells', known, flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--part',choices=['underground','surface','section','all'],default='all')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.part in ('underground','all'):
        plan('underground_plan',(-384,-505,64,384,-250,704),2,
             [(30,296,'NERV HQ'),(-265,355,'LAKE'),(30,160,'WET CAGES'),(130,273,'SURFACE LIFT')])
    if args.part in ('surface','all'):
        plan('coastal_city_plan',(-384,40,-192,768,245,704),4,
             [(30,220,'TOKYO-3'),(130,273,'PERSONNEL LIFT'),(540,290,'EAST COAST')])
    if args.part in ('section','all'): section('geofront_section',296)


if __name__ == '__main__': main()
