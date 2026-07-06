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

`run/` 已 gitignore，上表资产不会进入版本库与发行物。
