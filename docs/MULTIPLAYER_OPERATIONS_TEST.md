# NERV 多人协同与专用服务器验收

这一层用于 1–3 名玩家在同一个私人服务器上分工驾驶、指挥和观察。席位只表达“谁负责什么”，不会强制锁住 EVA，也不会影响现有单人测试；席位和 READY 状态保存在世界存档中，服务器重启后仍然存在。

## 玩家命令

所有普通玩家都可使用：

```text
/nerv crew status
/nerv crew claim commander
/nerv crew claim operations
/nerv crew claim magi
/nerv crew claim unit00
/nerv crew claim unit01
/nerv crew claim unit02
/nerv crew ready
/nerv crew standby
/nerv crew release
/nerv server status
```

一个玩家同一时间只能认领一个席位。认领新席位会自动释放自己的旧席位；不能抢占其他玩家的席位。离线玩家的席位会保留，管理员可用 `/nerv crew clear <station>` 清理过期席位。

`/nerv crew ready` 表示该岗位已经完成人工准备；`standby` 表示仍在检查。它不会阻挡发射，因为当前阶段优先保证单机和临时联机都能继续测试。

## 管理员诊断

```text
/nerv server status
/nerv server audit
```

`status` 是轻量只读检查，报告：

- 当前是单机集成服还是专用服务器，以及在线人数；
- 连续地图标记是否存在；
- 当前已加载的 EVA 数量；
- NERV 五块遥测屏是否完整；
- 三路驾驶画面中有几路正在上传；
- 已认领、在线和在线 READY 的岗位数。

`audit` 需要管理员权限。它只执行有界的出击门禁修复/审计（发射井出口、操作区、MAGI、供电柱、武器柜等），不会重建 640 格 GeoFront、第三新东京市或整张世界。

兼容别名：管理员也可使用 `/seele server status` 与 `/seele server audit`。

## 推荐三人流程

1. 玩家 A：`/nerv crew claim unit01`，进入初号机并确认 HUD、电力、武器后执行 `/nerv crew ready`。
2. 玩家 B：`/nerv crew claim operations`，站在指挥室驾驶视频墙与七键控制台前，确认画面后 READY。
3. 玩家 C：认领 `commander`、`magi` 或另一台 EVA，负责城市下沉、使徒状态与侧面录像。
4. 管理员执行 `/nerv server status`。确认地图 CONNECTED、EVA 3/3、遥测 5/5；驾驶画面只有在驾驶员客户端实际上传时才显示 LIVE。
5. 管理员执行 `/nerv server audit`，输出必须为 `NERV runtime gate READY`。
6. 三人都 READY 后，由指挥席释放发射井；同时观察 EVA、驾驶员、视频墙、同步率、武器柜和上升进度。

## 战略屏幕

指挥室战略屏幕底部会实时显示：

```text
CREW 3/6  ONLINE 3  READY 2/3
```

它读取服务端权威 SavedData，不依赖客户端猜测。详细玩家名与每个岗位状态使用 `/nerv crew status` 查看，避免把长名字挤进现有战术屏幕。

## 验收标准

- 普通玩家无需 OP 即可认领、READY、STANDBY、释放和查看状态；
- 同一席位不能被第二名玩家抢占；
- 重启服务器后席位和 READY 状态仍在；
- 离线席位显示 OFFLINE，不会被静默删除；
- 指挥室统计与 `/nerv crew status` 一致；
- `server status` 不重建地图，`server audit` 只做有界门禁修复；
- 服务器日志不存在 `client` 类在服务端误加载、网络包越权或 SavedData 反序列化异常。
