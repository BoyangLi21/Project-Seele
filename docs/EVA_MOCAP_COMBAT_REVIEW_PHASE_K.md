# EVA 免费真人动捕战斗 Phase K 人工验收

状态：**HUMAN_REJECTED**。项目负责人于 2026-09-01 拒绝全部三条；正式游戏
动作未替换，候选禁止晋升或换名重新包装。

## 候选

| # | 候选 | 真人捕捉窗口 | 语义 |
|---|---|---:|---|
| 01 | `free_mutant_claw_right` | Rokoko `MutantClaws` 778–792 | 单次右臂前冲爪击；上半身主导，非 boxing、掌炮或踹击 |
| 02 | `free_forward_knife_combo` | Rokoko `KnifeFight` 464–523 | Phase J 人工识别为正手，按要求保留 |
| 03 | `free_reverse_knife_combo` | 同一真人刀动作 | 新增几何约束反手版本 |

## 真反手合同

不能再以欧拉角名称判定握法。最终矩阵直接测量刀刃长轴与
`elbow -> wrist` 前臂方向：

- `dot=+1`：刀刃远离肘部；
- `dot=-1`：刀刃从手腕指向肘部，即反手；
- 新反手版本逐帧只写刀骨旋转，刀柄位置和全部身体关节不变；
- 最终 `minimum=-1.000000179`、`median=-0.999999985`、
  `maximum=-0.999999849`；
- 最大刀骨单帧旋转 `18.4208°`。

完整 Tiger 全局矩阵审计：`3 clips / 0 failures`。这只提供人工审查资格，
不代表动作已经视觉批准。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_mocap_combat_free_manual_review_phase_k\20260901-025256
D:\eva\artifacts\motion_research\eva_mocap_combat_free_manual_review_phase_k\20260901-025256.zip
```

合并视频：`00_EVA_FREE_CLAW_FORWARD_REVERSE_PHASE_K_ALL.mp4`。每帧三栏为
正面、侧面、背面；右下红色编号只表示动作号和时间顺序。

人工结论：`01/02/03` 全部不符合 EVA 原作战斗语言。Phase L 必须更换源动作，
改为双臂扑进下砸和带停顿／扭转的刺击，不再复用 `MutantClaws` 或
`KnifeFight`。
