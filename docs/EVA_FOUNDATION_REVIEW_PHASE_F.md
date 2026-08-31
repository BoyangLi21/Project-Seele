# EVA 六基础动作 Phase F 人工验收

状态：**自动门禁通过，仅具备人工审查资格；尚未视觉批准**。

Phase F 使用实际 Minecraft framebuffer 和 PoseGraph 提交后的最终骨矩阵，录制
Unit-01 的六个基础垂直切片：idle、walk、run、jump + landing、徒手攻击和
Progressive Knife 攻击。walk/run 使用真实骑乘输入，jump/攻击使用正式
`ServerboundEvaControlPacket`，Motion Lab 不直接写动作状态或 EVA 世界变换。

## 候选资产

- Tiger 外壳仍为 43 个单骨刚性 part、6,044 个三角面；
- weighted inner 为 23 骨、19 个胶囊、4,652 顶点、9,300 三角面；
- inner topology 为单组件、0 非流形边、Euler=2；
- 体素分辨率由 0.20 提高到 0.12 格；
- root 变换原点不再生成错误的可见 root-to-pelvis 胶囊；
- 肩/上臂/前臂与骨盆/髋使用分段半径，避免手—腿空间邻近造成错误混权；
- 每段绝大部分由 parent bone 控制，仅末端 12% 进入 child transition，再沿
  manifold 表面做 160 轮局部 geodesic 权重扩散并截取前四权重；
- LBS 后有统一的有界 orientation correction。它不写骨、不按动作名分支；
  Phase-F 录制峰值为 `0.001970478` 模型格，即机体高度的 `0.0166%`。

冻结基线的 `land` 会在恢复段让左手穿过左胫。Phase-F 候选只保留 land 的
root、torso_upper 和双腿八个通道，并相对首尾轨迹把 root 冲击压到 55%、
躯干压到 70%、下肢压到 65%。`eva_approved_actions.json` 因此正确把
`jump_landing` 标记为 `CANDIDATE_HASH_CHANGED`；其他五个切片仍保持冻结
基线。该候选只有人类接受后才能晋升。

## 自动证据

最终捕获 batch：`20260831-211450`。

```text
actions=6
views=3
framebuffer_frames=912
front_geometry_frames=304
runtime_inverted_triangles=0
runtime_collapsed_triangles=0
nonlocal_self_intersection_samples=83 (all pass)
self_intersection_local_exclusion=6 topology hops
maximum_runtime_offline_bounds_delta=3.0408e-6
maximum_orientation_correction_height_fraction=0.00016594
worst_seam_minimum_growth_height_fraction=0.00893392
worst_seam_contact_band_p05_growth_height_fraction=0.01099160
worst_clearance_p95_drop_height_fraction=0.01544864
worst_clearance_p95_drift_height_fraction=0.02169856
result=ELIGIBLE_FOR_HUMAN_REVIEW_ONLY
```

刚性铰链允许接触点沿装甲表面滑动。seam 门禁因此检查最近接触与前 5% 接触
带，而 P95 外弯开口只作为诊断数据保留。自交检查排除同一关节补丁内不超过
6 个网格边跳的局部面；这些局部面由 orientation/collapse 门禁负责，所有更远
的手穿胸、肢体互穿等仍执行精确三角形相交否决。

动作真实性同时由以下数据否决静止假捕获：walk 前进 `26.7368` 格，run 前进
`38.7646` 格且服务器 sprint=true，jump 垂直范围 `37.5752` 格并观察到 airborne，
徒手/粒子刀最终骨矩阵均有非零变化，武器分别为 fists/knife。

## 人工验收包

```text
D:\eva\artifacts\motion_research\eva_foundation_manual_review_phase_f\20260831-211450
D:\eva\artifacts\motion_research\eva_foundation_manual_review_phase_f\20260831-211450.zip
```

总视频为 `00_EVA_FOUNDATION_PHASE_F_ALL_ACTIONS.mp4`，1920×360、20 FPS、
304 帧、15.2 秒。每帧三栏依次为正面、侧面、背面。

右下角红色 `动作号-帧号` **只表示时间顺序**：数字小的更早，数字大的更晚；
它不是模型几何、贴图、游戏 UI，也不是骨骼或关节标记。反馈时应直接引用如
`04-021`。

人工需判断重量、发力顺序、轮廓、走跑差异、起跳/落地恢复、攻击回收、握刀、
装甲开缝和是否像 EVA。自动系统无权输出 `VISUALLY_APPROVED`。

## 复现

```powershell
py -3 tools\build_eva_manifold_inner_body.py
py -3 tools\validate_eva_phase_e_manifold.py
py -3 tools\validate_eva_phase_f_foundation.py
.\gradlew.bat runClient -PstrictHighDetail=true `
  -PquickPlayWorld=SEELE_EVA_MOTION_LAB `
  -PfoundationVideoCapture=true -PmanifoldInnerPreview=true `
  -PvisualCaptureUnit=unit01 `
  '-PvisualCapturePose=idle,walk_contact,run_contact,live_jump,live_melee,live_knife'
py -3 tools\audit_eva_foundation_capture.py `
  --batch run\screenshots\projectseele_foundation\20260831-211450
py -3 tools\build_eva_foundation_review_package.py `
  --batch run\screenshots\projectseele_foundation\20260831-211450
```
