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
