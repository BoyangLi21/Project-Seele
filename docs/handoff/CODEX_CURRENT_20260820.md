# Project SEELE — Codex 接力入口（2026-08-20）

> 新任务只需依次读取 `AGENTS.md`、本文件、
> `docs/handoff/GPT56PRO_KNOWLEDGE_INDEX_20260820.md`、`docs/DECISIONS.md`、
> `docs/MAP_EDITING_PROTOCOL.md`、`docs/ROADMAP.md`。禁止为了“补历史”读取旧聊天、
> `.Codex/ACTIVE_WORKLOG.md` 或整个 `artifacts/`。

## 1. 当前事实源

- 仓库：`D:\eva`，分支 `main`，本文件生成时 HEAD `7adc364`。
- 权威存档：`D:\eva\run\saves\SEELE_S20_RECOVERY_R28`。
- 维度：`projectseele:geofront`。
- 人类刚搭或改过的方块永远优先；任何地图修改必须先执行
  `docs/MAP_EDITING_PROTOCOL.md`，读取只用 `tools/query_blocks.py`。
- 工作树包含大量已确认但尚未提交的长期修改；禁止 reset、checkout 或覆盖无关文件。
- 游戏内视觉由用户验收；代码只做必要构建和日志验证，不写“测试的测试”。

## 2. 刚完成且不可丢失

### 地图 S33 / S34

- `y=-395` 新 B-49 层由用户先铺设，随后被整理为正式交通层。
- 南端人员电梯：轴心 `(94,*,241)`；上层 `(94,-394,241)` 改为朝 `NORTH/-Z`
  开门，下层仍朝 WEST。
- 北端人员电梯：轴心 `(93,*,204)`；正式三层：
  - `(93,-442,204)` EVA CAGES / LAUNCH PLANT
  - `(93,-394,204)` HANGAR INTERCHANGE / B-49
  - `(93,-370,204)` UPPER HANGAR OBSERVATION
- 北端电梯三个黑色 controller/locator 统一在东侧 `x=96,z=204`，不再放在
  西侧 `x=90`。
- 人工道路的真实路线是 `x=98..103,z=139..214`。S34 按此直线建设了地板、
  结构墙、观察窗、灯带和顶板，并保留 `x=98,z=204..210` 横向电梯接口。
- S33 误开的 EVA-02 机库后墙已按 S33 前体素精确恢复；不能再次从
  `(100,-395,187)` 向西打洞。
- 可步行验证锚点均在一个 3167 格组件：`(100,139)`、`(100,187)`、
  `(100,207)`、`(93,209)`、`(94,233)`，脚位统一 `y=-394`。
- 备份/差异：
  - `artifacts/s34_x100_route_20260819_235840`
  - `artifacts/s33_b49_interchange_20260819_234506`
  - `artifacts/s32_observation_platforms_20260819_174839`

### 电梯稳定性

- Moving Elevators 1.4.12 是人员电梯唯一运动实现。
- `S20MovingElevatorsAdapter` 曾每 tick 扫 4500 格旧轴并删除当前轿厢显示面；已改成
  每次服务器运行只迁移一次，并保护当前 cage 体积。
- 轿厢内部必须只有一个可点击楼层显示面；技术输入块藏在其下方并伪装成黑色实体墙。
- 健康停止轿厢现在应直接 adopt 持久状态，启动时 `shaftWrites=0`，不得每次清空整条井道。
- 外部每层只留一个召唤按钮；内部用 Moving Elevators 的文字显示面选楼层。

### 发射井、机库与观察层

- 三座地表发射井关闭时有 31×31 实体深板岩防雨层，开门时移除；视觉门负责滑动。
- 三座 EVA 正面观察结构是开放平台：平台上没有玻璃，只在 EVA 侧与边缘使用铁栅栏。
- S32 错误加入的 1053 格机库隔断玻璃已在 S33 精确撤销。
- 当前机库/插入栓/EVA 物流逻辑仍在长期打磨，地图不得再调用旧全图生成器。

## 3. 当前性能判断

- `build.gradle` 的 Forge console 已从 `REGISTRIES/DEBUG` 降为 `INFO`。
- 已移除运行中每 tick 旧电梯扫描；实体顶盖不再触发 2883 格邻居形状级联。
- 最新日志的前两次 `Can't keep up` 出现在启动、轿厢重建和舰队恢复阶段；持久轿厢
  adopt 修改用于消除这一部分。
- 日志中后两次紧跟 `Saving and pausing game...`，属于单机按 Esc/失焦后的同步保存。
  独立服务器不会因客户端暂停触发此类保存；本地测试不要把暂停保存时间误判为持续 TPS。
- 下一次人工启动应搜索：
  - 期望：`Moving Elevators adopted persisted ... shaftWrites=0`
  - 不期望：持续出现 `Moving Elevators normalized ...` 或稳定游玩时反复
    `Can't keep up!`

## 4. 接下来先做什么

1. 构建并让用户重启，验证上述 adopt 日志、北端三层电梯、南端北门和 S34 直通道。
2. 若稳定游玩仍掉 TPS，只加一个短期 `>50 ms` 系统级计时器，采集一次后删除；不要猜。
3. 视觉通过后再继续当前长期队列：插入栓机械/密封/吊机、拘束架、电源接口、EVA
   手指和动作、武器升降设施、指挥室真人第一人称直播。
4. 详细优先级以 `docs/DECISIONS.md` 与 `docs/ROADMAP.md` 为准；本文件只记录当前断点。

## 5. 用户协作约束

- 中文交流，先给结果；不要反复询问可以从仓库或地图测出的事实。
- 地图先扫描再写；未知空间 HOLD，禁止从空气推断房间。
- 用户愿意做真人视觉验证；不要让自动测试阻塞实现。
- Commit 必须追加：
  `Co-Authored-By: Ayanami_Rei <liboyang_621@126.com>`；不要加入 Codex 署名。
- 未经明确要求不清除模型、存档、人工地图改动或外部资源。

## 6. 新任务启动语句

```text
继续 Project SEELE。先读 AGENTS.md、docs/handoff/CODEX_CURRENT_20260820.md、
docs/handoff/GPT56PRO_KNOWLEDGE_INDEX_20260820.md、docs/DECISIONS.md、
docs/MAP_EDITING_PROTOCOL.md、docs/ROADMAP.md。
不要读取旧聊天或旧长日志。以 SEELE_S20_RECOVERY_R28 为唯一权威存档，保留工作树，
从接力文件第4节继续。
```
