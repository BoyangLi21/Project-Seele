# Project SEELE

An open-source **Neon Genesis Evangelion** universe mod for Minecraft **Forge 1.20.1**.

一个开源的《新世纪福音战士》世界观 Minecraft 模组（Forge 1.20.1）。

> God's in his heaven. All's right with the world.

## Status / 状态

Early development. **Operation Yashima is playable**: pilot original, animated EVA Units 00/01/02 against Ramiel with A.T. Fields, progressive weapons and the positron cannon. / **屋岛作战已可玩**：驾驶原创可动画的 EVA 零号机、初号机与二号机，以 A.T. Field、粒子武器和阳电子炮迎战拉米尔。

Pilot controls / 驾驶操作：`WASD` 移动、`Space` 跳跃、`Shift` 单膝跪地、`Z` 趴下/匍匐、`Ctrl` 冲刺、`B` 踩踏、`R` 切换武器、`G` 开关 A.T. Field、鼠标攻击/蓄力、`V` 弹出插入栓。零号机展开 A.T. Field 后按住 `Shift`，即进入单膝举盾防御。

## Docs / 文档

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — full plan through Third Impact & the Tree of Life / 完整路线图（直到第三次冲击与生命之树）
- [docs/SETUP.md](docs/SETUP.md) — dev environment setup / 开发环境搭建
- [docs/PROMPTS.md](docs/PROMPTS.md) — kickoff prompts for AI-assisted sessions / AI 协作开工手册
- [CLAUDE.md](CLAUDE.md) — project conventions for Claude Code / 项目协作约定

## Roadmap (short) / 路线图（简版）

1. ✅ **Angels attack** — Ramiel fight, alert siren, real beam rendering, cross explosions / 拉米尔战、警报、真光束、十字爆炸
2. 🔄 **EVA Unit-01** — piloting and combat complete; umbilical power, sync rate and berserk next / 驾驶与战斗已落地；下一步为电力、同步率、暴走
3. ⬜ **A.T. Fields & more Angels** — Sachiel, Shamshel, Zeruel, siege events / AT 力场与使徒图鉴
4. ⬜ **NERV / GeoFront / Tokyo-3** — dimension, launch catapults, retractable city / 场景与发射井
5. ⬜ **SEELE's scenario** — Lance of Longinus, Mass Production EVAs, **Third Impact & Tree of Life** / 朗基努斯、量产机、第三次冲击
6. ⬜ **Release** — integrations, optimization, CurseForge/Modrinth / 发布

## Building / 构建

Requires **JDK 17**.

```
./gradlew build
```

The mod jar is written to `build/libs/`.

## License / 许可

- Code is licensed under [MIT](LICENSE). / 代码使用 MIT 协议。
- This is an unofficial, **non-commercial fan work** created in the spirit of [khara's fan works guideline](https://www.khara.co.jp/guideline/). Not affiliated with or endorsed by khara, inc. / 本项目为非官方、非商业的粉丝创作，遵循 khara 官方二次创作指引精神，与 khara 公司无任何关联。
- No official assets (audio, artwork, footage) are or ever will be included. / 本项目不包含且永远不会包含任何官方素材（音频、原画、影像）。
