# Project SEELE 私人服务器部署（Forge 1.20.1）

本说明对应私人双人开发服务器。整合包包含本机测试所需的第三方模组和本地资源，只能在受邀开发者之间私下传递，不要公开上传或二次分发。

## 一、服务器面板部署

前提：Minecraft 1.20.1、Forge 47.4.10、Java 17。当前包默认服务器堆 `-Xms2G -Xmx8G`、视距 6、模拟距离 5；再按实际并发与内存调整。不要添加 `DisableExplicitGC`，它与远景缓存使用的堆外内存回收不合适。

1. 完全停止服务器，并先用面板做一次备份。
2. 在文件管理页进入 `/home/container`。
3. 上传 `Project_SEELE_Server_Files_*.zip`，解压并允许覆盖 `mods/`、`config/`、`projectseele-local-maps/`、`server.properties` 和 `user_jvm_args.txt`。
4. 打开“导入存档”，上传 `Project_SEELE_World_Import_*.zip`。压缩包根目录已经是 `level.dat`，不要再手工套一层目录。
5. 若面板把导入后的存档命名为别的名字，把 `server.properties` 的 `level-name` 改成实际目录名；当前正式目录是 `SEELE_TV_WORLD_PREVIEW_20260906`。
6. 在面板启动参数中确认 Java 17 与分配的堆。部分面板不会读取 `user_jvm_args.txt`，此时以面板的内存设置为准。
7. 启动服务器。控制台应出现 `Project SEELE initialized`，并且不能有 `Missing mandatory dependencies`。
8. 在控制台执行 `op <你的正版玩家名>`，然后只把两名开发者加入白名单。

不要在这个已经建好的存档上执行 `/seele geofront setup` 或任何全量重建指令。

## 二、客户端安装

1. 新建独立的 Minecraft 1.20.1 Forge 47.4.10 实例，使用 Java 17。
2. 给客户端分配 6–8 GB 内存。显卡驱动里确认 `javaw.exe` 使用独立显卡。
3. 将 `Project_SEELE_Client_Pack_*.zip` 解压到该实例的 `.minecraft` 根目录，允许合并 `mods/`、`config/`、`resourcepacks/` 和 `projectseele-local-maps/`。
4. 游戏内把 `eva_real_model` 资源包启用并置于最高优先级。
5. 连接服务器面板当前显示的地址与端口。

客户端和服务器必须使用同批次的公共模组：Project SEELE、GeckoLib、Ars Nouveau、Curios、Another Furniture、Moving Elevators 及两个 SuperMartijn 库、MTR、Superb Warfare、Kotlin for Forge。当前包为 11 个顶层服务器 JAR，另有模组内嵌依赖；不要另加这些依赖的冲突版本。Farsight 与 Cupboard 只在普通客户端包中；可选低配方案改用 Distant Horizons、Embeddium、FerriteCore。

R15 的人员名单 `nerv_staff_r15.json`、区域迁移元数据 `regional_plan.json`、全部 `data/` 和各维度的 `entities/` 都要随存档迁移。只复制地形会丢失人员身份；漏掉区域迁移元数据会把控制系统指向旧机库坐标。

低配与远景的使用方法见 [R15 人员、动作与远景记录](STAFF_WORLD_R15.md)。远景必须保留地下的多层结构，并先完成已有地图的缓存；不能把尚未生成的 LOD 缺面当成地图破损。当前打包器默认不带旧 DH 缓存，服务器可用 `PRE_EXISTING_ONLY` 从现有地图生成和发送远景，不会扩张新地形。

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
