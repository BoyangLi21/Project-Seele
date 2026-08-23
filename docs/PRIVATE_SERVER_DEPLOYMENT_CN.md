# Project SEELE 私人服务器部署（Forge 1.20.1）

本说明对应私人双人开发服务器。整合包包含本机测试所需的第三方模组和本地资源，只能在受邀开发者之间私下传递，不要公开上传或二次分发。

## 一、服务器面板部署

前提：Minecraft 1.20.1、Forge 47.4.10、Java 17。服务器有 18 GB 内存时，建议给 Java 设置 `-Xms14G -Xmx14G`，余下约 2 GB 留给系统和面板。

1. 完全停止服务器，并先用面板做一次备份。
2. 在文件管理页进入 `/home/container`。
3. 上传 `Project_SEELE_Server_Files_*.zip`，解压并允许覆盖 `mods/`、`config/`、`projectseele-local-maps/`、`server.properties` 和 `user_jvm_args.txt`。
4. 打开“导入存档”，上传 `Project_SEELE_World_Import_*.zip`。压缩包根目录已经是 `level.dat`，不要再手工套一层目录。
5. 若面板把导入后的存档命名为别的名字，把 `server.properties` 的 `level-name` 改成实际目录名；默认值是 `SEELE_S20_RECOVERY_R28`。
6. 在面板启动参数中确认 Java 17 与 14 GB 固定堆。部分面板不会读取 `user_jvm_args.txt`，此时以面板的内存设置为准。
7. 启动服务器。控制台应出现 `Project SEELE initialized`，并且不能有 `Missing mandatory dependencies`。
8. 在控制台执行 `op <你的正版玩家名>`，然后只把两名开发者加入白名单。

不要在这个已经建好的存档上执行 `/seele geofront setup` 或任何全量重建指令。

## 二、客户端安装

1. 新建独立的 Minecraft 1.20.1 Forge 47.4.10 实例，使用 Java 17。
2. 给客户端分配 6–8 GB 内存。显卡驱动里确认 `javaw.exe` 使用独立显卡。
3. 将 `Project_SEELE_Client_Pack_*.zip` 解压到该实例的 `.minecraft` 根目录，允许合并 `mods/`、`config/`、`resourcepacks/` 和 `projectseele-local-maps/`。
4. 游戏内把 `eva_real_model` 资源包启用并置于最高优先级。
5. 连接服务器地址 `mc9.r9mc.cn:50136`（若面板后来更换端口，以面板显示为准）。

客户端和服务器的五个模组版本必须一致：Project SEELE、GeckoLib、Ars Nouveau、Curios、Another Furniture。Create 与 Create: Connected 已退役，客户端和服务器都不得保留其 JAR。

## 三、本轮人工验证

1. 指挥室发射按钮：
   - `(32,-407,287)`：EVA-00 LAUNCH
   - `(32,-407,286)`：EVA-01 LAUNCH
   - `(32,-407,285)`：EVA-02 LAUNCH
2. 新增取消发射按钮：
   - `(24,-407,287)`：EVA-00 CANCEL
   - `(24,-407,286)`：EVA-01 CANCEL
   - `(24,-407,285)`：EVA-02 CANCEL
3. 三台 EVA 必须先完成驾驶员登舱和 PREPARE，再按 LAUNCH。若失败，记录聊天栏中的具体 preflight 原因。
4. GeoFront 与 Tokyo-3 不应再生成蝙蝠、史莱姆等普通生物；Project SEELE 的 EVA、使徒与训练驾驶员不受影响。
5. Tokyo-3 应保持晴天且不再积雪。当前权威存档已精确清除 50,849 个薄雪层。
6. 分别启动 EVA-00/01/02 的 dummy，确认皮肤为绫波丽/碇真嗣/明日香配色，并观察其是否还会掉出安全路线。

## 四、资源与隐私

客户端包中的 `eva_real_model` 和本地地图图像仅供这个私人开发服务器测试。不要把整合包、资源包或第三方模型提交到公开 GitHub、公开网盘或公共整合包平台。
