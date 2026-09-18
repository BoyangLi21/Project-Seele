"""Publish main-save readiness only from completed installation and native proofs."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21';MODELS=ROOT/'artifacts/un_models_r21';WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def main():
 map_proof=read(OUT/'map_acceptance.json');models=read(MODELS/'main_install.json');preserved=read(OUT/'main_preservation.json');flight=read(OUT/'native_flight_source.json')
 assert map_proof['passed'] and models['installed'] and preserved['passed'] and flight['passed']
 for name,digest in flight['sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
 assert len(read(WORLD/'quality_walk_cases.json'))==8865
 receipt=dict(revision='R21',installed=True,map_acceptance=str(OUT/'map_acceptance.json'),model_installation=str(MODELS/'main_install.json'),preservation=str(OUT/'main_preservation.json'),walk_routes=8865,models=['EVA-UN-00','EVA-UN-01'],network_protocol='30')
 (WORLD/'world_revision_r21.json').write_text(json.dumps(receipt,indent=2))
 p=ROOT/'docs/MANUAL_ACCEPTANCE_R21.md';s=p.read_text(encoding='utf8').replace('# R21 验收与操作（施工期间草稿）','# R21 验收与操作').replace('本文件尚未表示正式存档已安装完成。最终安装后使用新的 R21 启动入口。','本轮已安装到正式 TV 存档。双击仓库根目录 `start_eva_test_r21.bat` 开始；`start_eva_test_r21.bat --check` 只检查启动准备，不进入游戏。原存档与资源包的可恢复备份保留在本机。')
 p.write_text(s,encoding='utf8')
 p=ROOT/'docs/UN_MODELS_R21.md';s=p.read_text(encoding='utf8').replace('最终安装状态以 `artifacts/un_models_r21/main_install.json` 和正式存档 `un_commission_r21.json` 为准。','两台已安装到正式 TV 存档并完成原生配置验证；部署证明为 `artifacts/un_models_r21/main_install.json` 和正式存档 `un_commission_r21.json`。');p.write_text(s,encoding='utf8')
 p=ROOT/'docs/WORLD_REPAIR_R21.md';s=p.read_text(encoding='utf8').replace('双机和最终交通复验完成后，才写入 `world_revision_r21.json` 并启用 R21 启动入口。','双机与最终交通复验已完成，`world_revision_r21.json` 已发布，R21 启动入口已启用。');p.write_text(s,encoding='utf8')
 p=ROOT/'docs/ROADMAP.md';s=p.read_text(encoding='utf8');entry='- 2026-09-18 R21：完成金字塔／机库接驳、贯通观察廊、双向步道与导向牌，清理旧道路和武器井，城市沉降后中心战场平整。新增 NERV 机场与每分钟 F2 航班，修正飞机显示平滑和初次停靠对接，更新中文播报及短促双鸣警报。完整通行目录 8,865 项、乘梯、防坠、双机真实机库往返与 F2 完整往返已验证；EVA-UN-00／UN-01 新私有模型已安装到正式存档。入口 `start_eva_test_r21.bat`，详见 [R21 记录](WORLD_REPAIR_R21.md)、[双机记录](UN_MODELS_R21.md) 与 [操作手册](MANUAL_ACCEPTANCE_R21.md)。\n\n'
 if entry not in s:s=s.replace('## §0 现状快照\n\n','## §0 现状快照\n\n'+entry)
 p.write_text(s,encoding='utf8')
 print('Published installed R21 main-save readiness',flush=True)
if __name__=='__main__':main()
