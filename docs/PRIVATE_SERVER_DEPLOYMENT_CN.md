# Project SEELE R25 服务器部署

使用同一批 `Project_SEELE_R25_Server.zip`、`Project_SEELE_R25_World.zip` 和 `Project_SEELE_R25_Client.zip`，校验值在 `SHA256SUMS.txt`。两端 Project SEELE JAR 完全相同；存档仍为 `SEELE_TV_WORLD_PREVIEW_20260906`。

## Windows 服务器

1. 安装 **Java 17**，设置 JAVA_HOME 或加入 PATH。在空目录解压 Server ZIP。
2. 运行 `Install-Server.bat`，从 Forge 官方源下载并校验 **Minecraft 1.20.1 / Forge 47.4.10** 安装器，安装运行库；首次需联网。
3. 新建 `SEELE_TV_WORLD_PREVIEW_20260906` 子目录，将 World ZIP 内容解压进去。最终应有 `SEELE_TV_WORLD_PREVIEW_20260906/level.dat` 和 `r25_ready.json`，不要套两层同名目录。
4. 阅读 Minecraft EULA 后自行将 `eula.txt` 改为 `eula=true`。
5. 运行 `Start-Server.bat`；控制台应出现 `Project SEELE initialized` 与 `Done`。启动器在缺少 R25 存档时会停止，避免误建空世界。
6. 控制台执行 `whitelist add 正版玩家名`，管理员再执行 `op 正版玩家名`。远程访问需要主机放行 TCP 25565；客户端填写服务器实际公网 IP 或域名。

第一次以新账号联机若出现在普通世界，可由控制台执行下列命令（把 `玩家名` 换成实际名字）：

```mcfunction
execute in projectseele:geofront run tp 玩家名 27.5 -407 282.5
give 玩家名 projectseele:nerv_employee_card
give 玩家名 projectseele:satellite_phone
```

## Linux／服务器面板

空目录解压 Server ZIP，Java 17，执行 `bash install-server.sh`。按上述结构导入存档，阅读并接受 EULA 后，执行 `bash start-server.sh`。

面板已有 Forge 安装功能时，选择 **1.20.1 / Forge 47.4.10 / Java 17**，再覆盖本包的 mods、config、projectseele-local-maps 和配置文件。启动命令须运行 Forge，不能直接运行 projectseele 模组 JAR。

默认服务器堆 `-Xms2G -Xmx16G`，为系统和原生内存另外留余量；面板覆盖 JVM 参数时以面板为准。真实视距 24、模拟距离 8、在线验证和白名单开启。没有预置账号或远程控制密码。

## 客户端

1. 用自己的启动器新建独立 **Minecraft 1.20.1 / Forge 47.4.10** 实例，Java 17，客户端堆建议 6 GB。
2. 打开该实例游戏目录，解压 Client ZIP。首次用空实例，避免旧版本 JAR 重复。
3. Windows 双击 `Install-Textures.bat`，从作者官方 CDN 获取 **rotrBLOCKS V87、128×、2D Foliage** 并校验 SHA-512；其他系统可按 `realistic-pack.json` 下载并手动启用。
4. 启动游戏、加入服务器。资源包优先级：`eva_real_model` 在上，rotrBLOCKS 在下。

基础色贴图无需光影；PBR／POM 需要兼容光影，本包没有默认开启。作者禁止重分发材质 ZIP，因此客户端提供官方下载脚本，不夹带其贴图。[作者页面](https://modrinth.com/resourcepack/rotrblocks)、[条款](https://illystray.com/terms/)。EVA、专用面板、单向窗、LCL、NERV／UN 标识保留项目资源。

服务器 15 个顶层 JAR；客户端再加 Embeddium、Xaero 小地图和世界地图，共 18 个。内嵌依赖自动加载，已包含 Patchouli 载具说明书和钢琴。不要再添加另一版本 MTR、Superb Warfare、GeckoLib 或电梯模组。

默认真实 24 区块，没有开启曾产生透视的 Distant Horizons、Farsight 或 Acedium。服务器负责世界与实体模拟，本地显卡仍负责绘制。Windows 图形设置中将该实例实际使用的 `javaw.exe` 设为高性能独显。联机稳定后可尝试两端 32 区块，不要同时提高模拟距离。密集 UN 战备区域仍是高负载场景。

## 迁移与维护

存档包包含全部维度、实体、玩家资料、MTR 路线／时刻表、NPC 岗位、原生电梯能力数据、机械布局与剧情进度。不要只复制 region，也不要执行 `/seele geofront setup` 或全量重建。UN 双机沿用已安装机体。

控制台输入 `stop`，等待保存结束后再备份整个目录；不要热覆盖。单机离线身份与正版联机 UUID 可能不同，原玩家数据保留，新联机玩家需要重新发卡／物品，不要靠关闭 online-mode 迁移身份。

先按 `R25_TEST_GUIDE_CN.md` 验证电梯、NPC 出动与回收、车站换乘、姿态和电源。既有 UN、载具与飞机操作见随包 `MANUAL_ACCEPTANCE_R23.md`。这是私人测试交付包，第三方地图／模型与可公开的 GitHub 源代码分开管理。
