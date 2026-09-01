# EVA 真人踹击评审 Phase U

状态：**KICK_GROUP_ELIGIBLE_FOR_HUMAN_REVIEW_ONLY**。普通攻击 C 已按项目负责人
要求以 `2.0×` 晋升正式左键；本阶段的三条踹击尚未接入游戏。

## 来源与候选

三条均来自 G1 Moves 的 MOVIN TRACIN 真人 Karate 捕捉，许可为 CC BY 4.0；
没有使用视频姿态估计、拳击、体育投掷或旋转踢。

| 编号 | 动作 | 原始 BVH 窗口 | SHA-256 |
|---|---|---:|---|
| K1 | 左侧踹 | `M_Move10` 1468–1552 | `FADB13A4A2DCDD1C327E519210EFEE52334D191FCE29A32384BF71799102178E` |
| K2 | 右前踹 | `M_Move18` 574–660 | `D5498405E8CD8A81FAD2D3B25826F30D3B203E7A87FB2BAB9888D5C6F888EB3E` |
| K3 | 右弹踢 | `M_ShortMove13` 242–328 | `AF02568686439170B64D2D0D008423E6F96FE7F8F6FD04FA9B9EF85AEF6604C1` |

官方目录与动作标签见
[G1 Moves dataset](https://huggingface.co/datasets/exptech/g1-moves)。源文件只保留在
忽略的研究目录；仓库提交评审资源、确定性清单和生成工具。

## 重定向与接触合同

- 保留捕捉的骨盆、躯干、双臂、双腿与支撑转换，不锁死下半身；
- 双手使用半握守势，踢腿期间不把人体手指通道写进 Tiger；
- K1/K3 由非踢腿脚独占支撑；K2 在右脚准备支撑后切换到左脚承重；
- 支撑锁只写 root，不修改关节旋转；三条支撑脚水平／垂直漂移均低于
  浮点审计精度；
- K1/K2 的世界 root 缩放为 `0.72 / 0.85`，K3 为 `1.0`。该 root 只用于
  离线评审，若以后晋升，正式位移仍必须由服务端 EVA 实体授权；
- 精确接地使用每 clip 恒定 root 抬升，最大 `0.0144395m`，避免逐帧抬升破坏
  支撑脚锁定。

## 自动门禁

- 原始解剖重定向：三条方向误差 `0°`，膝肘无反折；
- Tiger 动作构建：`3 clips / 0 failures`；
- 单支撑 root 锁：`3 clips / 0 failures`，最大修正 `0.17872H`；
- 精确 Tiger 全身：`3 clips / 0 failures`；
- 精确 Tiger 通用 3D：`3 clips / 0 failures`；
- 自动结果只允许 `ELIGIBLE_FOR_HUMAN_REVIEW_ONLY`，不能批准动作是否像 EVA。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_ordinary_group_c_kick_phase_u_review\20260902-001238
D:\eva\artifacts\motion_research\eva_ordinary_group_c_kick_phase_u_review\20260902-001238.zip
```

合并视频：`00_EVA_GROUP_C_2X_AND_KICK_PHASE_U_ALL.mp4`。`01` 是已选 C 组的
两倍速节奏确认；`02–04` 依次为 K1/K2/K3。右下红色 `动作号-帧号` 只表示
视频时间顺序，不是模型、贴图、UI、骨骼、命中点或关节标记。

人工反馈可直接写：`选 K1/K2/K3`、指定组合，或`三条都不要`。在收到选择前，
踹击不会进入正式按键、伤害或动作批准锁。
