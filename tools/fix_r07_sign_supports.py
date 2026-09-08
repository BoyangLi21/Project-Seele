"""Relocate signs exposed by native screenshot review; keep the doorways open."""
import json
import regional_voxels as vox
from scan_regional_completion import volume
OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT;p=vox.Painter()
changes=[((1184,75,456),(1194,75,456),'north',['NERV 港湾・埠頭','P1 湾岸連絡線','城市方向 / CITY','']),
         ((512,85,456),(522,85,456),'north',['湾岸連絡口','P1 港湾・埠頭行','PORT SHUTTLE',''])]
for z in (-6544,-6456,-6192):changes.append(((6644,77,z),(6664,77,z),'south',['航空機格納庫','NERV / UN','飛行線・FLIGHT LINE','']))
for old,new,face,lines in changes:
    a,pal=volume(old,old);state=pal[int(a[0,0,0])];assert '_wall_sign[' in state
    dx,dz={'north':(0,1),'south':(0,-1)}[face];back=(new[0]+dx,new[1],new[2]+dz);a,pal=volume(back,back)
    assert pal[int(a[0,0,0])] not in ('minecraft:air','minecraft:barrier')
    p.match((*old,*old),state,'minecraft:air','r07/sign_support_repair');p.sign(*new,lines,'r07/sign_support_repair',face)
p.sign(6468,79,-6135,['機密試験格納棟','NERV EXPERIMENTAL','DRAIN → GATE','未命名試験機'],'r07/secret/sign','south')
p.apply('sign_support_repairs')
