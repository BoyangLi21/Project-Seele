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

## 克隆后直接连接 Codex

仓库已经提交项目级 [`.codex/config.toml`](../.codex/config.toml)。因此其他人
clone/pull 后，只要从仓库根目录打开 Codex、信任该仓库并新建任务，Codex 就会自动
启动 `tools/seele_mcp_sidecar.js`；不再需要把作者机器的绝对路径写进全局配置。

```bash
git clone git@github.com:BoyangLi21/Project-Seele.git
cd Project-Seele
bash ./gradlew createSrgToMcp
bash ./gradlew runClient
```

进入一个新建的、可丢弃的开发世界，然后执行：

```text
/seele mcp enable
/seele mcp setup
```

第二条命令仍会在聊天中生成全局配置命令，供旧版 Codex 或从仓库外启动时使用。
在本机等价于：

```bash
codex mcp add projectseele -- node "/absolute/path/to/Project-Seele/tools/seele_mcp_sidecar.js" --project-root "/absolute/path/to/Project-Seele"
```

添加后重启 Codex。Codex 桌面、CLI 与 IDE 扩展共享 MCP 配置。游戏未启动时，
sidecar 仍可正常初始化并列出工具；调用世界工具时会返回 `BRIDGE_UNAVAILABLE`。

首次载入项目级配置时若 Codex 显示信任提示，需要确认信任；项目 MCP 配置只会在
可信仓库中生效。修改 `.codex/config.toml`、插件或 Skill 后，请新建 Codex 任务，
不要指望已经打开的旧任务热加载工具。

## 安装参考建筑插件

仅使用 MCP 建造工具时，项目级配置已经足够。要让 Codex 自动采用“搜索外部/内部
图片 → 参考清单 → 蓝图 → 分批建造 → 多视角截图复核”的完整流程，再安装仓库内的
`project-seele-builder` 插件：

```bash
codex plugin marketplace add BoyangLi21/Project-Seele --ref main
codex plugin add project-seele-builder@project-seele
```

本地开发 checkout 也可以作为 marketplace：

```bash
codex plugin marketplace add .
codex plugin add project-seele-builder@project-seele
```

安装或更新后新建一个 Codex 任务。可显式触发 Skill：

```text
使用 $minecraft-reference-builder，先搜索巴拉蒂的外观和内部参考图，
生成有来源的 Minecraft 蓝图，再在安全检查通过后分批建造并截图修正。
```

插件不会打包或提交《海贼王》《EVA》等作品的官方图片。图片只在 Codex 研究阶段
作为临时参考；Git 中保留的是来源链接、由图片归纳出的建筑特征与自有方块代码。

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
| `minecraft_capture_view` | 只读 | 回传玩家当前世界视角的 PNG，供视觉对照 |
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
- 已提供当前视角截图回传；物品/配方查询、自动修复和任意命令执行仍不开放。
- 通用 voxel 计划适合独立建筑原型；GeoFront、东京-3 下沉都市和发射井仍应调用
  Project SEELE 的确定性 Java builders，不应用几十万条临时计划替代。
- `minecraft_capture_view` 不会移动角色或镜头。玩家先站到正面 3/4、侧后、入口或
  室内等验收视角，Agent 再分别抓图。画面默认 640×360、上限 960×540、1 MiB。
- `minecraft_buildsite` 是地表高度/方块采样，不是完整区域体素扫描。Agent 可以按
  人工给出的绝对坐标精确连接多条通道，但当前 preview 不会报告沿途将替换的原方块；
  要自动绕过未知地下建筑并作“不破坏”硬保证，仍需区域扫描、碰撞报告和寻路工具。
- 对权威 S20 存档的任何修改，都必须先走地点卡、旧状态证据、positiveEditMask、
  forward/inverse patch 和真人批准流程。

## 离线检查

不启动 Minecraft 也可以验证 sidecar：

```bash
node --check tools/seele_mcp_sidecar.js
node tools/seele_mcp_sidecar.js --self-test
```

完整发行构建：

```bash
bash ./gradlew build
```

JAR 位于 `build/libs/`。GitHub Actions 会在每次主分支/PR 构建时上传 JAR、Codex
插件 ZIP 和 marketplace 清单；推送 `v*` 标签时还会把 JAR 与插件 ZIP 附到
GitHub Release。普通玩家安装 JAR 时仍需 Minecraft 1.20.1、Forge 47.4.10 和
GeckoLib 4.8+；MCP/插件只在需要 AI 建造时安装。
