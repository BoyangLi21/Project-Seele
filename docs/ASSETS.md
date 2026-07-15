# 素材登记簿

> 合规基线：khara 二创指引（非商业、零官方素材）。本文件登记**所有**非代码资产的来源。
> 任何新素材入库前先在这里登记。

## 音效（全部原创合成）

| 文件 | 用途 | 来源 |
|---|---|---|
| `sounds/alarm.ogg` | 使徒来袭循环警报 | 原创：`tools/gen_sounds.ps1` 数学合成（正弦+奇次谐波双音） |
| `sounds/beam_charge.ogg` | 光束蓄力 | 同上（指数上扫+颤音） |
| `sounds/beam_fire.ogg` | 光束发射 | 同上（锯齿下坠+噪声） |
| `sounds/cross_explosion.ogg` | 十字爆炸 | 同上（低通噪声+低频轰鸣） |
| `sounds/crystal_hit.ogg` | 拉米尔受击 | 同上（高频正弦簇） |
| `sounds/crystal_break.ogg` | 拉米尔死亡 | 同上（下行玻璃音簇+噪声） |
| `sounds/drill.ogg` | 二阶段钻击 | 同上（锯齿嗡鸣+低通噪声） |
| `sounds/ramiel_hum.ogg` | 拉米尔环境音 | 同上（110/164.6Hz 拍频） |
| `sounds/rifle_fire.ogg` | 阳电子步枪 | 同上（锯齿快速下扫） |

全部由脚本以固定随机种子生成，可复现；无采样、无原作旋律。许可随仓库 MIT。

## 贴图（全部程序生成）

| 文件 | 规格 | 来源 |
|---|---|---|
| `textures/item/positron_rifle.png` | 32×32 | 原创：`tools/gen_textures.ps1` 程序绘制 |
| `textures/item/core_fragment.png` | 32×32 | 同上 |
| `textures/entity/ramiel.png` | 32×32 | 同上（渐变+棱面纹理） |

欢迎社区高清重绘（资源包可直接覆盖）。

## 本地测试资产（不在仓库内，永不提交）

| 资产 | 来源 | 状态 |
|---|---|---|
| NERV HQ 1:1 世界存档（`run/saves/NERV_HQ_1to1_Poodcie`） | PMC 项目 `nerv-hq`，作者 Poodcie，官方镜像下载 | 仅本地测试。**如需随 mod 公开发布，必须先取得作者授权**（ROADMAP §9 行动清单） |
| SmOd EVA/使徒本地参考包 | SmOd `EVANGELION: END ADDON V1.0`（Planet Minecraft / Bedrock addon），作者 SmOd774YT，未列开放许可证 | 旧版 EVA 转换结果已退出当前机体管线；仍作为使徒和造型参考保留。仅本地测试，**公开使用前必须取得作者许可** |
| 当前 EVA-00/01/02/量产机本机身体资源 | Tigerar1 的四个 Sketchfab 模型（逐项链接见下表），CC BY-SA | `make_tiger_unit01_pack.py` 与 `make_tiger_eva_variants_pack.py` 生成到忽略目录；这是当前测试身体来源，转换美术不属于 MIT 代码许可，正式发行前必须完成完整署名与 ShareAlike 审核 |
| 初号机/零号机通用高振动粒子刀 | [Udon-San `Progressive Knife`](https://sketchfab.com/3d-models/progressive-knife-e104dbec8c904f9b840c29c4a7d5d770)，CC Attribution | 用户下载的 FBX/贴图；3,766 三角面；由 `make_downloaded_eva_accessories_pack.py` 转换到本机包并以反握插槽使用。源文件与转换 mesh 均不入库 |
| 二号机专用粒子刀、双头刃剑与适配插入栓 | [Rainbow_Slakot `EVA-02 (rebuild version, not rigged)`](https://sketchfab.com/3d-models/eva-02-rebuild-version-not-rigged-4d715f56f7aa4f4cbed9703bc02a7171)，CC Attribution | **身体 mesh 明确排除**，只提取 1,032 三角刀、2,224 三角专武和插入栓模块；插入栓被缩放/换轴并补原创舱门以适配 Tiger 背部入口。仅本机评估，公开发行仍需署名及整体 EVA 二创合规复核 |
| Rei Chikita / EUD 本地参考文件 | 用户手动下载 | 已被 `.gitignore` 的 `/*.jar` 规则拦截，永不提交。Rei Chikita 只作为 SmOd 缺失时的本机 fallback/参考；EUD 1.1.0 清单标注 **CC BY-NC 4.0**，含驾驶服、LCL、三枪与 EVA 遗迹结构，但无可驾驶 EVA 模型；公开改用前仍联系作者确认署名方式 |
| 朗基努斯之枪本机附件（`tools/make_downloaded_eva_accessories_pack.py`） | EUD 1.1.0 的 Blockbench 方块模型与贴图 | 转换为 384 三角、独立 `longinus_lance` 附件，初号机/零号机使用双手前后握持；生成到本机资源包。公开发行前确认 EUD 作者署名，并遵守其清单所列 CC BY-NC 4.0 |
| 零号机本机头部模型（`tools/make_eud_eva00_pack.py`） | EUD 1.1.0 的 `eva00structure.nbt` 零号机头部雕塑 | 与 Project SEELE 原创可动画身体组合，仅本机测试；公开发行前确认 EUD 作者署名，并遵守 CC BY-NC 4.0 |

`run/` 已 gitignore，上表资产不会进入版本库与发行物。

## EVA 模型升级候选（2026-07-07 调研，尚未采用）

| 候选 | 技术情况 | 授权/下一步 |
|---|---|---|
| SmOd `EVANGELION: END ADDON V1.0` | Bedrock 1.21 addon，含 Unit-01/02 与动画；Bedrock geometry 可转换为 GeckoLib；目前仅保留为参考，不再覆盖 Tiger 身体 | Planet Minecraft 未列开放许可证；必须先联系 SmOd 获得移植与再发布许可 |
| BROWNCOAT `EVANGELION UNIT ONE` | Sketchfab 25.7k 三角面、未绑定骨骼；细节高但不能直接用作 GeckoLib 方块模型 | 页面标注 CC BY；仍需重新拓扑、绑定和制作 Minecraft 贴图，并登记署名 |
| PurpleGreenCream `EVA 01 (2022)` | 原生 Blockbench 长方体模型，最接近本项目技术路线 | 页面标注 CC BY-NC-SA；需联系作者索取源文件并确认 mod 再发布方式 |
| EUD 1.1.0 Forge 1.20.1 | 已下载官方文件并逐项审计；实际 jar 只有驾驶服、长枪、NPC 与 EVA 遗迹结构，没有页面所称的 EVA 实体模型/动画 | 不作为 EVA 模型来源；文件仅留在 `run/third_party/` |
| Tigerar1 [`Evangelion Unit-00`](https://sketchfab.com/3d-models/evangelion-unit-00-abe48f0c88914d66b7a5c916704767b3) | Sketchfab，3.7k 三角面，适合作为低多边形零号机重拓扑参考 | 已由用户下载并进入本机评估管线；CC BY-SA 4.0，发布时必须完整署名并以兼容方式共享改编模型 |
| Tigerar1 [`Mass Production Evangelion`](https://sketchfab.com/3d-models/mass-production-evangelion-a483209197814af99fc536b396813698) | Sketchfab，约 5k 三角面，比方块回退模型更接近 EoE 轮廓 | 已由用户下载并进入本机评估管线；CC BY-SA 4.0，正式打包仍需完成署名/ShareAlike 审核 |
| solodovnykov [`Sachiel - Evangelion`](https://sketchfab.com/3d-models/sachiel-evangelion-3c212c7ce6ac4284a8b718078bc6fc0f) | Sketchfab，524.7k 三角面/UDIM，细节很高但必须大幅减面 | CC BY 4.0；下载要求登录，作为后续高模烘焙候选，不直接塞入 Minecraft |

SmOd addon 已由用户下载为仓库根目录 `evaaddon1-0.zip`（被 `/*.zip` 忽略）。`tools/make_smod_model_pack.py` 可生成仅限本机测试的 Unit-01/02 GeckoLib 覆盖包；生成物和源素材均不得提交或发布。

## Local Tigerar1 Unit-01 evaluation (2026-07-12)

- Source: [Tigerar1 Evangelion Unit-01](https://sketchfab.com/3d-models/evangelion-unit-01-9fddeb0a7143436598c805dab2f147bf), user-downloaded OBJ and texture.
- Page licence: CC BY-SA; the converted art remains CC BY-SA and is not part of the MIT code licence.
- Local archive: `external-assets/incoming/evangelion-unit-01.zip` (Git-ignored).
- Converter: `tools/make_tiger_unit01_pack.py`; output is written only under the ignored `run/resourcepacks/eva_real_model/` tree.
- Current result: 3,789 source vertices / 4,226 triangles, mapped to 27 runtime mesh parts after the real finger and ankle splits. The `foot_l` / `foot_r` split preserves the source triangle count; non-mesh attachment bones are additional to the body contract. This is a rigid visual prototype, not release-approved art, and the poses still require in-game human review.

## Local Tigerar1 EVA variant evaluation (2026-07-12)

All archives and generated geometry below are Git-ignored. The converter code
may be distributed with Project SEELE, but the converted art remains under its
source licence and is outside the repository's MIT code licence.

| Target | Source and page licence | Local conversion state |
|---|---|---|
| EVA Unit-00 | [Tigerar1 Evangelion Unit-00](https://sketchfab.com/3d-models/evangelion-unit-00-abe48f0c88914d66b7a5c916704767b3), CC BY-SA | Downloaded OBJ; 3,120 vertices / 3,692 triangles; 27-part local pack generated. The finger/ankle splits preserve all triangles and pass offline contract validation; seams and animation feel remain blocked on an in-game visual pass. |
| EVA Unit-02 | [Tigerar1 Evangelion Unit-02](https://sketchfab.com/3d-models/evangelion-unit-02-a8731145a84f4e63b0fbc51f4f5948da), CC BY-SA | Downloaded OBJ; 3,384 vertices / 3,952 triangles; 27-part local pack generated. The finger/ankle splits preserve all triangles and pass offline contract validation; seams and animation feel remain blocked on an in-game visual pass. |
| Mass Production EVA | [Tigerar1 Mass Production Evangelion](https://sketchfab.com/3d-models/mass-production-evangelion-a483209197814af99fc536b396813698), CC BY-SA | Downloaded OBJ; 3,392 body + 1,509 wing triangles imported. The 440-triangle weapon lying at world origin is excluded. A 16-bone local rig carries gameplay `idle_1` / `move` / `attack`, explicit ritual, held Visual-Lab attack and folded revive animations. EUD's local replica lance is now rendered by the offline matrix; the ready pose removed a detected 26-pixel idle penetration. The five-state runtime matrix remains pending. |
| Positron rifle | [Kantrophe Positron Rifle](https://sketchfab.com/3d-models/positron-rifle-neon-genesis-evangelion-523e4d5b344543aa97b21e885f9dc064), CC Attribution | Download contains Blender 3.04 source and 4K PBR textures only. Portable Blender 3.6 exported and decimated 56,614 source triangles to 20,381; the 5,990-triangle ground cradles are excluded, leaving a 14,391-triangle local cannon. The axis/pivot correction passed an in-game Tigerar1 attachment capture; the two-hand support pose remains under Visual Lab review. |

`tools/make_tiger_eva_variants_pack.py` writes each EVA target incrementally
and never clears the active resource pack. During development its `--output`
must point at an ignored staging pack until the matching renderer and Visual
Lab batch have passed. `tools/render_tiger_variant_rig_preview.py` provides
deterministic four-view identity/stress checks without starting Minecraft.
