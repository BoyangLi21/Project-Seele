# NERV 发射井测试

项目现在有两套用途不同的发射井：

1. **主流程：连续地图发射井。** 第三新东京市与 GeoFront 位于同一维度，三条 11×11 净空竖井真实连接地下和地表，载台行程 522 格。
2. **兼容测试：独立短井。** `/seele silo setup` 生成旧的 31 格开发设施，继续用于快速验证插入栓、栈桥、载台和六阶段截图，但不能作为“GeoFront 已连接东京市”的证据。

## 离线结构验证

运行：

```bat
python tools\render_launch_silo_preview.py --strict
```

脚本读取 `IntegratedNervMapBuilder`、`NervConstructionKitItem`、`LaunchSiloCommands`、`EvaUnit01Entity`、EVA 渲染比例、模型与 `activation` 动画。它使用连续地图坐标绘制三井俯视图和 Unit-01 剖面，同时沿用短井的高位栈桥与插入栓细节合同。

输出：

- `external-assets/work/launch-silo-preview/launch_silo_preview.png`
- `external-assets/work/launch-silo-preview/launch_silo_preview.json`

严格门禁至少检查：

- GeoFront 原点 `(30,-380,296)`、第三新东京市原点 `(30,80,220)`；
- 三个床位 X=2/30/58、Z=220，GeoFront 球体内床位 Y=-379、东京-3 地表床位 Y=79；
- 三条 15×15 外壳、11×11 净空、522 格连续行程；
- Unit-00/01/02 与三个床位一一对应；
- 13×13 固定井底平台与 11×11 移动载台；
- 高位背部栈桥、24 格连续梯道和背部登乘扇区；
- 插入栓从高处下降到模型背部插口，而不是突兀显隐；
- 动态终点由上下站标记决定，522 格按 2 格/tick 得到 261 tick；
- `destination == sourceLevel` 同维分支位于 legacy `changeDimension` 之前，且该分支本身不调用 `changeDimension`；
- 独立短井 `LAUNCH_CLEAR` 为 18 tick（约 0.9 秒）；连续 522 格路线到站同步为 1 tick。

PNG/JSON 是坐标和状态合同检查，不代表 Minecraft 中碰撞、插值、粒子、声音、发射重量感或镜头舒适度已经通过。

## 推荐：真实 522 格出击测试

1. 用 `tools/start_test.bat` 或桌面启动器进入允许命令的创造世界。
2. 执行 `/seele geofront setup`，等待连续地图建造并通过审计。
3. 执行 `/seele geofront link`。Unit-00/01/02 应冻结在三个地下床位，目的地都是当前 `projectseele:geofront` 维度中的对应地表床位。
4. 执行 `/seele geofront sortie_audit`；只有三机、三目的地和三栈桥全部有效才继续。
5. 从 Unit-01 背部高位栈桥瞄准插入栓入口并右键。`/seele silo board` 只作为确定性后备。
6. 同步、舱盖闭锁后，移动载台应连续上升 522 格；中途维度和 EVA UUID 不得变化。
7. 到达地表时 EVA 基座应位于 Y=80，日志依次出现：

   ```text
   NERV launch locked
   NERV launch ascent
   NERV launch surface clear
   NERV continuous sortie complete ... rise=522
   ```

8. 正常主流程不应出现 `NERV cross-dimension sortie complete`。该日志只允许旧存档兼容场景使用。

## 快速：独立短井测试

1. 在开阔地表执行 `/seele silo setup`。
2. 命令建造三座短井并把玩家放到 Unit-01 背部高位栈桥。
3. 瞄准真实显示的背部插口右键；从正面、侧面或脚边隔空右键必须被拒绝。
4. 执行 `/seele silo audit`；结果必须同时包含 `units=3`、`variants00/01/02=true`、`beds=3`、`highGantries=3` 和 `clearShafts=3`。
5. 执行 `/seele silo status` 可查看 `LOCKED`、`ASCENT`、`SURFACE_CLEAR`、`IDLE` 与实时载台高度。

这个短井仍应保持以下安全规则：

- 机体在插入栓、同步、ASCENT 和 LAUNCH_CLEAR 期间彻底冻结位置、朝向、输入、重力、碰撞推动和 V 键弹出；
- 玩家必须位于约 24～29.5 格相对高度、1.75～8.5 格水平距离的背部登乘扇区，并真正瞄准插口；
- 插入栓完整收进背部后才闭合舱门，不能有半截栓体长期露在装甲外；
- 中断时清理移动载台，恢复一层完整井底平台，并把 EVA 与乘员安全复位；
- 保存/重进时有乘员关系恢复窗口，不能复制载台或 EVA；
- 到达终点后保持 18 tick（约 0.9 秒）`LAUNCH_CLEAR`，之后才恢复驾驶权。

## 自动视觉批次

```bat
tools\start_test.bat visual silo
```

该批次真实执行短井 `setup` 和 `board`，按 `IDLE → LOCKED → ASCENT → SURFACE_CLEAR` 保存六张 PNG：高位背部平台、插入栓下降外景、同步驾驶舱、舱盖闭锁、井内中段上升、地表释放。它适合快速检查插入栓和局部状态机，不验收 522 格同维路线。

连续地图另用：

```bat
tools\start_test.bat visual geofront_sortie
```

该批次必须在同一维度捕获地下待命、插入栓锁定、相对地下床位上升 80～208 格的井内阶段和东京市地表到达。最终仍需要人类检查井壁碰撞、载台重量感、镜头舒适度、EVA 朝向和城市比例。
## 脐带供电与发射联动

连续地图会在三座地下床位旁和三座地表站旁自动部署 6 个 `projectseele:umbilical_pylon`。地下待命时应保持 `POWER UMBILICAL`；沿 522 格竖井升空并离桩超过默认 32 格后自动断缆、切入 5 分钟内置电源；抵达同路线地表供电桩附近后自动重连。`/seele geofront link` 与实时发射准备都会补齐旧存档缺失的供电桩，`sortie_audit` 会拒绝供电点不完整的路线。
