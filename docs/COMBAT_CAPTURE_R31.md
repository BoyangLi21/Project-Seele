# R31 真人动作选材与独立重定向

本轮先盘点已有素材，选出三组。文件均从已经下载的本机来源副本复用，没有重复下载整库，没有调用付费生成服务。原件、许可、散列与解码输出存放于 `artifacts/facility_r31/motion_sources/`，不纳入公开源码。

## 实际选出的素材

| 组 | 文件／动作 | 已完成的工作 | 来源与限制 |
| --- | --- | --- | --- |
| Haley Tuffles | ArmsGrappleStart、SpinThrowDown、AerialSlapDownwards、GettingUp | 实际 BVH 解码；NERV 初号机及 UN-00、UN-01 三套骨架分别重定向 | [作者官网](https://haleytuffles.com/motioncapture)说明为真人表演，iPiSoft 记录、Blender 清理，允许个人／商业使用；保留作者署名。 |
| CMU 18／19 双人组 | 18_03+19_03、18_05+19_05 | 复用并解码四个 BVH，核对原来源记录 SHA-256、同步帧数 | [CMU 原库](https://mocap.cs.cmu.edu/)允许使用和产品内包含，禁止直接售卖数据；既有 BVH 是 Bruce Hahn 转换、una-dinosauria 镜像，未假称原站直接提供此 BVH。 |
| Quaternius UAL2 Standard | Hit_Knockback、LayToIdle、Melee_Hook/Rec、NinjaJump、OverhandThrow 等 | 实际 GLB 骨架、43 个动作名称、时间 accessor 已读取；原文件与 CC0 许可已归档 | [作者包页](https://quaternius.com/packs/universalanimationlibrary2.html)。这是制作好的游戏动画，不宣称为真人动捕，也没有把付费版 130+ 动作算作已经取得。 |

CMU 的两组动作是双人牵拉与抵抗，不能称作完整双人过肩摔。Tuffles 的 SpinThrowDown 只有施术者，受力方仍需真实接触、抛物线和落地反馈。AerialSlapDownwards 提供空中下挥的身体姿势，原演员髋部高度振幅约 8.6 个厘米级源单位，不是从起跳到落地的完整弹道。游戏中的起跳与重力仍必须由服务端推进。

[ACCAD 官方资料](https://accad.osu.edu/research/motion-lab/mocap-system-and-data)也已查阅，确认其 CC BY 3.0 真人武术动作库。项目已有 149 个 Male2 BVH，此次没有为“搜集更多”再次下载，也未列为第四组。

## 交付接口

- `eva_combat_capture_r31.json`：按现有初号机的实测膝肘比例。
- `eva_combat_capture_r31_un00.json`：使用当前 `eva_body_r25.json` 的 `rigs[3]`。
- `eva_combat_capture_r31_un01.json`：使用当前 `rigs[4]`。
- 三者均为独立 schema 2，现有 52 个运动骨名同序，`rotation_wxyz`、`root_m`、`bone_position_xyz`、`foot_contact` 与现有 `EvaBodyPose` 文件格式一致。
- 四个 clip 名为 `r31_grapple_start`、`r31_shoulder_throw`、`r31_air_downstrike`、`r31_get_up`，自然时长约 2.042、1.667、1.958、6.167 秒；分别 124、101、119、371 帧，名义采样率 60 Hz。
- 没有覆盖运行中的资源包、原 R30 动作或用户已有动画文件。接入、时长调整和实际游戏验证由主任务统一处理。

UN 版本使用 `r30_elbow_socket_*`、`r30_knee_socket_*` 的真实坐标重算姿态，没有沿用 Tiger 的膝部 +11.4 偏移。手指保留各自新网格的轴向绑定，由游戏抓握层接管卷曲，不借用旧模型拳头的局部轴。

原演员水平旅行不叠加到游戏实体：所有输出帧的 `root_m.x/z` 都为零。根骨旋转造成的绑定枢轴补偿转移到根骨直接子节点，保留骨盆支撑关系。原 SpinThrowDown 含约 400° 旋身，已剥离演员整体舞台朝向，以免视觉模型转到使徒背面而逻辑仍朝前；保留的是骨盆相对双脚及胸廓相对骨盆的扭转。空中动作以胸廓瞄准平面对齐，躺卧起身用最终站立朝向作为固定参考，避免将悬空脚或躺卧脚的投影误当成朝向。

## 接触时机

- 抓取：对齐后的双手平均前伸峰位于源第 23/49 帧附近。若抓取段长 18 tick，建议第 8–11 tick 渐进建立手端接触，再保持抓握；不要一按键就把使徒吸到固定点。
- 投掷：去除整圈旋身以后，双手速度及前伸峰仍位于第 25/40 帧，下挥速度峰在第 26 帧。建议释放相位 0.60–0.65；26 tick 的投掷段可在第 16 tick 释放。
- 空中下击：源第 6–9/47 帧是下挥段，建议接触窗口约 0.12–0.21。伤害结算仍应检查真实手端／目标接触，不用固定时刻无条件命中。
- 起身：源第 140/148 帧才达到髋部起立高度的 90%；恢复站立碰撞前要查上方净空，建议控制权交还接近相位 0.95，而非半途弹回站姿。

## 已检查与仍需处理

实际 BVH 与三套输出均完成有限值、单位四元数、根 X/Z 为零的检查。UN 膝、肘上下段连接点误差约 `10^-14` 格量级；这个数只说明骨架接缝连续，不代表整套战斗已经真实或好看。站立抓取／投掷的脚部几何最低点接近地面，空中姿势允许脚部低于实体原点，应由跳跃高度和落地状态约束。

当前文件保留演员的转步；没有宣称消除了游戏世界里的脚滑。原 R12 的 `foot_contact` 主要按高度判断，转脚时不等于脚掌静止。游戏接入仍需用脚部速度、支撑足、实体位置与朝向做接触锁定，并在腿部达到伸展极限时释放旧锚点。手端接触也应渐进加权，避免 IK 把肩膀和肘部猛拉到目标。

`un00_retarget_evidence.json`、`un01_retarget_evidence.json` 包含逐动作误差、未锁脚的位移统计及每动作六个实际姿势的关节点。`retarget_contact_sheet.png` 是 CPU 绘制的骨架检查图，不是游戏截图或完整网格视觉验收。

后续接入新增 `eva_recovery_r31.json`：从原起身片段末段提取连续的手撑、左脚支撑和髋部上升，分别按五个实际骨架生成支撑数据。该文件记录原动作散列与每个骨架散列，打包时一起核对；它是独立起身支撑层，不把上文未锁脚的原始候选直接宣称为游戏验收成品。

生成代码：`prepare_combat_capture_r31.py`、`retarget_un_capture_r31.py`、`inspect_combat_capture_r31.py`。原始数据不是 MIT 代码素材；公开发行时须保留各自许可和署名边界。
