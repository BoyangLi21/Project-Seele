"""Airfield markings and sealed industrial clerestories on the original surface hangar."""
import regional_voxels as vox
OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT;p=vox.Painter()
WHITE='minecraft:white_concrete';YELLOW='minecraft:yellow_concrete';BLACK='minecraft:black_concrete';DARK='minecraft:gray_concrete'
glyphs={'1':['010','110','010','010','111'],'8':['111','101','111','101','111'],'3':['111','001','111','001','111'],'6':['111','100','111','101','111']}
def number(text,z,dz):
    p.fill(6775,74,min(z,z+dz*9)-2,6793,74,max(z,z+dz*9)+2,BLACK,'r07/runway/designation_field','owned')
    for digit,c in enumerate(text):
        for row,line in enumerate(glyphs[c]):
            for col,pixel in enumerate(line):
                if pixel=='1':
                    x=6776+digit*9+col*2;zz=z+dz*row*2;p.fill(x,74,zz,x+1,74,zz+dz,WHITE,'r07/runway/designation')
number('18',-6610,-1);number('36',-6070,1)
p.fill(6720,74,-6608,6720,74,-6064,YELLOW,'r07/airfield/taxi_centreline','owned')
for z in (-6552,-6288,-6080):p.fill(6674,74,z,6766,74,z,YELLOW,'r07/airfield/taxi_turn','owned')
for z in (-6544,-6456,-6192):p.fill(6640,74,z,6720,74,z,YELLOW,'r07/airfield/shelter_leadout','owned')
for x in (6606,6634,6662):
    for xx in (x-7,x+7):p.fill(xx,74,-6374,xx,74,-6349,YELLOW,'r07/base/maintenance_bay_marks','owned')
    p.fill(x-7,74,-6374,x+7,74,-6374,YELLOW,'r07/base/maintenance_bay_marks','owned')
for z in (-6569,-6481,-6219):
    for x in (6624,6656):
        for zz in (z-17,z+17):p.fill(x,74,zz,x+3,74,zz,WHITE,'r07/airfield/parking_corners','owned')
# Side buttresses and roof ribs give the eighty-four-metre hall structural depth.
for z in range(-6272,-6151,24):
    for x in (6382,6501):p.fill(x,77,z,x+1,162,z+1,DARK,'r07/secret/exterior_frame')
    p.fill(6382,161,z,6502,163,z+1,DARK,'r07/secret/roof_girder')
    for x in (6384,6500):p.fill(x,148,z+4,x,155,z+17,'minecraft:gray_stained_glass','r07/secret/clerestory','owned')
p.apply('airfield_finish')
