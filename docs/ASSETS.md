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
| EVA-01/02、量产机、Sachiel、Israfel 本机高精资源包（`run/resourcepacks/eva_real_model`，由两个 `make_smod_*_pack.py` 脚本生成） | SmOd `EVANGELION: END ADDON V1.0`（Planet Minecraft / Bedrock addon），作者 SmOd774YT，未列开放许可证 | **当前本机测试主模型来源**。仅本地测试，包内含 `_SOURCE.txt` 免责声明。**公开使用前必须取得作者许可**；生成脚本入库，模型产物永不入库 |
| Rei Chikita / EUD 本地参考文件 | 用户手动下载 | 已被 `.gitignore` 的 `/*.jar` 规则拦截，永不提交。Rei Chikita 只作为 SmOd 缺失时的本机 fallback/参考；EUD 1.1.0 清单标注 **CC BY-NC 4.0**，含驾驶服、LCL、三枪与 EVA 遗迹结构，但无可驾驶 EVA 模型；公开改用前仍联系作者确认署名方式 |

`run/` 已 gitignore，上表资产不会进入版本库与发行物。

## EVA 模型升级候选（2026-07-07 调研，尚未采用）

| 候选 | 技术情况 | 授权/下一步 |
|---|---|---|
| SmOd `EVANGELION: END ADDON V1.0` | Bedrock 1.21 addon，含 Unit-01/02 与动画；Bedrock geometry 可转换为 GeckoLib；当前本机测试优先使用 | Planet Minecraft 未列开放许可证；必须先联系 SmOd 获得移植与再发布许可 |
| BROWNCOAT `EVANGELION UNIT ONE` | Sketchfab 25.7k 三角面、未绑定骨骼；细节高但不能直接用作 GeckoLib 方块模型 | 页面标注 CC BY；仍需重新拓扑、绑定和制作 Minecraft 贴图，并登记署名 |
| PurpleGreenCream `EVA 01 (2022)` | 原生 Blockbench 长方体模型，最接近本项目技术路线 | 页面标注 CC BY-NC-SA；需联系作者索取源文件并确认 mod 再发布方式 |
| EUD 1.1.0 Forge 1.20.1 | 已下载官方文件并逐项审计；实际 jar 只有驾驶服、长枪、NPC 与 EVA 遗迹结构，没有页面所称的 EVA 实体模型/动画 | 不作为 EVA 模型来源；文件仅留在 `run/third_party/` |
| Tigerar1 [`Evangelion Unit-00`](https://sketchfab.com/3d-models/evangelion-unit-00-abe48f0c88914d66b7a5c916704767b3) | Sketchfab，3.7k 三角面，适合作为低多边形零号机重拓扑参考 | CC BY-SA 4.0；下载要求 Sketchfab 登录，当前未下载。采用时必须署名并以兼容方式共享改编模型 |
| Tigerar1 [`Mass Production Evangelion`](https://sketchfab.com/3d-models/mass-production-evangelion-a483209197814af99fc536b396813698) | Sketchfab，5.3k 三角面，比当前方块回退模型更接近 EoE 轮廓 | CC BY-SA 4.0；下载要求登录，当前优先使用本机 SmOd 版本 |
| solodovnykov [`Sachiel - Evangelion`](https://sketchfab.com/3d-models/sachiel-evangelion-3c212c7ce6ac4284a8b718078bc6fc0f) | Sketchfab，524.7k 三角面/UDIM，细节很高但必须大幅减面 | CC BY 4.0；下载要求登录，作为后续高模烘焙候选，不直接塞入 Minecraft |

SmOd addon 已由用户下载为仓库根目录 `evaaddon1-0.zip`（被 `/*.zip` 忽略）。`tools/make_smod_model_pack.py` 可生成仅限本机测试的 Unit-01/02 GeckoLib 覆盖包；生成物和源素材均不得提交或发布。
