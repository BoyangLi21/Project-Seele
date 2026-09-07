"""Remove the measured two-layer road footing from the NERV car sweep."""
from collections import Counter
import regional_voxels as vox
from regional_voxels import WORLD,DIM,Painter
from query_blocks import read_box,AIR
from quality_structures import OUT

def repair():
    vox.OUT=OUT
    # The parked lower car ends at -459. The entire empty sweep above it is
    # independently read before clearing the exact known road-foundation fault.
    cells=read_box(WORLD,DIM,(-367,-458,743),(-353,88,757))
    obstructions={p:s for p,s in cells.items() if s not in AIR}
    expected={(x,y,z) for x in range(-367,-352) for y in (77,78) for z in range(743,751)}
    if set(obstructions)!=expected or set(obstructions.values())!={'minecraft:stone'}:
        raise RuntimeError(f'Unexpected shaft geometry: {Counter(obstructions.values())}')
    p=Painter();p.fill(-367,77,743,-353,78,750,'minecraft:air','clear_road_footing_from_native_shaft','owned')
    p.apply('gateway_shaft_clearance')
    after=read_box(WORLD,DIM,(-367,-458,743),(-353,88,757))
    if any(s not in AIR for s in after.values()):raise RuntimeError('Whole shaft sweep still obstructed')
    print('NERV shaft clear: removed240 exact road-footing cells; full empty sweep verified')

if __name__=='__main__':repair()
