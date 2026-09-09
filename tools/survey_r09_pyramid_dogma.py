"""Measure the user-identified platform, pyramid skin, directional glass and old Dogma shell."""
import json,math
from collections import Counter
import numpy as np
from scipy.ndimage import label,find_objects
from scan_regional_completion import volume
from regional_voxels import ROOT,WORLD
from query_blocks import AIR
OUT=ROOT/'artifacts/world_refinement_r09';OUT.mkdir(exist_ok=True)
def shell_coordinates(x,y,z):
    r=np.floor(120*(1-(y+466)/172)+.5);nr=np.floor(120*(1-np.minimum(1,(y+467)/172))+.5)
    return (y>=-466)&(y<=-294)&(abs(x-30)<=r)&(abs(z-327)<=r)&((y==-466)|(abs(x-30)>=nr)|(abs(z-327)>=nr))
def main():
    report={}
    for name,lo,hi in [('pyramid',(-110,-473,190),(176,-285,462)),('dogma',(-40,-631,240),(102,-528,405))]:
        a,p=volume(lo,hi);np.savez_compressed(OUT/(name+'_before.npz'),blocks=a,palette=np.array(p),lo=lo,hi=hi)
        y,z,x=np.ogrid[lo[1]:hi[1]+1,lo[2]:hi[2]+1,lo[0]:hi[0]+1]
        if name=='pyramid':
            skin=shell_coordinates(x,y,z);clear=np.array([s in AIR for s in p])[a];miss=skin&clear
            g=np.array([s.startswith('projectseele:one_way_glass') for s in p])[a];pts=np.argwhere(g)[:,[2,0,1]]+lo
            report[name]=dict(glass_count=len(pts),glass_bounds=[pts.min(0).tolist(),pts.max(0).tolist()],skin_cells=int(skin.sum()),air_in_skin=int(miss.sum()),skin_materials={p[int(i)]:int(n) for i,n in zip(*np.unique(a[skin],return_counts=True))})
            np.savez_compressed(OUT/'pyramid_shell_survey.npz',skin=skin,missing=miss,glass=g,lo=lo,hi=hi)
            comps,n=label(miss);holes=[]
            for i,b in enumerate(find_objects(comps),1):
                size=int((comps[b]==i).sum())
                if size:holes.append(dict(cells=size,lo=[b[2].start+lo[0],b[0].start+lo[1],b[1].start+lo[2]],hi=[b[2].stop-1+lo[0],b[0].stop-1+lo[1],b[1].stop-1+lo[2]]))
            report[name]['openings']=sorted(holes,key=lambda h:-h['cells'])
        else:
            # R28's documented ellipsoid remains measurable inside the R04 rectangular pressure room.
            radius=((x-30)/40)**2+((y+574)/44)**2+((z-296)/48)**2
            old=(radius>.88)&(radius<1.13)&(y>=-602)&(y<=-533)&(z>=268)&(z<=343)
            ids,cnt=np.unique(a[old],return_counts=True);report[name]=dict(old_shell_band={p[int(i)]:int(n) for i,n in zip(ids,cnt) if p[int(i)] not in AIR})
    (OUT/'survey.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:{a:b for a,b in v.items() if a not in ('skin_materials','old_shell_band','openings')} for k,v in report.items()},indent=2))
    print('Major skin openings',report['pyramid']['openings'][:12])
if __name__=='__main__':main()
