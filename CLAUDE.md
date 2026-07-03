# CLAUDE.md — Project SEELE 协作手册

> 给接手本项目的 Claude Code：先读这个文件，再读 `docs/ROADMAP.md`（完整计划）。
> 新机器环境搭建见 `docs/SETUP.md`；每个阶段的开工 prompt 见 `docs/PROMPTS.md`。

## 项目是什么

**Project SEELE**：开源的《新世纪福音战士》(EVA) 世界观 Minecraft 模组。
使徒 Boss 战 → 可驾驶 EVA → AT 力场体系 → NERV/GeoFront/第三新东京市 → 第三次冲击（生命之树）终局事件。
完全免费、完全开源、严格遵守 khara 二次创作指引（见下方红线）。

- 仓库：`git@github.com:BoyangLi21/Project-Seele.git`（GitHub 账号 BoyangLi21）
- 当前进度：Phase 0 完成，Phase 1 MVP 完成（Ramiel 可战斗），Phase 1 收尾进行中 — 详见 ROADMAP §0

## 技术栈（版本锁定，勿擅自升级）

| 组件 | 版本 | 备注 |
|---|---|---|
| Minecraft | 1.20.1 | Java 版 |
| Forge | 47.4.10 | MDK 模板化，属性在 `gradle.properties` |
| JDK | 17 (Temurin) | Forge 1.20.1 硬性要求 |
| Gradle | 8.8 | wrapper 已指向腾讯镜像（国内提速） |
| GeckoLib | 4.x（Phase 2 引入） | maven: `https://dl.cloudsmith.io/public/geckolib3/geckolib/maven/`，坐标 `software.bernie.geckolib:geckolib-forge-1.20.1:<ver>`，用 `fg.deobf()` |
| 映射 | official (Mojang) | |

## 常用命令

```
./gradlew build        # 编译 + 产出 build/libs/projectseele-<ver>.jar
./gradlew runClient    # 启动开发客户端（离线账号，无需登录）
./gradlew runServer    # 专用服务器（Phase 6 验证用）
```

- 游戏日志：`run/logs/latest.log`（每次启动重建，验证 mod 加载搜 `Project SEELE initialized`）
- 首次构建要反编译 MC，视 CPU 10–60 分钟；之后增量构建 <1 分钟
- gradle daemon 已启用（`gradle.properties`），内存 4G

## 代码结构

```
com.projectseele
├── ProjectSeele.java        # 主类：注册 DeferredRegister、commonSetup
├── CommonEvents.java        # MOD 总线事件（实体属性注册等）
├── registry/                # ModItems / ModEntities / ModCreativeTabs（新注册类型都放这）
├── entity/                  # RamielEntity（含内嵌 MoveControl/Goal AI）
├── item/                    # PositronRifleItem
└── client/                  # ClientEvents（渲染器注册，Dist.CLIENT）
    └── render/              # RamielRenderer（直连顶点渲染，无模型文件）

resources/
├── assets/projectseele/     # lang(en_us+zh_cn)/models/textures
└── data/projectseele/       # loot_tables 等
```

**注册模式**：一律 `DeferredRegister` + `RegistryObject`，注册类放 `registry/`，在主类构造器挂到 mod 总线。
**代码风格**：跟随 Forge MDK（Allman 大括号、UTF-8），注释只写代码看不出来的约束。
**渲染惯例**：几何体（使徒、特效）优先直连顶点渲染（参考 `RamielRenderer` 的八面体画法）；人形/复杂动画用 GeckoLib。

## 协作约定（用户偏好，务必遵守）

1. **中文交流**。
2. **Commit 署名**：每个提交末尾加 `Co-Authored-By: Ayanami_Rei <liboyang_621@126.com>`（用户的项目分身账号），**不要**加 Claude 署名——这是用户明确要求。多行提交信息用 `git commit -F <文件>` 避免引号问题。
3. **工作流**：构建通过 + runClient 日志验证无误 → commit + push（用户已授权此流程）。游戏内目视测试由用户负责——你看不到画面，写好日志检查点后把"看什么"列清楚交给用户。
4. `.claude/` 目录已 gitignore，**永不提交**。
5. 用户负责 GUI 安装类操作（装软件、网页建仓库）；其余全部你来。
6. 数值平衡（伤害/血量/冷却）改动要在回复里明确列出前后值，用户拍板。

## 合规红线（不可妥协）

- **永不**引入官方素材：音频（尤其 BGM）、原画、影像截图一概不行。音效用原创合成 / CC0 素材（登记来源），贴图全部原创。
- 永久免费、非商业。遵循 khara 指引：https://www.khara.co.jp/guideline/
- 代码 MIT；引用他人地图/模型必须先取得授权（待办清单见 ROADMAP §9）。

## 验证套路（无人值守测试）

1. `runClient` 用后台任务启动，同时起一个日志监听（PowerShell `Select-String` 轮询 `latest.log`）。
2. 检查点：`Project SEELE initialized` = 加载成功；再全文扫 `projectseele` 附近的 `error|missing|exception` = 资源/注册问题。
3. 实体行为验证：让用户 `/summon projectseele:ramiel ~ ~5 ~20`，生存模式触发 AI。
4. 提交前必须 `./gradlew build` 通过。

## 当前数值表（Phase 1 MVP，均在对应类顶部常量区）

| 项 | 值 | 位置 |
|---|---|---|
| Ramiel 血量/护甲 | 350 / 6 | `RamielEntity.createAttributes` |
| 光束伤害/蓄力/冷却/射程 | 18 / 50t / 90t / 64 | `RamielEntity` 常量 |
| 步枪伤害/冷却/射程 | 16 / 25t / 96 | `PositronRifleItem` 常量 |
| 核心碎片掉落 | 4–8 (+抢夺) | `loot_tables/entities/ramiel.json` |

## 已知占位/技术债

- 贴图为程序生成占位（生成器已入库：`tools/gen_textures.ps1`），欢迎高清重绘
- 音效暂用原版（信标/紫水晶/Warden 音效），Phase 1 收尾换原创
- Ramiel 光束是粒子线，计划换成真正的光束渲染（ROADMAP 任务 1.2）
- `ResourceLocation(String,String)` 有过时警告（Forge 迁移提示），1.20.1 内无害，Phase 6 统一清理
