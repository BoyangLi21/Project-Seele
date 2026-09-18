# R22 中途收尾后的续作清单

> 这是 R22 的历史交接快照。其暂停指令已被负责人后续“继续完成”明确取代；当前状态和证据以 [R23 记录](FACILITY_R23.md) 为准。下列旧交通源和“未完成”项不能覆盖 R23 的后续修复。

负责人在 2026-09-18 14:44 左右明确要求五分钟内收尾、立刻人工进入游戏，其他任务放到下一轮。**本轮不是全部完成。停止扩大施工。**

## 基线与入口

- 实际仓库 `D:/eva`；R21 已提交 `15510d5`。本轮尚未提交／推送。
- 正式地图：`run/saves/SEELE_TV_WORLD_PREVIEW_20260906`，本轮地图没有覆盖它。
- 验收地图：`run/saves/SEELE_R22_REVIEW`，入口 `start_eva_test_r22.bat`，启动参数 `--review r22-manual` 只选本轮资源包，无自动测试。
- 冷备份 `backups/SEELE_R22_20260918_122502`，基线 `artifacts/access_r22/baseline.json`，原有用户脏文件必须保留，不准整仓库 add/reset。
- 本轮私有资源包 `run/resourcepacks/eva_access_r22_review`，正式 `eva_real_model` 还未替换。
- 人工验收后，先备份用户在 R22 副本中的改动，再续作，不能用旧副本覆盖。

## 已实施与证据

1. 新交通图：`tools/plan_transit_r22.py`，选定 `.Codex/r22-native/rebuilt4`、`artifacts/access_r22/transit/built4`。两条地表线 R1/S1，保留 U1/U2/F1/F2；退休 C1/A1/S2/P1。R1 六节、其他列车四节。`geometry_audit.json` 无三维轨道交叉冲突或过陡标记；`cadence_trains.json` 覆盖四线，`cadence_F2.json` 覆盖一线，均检查真实原生 60 秒排班。
2. F2 有 18 段明确巡航弧线白名单，300→540 km/h；滑行/进近不改。Java offline agent 与游戏调用同一个 `UNFlightSpeedR22`；最新原生周期 420000 ms、七架。旧 `.Codex/r20-java` 的 Cadence class 曾过期导致空覆盖假阳性，已改为每次编译当前 Java 源，增加禁止空覆盖断言。
3. `build_transit_civil_r22.py`：14 组站台、251 根桥墩、两处双向扶梯换乘。首次应用前四个区有部分写入后遇到五个未完成区块；随后通过游戏原生生成五块，再完整应用。完整第二次 receipt 在 `civil/.../applied_20260918_141718_259290`，1,036,116 格；**最终总补丁要包括首次部分应用的差异，不能只用第二次 inverse 作为冷基线**。新增 `query_blocks.chunk_statuses` 预检防止再次部分应用。下一轮重点原生碰撞、桥下净空、站台到现有道路接口、扶梯首末级、护栏及柱子视觉。
4. 已用 `install_transit_r22.py` 安装原生数据到 R22 副本，并更新 `native_transit_r20.json` 兼容快照和 `native_transit_r22.json`。Main 安装受 `final_acceptance.json` 限制，尚无该通过文件。
5. `repair_access_r22.py` 已应用：删除 -308/-466/729 旧绕路，-335/-466/739 直连车站；西侧死端开向休息区；南上层落脚房间；210 个可达平台边缘防护，8018 格，含完整差量。
6. `replace_compact_walkways_r22.py` 已应用：5592 格自制慢步道退休，86 段原 MTR 配对步道，21872 格变化。1370 个截面因宽度／设备保留普通地面，需下轮逐类处理；禁止夸称所有长廊都已装齐。
7. 钢琴：固定官方 SHA512 的 Grand Piano Mod，`.Codex/local-mods/grandpianomod-1.0.0.jar`，`fetch_piano_r22.py` 已接入启动。原生 `BlockItem.place` 在 13/-389/355 放完整多方块琴，琴凳在13/-389/353。`r22_piano_review.json passed=true`，真实键盘 Z 的网络按下／释放通过。`artifacts/access_r22/piano_playable.png` 已目视。修复可选模组的固定420×270界面在大GUI倍率下裁切，以及Play页背包槽挡住琴键；退出后恢复原GUI倍率。第一次失败是测试误用了不映射的 A 键，已换 Z。向正式图迁移钢琴必须从 query_blocks 导出小范围精确差量，而非复制整块；大指挥室仅此例外获授权。
8. 三驾驶员皮肤为用户本机 Downloads 已有的64×64完整皮肤，未改像素，只私有安装；Renderer 用 slim。来源哈希 `asset_stage.json`。冬月的后梳灰发/眉毛/领口/外套模型层已改，待实景观察。
9. UN 膝甲根因为旧 `abs(x)>arm_edge && y>65` 把膝部归到前臂，旧手部裁剪还删掉部分腿甲。`build_lux_airframes_r22.py` 改为实际网格测地距离分区并按真正前臂裁手。新 UN00 243758 三角、UN01 228610、各62parts。`models/knee_weight_audit.json` 检查最终接缝权重，腿部低于85且absX<26无手臂权重。已放R22包，新增严格计数合同；还没实机攻击视觉验收。
10. `UNRecoveryR22`：新 `/seele military recover|reset 00|01` 及un00/un01别名；记录原UUID位置，等待加载而不重生，回原舱/原胶囊，reset恢复HP。UNBaseR21Review扩展r22-un-base准备了真实登机、攻击三帧、recover/reset及身份检查，**尚未运行**。`export_un_pair_r21.py`、`render_un_r21.py`支持 `--asset-root artifacts/access_r22/models`，尚未重新导出GLB/Blend。
11. NERV整词发音：`FacilityPronunciationR22`及NarratorWindows/Linux mixin，中文“奈尔夫”、英文nerve，界面名称不改。最早往MTR接口中注入的方法不能编译，已改为实际旁白实现类，当前编译/游戏已加载。语音听感仍需人工听。
12. 实时牌新增持久 `NativePlatformId`，减少挪站台后按旧坐标匹配失败。28块新地表牌已写入原生ID；地下及全部旧牌仍需扫描，时刻表运行画面还没逐站验证。

## 电梯：最高优先级未完成

`r22-lifts`测试入口和`LiftFrameR22Audit`已经加入。测试是站角落、持续走动并跳跃，8趟：主指挥后梯两趟、地表梯两趟、机库紧凑梯两趟、顶部会客梯两趟。World必须R22副本。

发现并改动：
- 原 `NervLiftPassengerSync` 对0.1格偏差就发 teleport，破坏插值；普通纠正改为setPos，并调用玩家 connection.resetPosition() 同步 vanilla first/lastGoodPosition，不关碰撞或移动校验。
- 原MovingElevators 1.4.12真实jar把世界X塞进move向量；改为(0,dy,0)。运动同步更频繁，小偏差渐进，大冷启动偏差轿厢和乘员一起校正。
- Native END-tick连续脚底支撑、实际顶棚形状限高、空中相对运动、横向舱内边界；到站最后一步不重复搬运。
- 客户端原生sendPosition发生在模组END-tick搬运前。新增 `LiftPassengerPacketsR22` / `LocalPlayerLiftPacketsR22Mixin` / `LocalPlayerPositionAccessorR22` / `LiftPassengerPhaseR22`，试图延后到native carry之后发位置。Invoker与Inject放同一Mixin会映射冲突，现分开，编译成功。

**仍未通过：** `lift_fixed7_run.log`、`r20_lift_review.json`：第一趟到站timer161发生一次inWall，位置约(13.70,-448,252.202)，蹭到Z251的轿厢墙。6th-fix保存的939帧 relative_y 全为0，无上下相对抖动，但到站靠墙问题还在。不要把早期曾8趟无伤的结果当成最新版本通过。下一轮先确认网络发送与native client END事件真正次序、人物位置何时被覆盖，以及到站贴墙碰撞；不要继续盲加全局免伤/关碰撞。最后一趟测试日志约14:45完成，客户端已退出。

## 指路牌与图的理解：未安装

`plan_pyramid_navigation_r22.py` 已建立209562个测量可走节点和明确电梯层口；80个计划路口中，机库与总部站互通，但**指挥室目标与全廊道图不连通**（可能是门/台阶表达，也可能是真缺口）。因此当前新标牌数量为0，拒绝生成无依据箭头。`artifacts/access_r22/navigation/junctions.json` 保存全部held及目标、层口。先核对指挥室入口和电梯到指挥层的真实路径，再装每路口三目的地牌。大指挥室认可布局不动，必要时修外围。

## 下一轮完成顺序

1. 接收人工反馈，冷备份人类这次修改；解决直梯到站与图中指挥室连接。
2. 新铁路/全部站台/换乘桥/原MTR步道的原生实走、整片边缘与门洞检查，修正所有发现，不只验中心线。
3. 扫描并补齐地下实时牌，装实测路口导向；检查重要建筑到站路径。
4. 跑r22-un-base，检查膝部攻击画面、UN回收复位身份；看冬月与三驾驶员实景；导出新版可编辑模型和离线预览。
5. 新线路至少实际乘车、F2加速后真实往返乘坐，保留R21 MTR共同单调时钟/有限纠错预算，不能退回旧绝对限速补丁。
6. 合并全图通行目录，剔除正式退休的旧站/旧路案例，重跑要求的检查并保留覆盖边界。
7. 正式图最终仅装审核过的精确差量；保留原机体/胶囊UUID、2344单向窗、236工作人员与大指挥室（只排除钢琴明确授权格）。R22五个新生成区块要有单独迁移/原生生成方案。
8. 完整build + 原生客户端检查通过后才按AGENTS提交推送；Trailer为 `Co-Authored-By: Ayanami_Rei <liboyang_621@126.com>`。不能暂时为了收尾宣称全部通过。

本轮Lux3D没有新扣费，原累计5/10积分未增加。不要泄露或重复用户密钥。
