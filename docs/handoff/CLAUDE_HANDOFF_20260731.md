# Claude → Codex 交接(2026-07-31)

范围:自上次交接以来 Claude 在本仓库做的全部改动、查明的事实、以及未完成的部分。
**所有改动均未提交**,与 Codex 的未提交改动混在同一工作区。

---

## 0. 一句话状态

- 编译 `compileJava` **通过**
- 指挥室问题已定位到根因并给出可执行修复(数据包函数 + 代码常量已改)
- **金字塔内部整体重做的清空函数已生成,尚未执行**(用户已批准,等执行)
- 两个新的离线审计工具已就位,可用于验证后续重建

---

## 1. 查明的事实(带证据,可复核)

### 1.1 指挥室母版从未包含 deepslate_bricks / sea_lantern
解析 `nerv_command_left.nbt`(149 种方块、33,797 格):
`deepslate_bricks = 0`、`sea_lantern = 0`。母版用的是 `deepslate_tiles(912)`、
`polished_deepslate(1099)`、`chiseled_deepslate(1425)`。
→ **S20 指挥室里所有这两种方块(9,286 格)都是我们自己的构建器后加的。**

### 1.2 指挥室在 S20 已被改掉 30.8%
母版 33,797 格 authored 方块中,**只有 23,372 格(69.2%)与现状一致**。
主要变化:`black_concrete→stone` 3,025 格、被挖空 2,555 格、
`→deepslate_bricks` 约 1,000 格、`→lcl` 355 格、屏幕 dummy 被删 1,088 格。

### 1.3 母版↔世界的精确映射(三重独立验证)
```
S20 = (模板x + 2, 模板y − 465, 模板z + 263)      ← 迁移前
```
- 由五个席位锚点联立解出,Ikari/冬月/左中右操作员**全部精确吻合**
- 房间尺寸 **56×77×129**,与母版模板尺寸一致
- 与代码里既有的 `COMMAND_TRANSFORM_ORIGIN = (2,-465,263)` 完全相同

### 1.4 挡住屏幕的是 z=353 的面板墙,且清理代码差一格
`clearCommandSightline()` 清的是 `z[348,352]`,而墙在 **z=353**。
从五个席位向两块屏幕射线投射,遮挡物 107 格,集中在 z=353(102 格)。
模拟清除后重新投射:**残余遮挡 = 0**。

### 1.5 指挥室前方被切掉了 9,110 格
提取边界 `COMMAND_BOUNDS = (1,-61,-33)..(56,15,95)` 在 **z=95 处切断**,
而源结构实际延伸到 **z=143**。丢失部分:`black_concrete 4,916`、
`blue_concrete 1,748`、`glass 493`、`green_wool 416`、`white_wool 203` 等。
**只有 +Z 一面被切,其余五面完整。** 切断原因:再往前会穿透金字塔外壳。

### 1.6 源存档里有两个相同的指挥室
`Nerv Comand Module` 中 x[8,46] 与 x[108,146] 各一个(相差 100 格),
形状完全相同。项目使用的是前者(Ikari 座椅在源坐标 `(27,-2,21)`)。

### 1.7 S21 实验:换干净世界救不了(假设被证伪)
建了一个零继承的新世界,用同一套构建器跑一次 `IntegratedNervMapBuilder.build()`,
**长出来的还是同样的墙和死路**。结论:**问题在构建器本身,不在"反复维护叠加"**。
(S21 世界与代码均已删除/回退,只保留这个结论。)

附带发现:`build()` **单跑一次建不出完整设施**——机库校验、MAGI 核心、
指挥桥、路线连通都是靠 `prepareRuntime()` 的 ensure 链补齐的。旧世界的
"完整"是 build + 每次登录跑一遍 ensure 叠出来的。

### 1.8 ensure 链会对自己撒谎
链中每步都有 `hasChunkAt` 守卫,区块未加载就静默跳过;而事后审计读同一批
未加载区块,会把"没建"报成"缺失"。玩家登录在地表时整个 GeoFront 未驻留,
一次补齐只跑 1.77 秒、什么都没做,审计却报告竖井 3/3→0/3。
**任何一次性补齐都必须先强制驻留目标区块。**

---

## 2. 代码改动

### 2.1 指挥室迁移(−40 Z)—— 已改,已编译
`S20CommandPresentationDirector.java`(11 处)
| 常量 | 旧 | 新 |
|---|---|---|
| `COMMAND_TRANSFORM_ORIGIN` | (2,-465,**263**) | (2,-465,**223**) |
| `COMMAND_MARKER` | (-2,-466,**242**) | (-2,-466,**202**) |
| `UPPER_SCREEN_Z` | 362.793 | **322.793** |
| `LOWER_SCREEN_Z` | 371.623 | **331.623** |
| `SIGHTLINE_MIN/MAX` z | 348 / 352 | **308 / 312** |
| 五个 `SeatSpec`(方块+落座点 z) | 317/326/331/339 | **277/286/291/299** |

`S20CommandTransitDirector.java`(4 处)
`COMMAND_TRANSFORM_ORIGIN` z 263→**223**、`INSTALLED_MARKER` z 299→**259**、
`NORTH_Z` 299→**259**、`SOUTH_Z` 301→**261**

**⚠️ `clearCommandSightline()` 行为变更**:原本遇到 `MEASURED_SIGHTLINE_STATES`
以外的方块会 **抛异常中止整个安装**。粘贴原始房间后那片区域会是 authored 方块,
必炸。已改为**跳过不认识的方块,只删它认得的外来填充**(air/deepslate_bricks/
sea_lantern)。不改这个,座椅和屏幕装不上。

### 2.2 插栓 / 机库 / 发射(本次交接期前半段)
- **驾驶员取消发射**:新增 `C` 键 → `ACTION_CANCEL_LAUNCH` →
  `EvaUnit01Entity.cancelLaunchFromPilot` → `EvaLogisticsDirector.requestCancel`
  (SILO_READY 且未授权发射时,沿 `TO_HANGAR→FILLING→PARKED` 推回机库;
  **取消时先开机库门**,否则 EVA 被拖过关闭的闸门)
- 观察室新增红色 RECALL 键 `EvaHangarBuilder.cancelControlPosition`
  (机库审计 `controls` 由 6/6 改为 **9/9**)
- **退出弹栓**:`EntryPlugCarrierEntity.STAGE_EJECTING` +
  `EntryPlugDirector.ejectPilotToPlug/tickEjection`(V 键弹出栓,人坐栓里,
  Shift 下车带缓降)。**弹出复用机库现有栓,不新建**——新建会导致两个栓、
  `canonical()` 认错、prepare 失败
- **插栓插入改两段吊车路径** + 吊绳/机械臂跟随(`setPlugCrane`/`stowPlugCrane`,
  用 copper_block + piston,机库内独有材质,缩回时不会误删甲板)
- 玩家进栓/进 EVA 后**隐身**,下机恢复
- `[entry_plug]` 配置节:`socketHeight` / `socketRearOffset` /
  `approachClearance` / `approachHeight` / `mechanicalArm`
- **LCL 灌装**扩到内壁(`HALF_WIDTH-1`/`HALF_DEPTH-1`),消除贴墙缝隙
- **去机库楼梯朝向** SOUTH→NORTH(原来装反)
- **观察廊横穿**:新增 `clearGalleryConcourse`,在 `linkHangars` 末尾重开
  5 格宽东西向走道(三条爬升坡道的侧墙原本把廊道切断,且每次登录重建)
- 机库审计新增 `galleryLinked`;`walkable()` 净空由 4 格改 **2 格**并
  **忽略吊车硬件**(否则吊绳一画出来就审计失败→整机库重建→卡顿掉物)
- `GeoFrontBuilder`:洞穴外壳改**按行挖满**(原角度采样会漏格成柱);
  旧地形清理上限 24→`CAVERN_CENTRE_Y`(清悬空 stone 残柱)
- 新增命令 **`/seele geofront rebuild`** —— `setup` 走审计门控**永不触发完整重建**,
  几何改动不进审计就永远不重画;这条直接调 `IntegratedNervMapBuilder.build()`

### 2.3 已回退,勿找
- `ThirdTokyoSurfaceBuilder` / `Tokyo3RetractionDirector` 的"清避雷针"逻辑
  —— 那是我把用户说的"柱子"误解成 lightning rod 写的,**城市原有的
  LIGHTNING_ROD 不该删**,已全部撤销
- `S21CleanBuildDirector.java`、`tools/prepare_s21_world.py`、
  `FacilityWorldPolicy`/`GameEvents` 的 S21 分支 —— 已删除/回退

---

## 3. 新增工具(不依赖游戏,秒级)

### `tools/facility_map.py` — 全设施扫描 + 分层 2D 地图
```bash
python tools/facility_map.py --emit artifacts/facility_map_s20
```
按 z 分带读区域文件,自动找出真实楼层高度,每层渲染带坐标网格的平面图并标出问题点。
检测:`corridor_to_air`(通道尽头悬空)、`blocking_wall`(一格厚隔墙分隔两个可行走区)、
`ladder_end`(梯子端点无落脚)、`door_without_footing`。
输出 `candidates.json`(每条带真实方块名 + 传送指令)+ `levels/floor_y*.png`。

### `tools/facility_audit.py` — 单构件细查
构件级(坡道/梯子/门)断言 + 自动渲染剖面&平面。

### ⚠️ 使用这两个工具必须知道的坑(我踩过的)
1. **只出候选,不出结论**。装饰性活板门被报成"坏门"、天然草地被报成"死胡同",
   都发生过。**报之前必须反查方块名 + 看渲染图**。
2. 邻居判定要算 **±1 台阶**,否则每级楼梯都会被当成"通道尽头"
   (这一个 bug 就制造了 23,789 条假阳性)。
3. 落脚点必须是**平台**(同 Y 的 3×3 多数可站),否则坡道会"落在自己身上"。
4. 只报**连通面积 ≥40** 的构件,否则柱顶/灯罩全被当成通道。
5. 分带接缝和扫描盒边界会制造假的"尽头",要加 margin 过滤。

**S20 当前基线**(供重建后对比):`corridor_to_air 367`、`blocking_wall 656`、
`ladder_end 41`、真门 15 扇**全部正常**。

---

## 4. 数据包(`run/saves/SEELE_S20_REBUILD/datapacks/seele_fix`)

`/reload` 后用 `/function seele:<名>` 执行。

### 待执行:金字塔整体重做(**用户已批准**)
```
seele:clear_pyramid_1 .. clear_pyramid_9    # 按顺序逐条跑
seele:paste_command_room                     # 再跑这条
```
- 清空范围严格按代码的收分公式逐层算:`y[-465,-295]`,
  每层 `|x-30| ≤ half(y)-1`、`|z-327| ≤ half(y)-1` —— **只清壳内,不碰外壳**
- 共 3,233,177 格空间、现有 489,573 个方块(含旧指挥室 70,820 格)全清
- 分 9 band 是为了避免单 tick 处理导致 watchdog 崩溃
- `paste_command_room` 放置 **36,914 格**:完整原始房间 38,128
  − 屏幕 dummy 1,181(留给真屏幕)− 会戳出外壳的 33 格
- 位置 `dx=0, dz=−40`,**与已改的代码常量一致**
- **不可逆,执行前建议备份存档**

### 其它(指挥室未整体重做时的局部修复,现已被上面取代)
`restore_command_room`/`undo_command_room`、`strip_foreign`/`restore_foreign`、
`wall_a_cone`/`wall_b_window`/`wall_c_bank` + 各自 restore、
`move_room_1_clear`/`move_room_2_paste`

---

## 5. 其它资产

- **`run/saves/NERV_COMMAND_SOURCE`** — 指挥室源存档副本(26MB,已设创造+作弊),
  原件在 `external-assets/work/maps/source_nerv_command/Nerv Comand Module`。
  两个指挥室在 x[8,46] 和 x[108,146],用的是前者。
- `artifacts/claude_audit_s19_20260729/` — S19 红队审计
  (`CLAUDE_AUDIT_FINDINGS.md` + `CLAUDE_SPATIAL_DELTA.json`)。
  判定 NOT SAFE TO IMPLEMENT;人类在审计后约 6 小时独立否决了 S19。
- `artifacts/facility_map_s20/` — 14 层 2D 地图 + 候选清单
- `artifacts/command_sightline/` — 视线分析、删除预览、房间 diff

---

## 6. 未完成 / 建议下一步

1. **执行金字塔清空 + 重新粘贴指挥室**(函数已就绪)
2. 清空后在空腔里重新布局:通道、电梯、湿仓连接
3. **淘汰的老电梯**:`S20PhysicalElevatorDirector.s20Lifts()` 是现役白名单,
   不在名单里的竖井结构即淘汰件 —— 这条可以完全自动判定,我没来得及做
4. **`LocalMapAssetLoader.COMMAND_V2_OFFSET = (27,-368,64)` 未跟随 −40 迁移**。
   S20 路径下似乎不会调用 `placeCommandModuleV2`(它由 S19 的
   `FacilityV2CommandInteriorDirector` 调用),但**如果将来在 S20 触发,
   会把房间放回旧位置**,需要一并处理。
5. 重建后用 `facility_map.py` 跑一遍,与 §3 的基线对比

---

## 7. 给 Codex 的方法建议(基于本次的教训)

- **语义不要反推,要在建造时记录**。我读不懂那扇门,是因为没人写下它属于哪个
  owner、对端该接什么。有 as-built manifest,"这是缺陷还是未完工"才有答案。
- **规格要能计算**。这次唯一一击命中的几件事,都来自权威数据而非判断:
  席位/屏幕坐标来自代码常量、遮罩数量 1,181 与代码注释吻合、
  房间尺寸 56×77×129 与模板吻合、映射由五个锚点联立解出。
- **改完先渲染成图自查**,再交给人。本次至少 5 类误报是在渲染后自己发现的。
- **一次性补齐必须先强制驻留区块**,否则会静默空转并报告成功(见 §1.8)。
