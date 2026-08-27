# EVA 单人战斗候选验收 R01

本批只包含已经通过严格物理重定向审计的三个**单人候选**。双人抓取已冻结，
普通攻击和连招尚未计入本批，避免再次把半成品当作完成项。

## 可直接观看的 MP4

每个动作有两种视图：

- `artifacts/motion_review/accepted_single_r01/*_eva_model.mp4`：使用本机游戏
  实际高精 EVA-01 网格的 60 fps 三维渲染；
- 同目录不带 `_eva_model` 的 MP4：MuJoCo 物理骨架四视图，用于检查骨盆、
  脚底、接触和隐藏在旧游戏网格中的关节。

| 动作 | EVA 模型 MP4 | 物理四视图 MP4 |
|---|---|---|
| 左侧高位拨架 | `01_ward_left_eva_model.mp4` | `01_ward_left.mp4` |
| 右侧高位拨架 | `02_ward_right_eva_model.mp4` | `02_ward_right.mp4` |
| 右腿推进踢 | `03_push_kick_right_eva_model.mp4` | `03_push_kick_right.mp4` |

完整可旋转场景为 `EVA_COMBAT_SINGLE_REVIEW_R01.blend`。

## Minecraft 验收步骤

1. 双击 `tools\start_motion_lab.bat`，进入专用存档
   `SEELE_EVA_MOTION_LAB`。不要在 R28 正式存档执行重建命令。
2. 进入后执行：

   ```mcfunction
   /seele motionlab reset
   /seele motionlab camera
   ```

3. 左侧拨架：

   ```mcfunction
   /seele motionlab demo unit01 stop
   /seele motionlab demo unit01 ward_left
   ```

4. 右侧拨架：

   ```mcfunction
   /seele motionlab demo unit01 stop
   /seele motionlab demo unit01 ward_right
   ```

5. 右腿推进踢：

   ```mcfunction
   /seele motionlab demo unit01 stop
   /seele motionlab demo unit01 push_kick_right
   ```

每条命令只播放一次并停在终点，方便逐帧观察。再次播放同一动作时，先执行
`stop`。聊天栏应显示 `STRICT SINGLE-EVA PHYSICAL REVIEW`；若显示普通 Gecko
动作或离线 G1 回放，则不是本批数据。

## 人工验收重点

- `ward_left` 和 `ward_right` 必须明确左右相反，不能镜像错位；
- 动作从骨盆和胸廓发动，手臂不能单独挥舞；
- 支撑脚不能漂移、抽动或翻面；
- 推进踢必须由右腿完成，左脚保持承重，回收前膝踝链不能断开；
- 肩、肘和腕不能穿入胸甲；
- 全身不能在动作开始或结束时发生根瞬移。

## 当前边界

这是隔离 Motion Lab 的可视验收入口，不驱动伤害或正式存档碰撞。当前 Minecraft
高精网格仍是旧 15 段可动骨架；物理骨架中的颈、锁骨、腕、踝和脚趾会折叠到
最近的可见父骨。因而关节质量以四视图 MP4 为准，模型映射和整体轮廓以
`*_eva_model.mp4` 与 Minecraft 为准。普通攻击、短连招与原作专用动作将在本批
人工通过后继续进入同一验收管线。
