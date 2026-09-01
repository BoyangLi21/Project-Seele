# EVA 普通攻击 Phase O 人工验收

状态：**COMBO_BEAT_CANDIDATE_ONLY**。它不再作为完整普通攻击接受验收，
只保留为后续持续左键连击中的重击节拍候选。正式游戏动作未替换。

## 已锁定边界

- 持刀左键：Phase M 正手刺入扭转；
- 持刀右键：Phase M 短反手刺入扭转；
- Phase O 没有修改或重新渲染两条刀动作；
- Phase N 低肩 Chidori 前冲已人工判退，不得靠加速或镜头震动重新包装。

## 动作词汇与来源

新候选 `eva_forearm_lariat` 是肩胯带动的右前臂横砸。来源为 Haley Tuffles
通过 iPiSoft 实拍并在 Blender 清理的免费动捕 `ArmsLariat.bvh`，取源帧
13--40 的完整蓄力、挥击、制动和随动段。内附 `ReadME.txt` 明确允许个人或
商业项目免费使用且无需署名。

该动作不是拳击、掌击、爪击、双臂下砸或纯前冲。源筛选中完整 Lariat 的
主臂峰值约 `6.63 H/s`，峰后速度下降约 `84.7%`，骨盆与胸肩角速度合计约
`648°/s`，冲击窗口存在脚底支撑。旋转接近 180° 的短花式 Lariat 被筛除。

## 运行时等价门禁

- 最终：70 个 60 FPS 采样，1.15 秒；
- 最大相邻旋转步长：`16.87° < 20°`；
- 精确 Tiger 全身审计：`1 clip / 0 failures`；
- 精确 Tiger 通用 3D 审计：`1 clip / 0 failures`；
- 无支撑占比：`0.0`；最大 root 位移：`0.07582 H`；
- 最大手部活动范围：`0.56326 H`；最低网格高度：`-0.050001`；
- 结束策略为 `PRESERVE_CAPTURED_FOLLOW_THROUGH`：不插入站姿重置。若后续
  晋升 live，移动或下一击必须从该随动姿势继续，不能把它强行循环回首帧。

自动门禁只表示可交人工验收，不构成 EVA 审美批准。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_mocap_ordinary_phase_o_manual_review\20260901-213327
D:\eva\artifacts\motion_research\eva_mocap_ordinary_phase_o_manual_review\20260901-213327.zip
```

合并视频：`00_EVA_ORDINARY_PHASE_O.mp4`，三视图、30 FPS、35 帧。右下红色
`01-帧号` 只表示时间顺序。项目负责人随后补充：普通攻击必须支持持续左键的
无站姿重置连击，因此该视频不再单独请求最终批准。
