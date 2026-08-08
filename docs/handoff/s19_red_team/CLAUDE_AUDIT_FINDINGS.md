# CLAUDE_AUDIT_FINDINGS — Project SEELE S19 红队审计

**审计者身份**:Claude Opus 5(模型 ID `claude-opus-5`),Claude Code CLI,启用扩展思考。
**身份可验证性**:**不可独立验证**。我对自身型号/版本/推理模式的唯一信息来源是本会话的系统提示;
我无法从内部检查权重、构建号或推理配置。本行应视为"转述系统提示",不构成自证。

**审计范围**:仅审计,不实现。本次未修改任何 Java 源码。
**审计时间**:2026-07-29。**输入**:`Project_SEELE_S19_VISUAL_REBUILD_CONTRACT.zip`(SHA256SUMS 随包)、
`LOCAL_AUTHORITY.md`、`local_evidence/nerv_command_left.nbt`(**由我独立解析实测**)、
`S19_LOCAL_COMMAND_ASSET_AUDIT.md`、`human_failures/*.png`、`current_code/*.java` 快照。

---

## 0. 执行结论(Executive verdict)

**判定:NOT SAFE TO IMPLEMENT。** Pro 的 S19 契约在**工程治理层面质量很高**
(fail-closed 端口、单一写者、guard band、97 owner 自洽无重叠、图全连通),
但它**建立在一个与本地权威证据不同的坐标系里**,并且**指挥室视觉核心的三轴全部判断错误**。

三个致命项(任一单独存在即应阻断实现):

1. **坐标系失配(P0-1)**:契约世界高度 `y[-64,319]`、椭球中心 `y=+140`;而权威要求
   `y[-672,320)`、椭球中心 `y=-336`。**97 个 owner 中 0 个落在实测指挥室高度带 `y[-368,-292]`**。
   存在唯一平移解 **ΔY = -476**(140-476 = -336,与提示椭球中心**精确吻合**),但契约未做,
   且椭球半径仍不符(704/120 vs 640/304)。
2. **屏幕遮罩三轴皆错(P0-4/P0-5)**:契约把黄/橙 dummy 放在 `Z[16,48]`(**司令席后方**)且左右并排;
   实测两块遮罩**都在 -Z(前方)、同一 X 中心 `[-7,9]`、上下叠放**。契约另立
   `main_screen_plane Z[-124,-120]`,即**被铁律禁止的"第二块视频墙"**。
3. **运行时写者未封(P0-6)**:清洁世界中仍有 5 个 tick-driven director 无条件写块,
   其中包含契约明文要求 `REJECT_FAIL_CLOSED` 的 `FacilityV2RescueDirector`。

**同时必须指出**:Pro 的 README 声称本地 NBT "未提供、无法独立扫描",因此把
`source_bbox / anchors / dummy masks` 全部 fail-closed 为 `TBD_LOCAL_SCAN`。
**这一前提已过时**:NBT 就在本地,我完整解析并**逐项复现了权威 #3 的每一个数字**(见 §1)。
按契约 §6.1 的 build gate 原文,`IntegratedNervMapBuilder::command_room` 会拒绝这个 slice ——
**契约会拒绝建造一份数据其实已经齐备的房间**。

---

## 1. 独立实测(权威 #2):我复现了什么

用 `nbtlib` 直接解析 `nerv_command_left.nbt`,施加变换 `(x,y,z) -> (27-x, -368+y, 64-z)`:

| 项 | 权威 #3 声明 | 我的实测 | 结论 |
|---|---|---|---|
| 模板尺寸 | `56 x 77 x 129` | `56 x 77 x 129` | ✅ 一致 |
| 方块总数 / palette | — | 33,797 / 149 | 补充 |
| 变换后 envelope | `x[-28,27] y[-368,-292] z[-64,64]` | `x[-25,27] y[-368,-292] z[-64,64]` | ⚠️ x 实占 -25(见 P2-1) |
| Amber 上屏(连通分量) | 425 blocks, `x[-7,9] y[-334,-304] z[-44,-28]`, dY/dZ=-1.940, 62.7°, XRot -27.3 | **425 blocks, 完全相同, -1.940, 62.7°, -27.3** | ✅ **精确复现** |
| Orange 下屏(连通分量) | 756 blocks, `x[-7,9]`, dY/dZ=-0.388, 21.2°, XRot -68.8 | **756 blocks, 完全相同, -0.388, 21.2°, -68.8** | ✅ **精确复现** |
| Orange 玻璃面 x 跨度 | `x[-6,8]` | `x[-6,8]` | ✅ |
| 5 个席位锚点 | Ikari/Fuyutsuki/3 operator | 全部为 `waxed_exposed_cut_copper_slab`,下方 `white_concrete` | ✅ |
| 层级 | Gendo 最高且居中 | Ikari `y=-309` 比 Fuyutsuki `y=-312` **高 3**;x=1 vs x=4 | ✅ |
| 后门 | `(1,-309..-308,15)` 两格 | `birch_door` × 2,下 `red_concrete`,上 `stone` | ✅ |
| 门后 authored 结构 | 约至 `z=27` | z=14→27 连续有料(z=20 峰值 173 块),z=28 起骤降至 10 | ✅ |
| 被禁旧走廊 `x[4,58] y[-340,-305] z[7,15]` | "横穿 authored 指挥塔" | **将覆写 1038 个 authored 方块**;其 x 伸至 58,**超出资产 envelope 上限 27 达 31 格** | ✅ 禁令成立且被量化 |

**重要方法学提醒**:不能用"全部 yellow_concrete"当遮罩——黄色混凝土 z 一直延伸到 **+28**(席位后方也有)。
必须用**连通分量**;整体最小二乘会给出 -0.211(11.9°),与真值 62.7° 相差 50 度。

---

## 2. P0 findings(阻断级)

### P0-1 坐标系失配:整份契约不在权威坐标系里
- **证据**:`S19_SPATIAL_CONTRACT.json → coordinate_convention.world_height = {min_y:-64, max_y:319}`;
  `domains[GEOFRONT_ELLIPSOID] = center(0,140,0) radii(704,120,704)`;`surface_datum_y = 260`。
  97 owner 的 Y 全域 = `[-62, 310]`。
- **权威**:世界 `y[-672,320)`;椭球中心 `y=-336`、rh 640、rv 304(→ `y[-640,-32]`);
  指挥室实测 `y[-368,-292]`。
- **量化冲突**:
  - 落在指挥室 Y 带的 owner:**0 / 97**。
  - 完全高于权威椭球顶(`y > -32`)的 owner:**94 / 97** —— 即 Pro 的整座设施位于 GeoFront 之上的岩体/空中。
- **唯一平移解**:**ΔY = -476**(`140-476 = -336` 与权威椭球中心精确吻合;平移后 0 处世界高度越界)。
  但**椭球半径仍不符**:Pro 704/120 vs 权威 640/304。**必须由人类锁定哪一组为准**。
- **结论**:**没有任何 owner/port 可以"直接翻译"**;全部需要统一 ΔY,且椭球定义须先裁决。

### P0-2 10 个机械 owner 越出 ±1024 保留区(+Z 最多 201 格)
`MECH_CARRIER_BRANCH_00/01/02`(z≤1043)、`MECH_CARRIER_TRUNK`(z≤1100)、
`MECH_WELL_LINK_00/01/02`(z≤1119)、`MECH_LAUNCH_WELL_00/01/02`(**z≤1224**)。
上限 1023,最大越界 **+201**。

### P0-3 机械线**无法靠平移**修复(合法带比需求短 136 格)
- 合法 Z 带 = 椭球外(rh 640 + 16 guard → z ≥ 656)∩ 区域内(1023 - 16 → z ≤ 1007)= **[656,1007],深 351**。
- Pro 机械线现深 `1224-737 = 487`。**缺口 136 格**。
- 我实测了朴素平移 **ΔZ = -224**(chunk 对齐,消除越界)的后果:
  - 区域越界 0 ✅、世界高度越界 0 ✅;
  - 但**新增 12 处 owner 重叠**(`GF_FOREST_SE` × `MECH_HANGAR_02/OBS_02/OBS_LINK_02/BOARDING_LINK_02/EVAC_EAST_CORRIDOR` 等);
  - 且 **10 个 MECH owner 侵入椭球**(本应在岩体内):`MECH_HANGAR_01`、`MECH_OBS_01`、
    `MECH_PERSONNEL_TRUNK`、`MECH_AIRLOCK_LINK`、`MECH_BOARDING_LINK_01`、`MECH_OBS_LINK_01` 等。
- **结论**:机械线必须**重新排布(压缩 Z / 向 X 展开)**,不能平移。这是需要人类拍板的设计决策,
  我给出约束而不替你选:`TBD_LOCAL_SCAN.mech_relayout_axis`。

### P0-4 黄/橙 dummy 保留区三轴皆错
| 轴 | Pro 契约 | 实测(已双重验证) | 偏差 |
|---|---|---|---|
| X | 黄 `[-76,-8]` / 橙 `[8,76]`(**左右并排**) | 两者皆 `[-7,9]`(**同一中心**) | 结构性错误 |
| Y | 黄橙**同带** `[120,146]` → ΔY 后 `[-356,-330]` | 上屏 `[-334,-304]`、下屏 `[-338,-322]`(**上下叠放**) | 上屏完全落空 |
| Z | 皆 `[16,48]`(**+Z,司令席后方**) | 皆负 Z(上屏 `[-44,-28]`、下屏 `[-64,-26]`) | **在房间错误一侧**,偏 44–112 格 |

契约 §2.1 自称"只是最大预约框",但该框**与真实遮罩无交集(X/Z 方向)**,
按 §6.3 `ForbiddenScreenWrites` 的集合定义,真实遮罩位置会落入**禁写集**。

### P0-5 `main_screen_plane` 构成被禁的"第二块视频墙"
契约 §2.1 主屏平面 `X[-96,96] Y[108,168] Z[-124,-120]`。
authored 资产的前缘(下屏)已到 **z=-64**,即**authored 屏幕本身就是前墙**。
在其前方再 56–60 格立一整面墙,直接违反铁律
"Yellow/orange sloped dummy masks are the screen surfaces… No second video wall"。

### P0-6 清洁世界中运行时写者未封(与 LOCAL_AUTHORITY 声明矛盾)
- **证据**:`current_code/GameEvents.java:133-147`。只有 `NervFacilityTopologyBuilder.tick` 与
  `NervRuntimeMaintenance.tick` 被 `if (!cleanRebuild)` 包裹;以下**无条件运行**:
  `FacilityV2BootstrapDirector.tick`、`FacilityV2BuildDirector.tick`、`FacilityV2ProgrammeDirector.tick`、
  `FacilityV2CommandInteriorDirector.tick`、`GeoFrontFabricDirector.tick`、
  **`FacilityV2RescueDirector.tick`**、`FacilityV2ElevatorDirector.tick`。
- **写调用计数**:`FacilityV2CommandInteriorDirector` 4、`FacilityV2ElevatorDirector` 4、
  `FacilityV2RouteGateDirector` 1(经 `FacilityV2ProgrammeDirector:195` 调用)、`LocalMapAssetLoader` 1。
- **策略引用计数**:上述四者 `FacilityWorldPolicy` 引用 **0**;
  而 `IntegratedNervMapBuilder` 6、`GeoFrontBuilder` 3、`GeoFrontCommands` 2(已封 ✅)。
- **契约冲突**:`builder_policy.runtime_repair_or_auto_tick = DISABLED_REJECT_WRITE`(所有 S19 世界)、
  `FacilityV2RescueDirector.restoreLegacyMechanicalOnly = REJECT_FAIL_CLOSED`。
- **结论**:LOCAL_AUTHORITY 的"legacy write paths have been sealed"**只对 legacy 成立,对 V2 不成立**。
  这是**真实阻断项**,不是只读代码。

---

## 3. P1 findings(必须在开建前解决)

### P1-1 指挥厅 owner 装不下 authored 资产(顶部差 8 格)
`HQ_COMMAND_BRIDGE` 经 ΔY=-476 后为 `x[-120,120] y[-388,-300] z[-128,104]`;
authored envelope 上沿 `y=-292`。**顶部短缺 8 格**(底部与 X/Z 包含 ✅)。

### P1-2 缺少"双向完工回执"门控
契约全文中 `receipt`/`completion`/`reciprocal`/`回执`/`完成` **各出现 0 次**。
101 个端口全部 `CLOSED_FAIL_CLOSED`(良好),但**没有定义开启前提**,
提示要求的"port opening cannot precede both reciprocal completion receipts"**未被规定**。

### P1-3 指挥室是全设施割点;应急疏散不独立
- **割点测试**(移除单个 owner 后从地表可达性):
  - 移除 `HQ_COMMAND_BRIDGE` → 可达 30/96,**66 个 owner 失联**(含整个机械厂与南 GeoFront);
  - 移除 `HQ_EAST_SAFETY_SPINE` → 失联 57;
  - 移除 `MECH_PERSONNEL_TRUNK` → 失联 38;移除 `GF_SOUTH_AIRLOCK` → 失联 40。
- **E6 实测路径**:`MECH_EVAC_EAST_SHAFT → … → HQ_COMMAND_EAST_LINK → **HQ_COMMAND_BRIDGE** →
  HQ_COMMAND_WEST_LINK → … → T3_SURFACE_C22_STATION`。
- **违反**:铁律"Human, EVA, plug and emergency flows remain separated";
  且与契约 §7"rear lift 仅是补充授权撤离,不是唯一出口"的意图自相矛盾——
  实际上**主疏散反而必须穿过指挥室**。

### P1-4 指挥厅体量与母版严重不成比例(臆造空间即人工否决的来源)
authored 资产 `56×77×129`;`HQ_COMMAND_BRIDGE` `241×89×233`。
资产仅占 owner 体积约 **5%**,其余 95% 为 Pro 臆造空间。
人工否决图 `codex-clipboard-1c9f04e0…png` 显示**司令席后方并排两扇 birch 门**,
而母版只有**一扇**(`(1,-309..-308,15)`)——正是"extra invented paths beside the command seat"。

### P1-5 东/西侧向 link 位于 operator 层且承担全部交通
`HQ_COMMAND_EAST_LINK` / `WEST_LINK`:`x=±121`,ΔY 后 `y[-372,-360]`,`z[-20,8]`。
母版 X 跨度仅 `[-25,27]`,故这两个口**不在 authored 资产上**,是 Pro 在外围臆造墙上的开口;
且由 P1-3 可知**全设施交通都从这里过**。存在复现"lateral gallery / 席位旁多余通道"的高风险。

---

## 4. P2 findings(记录级)

- **P2-1**:envelope 名义 `x[-28,27]`(56 宽)vs 实占 `x[-25,27]`。guard band 应按**名义**算,
  否则西侧 3 格保护带会被误判为可写。
- **P2-2**:Pro README/§6.1 的 `TBD_LOCAL_SCAN` 前提**已过时**(NBT 可测且已复现)。
  若照原文执行,build gate 会拒绝一个数据齐备的 slice。
- **P2-3**:发射井净空**合规**:`clear_bore` `x[-452,-412]`=41、`z[1152,1192]`=41 → **41×41 ≥ 41** ✅
  (但井体本身触发 P0-2 越界)。
- **P2-4**:`MECHANICAL_DOMAIN` 声明 `z[737,1224]`,与 P0-2/P0-3 同源;domain 自身也越界。

---

## 5. Pro 做对了什么(不应推翻)

1. **建造权限模型**:`sole_mutator = IntegratedNervMapBuilder`;
   `ensure` 绝不 repair/merge/救援叠加;legacy alias 全部 redirect 或 fail-closed;
   `SEELE_FULL_REBUILD` 只读归档。**这是本契约最有价值的部分,应原样保留**。
2. **端口默认全闭**:101/101 `CLOSED_FAIL_CLOSED`,并带 `guard_waiver` 仅限租约面 ±2 格 collar。
3. **自洽几何**:在其自身坐标系内 **97 owner 两两无重叠**、**全部有 guard band**(4/6/8/10/12/16)、
   **无孤儿 owner**、图 97/97 连通。
4. **后部链路拓扑正确**:`bridge → rear link(z105-111) → antechamber(z112-148) → lift link(z149-155)
   → rear lift(z156-184)`,与"authored rear route → 支撑袖 → 前室 → 常驻升降"要求一致,且**不开向空气**。
5. **拒绝把司令办公室猜成后门正后方的房间**:`HQ_COMMANDER_OFFICE x[136,196]` 放在东侧,
   经 P-024 独立进入 —— **完全符合铁律**。
6. **明令禁止已退役的 `buildCommanderLiftGallery` 体积** —— 我的 NBT 实测证明该禁令有据:
   那个体积会摧毁 **1038 个 authored 方块**。
7. **发射井 41×41 净空** ≥ 要求。
8. **实体政策**:NBT `entities` 必须为空或导入前剥离。

---

## 6. Pro 错误假设了什么

1. **假设世界是原版高度**(`y[-64,319]`,椭球在 `y=+140`)—— 与权威/实测相差 **476 格**。
2. **假设 NBT 不可得** → 把已可测的锚点/遮罩全部 fail-closed,反而使 slice 无法开建。
3. **假设两块屏幕左右并排、位于席位后方** —— 实测为**同轴上下叠放、位于席位前方**。
4. **假设需要一面独立主屏墙** —— 铁律与实测都表明 authored 斜面**本身就是屏幕**。
5. **假设机械厂可以延伸到 z=1224** —— 越出保留区,且合法带不足 136 格。
6. **假设指挥厅是 241 宽的大厅** —— 母版仅 56 宽;多出的臆造空间正是人工否决的来源。
7. **假设单一脊柱穿过指挥室可作为主疏散** —— 使指挥室成为割点,违反流线分离。

---

## 7. 最小纠正序列(按此顺序,不可跳步)

1. **锁定坐标系**(人类裁决):确认世界 `y[-672,320)`、椭球 `centre y=-336 / rh 640 / rv 304`、
   设施中心 world `(30,296)`、NBT 变换 `(27-x,-368+y,64-z)`。
   → 对**所有** owner/port 施加 **ΔY = -476**,重跑几何校验。
   ⚠️ 椭球半径 704/120 与 640/304 的分歧**必须先裁决**,否则 §5 的"岩体/腔体"判定全部失效。
2. **用实测替换 `local_command_template` 的 TBD 块**:尺寸、CLOCKWISE_180、base `(27,-368,64)`、
   envelope、5 席锚点、后门、两块遮罩(含 **XRot -27.3 / -68.8**,并显式标注
   "不得使用互余角 -62.7 / -21.2")。
3. **重定义指挥厅**:`HQ_COMMAND_BRIDGE` 收缩到 authored envelope + 最小 collar;
   顶部至少到 `y=-292`(修 P1-1 的 8 格);**删除 `main_screen_plane` 独立墙**;
   屏幕改为绑定到两块实测遮罩(原位、原坡度、不平移不复制不扩张)。
4. **把黄/橙保留区搬到实测位置**:`amber x[-7,9] y[-334,-304] z[-44,-28]`、
   `orange x[-7,9] y[-338,-322] z[-64,-26]`;删除 `Z[16,48]` 的错误框。
5. **重排机械厂**以适配合法带 `z[656,1007]`(351 深):压缩 Z 或向 X 展开。
   **禁止朴素 ΔZ 平移**(会产生 12 处重叠 + 10 个 owner 侵入椭球)。
6. **封死运行时写者**:`GameEvents` 中把 5 个 V2 director(尤其 `FacilityV2RescueDirector`)
   纳入 `!cleanRebuild` 或 `FacilityWorldPolicy` 门控;为 4 个零引用写者补上策略检查。
7. **补"双向完工回执"**:定义 receipt 结构与"两端 owner 均完工才允许开 port"的门。
8. **增设不穿越指挥室的第二条疏散脊柱**,消除 `HQ_COMMAND_BRIDGE` 割点;
   同时为 `MECH_PERSONNEL_TRUNK` / `GF_SOUTH_AIRLOCK` 增加冗余。

---

## 8. "Safe to implement" 门(全部为 AND)

**当且仅当以下 8 条全部为真,方可开始落块:**

- [ ] **G1**:椭球定义(640/304 vs 704/120)已由人类裁决并写入契约;ΔY=-476 已应用且重校验通过。
- [ ] **G2**:`local_command_template` 中不再有任何 `TBD_LOCAL_SCAN`,其值等于 §1 表格的实测值。
- [ ] **G3**:`HQ_COMMAND_BRIDGE` 完整包含 `x[-28,27] y[-368,-292] z[-64,64]`(含名义 x=-28)。
- [ ] **G4**:契约中不存在 authored 遮罩以外的任何屏幕面(`main_screen_plane` 已删除或已重定义为遮罩绑定)。
- [ ] **G5**:全部 owner 满足:区域 `[-1024,1024)`、世界 `y[-672,320)`、两两无重叠、guard band 齐备;
      机械 owner 全部位于椭球外。
- [ ] **G6**:清洁世界中**零**运行时写者;`FacilityV2RescueDirector` 在 S19 世界不可写(以代码验证,非声明)。
- [ ] **G7**:存在一条**不经过 `HQ_COMMAND_BRIDGE`** 的地表↔机械厂疏散路径。
- [ ] **G8**:双向完工回执机制已定义,且所有 101 端口在收到回执前保持 `CLOSED_FAIL_CLOSED`。

**当前状态:G1–G8 全部未满足。判定 NOT SAFE TO IMPLEMENT。**

---

## 9. 我未能判定的项(不猜)

| 标记 | 说明 |
|---|---|
| `TBD_LOCAL_SCAN.ellipsoid_authority` | 640/304(提示)vs 704/120(契约)。两者不可调和,须人类裁决。 |
| `TBD_LOCAL_SCAN.mech_relayout_axis` | 机械厂缺 136 格深度,压缩 Z 还是展开 X 属设计决策。 |
| `TBD_LOCAL_SCAN.surface_datum` | 契约 `surface_datum_y=260`;ΔY 后为 -216,与 Tokyo-3 地表关系未在权威中锁定。 |
| `TBD_LOCAL_SCAN.bridge_collar_width` | 指挥厅收缩后的 collar 宽度需由"共享视线"目视验收决定。 |
| `TBD_LOCAL_SCAN.authored_openings` | 母版 envelope 边界上的合法开口清单尚未逐面枚举(本次只验证了后门)。 |

**免责**:本审计中所有尺寸均为 Minecraft 重建选择;**未从任何动画帧推断官方比例**,
也未把任何帧推断当作尺寸依据。
