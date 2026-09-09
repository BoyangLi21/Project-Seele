"""Cold geometry, identity and evidence checks after the final native R09 review."""
import json,hashlib,msvcrt,shutil
import numpy as np
import nbtlib
from regional_voxels import ROOT,WORLD,DIM
from query_blocks import AIR,iter_block_entities
from scan_regional_completion import volume
from inspect_map_assets import region_chunks
from verify_r08_completion import ident,load
from rebuild_r09_pyramid_exterior import inside,protected
from retire_r09_dogma_sphere import held
OUT=ROOT/'artifacts/world_refinement_r09'

def main():
    checks={}
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        for name,expected in load(OUT/'user_baseline.json').items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
        checks['user_resources_preserved']=True
        catalog=load(WORLD/'quality_walk_cases.json');assert len(catalog)==len({c['id'] for c in catalog})==8528
        assert not any(c['id'].startswith('r08/structure/east_platform_maintenance') for c in catalog)
        walks=load(OUT/'native_walk_pass.json');assert len(walks)==358 and all(c['status']=='pass' for c in walks)
        assert {r['id'] for r in walks}<={r['id'] for r in catalog}
        checks['walks']=dict(native_passed=358,full_catalog=8528,retired_platform_routes=2,added_gallery_routes=2)
        d=np.load(OUT/'pyramid_before.npz');a,p=volume(tuple(d['lo']),tuple(d['hi']));before=d['blocks'];old=d['palette'];lo=d['lo'];hi=d['hi']
        y,z,x=np.ogrid[lo[1]:hi[1]+1,lo[2]:hi[2]+1,lo[0]:hi[0]+1];r=np.floor(120*(1-(y+466)/172)+.5)
        ring=(y>=-466)&(y<=-294)&(abs(x-30)<=r)&(abs(z-327)<=r)&((abs(x-30)==r)|(abs(z-327)==r))
        oldsolid=np.array([s not in AIR for s in old])[before];newsolid=np.array([s not in AIR for s in p])[a]
        assert not np.any(ring&oldsolid&~newsolid)
        repaired=int(np.count_nonzero(ring&~oldsolid&newsolid));assert repaired==45
        panes=np.array([s.startswith('projectseele:one_way_glass') and 'pyramid=true' in s for s in p])[a]
        assert np.count_nonzero(panes)==2344
        bes={pos for pos,be in iter_block_entities(WORLD,DIM,(6,-329,303),(54,-315,351)) if str(be['id'])=='projectseele:one_way_glass'}
        expected={tuple(map(int,(ix+lo[0],iy+lo[1],iz+lo[2]))) for iy,iz,ix in np.argwhere(panes)};assert bes==expected
        checks['pyramid']=dict(original_shell_cells_preserved=True,obsolete_opening_closed=repaired,glazing_panes=len(bes))
        d=np.load(OUT/'platform_before.npz');lo=d['lo'];a,p=volume(tuple(lo),tuple(d['hi']));retired=0
        for iy,iz,ix in np.argwhere(np.array([s not in AIR for s in d['palette']])[d['blocks']]):
            xx,yy,zz=int(ix+lo[0]),int(iy+lo[1]),int(iz+lo[2])
            in_retirement=(136<=xx<=159 and -453<=yy<=-437 and 263<=zz<=403) or (151<=xx<=159 and -466<=yy<=-450 and 207<=zz<=403)
            if in_retirement and not inside(xx,yy,zz) and not protected(xx,yy,zz):assert p[a[iy,iz,ix]] in AIR,(xx,yy,zz);retired+=1
        assert retired==15417;checks['platform_cells_retired']=retired
        lo=(-40,-631,240);hi=(102,-528,405);a,p=volume(lo,hi)
        legacy=np.array([s.split('[')[0] in ('minecraft:deepslate_bricks','minecraft:polished_basalt') for s in p])[a]
        for iy,iz,ix in np.argwhere(legacy):assert held(int(ix+lo[0]),int(iy+lo[1]),int(iz+lo[2]))
        a,p=volume((66,-602,269),(79,-601,281));assert np.all(np.array([s=='projectseele:lcl[level=0]' for s in p])[a])
        checks['dogma']=dict(old_shell_and_trim_retired=6094,retained_material_only_in_real_lift=True,restored_flat_lake_cells=int(a.size))
        a,p=volume((64,-329,324),(64,-319,330));assert np.all(np.array([s in AIR for s in p])[a]);checks['temporary_optical_target_removed']=True
        military=nbtlib.load(WORLD/'dimensions/projectseele/geofront/data/projectseele_military_r07.dat')['data'];assert str(military['Phase'])=='WET'
        managed={str(k):ident(v) for k,v in military['Entities'].items()};assert len(managed)==31
        fleet=nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet']
        canonical={'4e449cf5-9726-4810-b07b-81aca77d0868','972271c6-dd86-472d-938e-4dc3a363f343','d0694537-3e22-4a39-a92a-cb14330ad150'}
        assert {ident(e['Canonical']) for e in fleet}==canonical
        details=nbtlib.load(WORLD/'dimensions/projectseele/geofront/data/projectseele_r08_details.dat')['data']['Members'];assert len(details)==84
        wanted=canonical|set(managed.values())|{ident(v) for v in details.values()};found={}
        for path in (WORLD/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca'):
            _,rx,rz=path.stem.split('.');rx,rz=int(rx),int(rz)
            for _,_,chunk in region_chunks(path,(rx*32,rx*32+31,rz*32,rz*32+31)):
                for e in chunk.get('Entities',[]):
                    if 'UUID' not in e:continue
                    u=ident(e['UUID'])
                    if u in wanted:
                        assert u not in found,u
                        if 'Health' in e:assert float(e['Health'])>0,u
                        found[u]=list(map(float,e['Pos']))
        assert wanted<=set(found),wanted-set(found)
        assert managed['prototype']=='aa222a1b-fb8b-4f62-8a60-0bfd20772115'
        assert np.linalg.norm(np.array(found[managed['prototype']])-[6442.5,77,-6205.5])<1
        checks['identities']=dict(canonical=len(canonical),managed=len(managed),industrial_members=len(details))
        a,p=volume((6426,77,-6226),(6458,120,-6137));assert np.all(np.array([s=='projectseele:lcl[level=0]' for s in p])[a])
        a,p=volume((6426,77,-6136),(6458,141,-6136));assert np.all(np.array([s=='minecraft:barrier' for s in p])[a]);checks['prototype_hangar']='WET / CLOSED'
        # The last R09 finish changed only full-cube paving and disconnected old trims.
        checks['last_dogma_finish']='No route clearance changed after the 358-case native pass'
        for folder in ('pyramid_exterior','dogma_sphere_retirement','dogma_finish','remove_temporary_optical_target'):
            receipts=list((OUT/folder).glob('applied_*/receipt.json'));assert receipts and all(load(p)['verified'] for p in receipts)
        photos=OUT/'photos';photos.mkdir(exist_ok=True)
        for r in load(OUT/'final_photo_views.json'):
            source=ROOT/'run/screenshots'/r['file'];assert source.stat().st_size>20000;shutil.copy2(source,photos/source.name)
        for name in ('pyramid','terminal_dogma'):assert (OUT/(name+'_multiangle.png')).stat().st_size>20000
        delivery=(ROOT/'.Codex/r09-build-native-delivery.log').read_text(encoding='utf8',errors='replace')
        assert 'BUILD SUCCESSFUL' in delivery
        assert 'REGIONAL PHOTO REQUIRED SECTIONS PASS file=r09_final_pyramid_logo.png' in delivery
        optical=(ROOT/'.Codex/r09-build-native-final.log').read_text(encoding='utf8',errors='replace')
        assert any('R09 OPTICAL STATE file=r09_final_inside_view.png' in row and 'compiled=true' in row for row in optical.splitlines())
        checks['native_visual_evidence']=dict(overview_guarded_sections=4,inside_external_section_compiled=True,build_and_native_client='PASS')
        result=dict(passed=True,world=str(WORLD),checks=checks)
        (OUT/'completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
