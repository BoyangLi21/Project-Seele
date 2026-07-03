# Project SEELE

An open-source **Neon Genesis Evangelion** universe mod for Minecraft **Forge 1.20.1**.

一个开源的《新世纪福音战士》世界观 Minecraft 模组（Forge 1.20.1）。

> God's in his heaven. All's right with the world.

## Status / 状态

Early development. **Phase 1 MVP playable**: fight Ramiel, the Fifth Angel — a hovering crystal octahedron with a charged sniper beam, boss bar and drops. / **第一阶段 MVP 可玩**：与第5使徒拉米尔作战（悬浮八面体、蓄力光束、Boss 血条与掉落）。

## Docs / 文档

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — full plan through Third Impact & the Tree of Life / 完整路线图（直到第三次冲击与生命之树）
- [docs/SETUP.md](docs/SETUP.md) — dev environment setup / 开发环境搭建
- [docs/PROMPTS.md](docs/PROMPTS.md) — kickoff prompts for AI-assisted sessions / AI 协作开工手册
- [CLAUDE.md](CLAUDE.md) — project conventions for Claude Code / 项目协作约定

## Roadmap (short) / 路线图（简版）

1. 🔄 **Angels attack** — Ramiel fight polish: alert siren, real beam rendering, cross explosions / 警报、真光束、十字爆炸
2. ⬜ **EVA Unit-01** — pilotable, umbilical power, sync rate, berserk / 可驾驶初号机、电力、同步率、暴走
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
