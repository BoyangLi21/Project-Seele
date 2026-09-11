# 默认远景与服务器配置 R17

当前启动器采用正常画质和默认远景：客户端至少 18 区块原始几何，Distant Horizons 半径 128 区块，EXTREME 水平和 VERY_HIGH 垂直细节，完整粒子、纹理 mipmap 4、至少 100% 实体距离。首次安装配置后保留后续用户设置。旧低配入口继续保留为历史可选工具。

固定版本为 DH 3.2.0-b、Embeddium 0.3.31、FerriteCore 6.0.1 和 ModernFix 5.27.83。下载使用作者在 Modrinth 发布的文件及 SHA-512 校验。[DH 官方页面](https://modrinth.com/mod/distanthorizons)、[Embeddium 官方页面](https://modrinth.com/mod/embeddium)、[ModernFix 官方页面](https://modrinth.com/mod/modernfix)。调研过 Radium，但本轮没有加入运行环境。

未来服务器默认 16 GB 堆、原始区块视距 18、模拟距离 8。世界逻辑、实体、MTR 调度和远景生成由服务器承担；客户端仍负责可见网格、输入、动画与绘制。DH 两端保持 Distant Generation 开启，服务器从已有区块生成 LOD。服务器原生预生成命令已经在当前世界的冷副本上运行，范围为两座城市及远郊 UN 基地。

旧缓存没有直接沿用。两段城市范围和基地分别完成预生成，数据库通过完整性检查。`ChunkHash` 行数不能直接当成覆盖区块数；实际生成范围、`FullData` 元数据和实景检查共同用于验证。正式世界只接收经检查的 LOD 数据库，地形和实体不从测试世界反向覆盖。

原来的 DOUBLE_PASS 会使部分动态模型淡出。关闭它之后还必须关闭 DH 自身的抖动淡出，否则近远景交接处会出现棋盘状空洞。本轮将 `vanillaFadeMode=NONE`、`ditherDhFade=false`、`dhFadeFarClipPlane=false` 配套使用，保留地下垂直层次并忽略屏障、结构空位和 Skyweave 的远景绘制。

本地开发启动器先编译并准备 ForgeGradle 的真实启动参数，再退出构建 JVM、直接启动客户端，减少常驻内存。参数通过已安装 ForgeGradle 的 token 解析生成，保留完整模块路径、JVM 参数、资源路径与显式环境覆盖；不保存完整用户环境。Java/Javaw 请求 Windows 高性能 GPU，实景日志同时记录实际 OpenGL renderer，已确认使用本机 RTX 3070 Ti。

性能采样确认客户端环境动画的重复生物群系角点计算与 SBW 瞄准扫描占用较多时间。角点缓存与未注入 Mixin 的原版方法完成 216,000 次逐位一致性比较，保留粒子和生物群系结果。SBW 的长距 HUD 扫描在 EVA／插入栓驾驶及旁观模式下跳过；正常 SBW 武器和载具视角仍使用原扫描。单向窗渲染试验没有证实收益，已经恢复原实现，原 2,344 格窗及 NBT 保留。

现场启动 JFR 会显著干扰这台机器的短时帧率，因此最终视角测量关闭采样器，等待区块加载后再记录帧时间。冷启动、生成缓存时和稳定渲染时的数字分别保留，不混称持续帧率。最终媒体与记录保存在本机 `artifacts/rendering_r17/`。

最终无采样器实景测量（18 区块近景、128 区块 LOD、客户端 6 GB 堆）：

| 视角 | 中位 FPS | P95 帧时间 |
| --- | ---: | ---: |
| 城市 | 114 | 17.2 ms |
| 金字塔 | 71 | 20.0 ms |
| 地下湖 | 118 | 11.9 ms |
| 指挥室 | 117 | 11.9 ms |
| UN 基地 | 117 | 12.3 ms |

这些是本机固定视角完成预热后的测量，不能等同于行驶中或初次加载时的最低帧率。实测图与 JSON 位于 `artifacts/rendering_r17/review/`。正式缓存已安装并通过 28 项原存档保护检查。
