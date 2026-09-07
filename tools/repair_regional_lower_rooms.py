"""Remove the construction-only upper floor foundation fill from eight new rooms."""
from dataclasses import replace
from regional_voxels import Painter
from regional_architecture import furnished_room

p=Painter()
for side,x0,x1,rooms,exit_side in [
    ('west',-67,-34,[('医療室','MEDICAL'),('職員休憩室','QUARTERS'),('記録保管室','ARCHIVE'),('食堂','CAFETERIA')],'east'),
    ('east',94,127,[('作戦会議室','BRIEFING'),('解析作業室','ANALYSIS'),('通信審議室','SEELE LINK'),('補給準備室','SUPPLIES')],'west')]:
    for i,(label,purpose) in enumerate(rooms):
        z=263+i*32;furnished_room(p,(x0,x1,z,z+27),-462,f'hq/{side}/B2/{i+1}',label,purpose,exit_side=exit_side)
p.ops=[replace(op,mode='owned') for op in p.ops]
p.apply('repair_lower_rooms')
