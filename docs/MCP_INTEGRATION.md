# Project SEELE MCP 建造桥

Project SEELE 不能直接加载 `gemini-minecraft` 的模组 JAR：上游目标是
Fabric 1.21.1，而本项目锁定 Forge 1.20.1。本仓库因此实现了一个原生
Forge 兼容层，保留上游最有价值的工作流：

`读取会话 → 扫描地形 → 预览结构化计划 → 执行同一个 planId → 分批施工 → 撤销`

设计参考：[`aaronaalmendarez/gemini-minecraft`](https://github.com/aaronaalmendarez/gemini-minecraft)
的 loopback bridge、stdio sidecar、buildsite、preview/execute 和 undo 思路。
上游使用 MIT License。本实现为 Project SEELE 独立的 Forge 1.20.1 适配，
没有引入 Fabric 运行时或 Gemini API 依赖。

## 安全模型

- 默认关闭；每次服务端运行需 `/seele mcp enable`，或在 common config 中显式开启。
- HTTP 只绑定 `127.0.0.1`，所有世界工具都要求 256-bit bearer token。
- token 位于 `run/config/projectseele-mcp-token.txt`，不进入 Git。
- 同一时间只处理一个 HTTP 请求和一个施工任务。
- 建造按 `mcp.blocksPerTick` 分批写入，默认每 tick 2048 格。
- 每次施工保存完整旧方块状态和 BlockEntity NBT，可用 MCP 工具撤销。
- 服务器在施工中退出时，会在关闭流程中回滚已写入部分。
- `SEELE_S20_REBUILD`、clean rebuild、历史损坏档和带空间冻结标记的存档，
  一律拒绝通用 MCP 写入。它们继续受 `MAP_EDITING_PROTOCOL.md` 管理。

## 首次连接 Codex

```bash
cd /absolute/path/to/Project-Seele
bash ./gradlew createSrgToMcp
bash ./gradlew runClient
```

进入一个新建的、可丢弃的开发世界，然后执行：

```text
/seele mcp enable
/seele mcp setup
```

第二条命令会在聊天中生成可复制的命令。在本机等价于：

```bash
codex mcp add projectseele -- node "/absolute/path/to/Project-Seele/tools/seele_mcp_sidecar.js" --project-root "/absolute/path/to/Project-Seele"
```

添加后重启 Codex。Codex 桌面、CLI 与 IDE 扩展共享 MCP 配置。游戏未启动时，
sidecar 仍可正常初始化并列出工具；调用世界工具时会返回 `BRIDGE_UNAVAILABLE`。

常用管理命令：

```text
/seele mcp status
/seele mcp token
/seele mcp regenerate-token
/seele mcp disable
```

## MCP 工具

| 工具 | 类型 | 用途 |
|---|---|---|
| `minecraft_session` | 只读 | 玩家、维度、位置、模式和写入门禁 |
| `minecraft_seele_status` | 只读 | SEELE 存档角色与冻结状态 |
| `minecraft_buildsite` | 只读 | 玩家周围地表高度和材质采样 |
| `minecraft_preview_build_plan` | 只读 | 编译计划、返回精确边界/材料/planId |
| `minecraft_execute_build_plan` | 写入 | 执行预览缓存，启动分批施工 |
| `minecraft_batch_status` | 只读 | 查询施工或撤销进度 |
| `minecraft_undo_last_batch` | 写入 | 恢复上一次施工前的完整状态 |

## 建造计划示例

```json
{
  "plan": {
    "summary": "NERV 风格测试塔",
    "coordMode": "relative",
    "origin": [8, 0, 8],
    "rotation": 0,
    "palette": {
      "shell": "minecraft:gray_concrete",
      "glass": "minecraft:orange_stained_glass"
    },
    "steps": [
      {
        "label": "主体",
        "cuboids": [
          {"from": [0, 0, 0], "to": [20, 40, 20], "block": "shell", "hollow": true}
        ]
      },
      {
        "label": "观察窗",
        "cuboids": [
          {"from": [4, 20, 0], "to": [16, 24, 0], "block": "glass"}
        ]
      }
    ]
  }
}
```

`coordMode=relative` 时，`origin` 是相对玩家脚下方块的偏移；
`coordMode=absolute` 时必须给出绝对世界坐标。支持 0/90/180/270 度旋转。
方块字符串支持状态，例如：

```text
minecraft:oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]
```

## 直接描述大型建筑

不需要手写 JSON。可以直接向 Agent 描述 EVA 世界中的大型建筑，Agent 会先读取
会话和地形，再把自然语言要求转成尺寸、朝向、功能分区、材料表和多个可撤销施工批次。
如果没有可靠的精确比例，它应明确说明采用 Minecraft 尺度近似，而不伪造设定数据。

示例：

```text
在玩家前方建造一座受 NERV 总部金字塔启发的大型地下设施入口。
整体约 96×72×38 格，入口朝向玩家；需要中央装甲门、两侧斜坡、外露支撑肋、
橙色警示窗带，以及可进入的大厅、控制层和两条侧廊。使用混凝土、深板岩、
黑色玻璃和少量红色灯光，保持冷峻的军用工业风格。

先勘察地形并说明比例假设。按地基、轮廓框架、楼层与通道、外壳、立面细节、
照明六个批次建造。每批都必须 preview，检查边界和方块数，再执行同一个 planId
并等待完成。不要使用实心巨块代替内部空间；发生错误时撤销上一批并修正。
```

用户已经明确要求在可丢弃开发世界中建造时，这本身视为施工授权；安全检查通过后
不必重复询问。若存档写入门禁为 false，Agent 仍必须停止。GeoFront、Central
Dogma 等超大型场景应缩放或拆成多个区域，避免一次计划超过方块数和施工半径限制。

## 当前边界

- v1 只选择服务器玩家列表中的第一个玩家，定位为本地单人开发。
- 尚未移植上游的截图视觉、物品/配方查询、自动修复和任意命令执行。
- 通用 voxel 计划适合独立建筑原型；GeoFront、东京-3 下沉都市和发射井仍应调用
  Project SEELE 的确定性 Java builders，不应用几十万条临时计划替代。
- 对权威 S20 存档的任何修改，都必须先走地点卡、旧状态证据、positiveEditMask、
  forward/inverse patch 和真人批准流程。

## 离线检查

不启动 Minecraft 也可以验证 sidecar：

```bash
node --check tools/seele_mcp_sidecar.js
node tools/seele_mcp_sidecar.js --self-test
```
