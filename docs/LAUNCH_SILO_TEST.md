# NERV 发射井测试

当前实现是一套可重复验证的三井出击原型，三座井分别部署零号机、初号机和二号机。井底有 13×13 固定平台，背部有高位插入栓栈桥；同步序列结束后，独立的 11×11 移动载台会把 EVA 弹射到地表。

## 不启动 Minecraft 的结构验证

先运行离线预览：

```bat
python tools\render_launch_silo_preview.py --strict
```

脚本直接读取 `NervConstructionKitItem`、`LaunchSiloCommands`、`EvaUnit01Entity`、初号机渲染比例、初号机几何与 `activation` 动画，不另维护一套手填尺寸。默认生成：

- `external-assets/work/launch-silo-preview/launch_silo_preview.png`
- `external-assets/work/launch-silo-preview/launch_silo_preview.json`

PNG 同时给出三井俯视图和中井剖面图，明确标出：

- 三个型号及各自井床；
- 井壁、11×11×31 上升净空、13×13 固定井底平台与 11×11 移动载台；
- 地表、表面闸板、固定井底平台和移动载台的 31 格行程；
- 背部高位栈桥、20 格连续梯道和登乘点；
- 插入栓从高处下降至背部插口的动画路径；
- EVA 弹射终点（井床上方 32 格）。

`--strict` 当前执行 18 项门禁，至少覆盖三型号、三床位、井间距、井壳、11×11×31 净空、EVA 宽度、13×13 固定井底平台、11×11 移动载台、高位栈桥、梯道连续性、背部登乘扇区、插入栓自上而下、插入栓起点高于栈桥、31 格载台行程与弹射终点。任意 Java 循环、常量或动画合同漂移都会在 JSON 中留下 `FAIL` 并返回非零退出码。

这个离线图是尺寸和状态合同检查，不是游戏画面替代品。它不能证明 Minecraft 中的碰撞、插值、粒子、声音和弹射重量感已经通过。

## 一键布置与弹射

1. 用 `tools/start_test.bat` 启动开发客户端。
2. 进入允许作弊的创造模式世界，在开阔地表执行 `/seele silo setup`。
3. 命令会建造三井设施，并把玩家放到初号机背部的高位插入栓栈桥。
4. 执行 `/seele silo board`。插入栓锁定、LCL 与同步演出结束后，11×11 实体移动载台托住 EVA 自动弹射到地表。
5. 任意时刻执行 `/seele silo status` 查看 `LOCKED`、`ASCENT`、`SURFACE_CLEAR` 或 `IDLE`，以及实时 `carrier` 高度。
6. 弹射前执行 `/seele silo audit`；只有结果同时显示 `units=3`、`variants00/01/02=true`、`beds=3`、`highGantries=3` 与 `clearShafts=3`，才表示游戏内三井结构门禁通过。

创造物品栏里的 `NERV 出击设施建造器` 会生成相同设施。井内 EVA 只能从背部高位栈桥进入：玩家必须同时满足高度、4–11 格距离和背部扇区条件；从正面、侧面或井底隔空右键会被拒绝。地面自由放置的 EVA 仍保留直接驾驶方式。

## 游戏内验收点

- 地下横向通道的梯井可通往背部高位栈桥；`audit` 会逐格检查 20 格连续梯子。
- 从井底或 EVA 脚边右键应提示前往高位栈桥，不应直接进入驾驶室。
- 登乘后播放六秒插入栓/同步覆盖层；约五秒时进入最终联锁并启动载台。
- 上升期间 11×11 移动载台随 EVA 逐层移动，EVA 被引导到井中心；井底保留独立的 13×13 固定平台，驾驶输入和 `V` 弹出被联锁。
- 中途异常终止会清掉井内移动载台并重新关闭地表载台，不在井筒内遗留方块层。
- 中断时机体先回井底安全位，乘员随座舱一起复位；正常完成则先让机体与乘员整体越过 deck 平面，再闭合闸门。
- `ASCENT` 中保存并重进后，日志应出现 `NERV carrier recovered`；井内只能重建一层完整载台。
- EVA 基座到达井床上方 32 格后制动，并恢复重力与驾驶权。
- `run/logs/latest.log` 先出现 `NERV silo audit [setup]: valid=true`，随后依次出现 `NERV launch locked`、`NERV launch ascent`、`NERV launch surface clear`。

## 启动器参数

需要无人值守的初号机截图批次时，可从命令行运行：

```bat
tools\start_test.bat visual
```

桌面启动器会先重建并校验本地高细节资源，再启动 Forge。发射井的实际井壁碰撞、载台闭合观感、插入栓进入镜头和地表制动仍必须在游戏中按上述步骤目视验收；构建或离线合同通过不等于这些视觉项目已经通过。
