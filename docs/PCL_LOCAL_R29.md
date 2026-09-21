# R29 单 ZIP 本机整合包

将 `Project_SEELE_R29_PCL_AllInOne.zip` **直接拖入 PCL 窗口**，安装为新的 `SEELE-R29`，然后选择这个版本启动。不要先把文件解压到 PCL.exe 所在文件夹。

包中已放好 19 个客户端模组、EVA 模型、R29 完整存档、rotrBLOCKS 128x、Complementary Unbound r5.3 和相应配置，光影默认开启。进入单人游戏选择包内唯一的 TV 存档。无需另跑光影、材质安装脚本。

基础版本锁定 Minecraft 1.20.1 / Forge 47.4.10 / Java 17。PCL 可按需要补齐缺少的基础游戏／Forge 运行库；模组、模型、地图、材质和光影均已在 ZIP 内，不作为下载列表重新获取。原来的 PCL 版本和个人存档保留。

服务器文件在同一个 ZIP 的 `server/`。部署时将 `overrides/saves/SEELE_TV_WORLD_PREVIEW_20260906` 复制到 `server/SEELE_TV_WORLD_PREVIEW_20260906`，再按服务端部署说明操作。服务器无需光影。

这是现有用户本机资源的个人备份整合，不是公开分发包；原三包仍用于分开部署。公开发行的素材权限边界未改变。

## 本次修复

Windows PowerShell 5.1 会将 `ConvertFrom-Json` 的顶层数组作为单个管道对象输出。原脚本将这个数组包进 `@(...)` 后筛选，导致筛选的是整组对象，最终误报找到了两个光影。本次改为先解析，再逐条枚举配置；同时修正材质选择列表的同类兼容问题。

安装脚本增加本地缓存复用、指定游戏目录和 PCL 启动器目录误用检查。以 Windows PowerShell 5.1 实测本地缓存安装、无网络重复安装、用户设置保留、重复条目拒绝和资源包顺序保留。

ZIP 采用 [PCL 官方导入代码支持的 CurseForge 结构](https://github.com/Meloong-Git/PCL/blob/main/Plain%20Craft%20Launcher%202/Modules/Minecraft/ModModpack.vb)：根目录 `manifest.json`，`overrides/` 放实际游戏文件，`files` 下载列表为空。原生游戏核心仍使用已验证的 R29 文件，此次没有改变地图和战斗代码。
