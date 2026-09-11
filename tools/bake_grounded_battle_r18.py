"""Export the actual posed triangles for independent Blender collision/visual QA."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import author_first_battle_r12 as a
from preview_first_battle_r12 import angel_pose

def main():
    ap=argparse.ArgumentParser();ap.add_argument('candidate',type=Path);ap.add_argument('--label',default='r18final');ap.add_argument('--dense',action='store_true');ap.add_argument('--start',type=float,default=344);ap.add_argument('--end',type=float,default=560);args=ap.parse_args()
    if not args.label.replace('_','').isalnum():raise ValueError('Simple artifact label required')
    out=a.ROOT/'artifacts/world_refinement_r14'/('pair_'+args.label);out.mkdir(parents=True,exist_ok=True)
    data=json.loads(args.candidate.read_text());mesh=a.surface;e=a.eva
    parts=[n for n in mesh.MESH if n not in ('cannon','knife','lance','n2','entry_plug')]
    streams={n:np.asarray(e.mesh['parts'][n]['vertices']).reshape(-1,8) for n in parts}
    uv=np.vstack([streams[n][:,3:5] for n in parts]);names=[n for n in parts for _ in range(len(streams[n])//3)]
    raw=json.loads((e.PACK/'mesh/sachiel.mesh.json').read_text());av=np.asarray(raw['parts']['root']['vertices']).reshape(-1,8)
    _,inverse=np.unique(np.round(av[:,:3]*[-1,1,1],6),axis=0,return_inverse=True)
    poses=[e.decode(q,data['eva']['bones']) for q in data['eva']['frames']]
    angels=[angel_pose(q,data['angel']['bones']) for q in data['angel']['frames']]
    samples=np.arange(args.start,args.end,.5) if args.dense else [351,354,366,383,425,486,505,510,529,550,558]
    rows=[]
    for number,value in enumerate(samples):
        i=int(value);f=value-i;p=poses[i] if not f else a.mix_pose(poses[i],poses[i+1],f)
        s=angels[i] if not f else a.mix_pose(angels[i],angels[i+1],f,True)
        hr=a.b.mix(data['eva']['root_blocks'][i],data['eva']['root_blocks'][i+1],f)
        ar=a.b.mix(data['angel']['root_blocks'][i],data['angel']['root_blocks'][i+1],f)
        hero=np.vstack([mesh.vertices(p,n) for n in parts])*a.MIRROR*a.UNIT+hr
        enemy=s.skin()[inverse]*a.UNIT+ar;name='frame_'+str(round(value*10)).zfill(5)
        np.savez_compressed(out/(name+'.npz'),hero=hero,hero_uv=uv,angel=enemy,angel_uv=av[:,3:5])
        rows.append({'name':name,'time':value/30})
        if number%30==0:print('Paired triangle export',number,'/',len(samples),flush=True)
    (out/'manifest.json').write_text(json.dumps(rows),encoding='utf8')
    (out/'hero_parts.json').write_text(json.dumps(names),encoding='utf8')
    (out/'source.json').write_text(json.dumps({'clip':hashlib.sha256(args.candidate.read_bytes()).hexdigest(),'candidate':str(args.candidate.resolve()),'samples':len(rows)}),encoding='utf8')
    print(out,flush=True)

if __name__=='__main__':main()
