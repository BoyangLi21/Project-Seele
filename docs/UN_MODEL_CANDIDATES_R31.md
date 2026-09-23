# R31 UN 模型细化

来源是本机实际交付的 R30 双机主包。先在 `artifacts/facility_r31/models/un00|un01/runtime/assets/projectseele/` 制作和核对，再经原生复位、插入栓与俯卧运输检查安装到正式 `eva_real_model` 包。安装收据和逐文件逆向备份由 `tools/promote_un_models_r31.py` 生成，位于 `artifacts/facility_r31/models/promotion.json` 及其记录的备份目录。

先修骨归属，再加几何细节。按真实网格所有骨归属着色检查，R30 的两台机体都存在大腿前壳归到骨盆的问题，UN-00 另有肩柱前壳归到上臂。诊断抬臂、屈髋时，这些表面分别留在骨盆或随手臂横转。修复使用髋—膝轴附近的两侧腿壳包络、肩柱长轴包络，以及原有 owner/权重关系；中央裙甲和活动上臂仍保留各自归属。交界保留渐变权重。

`ownership_repair.json` 逐组记录旧/新 owner、源三角形索引区间、索引哈希、中立包络。单独修骨步骤三角形数量完全不变，中立位置最大误差约 `1.78e-15`；骨架 pivot、骨名、骨层级和原动作文件字节不变。实际运行时采用保体积蒙皮；离线 `ownership/*_flex_*.png` 使用线性权重的独立诊断姿态，用于查错，不能冒充实机战斗录像。

表面增加了闭合护板、倒角、固定件、前臂/背部百叶、手背护板和指节机械环。新护板的轮廓逐段落到真实身壳；射线表面池包含对应骨的加权接缝，防止板件或 UN 字样埋入另一层可见网格。肘膝环使用实际侧向三角形交点定位；没有有效接触面时不安装。眼睛、双侧飞行喷口、插入栓机构、手部基础几何和所有功能字段保留。黑金/绿蓝配色与 4K PBR 图不变。

最终数量与哈希以 `candidate_validation.json` 为准。两台候选约 49.6 万/44.6 万三角面；需要动态蒙皮的部分约 8.24 万/7.95 万，其他大件保留刚性 GPU 绘制。清掉小于百万分之一的无效余量权重，避免因为一条微小余量让整片大腿失去 GPU 缓存。

可复现工具：

- `refine_un_armour_r31.py --unit 00|01`：复制原包、修骨、加入真实几何细节，不接触主包。
- `repair_un_ownership_r31.py`：独立归属修复和逐面收据。
- `inspect_un_ownership_r31.py`，加 `--candidate` 看候选：实际骨归属及诊断弯曲图。
- `render_un_finish_r31.py --unit 00|01 --with-baseline`（Blender）：相同镜头的原包与候选，以及手部、背部近景。
- `validate_un_candidate_r31.py`：有限数、法线、UV、权重和、骨架及功能字段检查。
- `stage_un_models_r31.py`：输出独立 `run/resourcepacks/eva_un_r31_review` 与 `eva_body_r31_review.json` / `eva_dorsal_r31_review.json`，重算支持点、运输包络和兼容格式清单；不安装主包。

本轮改善的是具体错骨和机械细节，保留了生成底模的主要形体，尚不能宣称与概念图逐面一致或达到影视资产质量。安装同步更新模型清单、身体支持点和运输包络，原 NERV 骨架与动作深比较保持不变。两台原 UN 已完成原生蹲、趴、持枪与复位；UN-00 原机体完成俯卧横置空运，头部和支架使用实际绘制矩阵检查。其余战斗姿势和主观美术仍以人工验收为准。

`promote_un_models_r31.py` 是有边界的晋升工具，准备阶段不执行安装。没有 Minecraft JVM 时先 `--freeze` 固定已审阅源哈希，再使用 `--apply --evidence <真实 R31 mechanics pass.json>` 安装。它仅替换双机资源，并把 body 的 3/4 号配置和 dorsal 的 UN profiles 合并到正式文件；保留其他机体和动作的深比较结果，先备份再原子替换，最终写 `models/promotion.json`。任何源哈希变化、旧证据或活动 Minecraft JVM（包括 `client-*.args`）都会拒绝执行。
