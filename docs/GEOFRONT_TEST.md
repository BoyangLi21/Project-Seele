# GeoFront / 第三新东京市连续地图测试

连续地图的连接、发射井、LCL、审计和回退场景由 Project SEELE 原创代码实现。本机开发版还可拼接用户下载的 EVA-X 球体、NERV Command Module 与东京-3 高楼；这些私有资产位于 `external-assets/` / `run/`，不会进入 mod jar，正式发布前必须另行取得作者授权。第三新东京市和 GeoFront 位于 **同一个 `projectseele:geofront` 维度**：城市在地表，GeoFront 在封闭地下穹顶内，三条 EVA 发射井是连续方块空间，不是传送门。

## 坐标与硬契约

- GeoFront NERV 地板原点：`(30, -444, 296)`；椭球中心世界高度为 `Y=-332`。
- 第三新东京市原点：`(30, 80, 220)`。
- Unit-00 / Unit-01 / Unit-02 井中心：`X=2 / 30 / 58, Z=220`。
- GeoFront 球体内地下床位：`Y=-443`；东京-3 地表床位：`Y=79`。
- 每条井外壳为 `15×15`，内部连续净空为 `11×11`。
- 上下床位相距 **522 格**；正常发射按 2 格/tick 计算为 261 tick。
- 640 格宽 GeoFront 椭球顶部为 `Y=-12`、底部为 `Y=-652`，与东京-3 地面之间保留 92 格岩层；Terminal Dogma 最低层距维度基岩下界约 20 格。
- 东京-3 使用普通 Overworld 噪声地形，不是超平坦世界；可移动城区约 416×416，包含 66 栋内城装甲楼、29 栋外环楼与三座本机私有高楼。
- 维度拥有正常天空、昼夜与天气；GeoFront 使用 `0.62` 环境反射光、14 格间距的隐形地面光层和稀疏维护灯阵，穹顶仍保持实体封闭且不会刷怪。

## 首次建造与地图审计

1. 启动桌面的 `Project SEELE 测试.bat`，进入允许命令的创造世界。
2. 执行 `/seele geofront setup`。该命令先建第三新东京市，再建 GeoFront，最后切通三条竖井；首次运行写入方块较多，短暂卡顿属于预期。
3. 玩家会到达 GeoFront 观察位。执行 `/seele geofront audit`，通过结果必须同时包含：

   ```text
   valid=true mapVersion=17 controlMarkers=true lowerBeds=3/3
   surfaceBeds=3/3 continuousShafts=3/3 clearExits=3/3
   ```

4. `/seele geofront operations` 进入 NERV 作战中心；南侧路线通往观察桥，北侧三条通道分别通往三台 EVA 的高位插入栓栈桥。下层大厅东端的橙色通道通往 Central Dogma 实体梯井。
5. `/seele geofront surface` 只是开发用城市摄影机捷径，不代表 EVA 的正常移动方式。EVA 必须经过真实竖井上升。
6. `/seele geofront exit` 返回进入连续地图前保存的维度与坐标。

## 本机私有地图资产

桌面启动器与 `tools/start_test.bat` 会在检测到以下输入时运行 `tools/prepare_local_map_assets.py`：

- `EVA.rar` 解出的 EVA-X 球体：作为 GeoFront 外壳保留；
- `nerv-comand-module`：转换并放入地下作战指挥区；
- `tokyo-3-type-skyscrapper1-converted.schem`：在东京-3 战区放置三座实例。

转换结果和新建的 `SEELE_TOKYO3_REBUILT` 存档都只留在本机；旧 `SEELE_TOKYO3_COMPLETE` 原样保留，不再作为首选测试档。资源缺失时仍可使用原创方块回退结构，但审计会分别报告 `privateShell`、`commandMarkers`、`imported` 与 `skyscrapers=3/3`，不会把回退结构冒充下载资产。

专用维度的海平面被固定在最低构建高度 `-544`：这是为了避开原版噪声生成器在 `Y < min(-54, sea_level)` 强制放置岩浆的代码路径。每次新档仍会抽样整颗 640 格宽椭球；只要发现一个原版岩浆样本，自动化就拒绝把玩家送入 GeoFront。

无人值守截图会让服务端玩家跟随十三个机位的“镜头—目标”中点移动，保证六区块性能配置下两端都真实加载；除自然湖、森林、NERV 金字塔、Central/Terminal Dogma、LCL 湖和发射终端外，作战中心、观察廊、简报室、医疗支援室与压力前室也分别取证。自动会话结束时玩家回到东京-3 地表安全点，不再把下一次测试存到虚空中。

已安装地图再次执行 `setup` 时先补齐指挥室、MAGI 标签与遥测实体，再做整图审计；通过后日志会出现 `Integrated NERV map reused without full rebuild`。只有显式深度审计确实失败才会重建城市与球体，避免把暂未载入的显示实体误判成地图损坏。

日常的 MAGI CHECK、三机联接和屋岛作战启动走独立的 `runtime gate`：它仍逐格检查三条 11×11、522 格实体井、上下床位和地表出口，但不再同步加载远处森林、湖泊、外环城区与 Dogma 美术地标。2026-07-19 实机重复档结果为首次冷加载 `3228ms`、同一会话热检查 `29ms`；五阶段同维出击截图通过。MAGI 的文字标签属于显示层，缺失不会错误阻断机械联锁；深层分块保持加载时每 40 tick 自动自愈。

## 东京-3 实体下沉与穹顶都市

城市装甲不再把楼宇删除或只在地表做缩短动画。`/seele tokyo3 retract` 以每 20 tick 一层的速度驱动 66 栋内城装甲楼和 29 栋外环楼；每下降一层，地表少一层实体墙体，同时在 GeoFront 球体曲面下方多一层悬挂墙体。三座本机私有 NBT 高楼也按同一深度移动，但采用 12 格量化步长避免每 tick 重放大型模板。

- `/seele tokyo3 status`：报告当前深度、目标深度和运行状态；
- `/seele tokyo3 retract`：从地表下沉到最大深度 285；单程约 285 秒；
- `/seele tokyo3 restore`：沿原路线复位；完整下降—复位约 10 分钟；
- 地表完全回收时，审计必须同时得到 `towers=66/66`、`outerWards=29/29` 和 `ceilingBuildings=95/95`；只消失、不在地下出现会直接失败；
- 回升前会检查楼内的玩家与 EVA，检测到夹压风险时暂停该层，而不是把实体封死。

自动视觉入口 `tools\start_test.bat visual tokyo3_retraction` 依次拍摄地表部署、部分下降、GeoFront 完全悬挂和地表复位。该流程会真实等待状态机，不使用瞬移伪造关键帧，因此运行时间约十分钟。
## NERV 实时指挥室

`/seele geofront operations` 进入下载的指挥模块。五块 MAGI 风格文字/传感器屏每 40 tick 从服务端实体刷新：

- EVA-00 / 01 / 02：同步率、HP、A.T. Field、武器、姿态、发射阶段和载台高度；
- 战略屏：拉米尔 HP / A.T. Field / 核心暴露、驾驶员航向与俯仰、实体坐标，以及 522 格物理路线状态；
- 光学屏：从真实驾驶员眼位、yaw、pitch 采样 20×10 射线栅格，并标记视野内最近使徒。
此外，文字屏上方还有 00/01/02 三块 16:9 实体视频面板。对应机体的第一驾驶员客户端每 5 tick 抽取一次最终第一人称 framebuffer，缩放为 160×90 PNG，经服务器核验机体型号、维度和第一乘员身份后，只转发给位于作战中心/观察廊/支援房间边界内的玩家；无信号时显示对应机号的待机栅格。该链路目标约 4 FPS，与上述 20×10 服务端光学传感器是两套互补系统。真实多人画面仍必须按 `NERV_OPERATIONS_TEST.md` 用至少两个客户端人工验收。


结构审计必须包含 `operations={... telemetry=5/5}`。屏幕显示的是实际实体数据，不是固定装饰文本；为避免 640 格透明椭球场景中的服务器卡顿，遥测以 40 tick（2 秒）为周期刷新，并且不会在每次刷新时重装按钮或标签。

`overview`、`surface` 与 `operations` 是轻量导航指令：它们只加载目标/地图标记区块并修复小范围安全落点，不会触发整座 GeoFront 重建。只有显式执行 `/seele geofront setup` 才允许进行完整结构修复。

## LCL 湖

湖中必须是真正的 `projectseele:lcl` 流体，而不是橙色玻璃，也不能全局替换普通水：

- 湖床相对 GeoFront 原点为 `Y=-4`，LCL 从 `Y=-3` 填充到 `Y=1`，深 5 格；
- 进入后有橙色水下雾与低亮度效果；
- 玩家可以游泳并持续恢复空气，不会在 LCL 内溺水；
- 玩家默认每 40 tick 恢复 1.0 生命值；仅玩家恢复，使徒和 EVA 不会利用湖泊自动回血；
- 浸没在 LCL 中的掉落物到达原版过期时间后会持续短时续期，取出后恢复正常过期；
- 离开 LCL 后普通水的贴图、颜色与溺水规则必须保持原版行为；
- `/seele geofront audit` 的 `lclLake=true` 必须来自流体类型检查，而不是颜色方块检查。

## 三机同维度出击

1. 完成地图审计后执行 `/seele geofront link`。命令会在三个地下床位创建或复用 Unit-00/01/02，并把各自的地表床位登记为 **同一维度** 的目的地；不会搬运或复制 EVA 到另一个维度。
2. 执行 `/seele geofront sortie_audit`，必须报告三种机型、三条有效同维目的地和三个可达高位栈桥。
3. 从高位背部栈桥瞄准插入栓入口并右键，或用 `/seele silo board` 作为确定性测试后备。
4. 同步完成后，11×11 载台带着原实体、原驾驶员沿井上升。中途按 `F3` 观察：维度应始终为 `projectseele:geofront`，实体 UUID 不变。
5. 到达地表后 EVA 基座位于 `Y=80`，随后进入 1 tick 的连续路线同步清场；结束前输入和弹出仍被联锁。
6. 日志应出现 `NERV continuous sortie complete`，并报告 `rise=522`。主流程若出现 `NERV cross-dimension sortie complete` 即验收失败。

`EvaUnit01Entity` 中保留的 `changeDimension` 分支只服务旧存档或独立短井兼容。静态与人工验收都要求先命中 `destination == sourceLevel` 的同维分支；legacy 分支存在不等于连续地图通过。

## Central Dogma / Terminal Dogma

Terminal Dogma 不是独立维度或指令传送房间。正常路线为：NERV 下层大厅东端 `X=+32, Z=-23` → 橙色气密走廊 → `X=+42, Z=-23` 的 **61 格双向梯井** → 井底 L 形检疫通道 → Terminal Dogma 东侧观察廊。`/seele geofront dogma` 仅是开发摄影机捷径。

深层椭球封印室相对 GeoFront 原点中心为 `Y=-58`，包含：

- 三面 U 形观察栈桥与通往池边的第二段实体梯道；
- 独立 `projectseele:lcl` 封印池，液面 `Y=-75`，可呼吸/游泳规则与主 GeoFront LCL 湖相同；
- 红色十字封印架、白色静态巨人结构、七眼面具、核心观察窗与红色双叉封印枪轮廓；
- 顶部、梯井、深层走廊、椭球外壳、LCL、十字、标本和观察层的运行审计。

当前白色巨人是原创方块结构，用于把空间、比例、路线和剧情舞台做实；它不是已验收的最终莉莉丝角色模型。后续替换模型时不得删除这条物理通路、LCL 池和结构审计。

三座地下井的南侧下部使用防爆观察玻璃；高位插入栓检修门仍保持净空。重复执行测试时只会归并无人驾驶、未发射的同型号重复体；只要任一重复体有人驾驶或正在发射，自动归并必须拒绝执行。

## 自动视觉验证

地图景观：

```bat
tools\start_test.bat visual geofront
```

必须生成 `cavern_overview`、`natural_lake`、`forest_canopy`、`nerv_pyramid`、`nerv_operations`、`nerv_support_gallery`、`nerv_briefing_room`、`nerv_medical_support`、`nerv_pressure_vestibule`、`central_dogma_descent`、`terminal_dogma`、`lcl_lake`、`lift_terminals` 十三张图，并通过服务端与客户端地标审计。

连续发射：

```bat
tools\start_test.bat visual geofront_sortie
```

必须生成五个状态门控帧：`three_units_ready`、`entry_plug_locked`、`live_pilot_sensor`、`ascent_mid`、`tokyo3_surface_arrival`。`live_pilot_sensor` 保持自动化玩家真实乘坐 EVA，只把独立摄影机移到指挥室，因此第五块屏幕必须显示由驾驶员眼位、yaw、pitch 实时采样的 20×10 光学画面，而不是 `NO ACTIVE PILOT LINK`。`ascent_mid` 只允许在相对地下原点上升 80～208 格时拍摄；到达帧必须仍处于同一维度，并达到相对地下原点至少 201.5 格。

离线硬契约：

```bat
python tools\validate_geofront_contract.py
python tools\render_launch_silo_preview.py --strict
```

离线脚本能证明坐标、结构、分支顺序和状态机合同，不能代替玩家对碰撞、速度感、光照、城市比例与驾驶舒适度的肉眼验收。

## NERV 实体作战控制台

下载的 NERV 指挥模块内、五块实时屏幕前方现在有七个带发光标签的实体按钮。它们从左到右为：

1. “MAGI CHECK”：审计连续地图，创建或归并三台无人且未发射的 EVA，并重新链接三条实体竖井。
2. “EVA-00 RELEASE”、“EVA-01 RELEASE”、“EVA-02 RELEASE”：只释放已经从高位插入栓入口登机、处于 LAUNCH_LOCKED 的对应机体；无人机体、未链接床位和未完成联锁都会拒绝。
3. “CITY ARMOUR”：在装甲楼部署/回收之间切换，复用原有持久化逐层动画和防夹检查。
4. “YASHIMA START”：从指挥室启动拉米尔战、警报和装甲都市回收。
5. “BATTLE ABORT”：销毁本次作战拉米尔、清理持久化记录并请求城市复位。

按钮保留原版按下动画和点击声；执行结果同时写入玩家消息、日志和战略屏的 “LAST COMMAND” 行。/seele geofront audit 的作战中心结果必须包含：

    commandConsole={valid=true controls=7/7 bases=7/7 labels=7/7 supports=7/7}

单人游玩仍可由插入栓同步完成后自动发射；控制室释放用于多人指挥角色和紧急提前释放，不绕过驾驶员、床位或竖井安全联锁。

第五块 “ENTRY PLUG / LIVE OPTICAL SENSOR” 屏不是固定装饰文字。服务器每 40 tick 从实际驾驶员眼位、yaw 和 pitch 构造 70°×46° 视锥，采样 20×10 条射线并按天空、地形、LCL、水、植被、雪、玻璃和危险方块着色；最近使徒若进入视野会以红色 X 标出，中心黄色 + 是驾驶员光轴。它是低分辨率 MAGI 传感器画面，不是递归渲染的第二个 Minecraft 客户端视口。

## 当前完成边界

当前通过自动实机门禁的是：本机 EVA-X 穹顶、下载的 NERV 指挥模块、五屏实时遥测、七键实体控制台、主 LCL 湖、Central/Terminal Dogma 实体路线与封印池、三条连续发射井、防爆观察窗、三机地下冻结与同维地表出击，以及拼接了三座私有高楼的东京-3 战区。城市街区密度、莉莉丝最终模型、更多 MAGI/维修内饰、最终地图授权与人工观感仍需继续迭代；不得仅凭“能生成”标记为最终美术完成。
