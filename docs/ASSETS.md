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
| `sounds/rifle_fire.ogg` | EVA 帕雷特步枪 | 原创合成：机械枪机、爆音噪声与低频尾响，不含影视或现实枪械采样 |

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
| EVA-X / GeoFront 球体世界（用户下载的 `EVA.rar`） | Bilibili 分享存档；当前缺少可核验作者与再发布许可 | `prepare_local_map_assets.py` 只把该存档作为测量参考；新的 `SEELE_TOKYO3_REBUILT` 使用普通噪声地表与原创深埋球体。源文件、转换结构和存档全部 gitignored，作者身份与许可确认前绝不发布 |
| `Nerv Comand Module` 世界 | Planet Minecraft `nerv-comand-module`，用户手动下载；作者/许可信息待登记 | 本机转换为 NERV 指挥区并叠加原创四屏实时遥测；不进入 jar。发布前必须补齐项目链接、作者署名与明确授权 |
| `tokyo-3-type-skyscrapper1-converted.schem` | 用户手动下载的 Tokyo-3 高楼 schematic；作者/许可信息待登记 | 本机在东京-3 战区放置三座实例；结构和拼接存档均不提交。未获得授权时发布版使用原创回退楼群 |

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
| Pallet Rifle | [Oni Anniversary Edition community conversion](https://wiki.oni2.net/AE_talk%3ANew_weapons), provenance/redistribution permission not yet confirmed | Exact TV-style 167-vertex / 292-triangle OBJ and 1024x512 BMP are installed only under ignored external-assets/. tools/make_downloaded_pallet_rifle_pack.py is fingerprint-locked to that pair and emits a local-only runtime derivative. It must not ship until explicit author/licensor approval is recorded; the original 240-triangle MIT procedural rifle remains the distributable fallback. |
| Ultraman private avatar | User-supplied `ultraman-rig-updated.zip`; no licence or author metadata included | Local/private testing only. FBX contains a 54-bone Character Creator rig and 20,565 exported triangles. `tools/make_ultraman_avatar_pack.py` emits an ignored rigid-bone runtime derivative. Never publish or redistribute the source or derivative without provenance and permission. |


## Local Kiki260100 Lilith evaluation (2026-07-19)

- Source: [Kiki260100 `Lilith - Evangelion`](https://sketchfab.com/3d-models/lilith-evangelion-8203459ac3dc48e18bad7b2a6b46995f), downloaded manually by the user.
- Local archive: `external-assets/incoming/lilith-kiki260100.zip.zip`; GLB SHA-256 `6693b5ca325d6fa5c355152962e75cf50162266320a4519aab3130c2ecfef06c`.
- The downloaded archive contains only the GLB and two textures. No licence
  document is bundled, so this project treats the model as local evaluation
  material and will obtain explicit author approval before any release.
- `tools/make_lilith_model_pack.py` converts the GLB into six material layers
  inside the Git-ignored `run/resourcepacks/eva_real_model/` pack: body 11,814,
  eyes 1,540, face 322, mask 1,082, nails 448 and sealing spear 4,524
  triangles. The source cross material is deliberately excluded; Project
  SEELE retains its own pure-red block crucifix.
- Runtime height is 32 blocks and wrist span is approximately 42 blocks. The
  source body's front/side visual audit confirms the cross remains behind the
  body and the sealing spear extends toward the observation gallery.
- Converter, entity integration and clean-room fallback geometry may ship as
  code. The generated Kiki mesh/textures and source archive must never be
  committed or redistributed without permission.
`tools/make_tiger_eva_variants_pack.py` writes each EVA target incrementally
and never clears the active resource pack. During development its `--output`
must point at an ignored staging pack until the matching renderer and Visual
Lab batch have passed. `tools/render_tiger_variant_rig_preview.py` provides
deterministic four-view identity/stress checks without starting Minecraft.

## Local Entry Plug evaluation (2026-07-26)

- Exterior: [Crymsin `Entry Plug (Evangelion)`](https://www.thingiverse.com/thing:2501188),
  Thingiverse item 2501188, CC BY. The user-downloaded OBJ has 250,554 source
  triangles and five material groups.
- Cockpit reference: [DONW999 `Neo Genesis Evangelion Entry Plug Pilot Seat -
  The Soul Throne`](https://www.thingiverse.com/thing:4961673), Thingiverse
  item 4961673, CC BY. Its downloaded ZIP contains only `Stand.stl`, decals and
  render images; it does not contain the displayed chair/control meshes.
- `tools/make_entry_plug_model.py` cuts a physical hatch into the Crymsin
  pressure shell, decimates each material independently, then adds an original
  Project SEELE Soul-Throne-style seat, restraints, foot rests and two
  induction levers guided by the bundled DONW999 renders.
- The generated local contract is 14 x 58 x 14 model pixels, 11,670 triangles
  and three animated parts. It is written only to the ignored
  `run/resourcepacks/eva_real_model/` pack. Both source ZIPs and the derivative
  mesh remain local-only until release attribution and the wider EVA
  fan-work compliance review are complete.

## Open humanoid motion sources and animation references (2026-08-24)

| Asset | Licence and source | Project SEELE use |
|---|---|---|
| Quaternius Universal Animation Library Standard | [Official page](https://quaternius.com/packs/universalanimationlibrary.html), bundled `License.txt`: CC0 1.0; downloaded ZIP SHA-256 `CC73FC4E495B82958207316596317A3F40B9FA38065BDE1027937452DA537724` | 43 source actions were inventoried. Idle, walk, formal walk, jog, sprint, crouch, jump, punch, sword and firearm poses are clean-room retarget inputs. The raw ZIP/GLB remains under ignored `external-assets/`; the derived quaternion motion database may ship under the repository licence because the source is dedicated to the public domain. |
| Quaternius Universal Animation Library 2 Standard | [Official itch.io page](https://quaternius.itch.io/universal-animation-library-2), bundled `License.txt`: CC0 1.0; downloaded ZIP SHA-256 `4008EA208A604773A2B2177D965F0F5D3195498B5BF838C3F5785D68E95F2A68` | Adds hook punches, multi-stage sword attacks, dash, slide and ninja-jump references. Raw files remain ignored; selected derived clips are merged into `assets/projectseele/motion/eva_humanoid_v2.json`. |
| CMU Graphics Lab Motion Capture Database, subjects 02, 16, 22, 23, 54, 79, 80, 111, 120, 136 and 144 | [Official database](https://mocap.cs.cmu.edu/). The official FAQ explicitly permits copying, modification and redistribution without permission. ASF SHA-256: subject 02 `C9F5FF45B4437B279F58B95DACF017AFD3135373096274DF69436A9354D796CF`, subject 16 `2323F876564610F84BFBEC9B90B8EBFFB57515673B7F4A45B0FB0849AF465BDB`, subject 111 `8FE67A2163F1F70ED985E34ABE0E3FF4AF7F5DA76F2F3C178D59759CB18BBA16`. Phase-G review BVH SHA-256: `02_08.bvh` `9EB38F57C2D4AEDF00DA5A1700F134423AD5F3EE407E3AE1BDB00060569943D8`, `144_13.bvh` `0CC6D4BD771970FA1A07D33B8BF5E42F12E72E4EE9BD61AFECD53AC09D07CBE3`, `144_20.bvh` `D8E4025891F8FFC94FF53839525B0E71CFACD2CBEC30A181BD738EC8220CBFCE`. Phase-Q paired BVH SHA-256: `22_05.bvh` `742AD9875BFE1E8F192D3841A5F08B01447177B3386777FED0A2263AB08BD58F`, `23_05.bvh` `4E11A31FEFB9FC388231EB5E87BC166AFA99EF48B53CB27F848080821D829674`. | Subject 02 supplies sword/knife and staff-thrust mechanics; Phase G uses trial 08 strike 01/05 only. Subject 22/23 trial 05 supplies the synchronized body-entry, shoulder-control and target-reaction review for Phase Q. Subject 144 trial 13/20 supplies the isolated left/right unarmed candidates. Subject 54 supplies the promoted creature-roar pantomime, subject 120 the gorilla-style berserk run, and subject 136 the crouch walk. Subject 16 supplies locomotion transitions, subject 111 floor-motion references, and subject 80 trial 03 the Pallet Rifle torso/shoulder stance. Subject 79 trial 96 was screened but rejected as a rifle source. Raw ASF/AMC/BVH files remain ignored. |
| Rokoko free superhero and fight mocap packs | [15 free superhero animations](https://www.rokoko.com/resources/rokoko-mocap-15-free-superhero-animations) and [13 free fight animations](https://www.rokoko.com/resources/rokoko-mocap-13-free-fight-animations). Rokoko states that the full-body/finger recordings were captured with its motion-capture tools and may be used from passion projects through commercial projects. ZIP SHA-256: Superhero `B911E7B200C66916D812C2E9C392DF458C5CAE2C093D7D3CE832749D24AAAD72`; Combat `380C9854B4AC21DE8A2EE436AE3D2BBEF9AFDDB6AF3BC97345EEB49B93DE7CF8`. Selected FBX SHA-256: `IronMan_Combat_mixamo.fbx` `B7E47877D89EDCE72EB70C3A71EEC896C4CAE3A5C097E3DE62BFE04F6BD340B7`; `MutantClaws_mixamo.fbx` `10D01206DE575F4005D8BA5411FD70852CF41B377402143C4A7108F6986A7A85`; `KnifeFight_mixamo.fbx` `46E126F8407E84CEA105B05E94AF55BE4CE26073E089FE7C012466AA8FE5C027`. | Phase J tested `IronMan_Combat` frames 177–196, which were human-rejected, and preserved `KnifeFight` frames 464–523 after correcting their label to forward grip. Phase K replaces the ordinary attack with `MutantClaws` frames 778–792 and adds a geometry-solved reverse-grip copy of the knife motion. Raw ZIP/FBX files remain ignored. The derived databases are isolated, not live and not visually approved; promotion also requires a final redistribution/licence check. |
| Rokoko free sports mocap pack | [12 free sports animations](https://www.rokoko.com/resources/rokoko-mocap-12-free-sports-animations), supplied as full-body Mixamo FBX captures for project use. ZIP SHA-256 `536D63D5B11B3A9B6324868FA24960743A1727FF3EC2375BF1738C541C9578B0`; selected `Baseball_Pitcher_mixamo.fbx` SHA-256 `442DECD763BA305CF71DB5086A1E72C0B7C691EC0187AE578802F860BC17F5E9`. | Phase R uses three independent early pitcher takes only for their planted rear-foot, pelvis, thorax and single-arm overhand kinetic chains. Ball/throw semantics are removed; the derivative remains review-only until human inspection confirms it does not read as pitching. Raw ZIP/FBX files remain ignored. |
| G1 Moves MOVIN TRACIN mocap dataset | [Official Hugging Face dataset](https://huggingface.co/datasets/exptech/g1-moves) and [processing repository](https://github.com/experientialtech/g1-moves), CC BY 4.0. The dataset documents 59 MOVIN TRACIN markerless captures plus one separate video-derived clip; Phases T/U use only MOVIN-captured Karate clips. Selected BVH SHA-256: `M_Move11` `583EB124C05C6098187B5A663EFB1CDE5806B42A4296A1CD71EEEEE0F1113079`; `M_Move17` `9844E4BFC2CE05CA37C66BB4F563643B660AFDED1DFB9F4F3E9C46A5417B2628`; `M_ShortMove16` `BDEA1DC9969C20B264B8EAEB26338973B55C6E77AD1FDB2212D64C4EBBD1A14E`; `B_AttackKarate` `B76D5F5B2BA581E28ABC8C6DF620E1BC2011C073280A762A99DA024FD8687A24`; `M_Move10` `FADB13A4A2DCDD1C327E519210EFEE52334D191FCE29A32384BF71799102178E`; `M_Move18` `D5498405E8CD8A81FAD2D3B25826F30D3B203E7A87FB2BAB9888D5C6F888EB3E`; `M_ShortMove13` `AF02568686439170B64D2D0D008423E6F96FE7F8F6FD04FA9B9EF85AEF6604C1`. | Phase T C group was human-selected and promoted to the standing-fists left-click runtime at `1.5×`; A/B/D remain unselected. Phase U K1 side kick was selected and promoted to the standing-fists B-key runtime at `1.5×`; K2/K3 remain review-only. Raw BVH files remain ignored, and both live actions still require in-game visual approval. |
| Rokoko free zombie and Motion Library weapon mocap | [12 free zombie animations](https://www.rokoko.com/resources/rokoko-mocap-12-free-zombie-animations) and [10 free fight/weapon animations](https://www.rokoko.com/resources/motion-library-10-free-fight-and-weapon-animations). Zombie ZIP SHA-256 `1927FED3086ACDA527C7D5D968B2DDC7B388FBD01AB2F60E8A05D277F8280D9B`; `ZombieAttack_Walking_mixamo.fbx` `BAFC35FE2471124DB4ADBD98DAC7C8D743E7BAE79F3410D74D9D79E1D937989D`; `stabTwist_Knife` take 01 `81B8AFF94388353A65A9E67C1294E8F81A17982C2D4D4D73888907C8147CEA6C`; take 02 `CF37B6EE6E2957261321D8D6096E690AD604206F62F6CF9EAE499860B4773C7C`. | Phase L uses only Zombie frames 208–251 for a torso-led two-arm maul and two independent stab-and-twist takes for forward/reverse knife candidates. These replace, rather than repackage, the human-rejected Phase-K motions. Raw files remain ignored; the derived database is review-only and not visually approved. |
| Rapa Motion FREE Mudra anime mocap samples | [Official itch.io download](https://rapamotion.itch.io/mudra-samples), stated free for personal/commercial work with no credit required. ZIP SHA-256 `93FF6A966590975D8FE3A225778A2DAD5BB39C8BC9C84BA78478821BC235D7E7`; selected `AS_Anime_Rasengan_Attack_Ybot.fbx` SHA-256 `3B5C1060D0BF42FCD537DD707494564D20763EB967D1851FEDB903ABCA7386E9`; selected `AS_Anime_Chidori_Attack_02_Ybot.fbx` SHA-256 `4F003CE84948F5B3414ADAF22314AB52902ECA80F05DE2A6724A693D64944B0F`. | Phase M Rasengan and Phase N Chidori ordinary-attack derivatives were both human-rejected. Raw files and isolated negative evidence remain ignored/non-live; neither motion may be repackaged as an accepted attack. |
| Haley Tuffles Premade Mocap Pack | [Creator motion-capture page](https://haleytuffles.com/motioncapture); bundled `ReadME.txt` states free personal/commercial use and no credit requirement. The author records with iPiSoft and cleans in Blender. Selected `ArmsLariat.bvh` SHA-256 `EAE6D32AA4C9FAD0EADA1905182E5B2308FFB46B4C7F9E844048EACE8FA25A77`; `ArmsSlap.bvh` SHA-256 `82CB7AE1C23B4A7783F71CAD79F7F757649D3D957FA08E5913E4C5E2AFFF65CE`; `HurtPunchedStomach.bvh` SHA-256 `4CF814892ADF733300FB57C6DD07512AC9359B502E02A2C00EA100859173699A`; `PushedBackwards.bvh` SHA-256 `122D0C49F0EE5A6C65C36FC1F85E8544A26E918BADA2BD5370FCC75E0706964B`; `ReadME.txt` SHA-256 `0890A5A4F1C1F91732CA960B89758077B6867581762DF9DBECEB728633BC3C51`. | Phase O/P Lariat and slap derivatives were not accepted as ordinary attacks. Phase R uses only the hurt/backward takes as red target hit reactions, triggered on confirmed hits; they do not define the attacker motion. Raw files remain ignored and derivatives are non-live pending human review. |
| ACCAD Open Motion Project, Male-2 General Movements | [Official page](https://accad.osu.edu/research/motion-lab/mocap-system-and-data), CC BY 3.0. | Crouch idle, stand-to-crouch, crouch-to-lie, lie-to-crouch and crawl takes provide the real-human low-posture mechanics. Project SEELE trims, retargets, loop-closes and target-constrains the derivatives; raw BVH files remain ignored. |
| Cologne Motion Capture Database (CMCD), `KingKong2` | [Official licence page](https://mocap.web.th-koeln.de/about.php), CC BY 4.0. | Selected right/left creature swipes and a forward pounce supply the Unit-01 berserk body mechanics. The source remains human performance capture; Project SEELE performs axis normalization, Tiger retargeting and runtime constraint repair. |
| `amc2bvh` 0.1.0 | [Tom Copeland repository](https://github.com/thcopeland/amc2bvh), MIT | Local-only deterministic ASF/AMC to BVH conversion for Blender. The binary/source archive remains ignored; no executable is shipped in the mod. |
| GenoView Inverse Kinematics / Foot Locking | [Daniel Holden source](https://github.com/orangeduck/GenoView-InverseKinematics), MIT; article [Inverse Kinematics and Foot Locking](https://theorangeduck.com/page/inverse-kinematics-foot-locking) | Algorithmic reference for velocity-based contact annotation, shared-pelvis two-leg IK and offline contact locking. Project SEELE's implementation operates on its own EVA skeleton and data. |
| Motion Matching example | [Daniel Holden source](https://github.com/orangeduck/Motion-Matching), MIT | Reference architecture for trajectory features, database search, pose inertialization and contact fix-up. The external checkout is ignored; only independently adapted Project SEELE code may ship. |
| ozz-animation | [Official repository](https://github.com/guillaumeblanc/ozz-animation), MIT | Data-oriented sampling/blending reference. No native ozz binary is currently linked into Forge; the Java renderer follows its phase-synchronised local-pose blending principles. |

`tools/inspect_humanoid_motion_library.py` inventories source skeletons and
actions through the same Blender importer used by production.  The reusable
`tools/build_eva_motion_database.py` collapses the source spine/clavicle chains
onto the EVA hierarchy, calibrates against a standing idle rather than a
T-pose, changes coordinate systems, records 30 Hz normalized quaternions and
annotates left/right foot contact. No Evangelion animation, footage or official
asset is present in this database.

CMU trials are segmented by `analyze_bvh_locomotion.py`,
`analyze_bvh_jump.py` and `segment_bvh_combat_motion.py`.  Retargeted candidates
are built by `build_eva_cmu_motion_candidates.py`, then rejected unless both
`audit_eva_motion_database.py` and the exact-matrix Blender mesh audit are
green.  `refine_eva_motion_database.py` performs velocity-aware contact
annotation, fitted stride extraction, shared-root correction and two-leg IK;
`promote_eva_motion_candidates.py` refuses promotion from a failed audit.
