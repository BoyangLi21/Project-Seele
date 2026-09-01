# EVA 真人动捕战斗 Phase M 人工验收

状态：**PARTIAL_HUMAN_REVIEW**。两条粒子刀已通过并锁定；普通攻击被拒绝。
正式游戏动作仍未替换。

## 候选

| # | 候选 | 状态／来源 |
|---|---|---|
| 01 | `eva_anime_body_drive` | **人工拒绝**；仍缺少 EVA 普通攻击应有的动作感觉 |
| 02 | `eva_locked_knife_stab_twist_forward` | **人工通过并锁定**；规划为持刀左键正手 |
| 03 | `eva_short_knife_stab_twist_reverse` | **人工通过并锁定**；规划为持刀右键反手，最终 2.08 秒 |

锁定正手帧数据 SHA-256：
`414427cf77b59c25912f9fb1821dfa480c5e0be14a88d4969c945e8ff64acbbb`；
Phase L 与 Phase M 完全一致。

锁定短反手帧数据 SHA-256：
`19e7d2a37b46574620df1d55e0ce02d6c0373c02c778740beccece6c8dfe4ae9`。

自动否决结果：精确 Tiger `3 clips / 0 failures`；正手刀分类 `FORWARD`，
反手刀分类 `REVERSE`，反手 blade/forearm dot 全程为负。两条哈希均只覆盖
按键动作的 `frames` 数组，后续元数据更新不会解除动作锁。自动结果不构成
视觉批准。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_mocap_combat_phase_m_manual_review\20260901-204641
D:\eva\artifacts\motion_research\eva_mocap_combat_phase_m_manual_review\20260901-204641.zip
```

合并视频：`00_EVA_PHASE_M_ALL.mp4`。人工结论已经写回：02/03 不再重新选
动作；Phase N 只替换 01 的普通攻击候选。
