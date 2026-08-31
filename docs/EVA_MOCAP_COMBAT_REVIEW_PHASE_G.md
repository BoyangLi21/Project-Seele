# EVA 真人动捕战斗 Phase G 人工验收

状态：**自动门禁通过，仅具备人工审查资格；尚未替换正式游戏动作**。

Phase F 的 idle、walk、run 与修正后 jump + landing 已由项目负责人接受。
正式徒手和粒子刀仍保持回滚基线；本阶段只生成独立真人动捕候选，不修改左键、
右键、伤害、冷却或正式 Gecko 动画。

## 公开动捕来源

| 候选 | CMU 原始捕捉 | 原始窗口/段 |
|---|---|---|
| `mocap_unarmed_left` | Subject 144 trial 13 Left Punch Sequence | 1044–1173 |
| `mocap_unarmed_right` | Subject 144 trial 20 Punch Sequence | 504–633 |
| `mocap_knife_light` | Subject 02 trial 08 swordplay | strike 01, 159–273 |
| `mocap_knife_heavy` | Subject 02 trial 08 swordplay | strike 05, 763–881 |

原始 BVH 与转换产物保持 gitignored；精确 SHA-256 已登记在 `docs/ASSETS.md`。
CMU 数据库允许自由使用并请求致谢。本阶段没有使用官方 EVA 影像或动作资产。

## 约束方式

失败的 R01 直接全身物理 IK 同时出现手臂净空、脚底漂移、关节导向和自碰撞
问题，因此被保留为否决证据，未进入验收包。

R05 使用 `LOCKED_READY_LOWER_BODY`：

- 真人动捕负责胸廓、肩臂、头部时序与主手轨迹；
- Phase-F 已批准的正式 idle 提供唯一骨盆与双腿支撑姿势；
- root 位移保持为零，避免短攻击 clip 争夺服务器世界位置；
- Tiger 关节动作幅度受限，经过一次 0.20 强度的对称相邻帧平滑；
- 26 个可见手指控制使用连续原生拇指修复后的静态拳/刀握姿；
- 动作前有 8 帧准备，后有 15 帧连续回收与 4 帧 ready 保持；首尾姿势完全一致。

这不是“原样全身人体重定向”。锁定下半身可能显得过僵，必须由人眼判断；
自动系统不得把稳定性门禁冒充动作审美批准。

## 自动证据

```text
clips=4
bones=50
sample_rate=60 Hz
maximum rotation step:
  unarmed left  = 19.7362 degrees
  unarmed right = 17.6385 degrees
  knife light   = 16.0993 degrees
  knife heavy   = 15.2922 degrees
ready pose seam=0 degrees (all clips)
root horizontal offset=0 m (all clips)
exact Tiger 3D audit=4 clips / 0 failures
result=ELIGIBLE_FOR_HUMAN_REVIEW_ONLY
```

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_mocap_combat_manual_review_phase_g\20260901-000802
D:\eva\artifacts\motion_research\eva_mocap_combat_manual_review_phase_g\20260901-000802.zip
```

合并视频为 `00_EVA_MOCAP_COMBAT_PHASE_G_ALL.mp4`，1920×360、30 FPS、
177 帧、5.9 秒。每帧三栏依次为正面、侧面、背面。

右下角红色 `动作号-帧号` **只表示时间顺序**：数字小的更早，数字大的更晚；
它不是模型几何、贴图、游戏 UI、骨骼或关节标记。反馈时请引用例如 `03-018`。

人工需判断上身是否过僵、意图是否清楚、双臂轮廓、刀轨迹、握持、手指、首尾
回收以及是否像 EVA。即使接受 MP4，晋升正式游戏仍需要一次明确授权。

## 复现

```powershell
# 两条 CMU 144 原始片段先由 export_bvh_landmarks.py 与
# export_eva_anatomical_action_candidate.py 生成 ignored 中间件。
& <blender-3.6> --background --python tools\build_eva_mocap_combat_review.py -- `
  --manifest tools\eva_mocap_combat_review_manifest.json `
  --output src\main\resources\assets\projectseele\motion\eva_mocap_combat_review_v1.json `
  --report artifacts\motion_research\eva_mocap_combat_phase_g\EVA_MOCAP_COMBAT_CONSTRAINT_GATE_R05.json

py -3 tools\build_eva_mocap_combat_review_package.py `
  --blend artifacts\motion_research\eva_mocap_combat_phase_g\EVA_MOCAP_COMBAT_EXACT_R02.blend `
  --motion-db src\main\resources\assets\projectseele\motion\eva_mocap_combat_review_v1.json `
  --constraint-report artifacts\motion_research\eva_mocap_combat_phase_g\EVA_MOCAP_COMBAT_CONSTRAINT_GATE_R05.json `
  --exact-audit artifacts\motion_research\eva_mocap_combat_phase_g\EVA_MOCAP_COMBAT_EXACT_AUDIT_R02.json
```
