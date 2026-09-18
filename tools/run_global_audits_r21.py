"""Read-only whole-map checks against the frozen final geometry."""
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21';WORLD=OUT/'global_audit/world_geometry'
def main():
 deadline=time.monotonic()+3000
 while not (OUT/'global_audit/frozen_geometry.json').exists():
  assert time.monotonic()<deadline,'Geometry freeze not ready';time.sleep(3)
 import audit_regional_transit_clearance as air
 sys.argv=['audit','--airborne','--world',str(WORLD),'--samples',str(OUT/'airport/native_flight_samples.json'),'--report-dir',str(OUT/'airport/airborne_final')];air.main()
 import audit_spatial_contract_r21 as contract
 contract.main()
 import retire_floating_labels_r19 as labels
 labels.vox.WORLD=WORLD;labels.OUT=OUT/'global_audit/labels';labels.survey()
 import inventory_world_r19 as inventory
 inventory.WORLD=WORLD;inventory.OUT=OUT/'global_audit/inventory';inventory.main()
 import scan_world_components_r19 as components
 components.WORLD=WORLD;components.main(OUT/'global_audit/components')
 print('All frozen-geometry audits finished',flush=True)
if __name__=='__main__':main()
