# Project SEELE — Motion Database Audit R01

Retrieval date: 2026-08-26

## Decision snapshot

| Source | Current role | Licence evidence | Distribution / training conclusion |
|---|---|---|---|
| [100STYLE](https://www.ianxmason.com/100style/) | Primary locomotion candidate | Official page states CC BY 4.0; [Zenodo record](https://zenodo.org/records/8127870) also records CC BY 4.0 | Over four million frames, 60 fps, one actor, and matched forward/backward walk/run, side locomotion, idle and transition files for every style. Best current structure for locomotion Motion Matching. |
| [ACCAD Open Motion Project](https://accad.osu.edu/research/motion-lab/mocap-system-and-data) | First unarmed-combat supplement | Official page applies CC BY 3.0 to the Open Motion Project | Official downloads include Male 2 BVH plus 21 kicks, 15 punches, 15 stances and 22 martial-arts walks/turns. Modification and redistribution are permitted with attribution and modification notice. Frame rate and C3D solve quality remain per-package QA items. |
| [CMU Graphics Lab Motion Capture Database](https://mocap.cs.cmu.edu/) | Selected transitions, obstacles, recovery and interaction only | [Official FAQ](https://mocap.cs.cmu.edu/faqs.php) | The FAQ permits copying, modification, redistribution and embedding in products, while prohibiting direct resale of the data even after format conversion. It does not expressly discuss ML training, so ML use remains unverified and must not be inferred from the reuse clause. |
| [Quaternius Universal Animation Library 2](https://quaternius.com/packs/universalanimationlibrary2.html) | Import/viewer/runtime placeholder only | Official page states CC0 | 130+ FBX/GLB animations with a universal humanoid rig. Useful for pipeline and CI testing, but its stylised authored motion is not biomechanics evidence and cannot approve final EVA movement. |
| [HDM05](https://resources.mpi-inf.mpg.de/HDM05/index.html) | Non-core supplemental candidate | Official page states CC BY-SA 3.0 | Legally usable with attribution and ShareAlike isolation, but not selected for the first production corpus because 100STYLE + ACCAD + exact CMU trials cover the first milestones with a simpler provenance chain. |
| [Adobe Mixamo](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) | Prototype/reference only | Official FAQ allows royalty-free use in games | Raw animation redistribution and open-source source-asset publication are not established by the FAQ. Do not make it the main distributable database without written clarification. |
| [Epic Game Animation Sample](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine) | System-design reference | Epic documentation | Excellent reference for motion matching, trajectory queries, Choosers, capsule movement, warping and leg IK. Do not migrate its animation content into Minecraft until an official licence explicitly permits that use. |
| [Reallusion / ActorCore](https://www.reallusion.com/Content/EULA/EULA.htm) | Rejected for open database and ML | Reallusion Content EULA, updated 2025-08-01 | EULA prohibits redistribution, embedded application content and machine-learning use. Not suitable for Project SEELE’s open asset pipeline. |
| [LaFAN1](https://github.com/ubisoft/ubisoft-laforge-animation-dataset) | Research/evaluation only | CC BY-NC-ND 4.0 in official repository | Contains excellent obstacle, fall/get-up, aiming and combat coverage, but adapted material may not be shared. Do not ship retargeted derivatives. |
| [AMASS](https://amass.is.tue.mpg.de/license.html) | Research/evaluation only | Official non-commercial research licence | No third-party distribution and no modification/availability without permission. Cannot be an open distributable source. |
| [Rokoko Motion Library](https://www.rokoko.com/products/motion-library) | Unverified marketplace candidate | Marketplace page located; per-asset redistribution evidence not yet verified | Do not download into the production corpus until each asset’s licence and source redistribution terms are recorded. |
| [JLPM22 MotionMatching](https://github.com/JLPM22/MotionMatching) | Architecture/code reference only | Repository code is MIT | The implementation may be studied or adapted with its MIT notice. Sample motion data and the separate 2025 EMM dataset are not inherited by the code licence; neither enters the public motion corpus without its own verified rights record. |

## Verified GPT-5.6 Pro decision

The completed independent review was read in full on 2026-08-26 and its new
claims were checked against primary pages before adoption. The production
decision is now **one primary, two supplements, one placeholder**:

1. `100STYLE` is the only primary locomotion/control distribution, under a
   strict style allowlist.
2. `ACCAD` is the first public unarmed-combat and combat-footwork supplement.
3. Exact `CMU` trials fill specific stop, turn, terrain, obstacle, jump and
   paired-interaction gaps. There is no CMU whole-library import.
4. `Quaternius UAL2` exists only to test FBX/GLB import, root/no-root handling,
   the viewer and CI. It is never final-motion evidence.

The following must be recorded or authored specifically for Project SEELE:
directional falls and recovery, paired grappling, progressive knife work,
two-hand rifle handling, long-spear/Lance handling, berserk quadrupedal motion,
and body/environment destruction contacts.

### Evidence checked after the Pro response

- ACCAD's official page names all five required packages, exposes direct ZIP
  downloads, and applies CC BY 3.0 to the Open Motion Project. Its official PDF
  indexes confirm the stated 21/15/15/22 kick/punch/stance/walk-turn counts.
- Quaternius' official UAL2 page identifies CC0, FBX/GLB/Blend formats and 130+
  animations. The free export and paid/source-kit split does not change the
  stated CC0 licence, but only the freely obtained files may be assumed present.
- The JLPM22 code repository is MIT and provides trajectory matching,
  inertialization and foot-locking architecture. Its sample motion data and the
  separate Environment-aware Motion Matching dataset require independent data
  provenance; code permission is not data permission.
- All CMU trial identifiers listed below were compared against the official
  subject catalogue. The catalogue reports 120 fps for these exact trials.
  Notably, `10_01-03`, `10_05-06` and `11_01` are **soccer ball kicks**, not
  martial-arts kicks; they are biomechanics/reference candidates only.

The verified ACCAD seed is now reproducible with
`tools/fetch_accad_eva_motion_seed.ps1`. Its private manifest is
`external-assets/incoming/mocap/accad-eva-seed-r01/manifest.json`: five official
archives, 149 BVH files and 82 C3D files, with archive/file SHA-256 hashes,
official index PDFs and licence snapshots. It remains external-3D input, not a
runtime pack.

### ACCAD ingestion probe

The Male 2 BVH files declare approximately `30 fps`; the C3D package timing is
still validated per file. Official clips now detected as useful vertical-slice
references include `C1 StandToRun`, `C2 RunToStand`, `C11/C14 RunTurn90`,
`B9/B12 WalkTurn90` and the explicit martial-arts turn/footwork files.

ACCAD's unconventional BVH rest axes initially produced `62–128 degree` chain
errors through the generic retargeter. A source-profile correction now builds
the body basis from evaluated hip/head landmarks and solves every arm/leg chain
in world space; the pre-contact chain-direction audit reaches `0 degrees` on
the `C1` probe. The canonical review rig also now separates an unskinned
`world_root` from the anatomical pelvis, so contact repair cannot rewrite the
authoritative trajectory.

The clip is still not accepted. Exact foot locking on the long-proportioned EVA
requires up to roughly `52 degrees` of leg-chain deviation; shifting the pelvis
by as much as about `0.23 BH` still leaves roughly `37 degrees`. This is a hard
rejection and evidence that a weighted full-body contact/COM solve is required;
two-bone IK or large pelvis translation is not a production repair.

## Corpus isolation and release policy

The corpus is physically and logically split into:

```text
third_party_raw/
third_party_normalized/
project_mocap_raw/
eva_authored/
runtime_database/
research_reference_not_for_release/
provenance/
qa_reports/
```

Raw files are immutable. Every derived clip must trace to source URL, creator,
retrieval date, original filename, SHA-256, licence URL, allowed uses and every
normalization/retarget revision. CI must reject release assets with an
unverified licence, NC/ND source, missing hash or missing derivation chain.

`tools/validate_motion_source_manifest.py` now enforces the file path, byte
count, SHA-256, licence and required provenance fields. A strict-release audit
of the 66-file 100STYLE allowlist and all five ACCAD archives/extracted
inventories passes with zero failures or warnings; the report is
`artifacts/motion_research/MOTION_SOURCE_PROVENANCE_AUDIT_R01.json`.
Human-readable attribution and modification obligations are maintained in
`docs/THIRD_PARTY_MOTION_NOTICES.md`.

Research-only data (HiPHI, LaFAN1, OmniContact, AMASS/BABEL, Bandai Namco,
SFU and MoVi) stays outside Git and outside any reversible release cache.
Mixamo, ActorCore, Rokoko, MoCap Online and Epic sample animations do not enter
the public corpus. Epic/JLPM22 implementations may be studied as architecture.

## Production database boundaries

There is no single global search pool. Runtime data is compiled into these
semantic domains:

- `MM_LOCOMOTION`;
- `MM_COMBAT_UNARMED`;
- `MM_TRAVERSAL`;
- `MM_KNOCKDOWN_RECOVERY`;
- `MM_WEAPON_KNIFE`, `MM_WEAPON_RIFLE`, `MM_WEAPON_SPEAR`;
- `MM_BERSERK_QUADRUPED`.

Cross-domain changes require an explicit transition clip/window. Weapon stance,
biped/quadruped support, planted contact, obstacle envelope and non-interruptible
strike/landing/grab windows are hard filters, not soft pose-search costs.

The first implementation is deterministic Pose Search with contact metadata,
inertialization, bounded warping and IK repair. Learned motion matching is
deferred until that database passes repeatable kinematic and semantic QA.

## Why 100STYLE is the locomotion primary

100STYLE was designed as a continuous locomotion/style dataset rather than a
catalogue of unrelated trials. For each style, one actor records forward and
backward walking/running, side-step walking/running, idle and transitions. This
provides the neighbouring poses and transitions required by Motion Matching.

The first local seed contains the complete official `Neutral` set:

- `Neutral_ID`, `FW`, `FR`, `BW`, `BR`, `SW`, `SR`, and `TR1`;
- `Dataset_List.csv` and `Frame_Cuts.csv`;
- official page licence evidence and a SHA-256 manifest.

Local manifest:

`external-assets/incoming/mocap/100style-neutral-r01/manifest.json`

Nothing in this seed is a runtime asset yet. Neutral is a biomechanics baseline;
EVA style selection and retarget review remain separate gates.

### First direct-retarget gate

The source files were analysed at their native 60 fps before retargeting:

- `Neutral_FW`: 268 stable cycles within the official cut; selected
  frames `2719–2768`, source speed about `0.886 m/s`;
- `Neutral_FR`: 121 stable cycles; selected frames `1951–1980`, source speed
  about `1.517 m/s`.

Both were retargeted through the existing Blender anatomical EVA rig and the
pinned Rokoko add-on, without GMR, MuJoCo or robot proxy data.

- Walk chain direction median/max error: `2.15° / 6.14°`;
- Run chain direction median/max error: `2.61° / 5.80°`;
- Walk facing/velocity median dot: `0.983`;
- Run facing/velocity median dot: `0.970`;
- The original walk passed the earlier `0.15 BH/s` fixed-vertex gate but did
  not meet the Pro review's stricter `0.02 BH/s` production target;
- the original run failed across five candidate cycles. Root-motion scaling
  alone could not satisfy both feet.

The rebuilt canonical review rig now separates `world_root` from the anatomical
pelvis. Source-contact leg IK, a bounded reach/COM pelvis adjustment and swing
foot ground clearance were then applied without changing `world_root`:

- walk planted-foot P95: approximately `0.0000296 / 0.0000175 BH/s`;
- run planted-foot P95: approximately `0.0000256 / 0.0000458 BH/s`;
- walk chain direction median/max: approximately `2.18 / 11.00 degrees`;
- run chain direction median/max: approximately `2.61 / 6.33 degrees`;
- no missing target contact pairs in either clip;
- maximum pelvis correction is about `0.013 BH` for walk and `0.022 BH` for
  run; the authority world root is unchanged.

Both clips therefore pass the current **kinematic candidate** gate. They are
not final assets until interactive 3D aesthetic review, loop-seam review and
multi-entry/multi-exit transition tests pass.

Review assets:

- `artifacts/motion_research/100style_neutral_retarget/neutral_walk_review_6s.mp4`;
- `artifacts/motion_research/100style_neutral_retarget/neutral_run_review_6s.mp4`;
- corresponding `.blend`, chain audits and contact-manifold audits in the same
  private research directory.
- canonical world-root candidates and strict audits:
  `artifacts/motion_research/100style_worldroot_retarget/`, notably
  `EVA_100STYLE_NEUTRAL_WALK_CLEARANCE_R10.blend` and
  `EVA_100STYLE_NEUTRAL_RUN_M01_R07.blend`.
- six-second synchronized front/side/back review loops:
  `artifacts/motion_research/100style_worldroot_review/neutral_walk_review_6s.mp4`
  and `neutral_run_review_6s.mp4`.

### 100STYLE ingestion allowlist

The first-wave families are deliberately narrow:

- `Neutral`: `ID/FW/FR/BW/BR/SW/SR/TR1`;
- `StartStop`: `ID/FW/FR/BW/BR/SW/SR/TR1`;
- `SpinClock` and `SpinAntiClock`: `ID/TR1/TR2/TR3`;
- `Rushed`, `BentForward`, `BentKnees`, `OnToesBentForward` and
  `OnToesCrouched`: `ID/FW/FR/SW/SR/TR1`;
- `ShieldedLeft` and `ShieldedRight`: `ID/FW/FR`;
- `TwoFootJump`: `ID/FW/FR/TR1`.

`Punch_*` may inform moving attack posture but is not punch ground truth.
`Robot_*`, `DuckFoot_*`, `PigeonToed_*`, `Penguin_*` and other comic/imitation
styles are excluded from production ingestion and retained only as negative
regression examples.

The allowlist is reproducible with
`tools/fetch_100style_eva_allowlist.ps1`. The private manifest at
`external-assets/incoming/mocap/100style-eva-allowlist-r01/manifest.json`
contains 64 BVH files plus the two official metadata CSV files (about 248 MB),
all checked against their recorded SHA-256 hashes. These files are candidates,
not accepted runtime motions.

### Predatory-sprint vertical-slice probe

Four official-cut forward-run families were measured at source fps. Representative
stable-cycle median speeds were approximately `1.30 m/s` (`BentForward`),
`1.48 m/s` (`BentKnees`), `1.73 m/s` (`OnToesBentForward`) and `2.36 m/s`
(`Rushed`). `Rushed_FR` frames `984-1013` are the first predatory-sprint probe;
this is a candidate choice, not an aesthetic acceptance.

Direct retargeting failed contact QA: planted-foot slide P95 was about
`0.542 BH/s` left and `0.295 BH/s` right. A source-contact-driven two-bone leg
IK pass, with world foot orientation/ground alignment and **no root translation
rewrite**, reduced those values to about `0.000070 BH/s` and `0.000627 BH/s`,
with no missing contact pairs and a facing/velocity median dot of `0.933`.

The repaired clip remains pending because its maximum source/target leg-chain
direction deviation reaches about `34.85 degrees` during the planted foot roll.
That contact/pose tradeoff must be reviewed and refined before the clip can be
promoted. Evidence is stored under
`artifacts/motion_research/100style_allowlist_retarget/`.

## Why CMU remains the first supplement

CMU is not automatically the most stylish source, but it combines clear official
reuse permission, 120 Hz source data and broad transition/interaction coverage.
The official catalogue includes:

- Subject 16: run, jump, walk and sudden stops;
- Subject 56: locomotion/upper-body transition vignettes;
- Subject 91: walks and turns;
- Subject 127: action-adventure running, quick stops, turns and obstacles;
- Subject 128: running, ducking, rolling and stopping;
- Subject 140: get-up motions from prone, side and supine positions;
- Subject 144: blocks, kicks, lunges and punch sequences;
- Subjects 2 and 14: strike, swordplay and boxing.

The official FAQ also warns that quality and classification are not guaranteed.
Every clip therefore remains a candidate until the 3D and contact gates pass.

### CMU exact-trial allowlist

The Pro list was checked against the official subject catalogue. It is an
inspection queue, not an automatic acceptance list:

- stop: `16_08`, `16_57`;
- 90-degree walk turns: `16_17-20`, `16_27-30`;
- 90-degree jog/run turns: `16_41-44`, `16_51-54`;
- jump/leap: `13_10-13`, `13_19`, `13_32`, `16_01-10`, `49_04-05`;
- stairs/uneven ground: `13_35-38`, `36_16-37`;
- step stool/obstacles: `40_06-09`, `41_07-09`, `54_20-22`;
- punch/boxing: `02_05`, `13_17-18`, `14_01-03`, `17_10`;
- kick references: `10_01-03`, `10_05-06`, `11_01` (officially labelled
  soccer-ball kicks; never silently relabel as combat);
- long-object rhythm only: `02_07-09` (officially swordplay);
- paired pull/resistance: matching subject-A `18_03-06` and subject-B
  `19_03-06`.

Each trial must be viewed on its original skeleton before retargeting. Paired
trials must preserve their shared time base and contact anchors.

## Minimum clip schema

Every normalized clip must contain at least:

- source dataset, asset/trial ID, source URL, original filename, SHA-256 and
  retrieval date;
- licence ID/URL, creator/attribution and modification history;
- source/runtime fps, duration and loopability;
- source/target skeleton profiles and retarget revision;
- semantic domain/action/direction/speed/posture/stance/lead foot/turn angle,
  support mode, weapon and EVA style strength;
- root mode, average speed in body-heights per second, yaw delta, pelvis/COM
  height statistics;
- contact events and segments;
- allowed transition windows and interruption class;
- foot/hand/weapon/obstacle constraints;
- measured quality values, threshold version and pass/fail status.

The common event vocabulary is:

```text
L/R_FOOT_STRIKE  L/R_FOOT_FLAT  L/R_TOE_OFF
L/R_HAND_CONTACT L/R_KNEE_CONTACT FOREARM_CONTACT BODY_CONTACT
WEAPON_CONTACT GRAB_ATTACH GRAB_RELEASE
TAKEOFF APEX LAND SLIP_START SLIP_END
OBSTACLE_ENTER OBSTACLE_EXIT WARP_BEGIN WARP_END
IMPACT RECOVERY_READY
```

Pose-search features include root trajectory, pelvis/COM, local positions and
velocities of both feet/hands/head (plus knees/elbows for traversal/berserk),
future trajectory samples at `+0.2/+0.4/+0.7/+1.0 s`, contact/phase/lead-foot,
stance/weapon/support mode, obstacle envelope and interruption semantics.

## Retarget and repair order

1. Record provenance and store immutable raw data.
2. Apply official frame cuts and remove preparation/T-pose tails.
3. Normalize coordinates and scale to one body height; preserve the conversion
   matrix.
4. Build a separate source profile containing hierarchy, rest pose, axes,
   rotation order and scale.
5. Extract planar world root and yaw from hips while retaining pelvis height and
   local tilt.
6. Detect and repair contacts at source fps before runtime resampling.
7. Solve pelvis/COM, feet and hands with IK and explicit knee/elbow planes; do
   not copy Euler channels bone by bone.
8. Apply the EVA style layer only after contacts are locked, then solve contacts
   again.
9. Mark transition, inertialization and bounded warp windows.
10. Export glTF/Blender review data, runtime binary and human-readable
    provenance/semantics/QA reports.

Contact repair exposes `REPORT_ONLY`, `ROOT_AND_PELVIS` and `FULL_BODY_IK` modes
and logs the magnitude of every modification. Motion warping is limited to its
declared window, normally at most 10–15% translation/reach and 15–20 degrees of
yaw; otherwise a different clip is required.

## Automatic acceptance thresholds (v1)

All values are measured in body-height (`BH`) space before mapping to the
24-block visual scale:

- planted-foot accumulated horizontal drift `< 0.005 BH`; primary locomotion
  target `< 0.003 BH`;
- planted-foot speed P95 `< 0.02 BH/s`;
- maximum ground penetration `< 0.002 BH`; `> 0.004 BH` or more than two
  consecutive frames is a hard failure;
- `FOOT_FLAT` mean hover `< 0.002 BH`;
- automatic contact events within one source frame of human reference;
- no joint-limit violation; knee/elbow reverse extension over 3 degrees fails;
- loop effector seam `< 0.005 BH`, key-bone rotation seam `< 3 degrees`, root
  speed mismatch `< 5%` and compatible support phase;
- turn-in-place heading error `<= 2 degrees` and root translation `<= 0.01 BH`;
- moving-turn heading error `<= 3 degrees` and exit path error `<= 0.01 BH`;
- transition key-point RMS `< 0.015 BH`, key-bone rotation RMS `< 8 degrees`,
  with zero planted/swing conflict;
- locomotion inertialization normally `80–160 ms`, combat `40–80 ms`, never
  across a core strike/contact frame;
- non-contact obstacle clearance `>= 0.02 BH`, climb hand target error
  `<= 0.01 BH`, landing target error `<= 0.015 BH`;
- weapon/body penetration outside a storage pose is a hard failure.

Numerical gates cannot approve aesthetics. Every clip still requires human
review of pelvis initiation, thorax/scapula lag, foot progression, readable
anticipation/commit/follow-through, giant-scale consequence, weapon mass and
support-driven falls/recovery.

## First ten vertical slices

Implementation order is fixed until the base system works:

1. EVA alert/breathing idle;
2. forward walk;
3. forward jog/run;
4. forward-leaning predatory sprint;
5. idle to sprint start;
6. sprint to hard stop;
7. moving 90-degree left/right turns;
8. in-place 180-degree left/right turns;
9. forward jump with low/medium/heavy landings;
10. directional hit imbalance to forward fall to prone recovery.

The straight punch is slice 11. Combat cannot conceal an invalid root, COM,
contact, turn, landing or recovery foundation.

## Downloaded provisional seed

Reproducible downloader:

`tools/fetch_cmu_eva_motion_seed.ps1`

Private local output:

`external-assets/incoming/mocap/cmu-eva-seed-r01/manifest.json`

The seed contains three ASF skeletons and twelve AMC clips. The manifest records
the official URL, role, byte count and SHA-256 for every file, plus a local copy
of the official FAQ licence evidence. It is deliberately stored outside the mod
and is not yet a runtime asset.

## Stop-investing list

- G1 robot motions as EVA visual locomotion;
- automatic mapping from an arbitrary humanoid skeleton without bind-axis tests;
- one looping walk/run clip per speed;
- Minecraft as the first visual review environment;
- paid marketplace content whose raw redistribution cannot be proven;
- research-only datasets as shippable source material;
- “weight” implemented as uniform slow playback or vertical bob;
- clip playback without root trajectory, contacts and transition metadata.

## Next audit gate

The independent Pro review is complete. The next gate is empirical, not another
broad search: ingest the verified ACCAD packages and the first 100STYLE allowlist
families, generate side-by-side source/retarget/contact reports, and accept one
vertical slice at a time. A source recommendation without an official download
URL, exact licence, concrete motion identifier and reproducible hash cannot enter
the corpus.

## Rejected grounded locomotion checkpoint (2026-08-26)

The first Minecraft-facing `BentKnees` replacement was isolated to the motion
lab and then rejected by human visual review. It never replaced campaign
locomotion and its commands are now quarantined.

- Source: 100STYLE `BentKnees_FW.bvh` frames 1654–1741 and
  `BentKnees_FR.bvh` frames 603–662, from the strict CC-BY-4.0 allowlist.
- Period selection now uses full-body pose recurrence across 18 joints. The
  previous heel-height detector had admitted half-steps as complete cycles.
- Mean lateral lean is -0.455 degrees for walk and +0.464 degrees for run; the
  former run candidate had a fixed approximately 12-degree right lean.
- Contact IK uses no pre-contact reach. That prevents the knee from being
  pulled nearly straight before foot strike; an explicit 0.99 leg-extension
  cap holds maximum knee angles near 163 degrees in both walk and run.
- Pelvis load response is approximately 0.008 BH for walk and 0.029 BH for run.
- Exact rigid-foot runtime contact gates pass for both clips.
- Blender-to-runtime roundtrip: all measured limb-chain direction errors are
  0 degrees; root-relative joint-position P95 is below 0.0003 model units.
- Source-world heading is removed at export: runtime travel has X=0 and the
  first-frame root yaw is approximately 1.1 degrees (walk) / 3.7 degrees
  (run), preventing the earlier backwards or diagonal locomotion failure.
- Human verdict: walk looked crouched, exhausted and upper-body paralysed;
  run read as the same gait played faster. Passing contact/roundtrip metrics
  did not make either motion semantically correct.
- `grounded_walk` / `grounded_run` command routing was removed immediately.

The remaining visible cycle endpoint mismatch is 14.02 degrees (walk) and
11.98 degrees (run), both lower than the ordinary contact-transition maximum.
It is left unforced because the naive zero-seam correction breaks planted-foot
contact. Runtime inertialization masks the small residual while a later
contact-constrained periodic solve is developed.

### ACCAD semantic replacement candidate R31

R31 replaces the rejected style source with explicit natural locomotion:

- walk: ACCAD `Male2_B3_Walk.bvh`, frames 235–356;
- run: ACCAD `Male2_C3_Run.bvh`, frames 11–34;
- walk minimum arm-swing range `0.390 H`, thorax/pelvis counter-yaw range
  `23.55 degrees`, zero mean lateral bias and `3.85-degree` centered P95;
- run minimum arm-swing range `0.303 H`, mean elbow angles about
  `85/89 degrees`, counter-yaw range `31.97 degrees` and zero mean bias;
- the redundant per-frame ACCAD root-basis correction was removed. Walk root
  angular-speed P95 fell from `6329` to `69.8 deg/s` and its rotation seam
  from `169` to `1.17 degrees`; run fell from `1875` to `101 deg/s` and from
  `76.6` to `2.79 degrees`;
- leg IK and contact root warping are not present in this visual candidate;
  original hip/knee/upper-body curves remain intact;
- R31 is rejected. Its fixed-camera three-view silhouette hid a coordinate-
  basis failure that became obvious in game: the final walk/run foot-swing
  axes were `49.05/44.12 degrees` left of EVA forward, foot ordering reversed
  in about `42%` of samples, and the knee lateral/sagittal bend ratio reached
  `2.07`. Mean-lean correction could not make that motion valid.

### ACCAD heading-normalized replacement R32

The ACCAD source clips are valid and straight relative to the performer, but
their capture-world travel headings are `-45.41/-46.49 degrees`. The rejected
retarget copied source-world leg directions into a target pelvis that remained
on canonical +Y. R32 rotates the complete source authority onto target +Y
before retargeting any chain; it does not patch the resulting EVA angles.

- Blender target walk/run travel error: `0.000/0.000 degrees`;
- Blender target foot-swing error: `0.120/1.957 degrees`;
- Blender target foot-order reversals: `0%`;
- Blender target knee lateral/sagittal bend ratios: `0.09–0.24`;
- final Gecko foot-swing error: `0.344/2.425 degrees`;
- final Gecko foot-order reversals: `0%`;
- final Gecko knee bend ratios: `0.09–0.24`.

R32 replaces R31 in the live EVA-00/01/02 resource pack and still requires the
next in-game human review. Configured sprint-key reconciliation and the
head-first/rate-limited chassis turning changes remain active. A rejected
distance-phase controller quantized the otherwise smooth render-clock motion
and was removed after the first R32 game test. Walk/run use Gecko's native
render interpolation again. The base controller uses its stable two-tick
transition, and an already-active walk/run returns `CONTINUE` without calling
`setAnimation` again. Selection changes are logged once with sprint, movement,
airborne, speed and visual-pose evidence for the next game review.

That log exposed the autonomous-run reset: the motion-lab director set sprint
`true`, then the generic no-passenger cleanup set it `false` in the same tick.
Selection alternated `run(5) -> walk(6)` about every 50 ms. Tagged motion-lab
units now use a separate synchronized autonomous-running field rather than
borrowing pilot sprint at all, so generic cleanup and the director cannot
write the same state. A synchronized lab-active flag also supplies the dummy
airframe's control circuit without inventing a passenger. Client locomotion
now latches RUN across six release ticks and while measured speed remains in
the run band, so one late data sample cannot restart the loop before its second
footfall. Jump phase is monotonic (`ascending -> descending -> grounded`), and
moving touchdown skips the full-body stationary landing clip using both actual
velocity and current pilot movement intent. Forward locomotion can therefore
no longer be composed with a stationary recovery pose.

### Ordinary unarmed attack R19 rejected experiment

The procedural `claw_strike` body motion remains rejected. ACCAD Male-2
`E1 JabLeft` and `E4 CrossRight` were retargeted on the current rig, resampled
to 60 Hz, fitted with DFKI-referenced anatomical fists, and joined with
contact-aware stance steps. The experiment passed the old pivot/contact gates
but failed human review for two independent reasons:

1. the sport-boxing 1-2 is the wrong default vocabulary for an EVA;
2. evaluated mesh surfaces show the shin/foot seam growing by about
   `0.050/0.056 H`, while the underlying endpoints remain connected.

The right ankle reaches roughly `130 degrees` relative to the first frame.
R19 is permanently excluded from runtime. The seam failure is now a mandatory
mesh-level gate for every retarget and transition. Full evidence and exact
timing remain in `docs/EVA_ORDINARY_ATTACK_RESEARCH_R01.md`.

### Original-aligned combat expansion R01

Combat research no longer treats the punch catalogue as the default action
identity. The adopted free-combat grammar starts with ward/deflection, body
entry, push kick or two-hand control, then branches from real target contact.
Punches remain valid as committed brawl, grapple or mounted impacts rather than
a repeating sport-boxing neutral loop. Forward pounce is a distinct
launch/contact/landing action, and recognisable Angel encounters use separate
paired or multi-actor finisher graphs.

The reproducible source fetcher
`tools/fetch_eva_original_combat_seed.ps1` added 38 CMU candidates with hashes,
official catalogue snapshots and licence evidence. The first original-skeleton
screen produced:

- 16 source shortlists;
- four pounce trajectory/contact references;
- three aerial-kick references;
- eight paired pull/resistance captures awaiting shared-space review;
- two contact-repair-required candidates and four source rejects;
- one broad sequence retained only for segmentation/reference.

Important exact candidates include CMU `18/19_03-06` for paired resistance,
`49_04-05` and `127_23-24` for pounce ordering, `90_05-07` for aerial-kick
reference, `135_04`, `144_06` and `144_09` for supported front kicks, plus
selected `144` block/reach/lunge captures. None is an accepted EVA motion.

The complete action grammar, original encounter mapping, finisher queue and
quality contract are in `docs/EVA_ORIGINAL_COMBAT_MOTION_PLAN_R01.md`.

### Original-aligned physical-rig checkpoint R01

The first candidates have been solved directly onto the 41-DOF R03 ball-joint
physical skeleton at 60 Hz. This is an offline kinematic reference stage, not
reinforcement-learning progress and not a runtime controller.

The initial audit was incomplete: it measured horizontal support drift but did
not measure absolute sole height. A strict recheck found hovering/penetration
and withdrew the old passes. After explicit full-source height normalization,
action-window segmentation and offline vertical free-root grounding:

- ACCAD `Male2_G18_PushKickRight` frames 23–48 is the only current full pass;
  marker, articulation, planted-patch speed/drift, sole clearance,
  penetration, root-step and tangent-step gates all clear;
- left/right wards still trade foot constraints against pose/transition error;
- ACCAD B18 frames 40–91 remains a useful launch reference, but its new
  grounding/contact-speed gate is not yet clear; frames 92–93 remain rejected;
- synchronized CMU `18_05/19_05` frames 165–219 still closes the shared
  hand/elbow envelope, but both actors fail the new grounding gate. The
  remaining pull capture is not played after attachment; resistance and
  release belong to a compliant physical grip.

The machine-readable combat graph now contains 13 action nodes and 21
conditional edges. Nine Angel-specific interaction graphs specify contact
anchors, entry conditions and abort paths for Sachiel, Israfel, Sahaquiel,
Shamshel, Gaghiel, Bardiel, Zeruel, Arael and Leliel. They are design contracts,
not copied official animation or accepted runtime content.

Exact metrics and rejected variants are recorded in
`docs/EVA_COMBAT_PHYSICAL_RETARGET_R01.md`.

### CMCD CC BY 4.0 combat supplement

The official Cologne Motion Capture Database was added as a second openly
licensed combat source. `tools/fetch_cmcd_eva_combat_seed.ps1` downloads eight
private candidates and records hashes plus the official CC BY 4.0 evidence.

- one forward jumping-kick capture passes as an aerial reference after fixing
  the source auditor to select a foot event during measured two-foot flight;
- the 2018 paired clip contains a long two-hand contact exchange suitable for
  hand-fighting/attach research, but its database label also includes a
  handshake, so it is not treated as impact ground truth;
- the 2019 paired clip contains a brief kick-to-hand proximity event only;
- roll, hit/fall and ape-fight material remains reference or negative-example
  data, not production motion.
- CMCD Nussknacker3 frames 340–390 is the first low-line right-kick shortlist.
  ACCAD G8 is explicitly not a low-reap source: its measured swing height is
  about `0.714 H`, so retaining it under that label would corrupt semantics.

This preserves a clean licence path without lowering the semantic or contact
gate merely because a dataset is legally usable.

### Expanded CMU paired interactions

CMU subjects 20–23 add higher-value shared-contact semantics: two-person whip,
two-hand shoulder control, stumble/body collision, arm wrestling, assisted
get-up and shelter/support. The downloader now records 54 total CMU clips.
Shared-space audits confirm sustained contacts rather than trusting catalogue
labels. The preferred new windows are listed in
`tools/eva_paired_interaction_source_catalog_r01.json`; all remain source
references until grounded paired retarget and physical-constraint tests pass.
