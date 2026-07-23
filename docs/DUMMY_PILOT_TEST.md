# NERV Dummy 驾驶员与实体插入栓测试

这套流程用于单人档验证“驾驶员在机库登栓、主指挥室下令、指挥屏直播”的多人协同，不再让 Dummy 瞬移进 EVA。

## 准备

1. 从桌面的 `Project SEELE 测试.bat` 启动。
2. 首次升级旧档时运行 `/seele geofront setup`，等待地图审计完成。
3. 运行 `/seele eva reset unit01`，确保初号机、LCL、登机桥和外部白色插入栓回到停车状态。

## 单人完整流程

1. 运行 `/seele eva dummy start unit01`。
2. 到初号机机库观察：Dummy 应从共用走廊步行到背部桥，随后消失进入悬吊插入栓；它不能直接瞬移到 EVA 头部。
3. 进入主指挥室。Unit-01 屏幕此时应显示等待/登栓状态。
4. 在主指挥台按 `MAGI CHECK`：八段登机桥应逐段向左右收起，白色插入栓应沿斜线下降并进入后颈，随后才排空 LCL。
5. EVA 应保持冻结，随实体承载台平移到对应发射井；未按 `EVA-01 RELEASE` 前不能弹射。
6. 按 `EVA-01 RELEASE` 后观察连续竖井弹射。Dummy 完成链接后，Unit-01 16:9 屏幕应显示带 NERV 框线的移动第一人称画面和 `TRAINING LIVE`。

## 人工检查点

- 插入栓是独立白色模型，停车时悬在 EVA 背后上方，能被右键登乘。
- 观察控制室位于登机桥正上方，有玻璃正对 EVA；按钮均有实体平台承托。
- 指挥区至三座机库各有一条有地板、墙、顶灯的连续步行通道，任何出口都不通向空气。
- 顺序必须是：`PARKED → BRIDGE_RETRACTING → PLUG_INSERTING → PLUG_LOCKING → DRAINING → TO_SILO → SILO_READY`。
- 真人驾驶画面优先级高于 Dummy；同一台 EVA 不应同时出现两路直播。

## 清理

- `/seele eva dummy stop unit01`：移除一号 Dummy。
- `/seele eva dummy stop all`：移除全部 Dummy。
- `/seele eva dummy status`：查看当前 Dummy 所在阶段。
