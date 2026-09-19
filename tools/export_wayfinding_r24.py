"""Build navigation from current measured R24 floors; no map edits."""
from pathlib import Path
import plan_pyramid_navigation_r22 as nav
ROOT=Path(__file__).resolve().parents[1]
nav.WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW'
out=ROOT/'artifacts/facility_r24/wayfinding';out.mkdir(parents=True,exist_ok=True)
nav.main(False,out,out/'nerv_routes_r24.json.gz')
