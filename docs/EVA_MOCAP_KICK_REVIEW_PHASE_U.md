# EVA 真人踹击评审 Phase U

状态：**K1_SIDE_LEFT_SELECTED_LIVE_1P5X**。普通攻击 C 和 K1 左侧踹均按项目
负责人最终要求以 `1.5×` 接入；K2/K3 继续保持未选评审证据。

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

## 正式运行时晋升

- K1 live 资源：`assets/projectseele/motion/eva_kick_side_left_v1.json`，
  `1 clip / 50 bones / 84 frames`，不重采样，运行时 `1.5×`；
- 沿用 B 键原“踩踏”动作入口，界面名称改为“EVA：侧踹”；
- 原踩踏伤害 `50`、冷却 `50 tick`、范围和击退均保持不变；伤害改在 K1
  第 48 源帧、约第 `11 tick` 接触时结算；
- 普通攻击期间按 B 会缓冲侧踹，侧踹期间按左键会缓冲下一次普通攻击；双方
  都等待当前动作完成后再切换，不允许两个 full-body owner 同时写骨；
- 跨动作前 `0.14s` 使用 `0.060s` 半衰期惯性连接，root 单渲染帧限幅
  `0.0055m`。五个普通攻击↔侧踹边界的最大渲染旋转步长 `18.0063°`；
- 水平前压由服务端读取同一 root 曲线并移动实体；按最高同步率审计，最大
  `5.6094 blocks/tick`，低于 `6` 格安全门槛；
- K1 live 精确 Tiger 全身、通用 3D 与资源/代码合同均 `0 failures`。

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

该包为历史选片证据。项目负责人已选择 K1；K2/K3 不接入正式按键、伤害或
动作锁。
