# R05：蹲行、持枪与空手右键重击

2026-09-08。负责人明确确认本轮替换的是 **空手右键重击**。R04 录像中的蹲行、枪身随动、肘部裂缝与低姿射击穿模被指出后，本轮重新检查了实际渲染网格，不能再用枪口或手腕坐标误差替代视觉验收。

## 本轮实现

- 蹲行换成本机 MoCap Online Demo 的 `MOB1_CrouchWalk_F`，保留左右脚、骨盆起伏和向前迈步时序，按 EVA 膝部与脚底重新求解。循环为 37 帧，行进相位对应 15 格步幅；蹲起使用两脚支撑约束。蹲姿碰撞高度由 42 改为 48 格，匹配新姿势的实际高度。
- 枪托由最终肩部姿态承载，绕贴肩位置转动。地面姿态的客户端身体与服务端枪口共享 `EvaBodyPose` 和同步的步态、蹲卧、抬枪及后坐信号。视线目标用于确定枪轴，再由头颈朝向瞄准线。左右手约束到实测握持位置；仰角增大时，左手可沿下护木滑动，右肘随仰角收拢。
- 头部最终朝向使用当前头盔与枪身的实际三角形检查，必要时选择最小的轻微抬头或侧倾，并平滑回到瞄准姿势。该避让只调整头部，不移动枪；避免固定间距在不同跑步阶段反复失效。
- 弹道直接采用同一枪架的枪口与轴向，包括卧射的地面俯角限制。取消了显示枪轴与实际弹道各自重新瞄准的分歧。
- 原模型上臂与前臂原本是分开的刚性片。修正肘部转动中心，并在接缝附近采用双四元数蒙皮；用空间容差匹配共享顶点，给两侧相同的焊接位置和权重。普通拳、重击、侧踹与刀动作也保留原手部目标后重新求解肘部。
- 空手站立右键换为 ACCAD `Male2_E4_CrossRight`，完整保留躯干转动、腿部支撑、出拳与回收，并修正手指轴辅助骨与握拳。资源为 58 骨、73 帧、1.2 秒；命中改为右拳曲线在 0.45 阶段结算。伤害仍为 35，冷却仍为 60 tick；左键已选 Group C、K1 侧踹和 Phase M 刀动作继续使用原资源。
- 动作过渡记录最终提交的姿态，因此退出持枪时能从实际身体和手部位置过渡。进入持枪的胸部变化随抬枪进度展开。剧情姿态、后勤锁定、启动及十字架状态不会被持枪求解接管。

右拳表演整体按接触方向旋转到驾驶员前方，脚部与身体使用同一方向校正。命中曲线移除了由实体物理已经执行的 root X/Z 位移，避免判定点重复平移。专用回放会在机体前方 30 格、拳头高度放置一个无 AI 的铁傀儡，读取重击造成的实际扣血后清理，以验证正前方目标确实会被击中。

网络协议由 25 升为 26。测试场的凸起标线与展示台边框已改为平铺；此前它们会把 EVA 抬高一至两格，干扰对蹲行的观察。该改动仅作用于专用 Motion Lab 的重置。

## 证据与检查方法

`EvaMeshAuditR05` 在真正提交三角形之后记录顶点，包含肘部蒙皮后的结果；坐标来自实际 draw matrix，而非 GeckoLib 4.8.4 中会重复加单位矩阵的 world-space 便利函数。独立 Blender BVH 检查枪与头、躯干、上臂、前臂的三角形相交，并逐对核对原始肘缝顶点。

前四轮回放明确记录过失败：最初肘缝最大接近一格，站立枪身穿头和上臂；修复后又发现仰角卧射左手不可达，以及俯瞄时枪托扫过头部。中间结果保留在 `artifacts/motion_review_r05/geometry_audit_*.json`，不能作为最终通过记录。

最终批次为 `run/screenshots/projectseele_connected/20260908_114757`：三机共 1,950 tick，1,560 张原生画面、1,557 条最终姿态记录。`runClient` 正常完成，随后 `gradlew --offline build` 通过。

| 检查 | 最终结果 |
|---|---|
| 实际提交网格 | 78 个三维快照，覆盖三机、跑步、移动中蹲下、站/蹲/卧射与近战衔接 |
| 枪与头/躯干/上臂/前臂 | 57 个持枪快照，三角形相交均为 0 |
| 肘缝最大距离 | 0.000063 格 |
| 枪口最大偏差 | 0.000051 格以内 |
| 右/左手腕约束最大偏差 | 分别小于 0.000027 / 0.000034 格 |
| 右拳命中曲线与实际手骨 | 接触/回收采样偏差小于 0.045 格；不重复加入实体移动 |
| 正前方目标实际扣血 | 初号机 35、零号机 29.75、二号机 42，符合既有型号倍率 |

原始报告为 `artifacts/motion_review_r05/geometry_audit_20260908_114757.json`，启动与构建日志为 `.Codex/r05-native-clearance.log`、`.Codex/r05-build-clearance.log`。完整录像 `artifacts/motion_review_r05/eva_r05_review.mp4` 按原生 tick 间隔导出；`eva_r05_heavy_slow.mp4` 仅截取空手重击及其起手准备，以 0.5 倍速显示。

新姿势仍需负责人确认观感与手感；没有把自动检查等同于人工视觉批准。

运行：

```powershell
$env:JAVA_HOME='C:\Users\liboy\jdks\jdk-17.0.19+10'
.\gradlew.bat --offline runClient -PquickPlayWorld=SEELE_EVA_CONNECTED_REVIEW_20260905 -PmotionReviewR05=true -PmotionReviewR05All=true
```

该开关只允许 `SEELE_EVA_CONNECTED_REVIEW*` 副本，依次通过真实驾驶包检查 01、00、02 的站射、行进、蹲行、卧射、仰俯角、空手重击接左键、侧踹、正反手刀与切回步枪。俯仰输入超过限值时，游戏仍使用既有 ±55° 限制。

验收覆盖的是地面姿态。空中仍保留原跳跃身体；服务端弹道与原跳跃姿态的完整同源校准不属于本轮已通过范围。

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --python tools/audit_eva_mesh_r05.py -- run/screenshots/projectseele_connected/BATCH
python tools/export_eva_review_video.py run/screenshots/projectseele_connected/BATCH artifacts/motion_review_r05/eva_r05_review.mp4
```

## 动捕来源与本机数据

[ACCAD / The Ohio State University Open Motion Project](https://accad.osu.edu/research/motion-lab/mocap-system-and-data) 按 [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) 提供数据；官网 Male 2 清单包含本轮右拳来源。派生资源记录来源链接、许可、源轨迹哈希、裁剪范围及修改内容。

[MoCap Online Demo](https://mocaponline.itch.io/mocap-online-demo) 的蹲行、持枪动捕及其重定向结果只保存在本机资源包和 `run/projectseele-local-maps/eva_body_r05.json`。原始数据、模型、贴图及私有重定向不进入仓库。`tools/build_eva_body_r05.py` 可利用本机已提取数据重建；发行代码提供无私有文件时的既有资源回退。

开工时已为三个原有未提交资源记录 SHA-256；本轮不得提交或覆盖它们：`eva_unit01.animation.json`、`eva_unit00.geo.json`、`eva_unit02.geo.json`。

## 三处设施的斜视图

三张图读取当前 `SEELE_TV_WORLD_PREVIEW_20260906` 的 R04 实际方块与保留实体，以三维遮挡和剖切方式绘制：

- `artifacts/facility_views_r05/pyramid_3d.png`
- `artifacts/facility_views_r05/terminal_dogma_3d.png`
- `artifacts/facility_views_r05/launch_3d.png`

金字塔显示六层房间与楼梯核心；Dogma 包含按存档位置放置的 Lilith 网格。发射区图裁掉近侧墙与部分顶面以展示机库和下段竖井，没有显示动态 EVA 与车辆。图中的剖开并不是实景破洞，机库实际屋顶仍为 R04 封闭结构。生成过程使用 `query_blocks.py` 的既有读取链，本轮没有改写当前 TV 存档的方块。
