"""Resolve voxel edge contacts after the whole-map component pass completes."""
from pathlib import Path
import time
import classify_component_contacts_r19 as c
def main():
 c.OUT=c.ROOT/'artifacts/world_repair_r21/global_audit/components';c.WORLD=c.ROOT/'artifacts/world_repair_r21/global_audit/world_geometry'
 deadline=time.monotonic()+4000
 while not (c.OUT/'report.json').exists():
  assert time.monotonic()<deadline,'Global components not finished';time.sleep(3)
 c.main()
if __name__=='__main__':main()
