# R20 人工验收与操作

使用仓库根目录 `start_eva_test_20260917_r20.bat`。它打开 `SEELE_TV_WORLD_PREVIEW_20260906`；只有正式存档安装了 R20 才会启动。准备检查命令：

```powershell
& 'D:\eva\start_eva_test_20260917_r20.bat' --check
```

正常双击即可进入游戏。默认 6 GB 客户端内存、24 区块真实视距，Distant Horizons 与 Farsight 均不加载；Xaero 小地图／大地图保留。首次到达区域先等区块载入。`F3` 可确认使用 NVIDIA 独显，`F5` 切换视角，`F2` 截图，`M` 打开大地图，`F8` 切换地下洞穴层。

使用独立服务器时，按服务器包的 `README_CLIENT_CN.txt` 安装和连接；下面的游戏内操作与坐标相同。

以下全部坐标属于 `projectseele:geofront`。按 `/` 打开聊天栏逐条输入指令。开始前可领取身份卡：

```mcfunction
/gamemode creative
/give @s projectseele:nerv_employee_card
/give @s projectseele:terminal_dogma_access_card
```

步行、电梯和交通测试时落地并关闭创造飞行。正式 NERV 入口要求手持职员证刷卡；深层、会客厅权限用 Terminal Dogma 卡。不要执行重建、bootstrap 或 force reset。

## 道路、通道与电梯

| 内容 | 落脚点／路线 |
| --- | --- |
| 原崩裂路口 | `-676 96 676`；沿路走过高架下方，检查连续坡度 |
| 金字塔东侧接驳 | `112.5 -448 255.5`；走六级楼梯到 `123.5 -442 247.5` |
| 东侧各房间 | 从 `89.5 -448 285.5` 沿长廊检查房门与支柱 |
| 指挥室北侧 | `28.5 -418 258.5`；通往指挥室楼梯与后方电梯厅 |
| 深层电梯 | `12.5 -566 258.5`；进轿厢后选楼层，往返时靠近边角走动、跳一下 |
| 地表公共电梯 | `123.5 -442 273.5`；通过层门正常上车 |
| 机库上层观察廊 | `103.5 -369 -70.5`；向北走到新机库，留意顶棚与吊机支撑 |
| 机库中层 | `101.5 -394 -46.5`；沿东侧绕过电梯井，继续向北到三台机体的登机廊 |
| 机库下层 | `107.5 -442 -44.5`；通往新机库下层、机库站和金字塔 |

传送格式示例：

```mcfunction
/execute in projectseele:geofront run tp @s -676 96 676
/execute in projectseele:geofront run tp @s 103.5 -369 -70.5 180 0
```

小型机库电梯上站标高为 -370，观察室脚面为 -369，两者之间有实际梯级。原 `87 -412 -15` 观察通道与那座独立旧电梯已经退役；改走现有三站电梯和新的连续观察廊。

## 初号机整备、发射与回收

机库沿 -Z 移动了 144 格，三台机体仍保留各自身份。现在机库床面为 -443、发射床面为 -411，中间通过长斜坡连接。

```mcfunction
/execute in projectseele:geofront run tp @s 30.5 -394 -267.5 0 0
/seele eva status unit01
```

正常起点为 `PARKED`。沿机体侧面的登机廊走到背后，空手右键悬挂插入栓的舱口。若提示 DUMMY 占用，先执行 `/seele eva dummy stop unit01`。

亲自入栓后：

```mcfunction
/seele eva prepare unit01
/seele eva status unit01
```

观察入栓、排液、开门和斜坡转运。达到 `SILO_READY` 后：

```mcfunction
/seele eva launch unit01
```

到地表后测试停留、走跑和转身。回收时驾驶机体回到对应板中心并停下；表中 Y 是机体脚部高度：

| 机体 | X / Y / Z |
| --- | --- |
| 零号机 | -11.5 / 81 / -35.5 |
| 初号机 | 30.5 / 81 / -35.5 |
| 二号机 | 72.5 / 81 / -35.5 |

```mcfunction
/seele eva recover unit01
/seele eva status unit01
```

可特意让机体侧向站在回收板上再回收，检查下降及回机库时的朝向。等待最终恢复 `PARKED`，离开插入栓后再去其他区域。驾驶期间不要用玩家传送指令换景。

## 火车：一分钟一班

八条列车线路采用每 60 秒一班的原生运行安排。站牌读取真实 MTR 预计发车时间，时钟为北京时间；停站、排队会产生小幅运行偏差。

| 线路／站点 | 可站立位置 |
| --- | --- |
| P1 城市—港口，城市端 | `512.5 95 464.5` |
| C1 第三新东京中央 | `-119.5 95 -207.5` |
| U1 地下都市入口 | `-330.5 -466 777.5` |
| U2 NERV 总部 | `30.5 -466 514.5` |
| S1 新箱根机场 | `-1669.5 95 -272.5` |

例如：

```mcfunction
/execute in projectseele:geofront run tp @s 512.5 95 464.5
```

等车停稳开门，从车门正常走进去，再向车厢中央走两步。无需右键车头，也不要按住 Shift 登车。到站停稳后从开门处出去；需要解除乘坐状态时按 Shift。首轮加载后列车需要进入正常运行循环，传送到站台不会立即召来一班车。

## F1 飞机

F1 在箱根湾机场和新箱根机场之间自动往返，包含滑行、起降和机位停靠。登机梯下方：

```mcfunction
/execute in projectseele:geofront run tp @s 669.31225 81 1232.5 0 0
/execute in projectseele:geofront run tp @s -1628.31225 81 -217.5 0 0
```

任选一个机场等待飞机停稳开门。登机梯展开后，沿梯向南走入机舱，再往里面走几步；飞机离开前梯子会收回。乘客不需要操作油门。抵达另一机场、完全停稳开门后再下机。该操作用于 MTR 客机，基地战机使用 Superb Warfare 自己的载具交互。

## UN 基地与两个机库

基地在主城东北约九千格。现有 UN-00 保留上一版模型；新建 UN-01 试验舱已预留模型位置。本轮模型工作交给 ChatGPT Pro，UN-01 空舱不生成占位机体。

```mcfunction
/seele military visit base
/seele military visit hangar
/seele military status
/seele military drain
```

排液完成后开门、去 UN-00 登机栈桥：

```mcfunction
/seele military door
/seele military visit gantry
```

面对黑色插入栓舱口空手右键，等入栓完成，再驾驶向南走出地表机库。UN-00 不使用原三机的发射井。`K` 为眼部激光。回收时走回 `6442.5 77 -6205.5`，朝南停稳，按 `V` 申请退栓；离开液舱后关闭舱门，再执行 `/seele military fill`。

UN-01 新舱在现有机库西侧 160 格。到其外部控制区：

```mcfunction
/execute in projectseele:geofront run tp @s 6238.5 77 -6144.5 0 0
/seele military un01 status
/seele military un01 drain
```

等排液结束后执行 `/seele military un01 door` 开门，再次执行关门；门完全关闭后用 `/seele military un01 fill` 注液。舱内有人时不要注液，门口有人时关门联锁应拒绝。这一套操作独立于 UN-00。

## 反馈

重点评价道路高架交汇、车站空间比例、机库斜坡和观察廊，以及 F5 转运／回收的连续性。遇到问题保留 F3 坐标、刚执行的命令、聊天栏原文和 F2 截图。截图在 `D:\eva\run\screenshots`，当前游戏日志在 `D:\eva\run\logs\latest.log`。

模型制作提示词见 [MODEL_HANDOFF_R20.md](MODEL_HANDOFF_R20.md)，模型参考包在 `artifacts/world_rebuild_r20/model_handoff`。
