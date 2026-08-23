# GPT-5.6 Pro 已有知识索引（禁止重复调研）

> 本索引是 Project SEELE 的既有 Pro 成果入口。新任务必须先复用这些文件；只有明确
> 缺少某个新问题的资料时才允许继续咨询，不得重新搜索已经回答过的主题。

## 1. 固定工作流

- 地图空间理解与微改方法：
  `artifacts/GPT56PRO_SPATIAL_UNDERSTANDING_METHOD_20260808.md`
- 已落地的项目版协议：`docs/MAP_EDITING_PROTOCOL.md`
- 当前短决策：`docs/DECISIONS.md`
- 当前断点：`docs/handoff/CODEX_CURRENT_20260820.md`
- 原则：`query_blocks.py` 读真实体素 → 小范围证据板/GLB → 唯一候选 → 精确正反补丁 →
  人眼验收。不得凭空气推断房间，不得全图盲建，不得重复扫描同一大体积。

## 2. 原作空间、NERV 与 GeoFront

- 原作式 NERV/GeoFront 架构调研：`docs/TV_NERV_ARCHITECTURE_REFERENCE.md`
- 驾驶舱/第一人称资料：`docs/TV_COCKPIT_REFERENCE.md`
- S19 本地指挥室实测：`docs/S19_LOCAL_COMMAND_ASSET_AUDIT.md`
- Pro 空间审查包：`artifacts/pro_spatial_review/`
- Pro S19 空间合同原包：
  `artifacts/claude_audit_s19_20260729/pro_s19/S19_REBUILD_CONTRACT/`
- Claude 对 Pro 空间合同的红队修正：
  - `artifacts/claude_audit_s19_20260729/CLAUDE_AUDIT_FINDINGS.md`
  - `artifacts/claude_audit_s19_20260729/CLAUDE_SPATIAL_DELTA.json`
- 结论：旧 Pro 合同的治理思路可复用，但其 Y 坐标系和机械区总体布局被红队判定错误；
  禁止直接照搬其中 owner 坐标。

## 3. EVA 动作、手部与人体力学

- R03 人体力学完整交付：`artifacts/gpt56pro_r03_biomechanics_20260815/`
  - 中文审计：`reports/EVA_FULL_ANIMATION_R03_AUDIT_CN.md`
  - 旧→新关键帧：`reports/r03_keyframe_old_to_new.csv`
  - 接触/脚底门禁：`reports/r03_contact_foot_gates.md`
  - 三机动画与复现工具均在同目录。
- R04 动作与手部精修交付：
  `artifacts/gpt56pro_r04_animation_hand_fixes_20260815/`
  - 应用状态：`integration_validation.json`
  - 原包、审计、报告、runtime 文件位于 `unpacked/Project_SEELE_EVA_R04_Animation_Hand_Fixes/`
- 早期审计链（仅考古，不覆盖 R03/R04）：
  - `artifacts/gpt56pro_full_eva_animation_audit_20260814_r02/`
  - `artifacts/gpt56pro_full_eva_audit_r03_20260814/`
  - `artifacts/gpt56pro_full_eva_audit_z_hinge_20260814/`
  - `artifacts/gpt56pro_animation_fix_r02_20260814/`
- 仍待真人复核的最新输入：`artifacts/gpt56pro_eva_motion_audit_20260817/`。
- Blender 人工动作台说明：`docs/BLENDER_POSE_LAB.md`。

## 4. 模组联动与机械方案

- 已整理矩阵：`docs/MOD_INTEGRATION_MATRIX.md`
- Pro 动作/战斗模组审计输入与运行包：
  `artifacts/gpt56pro_eva_motion_mod_audit_20260816/`
- 已采用：Moving Elevators 1.4.12（人员电梯）。
- 已否决/移除：Create 用于插入栓吊机、Escalated、旧伪武器塔；不得在新任务中重新引入。
- EVA 发射台、转运台和武器设施是独立巨型机械，不得拿人员电梯实现。

## 5. 视觉、剧情与测试资料

- 第三次冲击/生命之树：`docs/THIRD_IMPACT_VISUAL.md`
- 发射井：`docs/LAUNCH_SILO_TEST.md`
- 舰队物流：`docs/FLEET_LOGISTICS_TEST.md`
- NERV 指挥协同：`docs/NERV_OPERATIONS_TEST.md`
- 多人测试：`docs/MULTIPLAYER_OPERATIONS_TEST.md`
- 私服部署：`docs/PRIVATE_SERVER_DEPLOYMENT_CN.md`

## 6. 网页原会话（仅缺件时回看，不重新提问）

- 已登录的 Pro 会话：
  `https://chatgpt.com/c/6a704187-f4e8-83ec-9b99-105c47e97fa9`
- 只有当本索引与本地成果包都缺少某条已经返回的回复时，才只读回看该会话并将回复
  落盘；不得让 Pro 重新执行同一调研。

## 7. 新任务读取顺序

1. `AGENTS.md`
2. `docs/handoff/LATEST.md`
3. 本索引
4. `docs/DECISIONS.md`
5. `docs/MAP_EDITING_PROTOCOL.md`
6. 仅按当前任务打开上面对应的一份 Pro 成果；禁止一次加载全部动作包或全部空间包。
