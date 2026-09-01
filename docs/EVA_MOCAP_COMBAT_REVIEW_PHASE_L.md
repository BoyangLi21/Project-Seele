# EVA 原作动作语言 Phase L 人工验收

状态：**PARTIAL_HUMAN_REVIEW**。正手刺入扭转人工通过并锁定；双臂扑砸被
拒绝，反手刀因时长被拒绝。正式游戏动作未替换。

Phase K 三条已全部人工拒绝；本阶段没有复用其动作窗口、KnifeFight 源或
逐帧硬锁反手刀方案。

## 三条全新真人捕捉候选

| # | 候选 | 新来源 | 动作语义 |
|---|---|---|---|
| 01 | `eva_style_maul_lunge` | Rokoko `ZombieAttack_Walking` 208–251 | 躯干／骨盆先行的双臂扑进下砸 |
| 02 | `eva_style_knife_stab_twist_forward` | Eric Jacobus `stabTwist Knife` take 1 | 正手刺入、停顿、扭转、拔出 |
| 03 | `eva_style_knife_stab_twist_reverse` | 独立 take 2 | 反手冰锥式刺入、扭转、回收 |

这不是复制 EVA 原片关键帧，而是把原作的巨大生物感、扑进、贴身刺入和
重惯性回收作为筛选条件，再使用许可明确的免费真人捕捉实现。

## 自动否决门槛

- 全部保留捕捉骨盆、双腿、支撑脚和 root；
- 精确 Tiger 全局矩阵：`3 clips / 0 failures`；
- 正手刀 blade/forearm dot：`min +0.1864 / median +0.3063 / max +0.8488`；
- 反手刀：`min -0.9809 / median -0.4763 / max -0.1084`；
- 两种握法全程符号相反，均为静态握法，不再逐帧强制刀刃朝向；
- 自动结果仅为 `ELIGIBLE_FOR_HUMAN_REVIEW_ONLY`。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_mocap_combat_eva_style_manual_review_phase_l\20260901-201712
D:\eva\artifacts\motion_research\eva_mocap_combat_eva_style_manual_review_phase_l\20260901-201712.zip
```

合并视频为 `00_EVA_STYLE_PHASE_L_ALL.mp4`，三栏依次为正面、侧面、背面；
右下红色编号只表示动作号和帧顺序。

## 人工结论

- `01 eva_style_maul_lunge`：**HUMAN_REJECTED**，动作奇怪，不适合作为普通攻击；
- `02 eva_style_knife_stab_twist_forward`：**HUMAN_APPROVED_AND_LOCKED**；
- `03 eva_style_knife_stab_twist_reverse`：**HUMAN_REJECTED**，动作过长。

Phase M 必须逐帧保持 02 不变，只替换 01，并将独立 take 2 截成约 2 秒的
短反手核心。
