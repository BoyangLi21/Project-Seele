# Project SEELE

An open-source **Neon Genesis Evangelion** universe mod for Minecraft **Forge 1.20.1**.

一个开源的《新世纪福音战士》世界观 Minecraft 模组（Forge 1.20.1）。

> God's in his heaven. All's right with the world.

## Status / 状态

Early development. **Visual recovery is in progress.** The Ramiel combat logic is playable, but EVA models, animation, first-person presentation, launch silo and Third-Impact tableau remain prototypes and are not release quality. Current recovery is bounded to Unit-01/00/02, Mass Production EVA, the Tree and the launch/entry-plug flow; no further campaign expansion occurs before their visual gates. / **视觉基础抢救中。** 拉米尔战斗逻辑可以运行，但 EVA 模型、动画、第一人称、发射井和第三次冲击构图均仍是原型。当前只收口初/零/二号机、量产机、生命之树及发射井/插入栓；这些项目通过视觉门禁前不再扩大战役范围。

Pilot controls / 驾驶操作：`WASD` 移动、`Space` 跳跃、`Shift` 单膝跪地、`Z` 趴下/匍匐、`Ctrl` 冲刺、`B` 踩踏、`R` 切换武器、`G` 开关 A.T. Field、鼠标攻击/蓄力、`V` 弹出插入栓。零号机展开 A.T. Field 后按住 `Shift`，即进入单膝举盾防御。

## Docs / 文档

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — full plan through Third Impact & the Tree of Life / 完整路线图（直到第三次冲击与生命之树）
- [docs/SETUP.md](docs/SETUP.md) — dev environment setup / 开发环境搭建
- [docs/PROMPTS.md](docs/PROMPTS.md) — kickoff prompts for AI-assisted sessions / AI 协作开工手册
- [docs/VISUAL_RECOVERY.md](docs/VISUAL_RECOVERY.md) — fixed Visual Lab workflow and acceptance gate / 固定视觉实验室与验收门槛
- [docs/THIRD_IMPACT_VISUAL.md](docs/THIRD_IMPACT_VISUAL.md) — deterministic Tree/tableau capture and current visual verdict / 生命之树固定构图与当前验收结论
- [docs/LAUNCH_SILO_TEST.md](docs/LAUNCH_SILO_TEST.md) — launch carrier, high entry-plug gantry and manual test / 发射井、高位插入栓栈桥与测试流程
- [CLAUDE.md](CLAUDE.md) — project conventions for Claude Code / 项目协作约定

## Roadmap (short) / 路线图（简版）

1. ✅ **Angels attack** — Ramiel fight, alert siren, real beam rendering, cross explosions / 拉米尔战、警报、真光束、十字爆炸
2. 🔄 **EVA Unit-01** — piloting/combat function as a prototype; visual and first-person gates remain open / 驾驶与战斗原型可运行；模型、动作与第一人称门禁仍未关闭
3. ⬜ **A.T. Fields & more Angels** — Sachiel, Shamshel, Zeruel, siege events / AT 力场与使徒图鉴
4. 🔄 **NERV / GeoFront / Tokyo-3** — a test launch silo exists; dimension/city remain future work / 测试发射井已落地；完整维度与城市仍属后续
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
