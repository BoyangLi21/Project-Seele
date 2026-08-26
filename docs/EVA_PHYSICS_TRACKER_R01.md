# EVA 物理动作系统 R01

> 状态日期：2026-08-26。此文档记录当前已验证结论，防止后续任务重新走
> GeckoLib 动作播放、vanilla 根运动或手写 MPC 的旧路线。

## 目标架构

- 训练：ProtoMotions 3.1 + Isaac Lab（Linux x86_64）。
- 低层：50 Hz recurrent contact-aware tracker，导出 ONNX。
- 运行时：原生 C++ MuJoCo，固定 250 Hz。
- 高层：25 Hz 流式未来目标生成器；只输出身体相对目标、接触概率和
  效应器约束，禁止写根位姿。
- 权威状态：唯一物理骨架同时驱动 root、关节、碰撞、命中、抓取、渲染和
  网络状态。
- Forge 实体的位置/朝向仅镜像 physics pelvis，不参与运动求解。

目标生产链中必须移除：

- GeckoLib EVA 身体姿态控制；
- vanilla `travel` / jump impulse 对物理根的写入；
- animation ID / attack keyframe 驱动的伤害；
- 前方 AABB 近战；
- 实时手写 MPC；
- clip/state-machine 作为物理控制后备。

## P1 G1 验证结论

已验证：

- 策略与参考更新直接写 free root 的次数为 0；
- MuJoCo 真实接触与状态日志可记录、可复现；
- 经过路程重采样、接触 IK、Savitzky-Golay 平滑和二次接触修复后，P1
  参考达到：足部最大位置残差约 11.6 mm、最大朝向误差约 0.74°、marker
  P95 约 31.4 mm、关节硬极限违规 0、左右支撑脚平均滑速约
  0.0032/0.0026 m/s、逐帧关节变化 P95 约 1.69°。

未通过：

- 官方 G1 deployment tracker、速度列 PEFT、低学习率动作头、全 actor
  接触微调均未同时通过运行时接触、足滑和受推恢复门槛；
- 最好运行时接触 F1 为约 0.9343，低于 0.95；
- 没有候选在 4.0 秒前形成满足平面速度、直立、真实支撑和足滑门槛的
  0.5 秒恢复窗口；
- 因此这些 G1 权重只能作为失败/消融基线，禁止迁入 EVA 或 Forge。

本地 Windows 主机只有 RTX 3070 Ti 8 GB，且 ProtoMotions 的 Isaac Lab
依赖当前限定 Linux x86_64。完整训练应使用 24–48 GB Linux GPU；本机只做
Newton/MuJoCo 烟测、ONNX 和确定性验证。

## 41-DOF EVA 物理骨架

当前规范骨架：4 m、1080 kg、41 个受控 tangent DOF、free root；生产表示为
球关节，逐轴 hinge 版本仅用于重定向与扫轴测试。

已通过：

- `nq=55`、`nv=47`、`nu=41`；
- 质量 1080 kg，惯量正定并满足三角不等式；
- 六块足底碰撞几何在 bind pose 距地 2.5 mm；
- bind pose 无穿地/自穿透；
- 41 个单轴球关节/hinge 工具映射误差为 0；
- 16 对左右关节镜像位置和旋转误差为 0；
- 独立 heel/forefoot/toe、膝、掌面和指节接触体；
- 18 cm 落体测试中生产球关节骨架最低 upright cosine 约 0.996、最大地面
  穿透约 10.1 mm、root 直接写入 0。

当前视觉尺寸仍保持用户已确认的 24 blocks；规范物理空间 4 m 对应
6 blocks/m。除非另行确认，不采用 60 blocks 假设。

## 已验证运行契约

- 未训练 GRU ONNX 形状：G1 `354 -> 29`，EVA `1707 -> 92`，hidden 512。
- EVA 网络约 696 万参数；PyTorch/ONNX 最大误差约 `6e-8`。
- 本机 ONNX Runtime CPU 单角色 P95 约 0.46 ms（仅网络前向，不含物理）。
- ProtoMotions/Newton 已完成 2 轮端到端 recurrent PPO 烟测：hidden 会进入经验
  回放、按 done 单行清零，并按环境组成连续 8 步 truncated BPTT；最后一步损失
  可反传到第一步，checkpoint 保存成功。该随机策略又已导出显式 hidden ONNX，
  数值误差约 `3.6e-7`、CPU P95 约 0.23 ms。
- 共享内存 SPSC 固定包：command 256 B、state 512 B；state 包包含 root、
  41 关节、接触掩码和 8 个接触力值，不走 Minecraft 大 NBT payload。

以上 ONNX 权重均未训练，只证明形状、隐藏状态连续性、数值一致性和性能，
不证明动作质量。

## 本地私有审查资产

均位于 gitignored 的：

`artifacts/motion_research/physics_v1/`

关键文件：

- `P1_G1_AUTHORITY_FAILURE_AUDIT_R01.md/.json`
- `P1_ISAACLAB_LINUX_BUNDLE_R01.zip`
- `EVA_PHYSICAL_R02_VIEWER_R01.html`
- `EVA_PHYSICAL_R02_BALL_DROP_MULTIVIEW_R02.mp4`
- `EVA_GTP_RECURRENT_CONTRACT_R01.json`
- `EVA_PHYSICS_IPC_SCHEMA_R01.json`

## 下一硬门槛

1. 在 Linux 24–48 GB GPU 上训练新的 recurrent contact-aware G1 P1 tracker。
2. 20 固定种子至少 19 个不倒，root 写入 0，contact F1 >= 0.95，恢复
   P95 <= 1.5 s，支撑足平均/ P95 累计滑移分别 <= 0.005H / 0.01H。
3. Isaac Lab 结果导出 ONNX，在 MuJoCo 中通过相同测试及确定性重放。
4. P1 通过后，才把同一观测、动作、奖励和课程迁到 41-DOF EVA 骨架。

## 2026-08-26 阶段收尾与 Minecraft 预览

G1 是 P1 的标定机器人，不是最终 EVA。使用它是为了先验证强化学习、
权威 free root、接触、脚滑、恢复、ONNX 与 MuJoCo 链路；P1 未通过前，
不得把 G1 外形或权重称为 EVA 成品。

本轮新增验证：

- frozen teacher + recurrent residual 在 600 帧 MuJoCo 闭环中，root、关节、
  33 个刚体、接触力和 29 维动作与官方 teacher 逐值相同；
- residual 显式读取 heading-frame root velocity，恢复 episode 不再因普通跌倒
  立即终止；训练与验收均使用 2.5 s 的单次 `delta-v=0.5 m/s` 冲量；
- 从 G1 研究动作包提取 3 条 push-recovery 与 2 条 PushStand，经接触 IK 后
  marker P95 约 3.8--12 mm、无关节硬越界；
- 严格左右镜像 capture future 的往返关节误差为 0、轴基 determinant 为 +1；
- R63-E10 首次让负向冲量在 0.98 s 内形成合格恢复窗口，速度误差约
  0.053 m/s、支撑滑速约 0.009 m/s；正向未通过，因此不能升级为 P1 成功；
- R79-E20 的无扰动停止为 2/2，P95 约 0.34 s；启动、contact F1、整体足滑
  仍未同时达标。

为了让用户在 Minecraft 中看到当前姿态结果，Motion Lab 新增了一个隔离的
离线预览适配器：

- 资源：`assets/projectseele/motion/eva_physics_preview_v1.json`；
- `/seele motionlab demo unit01 physics`：回放当前 MuJoCo walk 状态；
- `/seele motionlab demo unit01 recovery`：回放当前单方向恢复候选；
- `/seele motionlab demo unit01 stop`：退出预览；
- 启动：`tools\start_test.bat motion`。

命令会显示 `OFFLINE MUJOCO REPLAY (NON-AUTHORITATIVE)`。该预览使用真实
MuJoCo 状态矩阵驱动实验场 EVA 骨骼，但它是记录回放，不是实时 sidecar，
不驱动战斗、碰撞或正式存档。普通 EVA 与 R02 动作链保持不变。

## 2026-08-26 实时校准控制器接入

离线预览不能作为强化学习接入验收：它仍然是逐帧播放记录。为避免再次混淆，
新增的 `live` 路径不读取 `.npz` 或动作 JSON：

- `tools/run_eva_live_physics_sidecar.py` 加载 R63 `epoch_10.ckpt`；
- 每个控制步先执行真实策略推理，再由 MuJoCo 积分，随后才发布当前状态；
- 共享文件保留 256 B 命令包与 512 B 权威状态包，并增加一个仅供当前 G1→EVA
  模型映射检查使用的 512 B 骨骼页；
- Java 使用序列锁读取实时根、接触和 15 个局部刚体四元数，并在渲染帧间插值；
- `/seele motionlab demo unit01 live` 是唯一实时入口；`physics/recovery`
  仍明确保留为离线负面对照；
- `/seele motionlab demo unit01 livepush` 对当前 MuJoCo 根施加真实横向
  `delta-v=-0.5 m/s`，不是切换受击动画。

本机烟测的 3 秒有效窗口产生 73 个状态，单独运行约 24 Hz；与 Minecraft
并行时约 19--20 Hz。它证明检查点已在线运行并被 Java 消费，但尚未达到产品
要求的 50 Hz 策略与 250 Hz 物理预算。当前使用的是 29-DOF G1 校准权重，
并通过 15 个身体刚体临时映射到 EVA；它不是尚未训练完成的 41-DOF EVA
策略，也没有接管正式存档的碰撞、伤害或玩家输入。

训练是必要的，因为 clip 只能给出固定时间上的姿势，不能根据当前速度、地形、
接触冲量、落脚失败、被阻挡或玩家中途改向重新分配关节力矩。生产目标是让
同一个低层策略在真实物理状态上连续输出控制量；动画数据仅可作为训练参考，
不能再成为运行时权威。

人工检查否决了把该 G1 校准器直接映射为 EVA 的视觉结果：关节比例与 bind
轴不匹配造成软腿和无意义摆动；仅移动渲染根而未镜像实体根又导致靠近时被
Minecraft AABB 错误剔除。该入口现已从普通 `motion` 启动流程隔离，只有显式
`tools/start_test.bat motion live` 才会启动，用途仅限检查通信和在线时间戳。
不得继续把这条 G1→EVA 临时映射用于动作质量迭代，也不得计入 EVA 进度。
