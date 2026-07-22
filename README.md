# Project SEELE

An open-source **Neon Genesis Evangelion** universe mod for Minecraft **Forge 1.20.1**.

一个开源的《新世纪福音战士》世界观 Minecraft 模组（Forge 1.20.1）。

> God's in his heaven. All's right with the world.

## Status / 状态

Early development. **Visual recovery is in progress.** EVA presentation and Third Impact remain prototypes. The local connected map now places a 416-block Tokyo-3 district above a deeply buried 640-block GeoFront sphere; 95 generated buildings and three private high-rises physically descend into the curved ceiling city instead of disappearing. The same world contains the 522-block launch shafts, Central/Terminal Dogma, live NERV telemetry and persistent Operation Yashima gates. Downloaded assets remain local-only. / **视觉基础抢救中。** EVA 动作与第三次冲击仍是原型。本机连续地图现已把 416 格第三新东京市置于普通地表、640 格 GeoFront 深埋地下；95 栋生成楼宇与三座私有高楼会真正沉入曲面穹顶都市，而不是消失。同一世界还包含 522 格实体发射井、Central/Terminal Dogma、NERV 实时遥测与持久化屋岛作战门禁；下载资产仍只限本机。

Pilot controls / 驾驶操作：`WASD` 移动、`Space` 跳跃、`Shift` 单膝跪地、`Z` 趴下/匍匐、`Ctrl` 冲刺、`B` 踩踏、`R` 切换武器、`G` 开关 A.T. Field、左键近战/自动步枪、右键阳电子炮蓄能/N² 解锁、`V` 弹出插入栓。零号机展开 A.T. Field 后按住 `Shift`，即进入单膝举盾防御。战略武器测试与数值见 [`docs/WEAPONS_TEST.md`](docs/WEAPONS_TEST.md)。

## Docs / 文档

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — full plan through Third Impact & the Tree of Life / 完整路线图（直到第三次冲击与生命之树）
- [docs/SETUP.md](docs/SETUP.md) — dev environment setup / 开发环境搭建
- [docs/PROMPTS.md](docs/PROMPTS.md) — kickoff prompts for AI-assisted sessions / AI 协作开工手册
- [docs/VISUAL_RECOVERY.md](docs/VISUAL_RECOVERY.md) — fixed Visual Lab workflow and acceptance gate / 固定视觉实验室与验收门槛
- [docs/THIRD_IMPACT_VISUAL.md](docs/THIRD_IMPACT_VISUAL.md) — deterministic Tree/tableau capture and current visual verdict / 生命之树固定构图与当前验收结论
- [docs/LAUNCH_SILO_TEST.md](docs/LAUNCH_SILO_TEST.md) — launch carrier, high entry-plug gantry and manual test / 发射井、高位插入栓栈桥与测试流程
- [docs/GEOFRONT_TEST.md](docs/GEOFRONT_TEST.md) — connected Tokyo-3 / GeoFront, LCL and command telemetry / 连续地图、LCL 与指挥室遥测
- [docs/FRIEND_TEST_PACK.md](docs/FRIEND_TEST_PACK.md) — private LAN test bundle and server/client install / 私有联机测试包与服务器部署
- [docs/MULTIPLAYER_OPERATIONS_TEST.md](docs/MULTIPLAYER_OPERATIONS_TEST.md) — persistent NERV crew stations and server readiness / 持久 NERV 席位与服务器就绪诊断
- [docs/OPERATION_YASHIMA_TEST.md](docs/OPERATION_YASHIMA_TEST.md) — persistent Ramiel battle and visual gate / 持久化屋岛作战与视觉验收
- [docs/ANGEL_SIEGE_TEST.md](docs/ANGEL_SIEGE_TEST.md) — restart-safe Sachiel/Shamshel/Zeruel beacon defense / 可重启的三使徒信标防卫
- [docs/LCL_TEST.md](docs/LCL_TEST.md) — breathable recovery fluid and submerged-item persistence / 可呼吸恢复与浸没物品保护
- [docs/EVA_POWER_TEST.md](docs/EVA_POWER_TEST.md) — five-minute battery, umbilical pylon and shutdown interlock / 五分钟电池、脐带供电与停机联锁
- [docs/EVA_SYNCHRONIZATION_TEST.md](docs/EVA_SYNCHRONIZATION_TEST.md) — persistent pilot growth, response scaling and neural feedback / 持久同步率成长、响应增益与神经反噬
- [docs/EVA_BERSERK_TEST.md](docs/EVA_BERSERK_TEST.md) — autonomous Unit-01 override and forced shutdown / 初号机自主暴走与强制停机
- [docs/EVA_ARMAMENT_RACK_TEST.md](docs/EVA_ARMAMENT_RACK_TEST.md) — persistent physical EVA weapon loading and launch-bay racks / 持久化 EVA 实体装载与发射笼武器柜
- [CLAUDE.md](CLAUDE.md) — project conventions for Claude Code / 项目协作约定

## Roadmap (short) / 路线图（简版）

1. ✅ **Angels attack** — Ramiel fight, alert siren, real beam rendering, cross explosions / 拉米尔战、警报、真光束、十字爆炸
2. 🔄 **EVA Unit-01** — piloting/combat function as a prototype; visual and first-person gates remain open / 驾驶与战斗原型可运行；模型、动作与第一人称门禁仍未关闭
3. 🔄 **A.T. Fields & more Angels** — Sachiel, Shamshel and Zeruel combat prototypes now share a restart-safe NERV beacon siege; final models and visual acceptance remain / 三使徒战斗原型已接入可重启的 NERV 信标围城；最终模型与目视验收仍待完成
4. 🔄 **NERV / GeoFront / Tokyo-3** — connected local prototype, real LCL, live command room, deeply buried 640-block sphere, ceiling city and 522-block launch; art, multiplayer visual validation and licensing remain / 本机连续原型、真实 LCL、实时指挥室、深埋 640 格球体、穹顶都市与 522 格发射已接线；多人目视验收、美术和授权仍待完成
5. 🔄 **SEELE's scenario** — local Longinus/Mass EVA/Tree prototypes exist but have not passed the tableau gate / 本地朗枪、量产机与生命树已有原型，但构图尚未通过验收
6. ⬜ **Release** — integrations, optimization, CurseForge/Modrinth / 发布

## Building / 构建

Requires **JDK 17**.

```
./gradlew build
```

The mod jar is written to `build/libs/`.

## Local visual testing / 本机视觉测试

The desktop `Project SEELE 测试.bat` is a stable shim into the tracked
`tools\start_test.bat`, so later repository changes cannot leave a stale copy
on the desktop. The repository launcher rebuilds and validates the ignored
local model pack before starting Forge. / 桌面文件直接转发到仓库内的最新版启动器，
因此后续更新不会再遗留旧副本；启动 Forge 前会先重建并校验本机模型包。

```text
tools\start_test.bat offline
tools\start_test.bat visual unit01
tools\start_test.bat visual unit00
tools\start_test.bat visual unit02
tools\start_test.bat visual mass
tools\start_test.bat visual impact
```

`offline` regenerates all local EVA assets and writes a timestamped Unit-01 /
Unit-00 / Unit-02 / Mass Production pose matrix without launching Minecraft.
`visual mass` captures idle, move, attack, revive and ritual from seven fixed
exterior views. / `offline` 不启动游戏，直接重建四台机体并输出带时间戳的离线姿态矩阵；
`visual mass` 会分别截图待机、移动、攻击、复活与仪式五种状态。

Screenshots are written to `run/screenshots/projectseele_visual/`. These local
captures and third-party evaluation assets are ignored by Git and are not part
of the distributable mod. / 截图与第三方评估模型只保留在本机，不进入发行包。

## License / 许可

- Code is licensed under [MIT](LICENSE). / 代码使用 MIT 协议。
- This is an unofficial, **non-commercial fan work** created in the spirit of [khara's fan works guideline](https://www.khara.co.jp/guideline/). Not affiliated with or endorsed by khara, inc. / 本项目为非官方、非商业的粉丝创作，遵循 khara 官方二次创作指引精神，与 khara 公司无任何关联。
- No official assets (audio, artwork, footage) are or ever will be included. / 本项目不包含且永远不会包含任何官方素材（音频、原画、影像）。
