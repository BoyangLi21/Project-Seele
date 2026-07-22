# LCL 流体人工测试

LCL 是独立的 `projectseele:lcl` 流体，不替换原版水。GeoFront 主湖和 Terminal Dogma 封印池使用同一种服务端玩法规则：可游泳、不溺水、缓慢恢复，浸没其中的掉落物不会过期。

## 当前数值（新增，待玩家拍板）

| 项目 | 默认值 | 配置键 |
|---|---:|---|
| 每次恢复 | 1.0 生命值（半颗心） | `lcl.healAmount` |
| 恢复间隔 | 40 tick（2 秒） | `lcl.healIntervalTicks` |
| 浸没物品不消失 | 开启 | `lcl.itemsPersist` |

恢复仅作用于玩家，不会让使徒、EVA 或莉莉丝在池中自动回血。所有判定都在服务端执行，多人客户端不自行猜测生命值或物品寿命。

## 快速功能测试

1. 在普通测试区创建小池：`/fill ~-3 ~-1 ~-3 ~3 ~1 ~3 projectseele:lcl`。不要在需要保留的建筑内执行。
2. 切换生存模式，执行 `/damage @s 6 minecraft:generic`，完全潜入液面以下。
3. 保持 10 秒：空气值必须持续满格；生命值应每 40 tick 恢复 1.0，约恢复五次。离开 LCL 后恢复立即停止。
4. 在池中生成一个临近过期的钻石：`/summon minecraft:item ~ ~ ~ {Item:{id:"minecraft:diamond",Count:1b},Age:5990s}`。等待至少 20 秒，物品仍必须存在。
5. 清除物品周围 LCL 或捡起后重新丢在空气中。达到原版寿命的物品最多经过一个 200-tick 续期窗口便应恢复正常过期，不能永久污染世界。
6. 进入原版水重复测试：不得获得 LCL 恢复，原版溺水规则和水色不能改变。

## 配置复核

退出世界后可在 `config/projectseele-common.toml` 调整：

- `lcl.healAmount = 0.0`：只保留呼吸，不回血；
- `lcl.healIntervalTicks`：恢复脉冲间隔；
- `lcl.itemsPersist = false`：恢复原版物品过期。

重新进入世界后用同一套步骤复核。配置变化不需要重建模组。

## 离线门禁

```bat
python tools\validate_lcl_contract.py
```

该脚本验证独立流体注册、呼吸、玩家恢复、物品过期拦截、两处设施用液和人工测试合同。它不能替代多人服务器中对游泳手感、橙色雾效和性能的肉眼验收。