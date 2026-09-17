"""Package only explicit model references; credentials and failed candidates stay private."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_rebuild_r20/model_handoff'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files={
        'PROMPT_模型制作.md':'docs/MODEL_HANDOFF_R20.md',
        'design/UN00_original_shape_white.png':'artifacts/world_expansion_r07/prototype_concept.png',
        'design/UN00_black_gold_direction.png':'artifacts/world_repair_r19/references/eva_un00_black_gold.png',
        'design/UN01_user_reference_ignore_play_triangle.jpg':'artifacts/world_rebuild_r20/references/un01_user_reference.jpg',
        'design/UN01_design_sheet.png':'artifacts/world_rebuild_r20/un01/EVA-UN-01_design_sheet.png',
        'design/UN01_front.png':'artifacts/world_rebuild_r20/un01/EVA-UN-01_front.png',
        'raw_lux_not_final/UN00.glb':'artifacts/world_repair_r19/lux3d/EVA-UN-00-detail-original.glb',
        'raw_lux_not_final/UN01.glb':'artifacts/world_rebuild_r20/un01/EVA-UN-01-lux-source.glb',
        'installed_R19_compatibility/EVA-UN-00.glb':'artifacts/world_repair_r19/un00_local/delivery/EVA-UN-00-R19.glb',
        'installed_R19_compatibility/EVA-UN-00.blend':'artifacts/world_repair_r19/un00_local/delivery/EVA-UN-00-R19.blend',
        'integration/EntryPlugKinematics.java':'src/main/java/com/projectseele/world/EntryPlugKinematics.java',
        'integration/EvaDorsalProfile.java':'src/main/java/com/projectseele/entity/EvaDorsalProfile.java',
        'integration/EvaUNOptics.java':'src/main/java/com/projectseele/entity/EvaUNOptics.java',
        'integration/EvaScale.java':'src/main/java/com/projectseele/entity/EvaScale.java',
        'integration/eva_dorsal_r13.json':'src/main/resources/assets/projectseele/motion/eva_dorsal_r13.json',
        'integration/export_existing_mesh_to_glb.py':'tools/export_un00_glb_r19.py',
    }
    for category,name in [('geo','eva_prototype.geo.json'),('animations','eva_prototype.animation.json'),('mesh','eva_prototype.mesh.json'),('mesh','entry_plug_un.mesh.json'),('textures/entity','eva_prototype.png'),('textures/entity','eva_prototype_eyes.png'),('textures/entity','entry_plug_un.png')]:
        files['installed_R19_compatibility/assets/projectseele/'+category+'/'+name]='run/resourcepacks/eva_real_model/assets/projectseele/'+category+'/'+name
    manifest=[];target=OUT/'EVA_UN_ChatGPT_Pro_References_R20.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,relative in files.items():
            source=ROOT/relative;assert source.is_file(),source
            data=source.read_bytes();archive.writestr(name,data);manifest.append(dict(file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        archive.writestr('README_先读.txt','请把 PROMPT_模型制作.md 正文发送给 ChatGPT Pro，并附上本 ZIP。\n设计图定义外形；installed_R19_compatibility 是已运行但美术尚未满意的旧版本，只用于尺寸、坐标和骨架兼容。\nraw_lux_not_final 是已生成的原始网格，不是最终验收模型。\n本包没有 API 密钥，也没有本轮暂停的实验性模型。\nUN-01 空机库位置：projectseele:geofront，6282.5 77 -6205.5。\n不要修改项目地图或替换机体身份。交付模型后再由 Codex 集成。\n')
        archive.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert set(files)<=set(archive.namelist())
    (OUT/'package.json').write_text(json.dumps(dict(path=str(target),bytes=target.stat().st_size,files=manifest),ensure_ascii=False,indent=2),encoding='utf8')
    print('Model reference package verified',target,round(target.stat().st_size/1048576,1),'MiB')

if __name__=='__main__':main()
