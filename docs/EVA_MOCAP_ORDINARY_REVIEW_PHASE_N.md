# EVA 普通攻击 Phase N 人工验收

状态：**HUMAN_REJECTED**。正式游戏动作未替换。

## 已锁定边界

- 持刀左键：Phase M `eva_locked_knife_stab_twist_forward`，正手刺入扭转；
- 持刀右键：Phase M `eva_short_knife_stab_twist_reverse`，短反手刺入扭转；
- 本阶段没有重定向、重渲染或修改上述两条刀动作。

正手/反手 `frames` 锁哈希分别为
`414427cf77b59c25912f9fb1821dfa480c5e0be14a88d4969c945e8ff64acbbb` 与
`19e7d2a37b46574620df1d55e0ce02d6c0373c02c778740beccece6c8dfe4ae9`。

## 新普通攻击候选

`eva_low_shoulder_drive` 取自 Rapa Motion 免费 Anime/Mudra 真人动捕包的
`AS_Anime_Chidori_Attack_02_Ybot.fbx` 源帧 352--511。它保留全身步伐、
骨盆、躯干和肩部时序，动作意图是低肩与骨盆先行、右臂最后打出；不是
拳击直拳、掌击、爪击或双臂扑进下砸。最终 112 个 60 FPS 采样，时长
1.85 秒。

自动否决门禁结果：约束门禁通过；精确 Tiger 场景 `1 clip / 0 failures`。
精确场景实际无支撑占比为 `0.125`，低于此全身前冲候选预先声明的 `0.15`
上限；最大 root 位移 `0.16851 H`，因此若晋升正式游戏，服务端必须提供
对应 root motion。自动结果不构成视觉批准。

## 人工结论

项目负责人判退：动作只有向前位移，没有 EVA 普通攻击所需的冲击感。根因不是
播放速度，而是源动作缺少可读的蓄力、肩胯旋转加速、接触瞬间制动以及有重量的
随动回收。该候选只保留为负面证据，不得靠加速、镜头震动或换名重新晋升。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_mocap_ordinary_phase_n_manual_review\20260901-211122
D:\eva\artifacts\motion_research\eva_mocap_ordinary_phase_n_manual_review\20260901-211122.zip
```

合并视频：`00_EVA_ORDINARY_PHASE_N.mp4`，三视图、30 FPS、56 帧，右下红色
`01-帧号` 只表示时间顺序。本轮只需判断这一条普通攻击通过或不通过。
