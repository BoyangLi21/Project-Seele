"""Inventory release inputs without copying or relicensing private artwork.

An unresolved row is a review task, not a finding that its author did anything
wrong. This audit cannot infer a license from a filename or a successful download.
"""
from pathlib import Path
import csv,json,hashlib,collections
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r24/release'
R24_ORIGINAL={'mesh/period_details_r24.json','textures/entity/chest/nerv_equipment_r24.png','sounds/shamshel_whip_charge.ogg','sounds/shamshel_whip_crack.ogg','sounds/period_phone_busy.ogg','sounds/staff_radio_connect.ogg','sounds/staff_radio_ack.ogg'}
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True);rows=[];base=ROOT/'src/main/resources/assets/projectseele'
    for p in sorted(base.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(base).as_posix();status='needs_manifest_entry';license='';note='Consult docs/ASSETS.md and the named author/source before release.'
        if rel.startswith(('blockstates/','models/block/','models/item/','lang/','shaders/','style/')) or rel=='sounds.json':
            status='project_definition';license='MIT';note='Project definition; any referenced external art still needs its own source review.'
        elif rel in R24_ORIGINAL:status='original_r24';license='MIT';note='Authored in build_period_props_r24.py, build_facility_chest_finish_r24.py / original SVG, or build_tv_audio_r24.py.'
        elif rel=='textures/block/period_station_concrete_r24.png':status='ai_assisted_r24';license='MIT';note='Original image_gen output; prompt and technical conversion in docs/ART_DIRECTION_R24.md.'
        elif rel.startswith('sounds/pa_'):status='generated_voice_review';note='Original project words, Microsoft neural speech via edge-tts; verify output distribution conditions separately.'
        provenance=False
        if p.suffix=='.json' and p.stat().st_size<32*1024*1024:
            try:
                d=json.loads(p.read_text(encoding='utf8'));provenance=isinstance(d,dict) and any(k in d for k in ('provenance','source','sources','authorship'))
            except (ValueError,UnicodeError):pass
        rows.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest(p),status=status,license=license,embedded_provenance=provenance,note=note))
    private=[];pack=ROOT/'run/resourcepacks/eva_tv_r24_review'
    for p in sorted(pack.rglob('*')):
        if p.is_file():private.append(dict(path=p.relative_to(pack).as_posix(),bytes=p.stat().st_size,sha256=digest(p),status='local_only_not_in_public_asset_tree'))
    for name,data in [('source_asset_inventory.csv',rows),('private_pack_inventory.csv',private)]:
        with (OUT/name).open('w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    summary=dict(source_assets=len(rows),source_bytes=sum(r['bytes'] for r in rows),classifications=dict(collections.Counter(r['status'] for r in rows)),private_pack_assets=len(private),private_pack_bytes=sum(r['bytes'] for r in private),
        rules=['No private file was copied into a public directory.','Filename grouping is not a license clearance.','Unresolved rows require individual source/permission review before distributing the art.'])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
