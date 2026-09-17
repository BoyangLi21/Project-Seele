"""Check the new UN body's skeleton contract and real plug passage geometry."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from audit_dorsal_tv_r13 import hits

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19/un00_local';A=OUT/'runtime_candidate/assets/projectseele';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'

def main():
    mesh=json.loads((A/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((A/'geo/eva_prototype.geo.json').read_text());old=json.loads((PACK/'geo/eva_prototype.geo.json').read_text())
    bones={b['name']:b for b in geo['minecraft:geometry'][0]['bones']};before={b['name']:b for b in old['minecraft:geometry'][0]['bones']};assert list(bones)==list(before)
    changed=[]
    for name,b in bones.items():
        assert b.get('parent')==before[name].get('parent')
        if not np.allclose(b['pivot'],before[name]['pivot'],atol=1e-5):
            assert name.startswith('finger_');changed.append(name)
        assert b.get('rotation',[0,0,0])==before[name].get('rotation',[0,0,0])
    frame=mesh['r13_dorsal_socket'];C=np.asarray(frame['centre']);N=np.asarray(frame['outward']);Y=np.asarray(frame['hinge_axis']);H=np.asarray(frame['hinge']);cover=mesh['parts']['dorsal_cover']
    triangles=np.asarray(cover['vertices']).reshape(-1,3,8)[:,:,:3]+cover['pivot'];grid=np.linspace(-3.6,3.6,29);disk=np.asarray([(x,y) for x in grid for y in grid if x*x+y*y<=3.6**2]);origins=C+N*18+disk[:,0,None]*[1,0,0]+disk[:,1,None]*Y
    closed=hits(triangles,origins,-N);opened_tri=H+Rotation.from_rotvec(Y*np.deg2rad(frame['open_angle_degrees'])).apply((triangles-H).reshape(-1,3)).reshape(triangles.shape);opened=hits(opened_tri,origins,-N)
    assert closed.all() and not opened.any(),('Door coverage',closed.sum(),opened.sum())
    body=[]
    for name in ('torso_upper','torso_lower','neck'):
        part=mesh['parts'][name];body.append(np.asarray(part['vertices']).reshape(-1,3,8)[:,:,:3]+part['pivot'])
    # Verify the narrower physical plug envelope through the new torso,
    # independently of the liner's visual shadow and the moving lid.
    plug=json.loads((PACK/'mesh/entry_plug_un.mesh.json').read_text());part=plug['parts']['entry_plug'];v=np.asarray(part['vertices']).reshape(-1,8);radius=float(np.linalg.norm(v[:,:2]+np.asarray(part['pivot'])[:2],axis=1).max()*.2)
    assert radius<3.49*5/16
    probe_radius=radius/(5/16)+.02
    disk2=np.asarray([(x,y) for x in np.linspace(-probe_radius,probe_radius,29) for y in np.linspace(-probe_radius,probe_radius,29) if x*x+y*y<=probe_radius**2]);channel=hits(np.concatenate(body),C+N*4+disk2[:,0,None]*[1,0,0]+disk2[:,1,None]*Y,-N,max_distance=39.3)
    assert not channel.any(),('New torso obstructs plug',int(channel.sum()))
    report={'passed':True,'triangles':mesh['triangleCount'],'parts':len(mesh['parts']),'bones':len(bones),'scaled_finger_pivots':changed,'all_other_pivots_and_hierarchy_preserved':True,
        'closed_cover_rays':len(closed),'open_cover_hits':int(opened.sum()),'body_channel_rays':len(channel),'body_channel_hits':int(channel.sum()),'channel_probe_depth_model':35.3,'un_plug_radius_blocks':radius,'eye_socket_model':mesh['eye_socket_model']}
    (OUT/'runtime_geometry_audit.json').write_text(json.dumps(report,indent=2));print(report)

if __name__=='__main__':main()
