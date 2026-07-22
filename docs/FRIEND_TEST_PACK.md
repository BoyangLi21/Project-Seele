# Project SEELE 私有联机测试包

这套流程用于你和 1–2 位朋友在本机、局域网或私人服务器上验收 Project SEELE。它不会把第三方模型、地图、模组或下载源文件提交到 GitHub；生成的目录和 ZIP 固定写入已被 Git 忽略的 `external-assets/private-test-bundle/`。

## 版本与内存

- Minecraft Java Edition 1.20.1
- Forge 47.4.10
- Java 17
- GeckoLib 4.8.x（必需）
- Ars Nouveau 4.12.x + Curios 5.14.x（可选；安装后 GeoFront 使用 Skyweave 显示真实天空）
- 客户端建议分配 6G；私人服务器建议分配 8G

仓库桌面测试入口已经为高精度客户端设置 `-Xmx6G`，开发专用服务器设置 `-Xmx8G`。朋友使用普通 Minecraft 启动器时，需要在对应实例的 JVM 参数中自行设置 `-Xmx6G`。

## 在主机上生成私有包

先关闭 Minecraft 和正在运行的服务器，然后在 `D:\eva` 依次执行：

```bat
tools\start_test.bat offline
gradlew.bat build
python tools\build_private_test_bundle.py --include-world
```

- `offline` 会按当前固定顺序重建并校验本机 EVA、武器、插入栓和莉莉丝资源包；
- `build` 生成最新 Project SEELE jar；
- `--include-world` 会把 `SEELE_TOKYO3_REBUILT` 一并装入测试包，朋友无需重新生成 640 格 GeoFront；
- 如果只准备服务器/客户端公共文件而不传存档，去掉 `--include-world`。

输出：

```text
external-assets/private-test-bundle/
├── Project_SEELE_Private_Test_Pack/
└── Project_SEELE_Private_Test_Pack.zip
```

脚本只收集生成后的运行产物，不收集 `external-assets/incoming/`、模型来源压缩包、EVA.rar 或根目录下载 jar/zip。ZIP 仍然只允许私下传给测试者，禁止公开发布。

## 朋友客户端安装

1. 创建独立的 Minecraft 1.20.1 Forge 47.4.10 实例，使用 Java 17，分配 6G 内存。
2. 解压 ZIP，把其中 `minecraft/` 目录内的内容合并到该实例根目录：
   - `mods/` → 实例 `mods/`
   - `resourcepacks/eva_real_model/` → 实例 `resourcepacks/eva_real_model/`
   - `projectseele-local-maps/` → 实例同名目录
   - `config/` → 实例 `config/`
   - `saves/SEELE_TOKYO3_REBUILT/` → 仅单人或开局域网时需要
3. 在资源包界面启用 `eva_real_model`，并把它放在其他 EVA 资源包之上。不要启用 Chikita 参考包。
4. 所有联机客户端必须使用同一 Project SEELE jar 和同一 `eva_real_model` 包；否则视频墙、模型指纹和动画门禁会主动拒绝混合资源。

## 私人专用服务器部署

私测包现在自带 `server-template/`。推荐让服务器所有者在这个目录中安装 Forge 服务端，避免手工漏掉模组、配置或连续世界：

1. 解压完整私测包，在 `server-template/` 内安装 **Forge 1.20.1-47.4.10 服务端**。安装完成后这里应出现 Forge 自带的 `run.bat`；模板不会公开分发 Forge 安装器。
2. 运行 `sync-from-private-pack.bat`。它会从同一包的 `minecraft/` 同步模组、公共配置、本机地图缓存和 `SEELE_TOKYO3_REBUILT` 世界。
3. 运行 `start-server.bat`。第一次只用于生成 `eula.txt`；服务器所有者必须亲自阅读 [Mojang EULA](https://aka.ms/MinecraftEULA)，再自行决定是否改为 `eula=true`。脚本绝不会代替用户接受。
4. 模板默认 `-Xms2G -Xmx8G`、`view-distance=8`、`simulation-distance=6`、`allow-flight=true`（避免 EVA 弹射/跳跃被误踢）、`max-tick-time=120000`、异步区块写入和 150% 实体广播距离。
5. 模板默认 `online-mode=true`、`white-list=true`、`enforce-whitelist=true`。在服务器控制台依次执行 `whitelist add <正版玩家名>`；不要为了省事关闭正版验证或白名单。
6. 首位管理员进入后执行 `/seele geofront audit`。只有 `valid=true`、`mapVersion=17`、三条连续井均通过时才开始驾驶测试。旧 v16 世界会在 GeoFront 登录时执行有界基础设施修复，自动补三座武器柜而不会重建城市。
7. `eva_real_model` 是客户端资源包；每位玩家本地安装即可。服务器不需要也不应强制公开下发含第三方素材的资源包。

如果把模板复制到另一台机器，先保留其目录结构并再次运行同步脚本。公网服务器还需要路由器端口转发、防火墙规则与定期备份；这些涉及你的网络环境，模板不会自动修改。
## 推荐三人验收分工

- 玩家 A：驾驶 Unit-01，从高位插入栓入口登机并完成 522 格同维发射；
- 玩家 B：留在 NERV Operations，操作七键控制台并观察 01 驾驶视频；
- 玩家 C（可选）：驾驶 Unit-00/02 或在地表观察城市下沉和屋岛作战。

城市下沉使用 `/seele tokyo3 retract`，恢复使用 `/seele tokyo3 restore`。95 栋生成建筑最大行程为 285 层，完整下降再恢复约十分钟。验收时必须在 GeoFront 顶部看到悬挂城市；只看到地表建筑消失不算通过。

## 问题回报最低信息

每个问题至少附带：客户端日志 `logs/latest.log`、服务端日志、发生时命令、玩家角色、截图或录像、是否启用 Ars Nouveau，以及 `/seele geofront audit` 与 `/seele tokyo3 status` 的完整输出。不得把包含第三方素材的私有 ZIP 上传到公开 issue。
## NERV 多人席位与服务器状态

普通玩家可使用 `/nerv crew claim <commander|operations|magi|unit00|unit01|unit02>` 认领一个持久席位，再用 `/nerv crew ready`、`/nerv crew standby`、`/nerv crew release` 和 `/nerv crew status` 协调测试。管理员开测前执行 `/nerv server status`，再执行只修复运行门禁、不会重建整张地图的 `/nerv server audit`。完整步骤见 `docs/MULTIPLAYER_OPERATIONS_TEST.md`。
