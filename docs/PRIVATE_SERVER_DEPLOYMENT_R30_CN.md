# R30 五包部署

五个 ZIP 各自独立，均带同批 `R30_BATCH.json`。服务端、客户端、存档必须同批升级；网络协议为 34。材质和光影是可选外观包，服务器不加载它们。

本批按你的要求停止追加验证，直接封装供人工验收，标记为 `manual_by_user`。最终双机完整驾驶／飞行／回收流程，以及本批分发 JAR 的专用服务器启动，留待你确认；未将这些项目记作自动验证通过。

| 压缩包 | 解压位置 |
| --- | --- |
| `Project_SEELE_R30_Server.zip` | 新的服务端目录 |
| `Project_SEELE_R30_World.zip` | 服务端目录下新建的 `SEELE_R30_WORLD` 文件夹 |
| `Project_SEELE_R30_Client.zip` | PCL 的 Forge 1.20.1 独立游戏目录 |
| `Project_SEELE_R30_Textures.zip` | 与客户端相同的游戏目录，合并 `resourcepacks` |
| `Project_SEELE_R30_Shaders.zip` | 与客户端相同的游戏目录，合并 `shaderpacks`、`config` |

先完整备份现有服务器。不要把旧地图区域文件覆盖到新地图上；若远程服务器已经产生新的玩家或剧情进度，需要单独迁移这些数据，不能直接用本地旧副本覆盖。此次 R30 地图从本项目的正式 R29 基线修订而来。

## 服务端

1. 使用 Java 17。将 Server 包解压到一个新目录。
2. 解压 World 包，使路径是 `SEELE_R30_WORLD/level.dat`，不要多套一层文件夹。
3. Windows 运行 `Install-Server.bat`；Linux 运行 `bash install-server.sh`。首次安装 Forge 运行库仍需要联网；模组和存档已在包内。
4. 阅读 Minecraft EULA，同意后自行把 `eula.txt` 的 `false` 改为 `true`。
5. 按服务器实际内存调整 `user_jvm_args.txt`，给操作系统留出余量；不要直接把全部物理内存分配给 Java。
6. Windows 运行 `Start-Server.bat`；Linux 运行 `bash start-server.sh`。首次加载大量设施和交通数据需要等待。
7. 按自己的部署需求设置正版验证、白名单、服务器地址及端口。分发包不包含本机账号凭据或已接受 EULA 的状态。

确认 `server.properties` 的 `level-name=SEELE_R30_WORLD`。不要把客户端的 Oculus、Embeddium、Xaero 等客户端组件复制到服务端。

## PCL 客户端

在 PCL 的该版本设置中打开**游戏文件夹**，确认这是 Minecraft 1.20.1 / Forge 47.4.10 的独立目录。关闭游戏，备份旧目录后合并 Client 包。`mods` 内只保留本批的一份 Project SEELE JAR，避免旧版和新版重复加载。

客户端包已含必需模组和 EVA 私人模型资源。若要本地单机测试，把 World 包解压到该目录的 `saves/SEELE_R30_WORLD`。若连接服务器，则不需要在客户端安装整个 World 包。

材质包和光影包内直接附带已经校验的原始 ZIP，无需在 PCL 再下载：

- Textures 包合并后运行 `Install-Textures.bat`，它会校验并启用本地材质，EVA 专用资源保持在其上方。
- Shaders 包合并后，视频设置 → 光影 → Complementary Unbound。也可运行 `Install-Visuals.bat`；原包已在正确目录时只会复用，不会重新下载。
- 原始第三方资源 ZIP 不要自行拆散。材质和光影外层 ZIP 用于安装，内层原包由游戏加载。

如果误把脚本放到 PCL 启动器目录，请移动到该版本的独立游戏目录。新包沿用已修复的 PowerShell 数组筛选，不再依赖“数组恰好被当成一个对象”的错误判断。

远景延续真实区块渲染，未重新启用曾出现地下透视的 Distant Horizons / Farsight。服务器承担世界与实体模拟，本地仍负责绘制；光影、视距和分辨率会影响显卡负载。Windows 可在系统“图形”设置中将实际 Java 17 的 `javaw.exe` 指定为高性能独显，游戏内 F3 核对实际 GPU。

## 验收与校验

先按 `MANUAL_ACCEPTANCE_R30.md` 检查指挥室灯光、机库连接、交通和两台 UN 机体，再按 `FIRST_ACT_R30_CN.md` 测试亲自驾驶或真嗣出战。查看 `SHA256SUMS.txt` 可核对五个下载文件，勿混用其他批次的 JAR、地图或资源。

这些包是现有第三方素材的私人测试整合备份。日后公开开源时发布自有代码、生成工具和可再分发资源清单，私人整合包不直接作为公开发布物。
