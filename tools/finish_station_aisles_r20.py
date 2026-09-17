"""Give every platform a continuous aisle beside its stairs and boarding edge."""
import json
import regional_voxels as v
from build_transit_civil_r20 import station,OUT,SOURCE,load
def main():
    v.OUT=OUT;p=v.Painter();old=load(SOURCE/'native_snapshot.json');native=load(SOURCE/'built7/native_commission.json');plan=load(SOURCE/'native_plan.json');walks=[];boards=[]
    for q in old['platforms']:
        if q['transportMode']=='TRAIN':station(p,q,plan['platform_migrations'],native,walks,boards)
    p.meta.update(walk_cases=walks,boards=boards,layout='Outer stair banks at transverse +/-12, uninterrupted +/-8 platform aisles, two outer platforms on paired tracks, no inaccessible central island')
    p.save_plan('continuous_platform_aisles');print('Complete platform circulation',len(walks),'cases')
if __name__=='__main__':main()
