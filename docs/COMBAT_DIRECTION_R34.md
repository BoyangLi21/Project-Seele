# R34：已被用户否定的候选战斗版本

2026-09-24：用户观看制作过程后再次明确否定：EVA 与使徒倒地像僵尸，根本问题是整体战斗逻辑。**停止把 R34 候选作为交付对象，尚未正式安装 R34 动作集、打包、提交或推送。** 下述内容是实验记录，不能作为完成说明。后续重做需统一动作、受力、倒地碰撞和恢复状态，并先用完整双方交战证明方向成立。

R33 已被用户明确否定：出拳拘谨，上下半身像分别播放，使徒像木桩，攻击声音与暴走吼声不符合预期。R33 的数值检查通过不代表视觉或听觉质量被接受。

本轮重做对象是实际可操作的 EVA 与使徒交战；不是把一个固定演出视频当作操作体验。保留 R33 已独立交付的两分钟机库维修和黑色实体转移架。

## 参考及落实

- Netflix Anime 官方 TV 片段：[Unit 01 Awakens](https://www.youtube.com/watch?v=BYqWmWIatRI)。浏览器中确认发布者为 Netflix Anime，观察了躯干前压、近身抓压、机体与对手接触的画面。该片段是力天使战，不能当成水天使战的逐帧复刻证据。
- Netflix Anime 官方 TV 片段：[Fighting in Perfect Sync](https://www.youtube.com/watch?v=j_0aBLn-FUI)，作为连续动作与距离变化的进一步参考入口。
- TV 第 2 话公开节选：[EmmaCutVerse](https://www.youtube.com/watch?v=8xh1Tya4R9A)。非官方剪辑，仅用于动作观察，不打包影视画面。
- [圣莫尼卡战斗设计师 Denny Yeh：首场 Boss 战制作](https://blog.playstation.com/2018/08/16/fighting-a-god-behind-the-scenes-of-god-of-wars-first-boss-battle/)。重点采用敌人受击、被打退、脱离连击后重组攻势的设计；不将不可操作的镜头剪辑冒充战斗。
- [GDC：God of War Animation Bootcamp](https://www.gdcvault.com/play/1025836/Animation-Bootcamp-God-of-War)。动作设计应从角色性格、体态和动作目的出发，而不是泛用拳击片段直接套模型。

原先 khara 官方公开的第 2 话 YouTube 视频已转为私享，未声称看过该失效链接。EvaGeeks 与部分 Reddit 视频遇到访问验证，未绕过验证，也未将搜索摘要当作已经看过的连续视频。

## 动作架构

- 新动作由整套骨架、实体前进距离、每只脚的离地/着地时间共同组成。
- 取消 R33 在整段拳击中把两只脚钉在原地的规则。迈出的脚可以离地；承重脚才保留世界位置约束。
- 普通攻击依次采用跨步横击、转体直击、宽幅横扫；重击有高举、下压、后续收势。伤害判定沿实际手部路径扫过。
- 五套 EVA 骨架分别求解真实膝/肘关节，保持肢段长度；不扩大骨骼或缩放模型来制造动作幅度。
- 水天使使用专门的距离决策与移动循环，接近、侧移、后撤、反击和出招恢复连续发生。真实受击仍扣血并触发反应，不用永久霸体掩盖木桩问题。
- 普通角色受击累积的失衡阈值 2.25 → 3.20，防止每几拳就躺地数秒。重击仍可击倒。拳击基础伤害 20、重击基础伤害 35 不变。
- 普通攻击基础时长 24/27/29 → 23/25/27 tick，同步率加速上限仍为 1.08；重击时长维持 R33 的 34 tick 基准。

## 声音来源

以下为实录/录音编辑素材，作者页面均为 CC0 1.0；只做裁剪、变速、滤波及叠层，没有随机噪声或振荡器合成：

| 内容 | 来源 |
|---|---|
| 拳击瞬态 | [qubodup — Punch](https://freesound.org/people/qubodup/sounds/482134/) |
| 真实挥击 | [qubodup — Whoosh](https://freesound.org/people/qubodup/sounds/60013/) |
| 金属与混凝土接触 | [rifualk — iron hitting concrete](https://freesound.org/people/rifualk/sounds/613466/) |
| 重型金属冲击 | [magnuswaker — Heavy Metal Impact 2](https://freesound.org/s/614063/) |

本地另有 [TODDYN 上传的 5.28 秒 EVA Unit 01 Roar](https://tuna.voicemod.net/sound/46e80a30-57f0-4b20-8788-9c4e4d44da35)，作为用户要求的实素材吼声试听包，仅单声道转换和淡入淡出。**上传者未提供已核实的影视母带授权，TV 日语版本身份也未独立确认，不能标为官方原声或 CC0。** 此文件不进入开源 Git 仓库。

当前工具无法把音频作为可听输入返回给本代理，因此不声称已经耳听确认原剧一致性或主观听感。会提供可直接试听的文件与实机声音记录给用户判断。

## 实际验证

正式世界 `SEELE_R31_WORLD` 不作方块或玩家数据修改。候选动作先在 `SEELE_FIELD_R31_REVIEW` 中使用真实驾驶输入与主动使徒 AI 连续交战；记录双方位置、伤害、出招与实际渲染帧。Blender 检查图只用于看模型，不标为游戏截图。最终部署与验收记录在完成后补充。
