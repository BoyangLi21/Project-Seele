# GeoFront / 第三新东京市连续地图测试

本开发地图只使用原创程序化几何、原创代码与 Minecraft 原版方块。它把第三新东京市和 GeoFront 建在 **同一个 `projectseele:geofront` 维度** 中：城市位于地表，GeoFront 位于封闭地下穹顶内，三条 EVA 发射井是连续方块空间，不是传送门。

## 坐标与硬契约

- GeoFront 原点：`(0, -40, 76)`。
- 第三新东京市原点：`(0, 248, 0)`。
- Unit-00 / Unit-01 / Unit-02 井中心：`X=-28 / 0 / 28, Z=0`。
- 地下床位：`Y=-39`；地表床位：`Y=247`。
- 每条井外壳为 `15×15`，内部连续净空为 `11×11`。
- 上下床位相距 **286 格**；正常发射按 2 格/tick 计算为 143 tick。
- 维度拥有正常天空、昼夜与天气；GeoFront 的黑暗来自三层封闭穹顶，不依赖 `has_ceiling` 或固定时间伪装。

## 首次建造与地图审计

1. 启动桌面的 `Project SEELE 测试.bat`，进入允许命令的创造世界。
2. 执行 `/seele geofront setup`。该命令先建第三新东京市，再建 GeoFront，最后切通三条竖井；首次运行写入方块较多，短暂卡顿属于预期。
3. 玩家会到达 GeoFront 观察位。执行 `/seele geofront audit`，通过结果必须同时包含：

   ```text
   valid=true mapVersion=2 controlMarkers=true lowerBeds=3/3
   surfaceBeds=3/3 continuousShafts=3/3 clearExits=3/3
   ```

4. `/seele geofront operations` 进入 NERV 作战中心；南侧路线通往观察桥，北侧三条通道分别通往三台 EVA 的高位插入栓栈桥。
5. `/seele geofront surface` 只是开发用城市摄影机捷径，不代表 EVA 的正常移动方式。EVA 必须经过真实竖井上升。
6. `/seele geofront exit` 返回进入连续地图前保存的维度与坐标。

## LCL 湖

湖中必须是真正的 `projectseele:lcl` 流体，而不是橙色玻璃，也不能全局替换普通水：

- 湖床相对 GeoFront 原点为 `Y=-4`，LCL 从 `Y=-3` 填充到 `Y=1`，深 5 格；
- 进入后有橙色水下雾与低亮度效果；
- 玩家可以游泳并持续恢复空气，不会在 LCL 内溺水；
- 离开 LCL 后普通水的贴图、颜色与溺水规则必须保持原版行为；
- `/seele geofront audit` 的 `lclLake=true` 必须来自流体类型检查，而不是颜色方块检查。

## 三机同维度出击

1. 完成地图审计后执行 `/seele geofront link`。命令会在三个地下床位创建或复用 Unit-00/01/02，并把各自的地表床位登记为 **同一维度** 的目的地；不会搬运或复制 EVA 到另一个维度。
2. 执行 `/seele geofront sortie_audit`，必须报告三种机型、三条有效同维目的地和三个可达高位栈桥。
3. 从高位背部栈桥瞄准插入栓入口并右键，或用 `/seele silo board` 作为确定性测试后备。
4. 同步完成后，11×11 载台带着原实体、原驾驶员沿井上升。中途按 `F3` 观察：维度应始终为 `projectseele:geofront`，实体 UUID 不变。
5. 到达地表后 EVA 基座位于 `Y=248`，随后进入 `LAUNCH_CLEAR`；结束前输入和弹出仍被联锁。
6. 日志应出现 `NERV continuous sortie complete`，并报告 `rise=286`。主流程若出现 `NERV cross-dimension sortie complete` 即验收失败。

`EvaUnit01Entity` 中保留的 `changeDimension` 分支只服务旧存档或独立短井兼容。静态与人工验收都要求先命中 `destination == sourceLevel` 的同维分支；legacy 分支存在不等于连续地图通过。

## 自动视觉验证

地图景观：

```bat
tools\start_test.bat visual geofront
```

必须生成 `cavern_overview`、`nerv_pyramid`、`nerv_operations`、`lcl_lake`、`lift_terminals` 五张图，并通过服务端与客户端地标审计。

连续发射：

```bat
tools\start_test.bat visual geofront_sortie
```

必须生成四个状态门控帧：`three_units_ready`、`entry_plug_locked`、`ascent_mid`、`tokyo3_surface_arrival`。`ascent_mid` 只允许在相对地下原点上升 100～240 格时拍摄；到达帧必须仍处于同一维度，并达到相对地下原点至少 286 格。

离线硬契约：

```bat
python tools\validate_geofront_contract.py
python tools\render_launch_silo_preview.py --strict
```

离线脚本能证明坐标、结构、分支顺序和状态机合同，不能代替玩家对碰撞、速度感、光照、城市比例与驾驶舒适度的肉眼验收。

## 当前完成边界

当前声称完成的是：同维度上下地图骨架、封闭 GeoFront 穹顶、NERV 作战中心、独立 LCL 湖、三条连续发射井、三机地下冻结与地表出击。城市美术密度、更多 NERV 内部、Terminal Dogma、最终地图资产整合仍需继续迭代；不得仅凭“能生成”标记为最终美术完成。
