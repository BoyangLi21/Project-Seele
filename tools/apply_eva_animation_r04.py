#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PATCH=json.loads((HERE/'eva_animation_r04_replacements.json').read_text(encoding='utf-8'))

def semantic_sha(d):
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description='Apply Project SEELE EVA R04 animation replacements to an R03 catalogue.')
    ap.add_argument('inputs',nargs='+',type=Path)
    ap.add_argument('--out-dir',type=Path,required=True)
    ap.add_argument('--allow-source-mismatch',action='store_true')
    args=ap.parse_args(); args.out_dir.mkdir(parents=True,exist_ok=True)
    for src in args.inputs:
        data=json.loads(src.read_text(encoding='utf-8'))
        before=semantic_sha(data['animations']); expected=PATCH['source_animation_semantic_sha256']
        if before!=expected and not args.allow_source_mismatch:
            raise SystemExit(f'{src}: source semantic SHA mismatch: {before} != {expected}')
        for name,value in PATCH['replace_animations'].items():
            data['animations'][name]=copy.deepcopy(value)
        after=semantic_sha(data['animations']); target=PATCH['target_animation_semantic_sha256']
        if after!=target:
            raise SystemExit(f'{src}: target semantic SHA mismatch: {after} != {target}')
        out=args.out_dir/src.name
        out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'{src} -> {out} semantic_sha256={after}')
if __name__=='__main__': main()
