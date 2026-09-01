# EVA 免费真人动捕战斗 Phase J 人工验收

状态：**PARTIAL_HUMAN_REVIEW**。项目负责人拒绝开放掌普通攻击；刀动作被
纠正识别为正手并允许保留为候选。正式普通攻击与粒子刀动作未替换。

Phase G、H、I 已分别因锁死下半身、拳击／正握刀词汇和实际视觉质量被
人工拒绝，本阶段不复用其中任何动作。

## 免费真人捕捉来源

| 候选 | Rokoko 原始动作 | 窗口 | 目标语义 |
|---|---|---:|---|
| `free_open_palm_right` | `IronMan_Combat_mixamo.fbx` | 177–196 | 右手开放掌、上半身向前发力；非拳击、非踹击 |
| `free_reverse_knife_combo` | `KnifeFight_mixamo.fbx` | 464–523 | 右手下劈组合；人工确认实际为正手，后续改名保留 |

来源为 Rokoko 官方免费 superhero/fight packs。官方页面说明它们是全身／
手指真人捕捉，可用于个人到商业项目；原始 ZIP 与 FBX 保持 gitignored，
精确 SHA-256 记录于 `docs/ASSETS.md`。

## 约束与自动门禁

- 60 Hz 全身重定向，骨盆、双腿和支撑脚来自同一段捕捉；
- 开放掌源窗口 48 帧，原始双脚接触率均为 1.0；
- 刀源窗口 148 帧，未支撑比例 0.0541；
- 刀柄位置 `[-0.666, 3.507, 4.638]` 全程固定于右手；旧 Euler
  `[90, 0, 12]` 不能证明反握，最终几何审计将其归为 crosswise，人工观察
  则明确识别为正手；
- 错误连续接触段只在另一只脚确实支撑时撤销，不改关节旋转；
- 最终约束门禁 `2 clips / 0 failures`，精确 Tiger 全局矩阵门禁
  `2 clips / 0 failures`；
- 自动结果只为 `ELIGIBLE_FOR_HUMAN_REVIEW_ONLY`，不构成视觉批准。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_mocap_combat_free_manual_review_phase_j\20260901-020229
D:\eva\artifacts\motion_research\eva_mocap_combat_free_manual_review_phase_j\20260901-020229.zip
```

合并视频为 `00_EVA_FREE_NONBOXING_REVERSE_GRIP_PHASE_J_ALL.mp4`。每帧三栏
依次为正面、侧面、背面；右下角红色 `动作号-帧号` 只表示时间顺序。

人工审查结论：

1. `free_open_palm_right`：**拒绝**，普通攻击质量过差；
2. 原 `free_reverse_knife_combo`：不是反手，**改名为正手候选并保留**；
3. Phase K 改用 `MutantClaws` 单次右臂爪击，并新增逐帧几何约束的真正反手刀。
