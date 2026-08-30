# Project SEELE — EVA real-human combat and posture runtime R05

Status: **R04 visual acceptance is revoked. The R05 exact-preview atlas fix is
retained, but its Longinus action is withdrawn from the in-game review. Low
stance, prone, crawl and their transitions remain pending human acceptance.**

## Current human-review scope

The R05 Longinus action was withdrawn from the in-game Motion Lab at the
user's request on 2026-08-30. It remains research history only and is not part
of the current acceptance pass. The lab weapon mask and command parser both
reject the lance slot so it cannot be selected accidentally. Launch the
remaining actions directly into `SEELE_EVA_MOTION_LAB` with
`START_EVA_ACTION_REVIEW.bat` or `tools/start_motion_lab.bat`.

The same review rejected the live three-stage fist layer and all authored
crouch/prone connector clips. The three ACCAD strikes remain selectable only
through `motionlab demo`; live left-click returns to the Tiger-specific
alternating strikes with input buffering. Crouch and prone now switch directly
between their persistent poses and collision dimensions without playing
stand/crouch/prone transition animations.

The 2026-08-28 in-game review rejected the original CMU 02 weapon clips and
the ACCAD kneel/prone/crawl chain. R02 replaced the weapon and crouch subset;
R03 added a complete UT Dallas prone capture and re-solved rifle contact. R04
then used the second CMU crouch trial and a Motion-X++ staff capture, but its
review video paired a 1024x512-atlas mesh with a 256x256 texture. That video
could not validate either the model or the motion. R05 makes this mismatch a
hard error and uses the accepted ACCAD CrossRight capture for a one-handed
Longinus jab. No R04 low-stance visual claim survives this correction.

## Promoted capture windows

| Runtime action | Source | Source frames | R02 use |
|---|---|---:|---|
| Progressive Knife light | ACCAD Male2 E6 HookRight | 16–56 | right-hand horizontal cut |
| Progressive Knife heavy | ACCAD Male2 E4 CrossRight | 5–45 | committed straight thrust |
| Longinus ready | ACCAD Male2 E4 CrossRight | 5 | one-handed diagonal guard, left hand free for balance |
| Longinus thrust | ACCAD Male2 E4 CrossRight | 5–45 | captured hip/shoulder drive aligned to the right-hand lance socket |
| stand to crouch | CMU 136_09 Walk Crouched | 51–230 | continuous standing-height to low stance |
| crouch idle | CMU 136_10 Walk Crouched | 169 | settled low stance hold |
| crouch walk | CMU 136_10 Walk Crouched | 121–241 | in-place crouch gait loop |
| stand to prone | UT Dallas MCP_prone01 | 100–340 | continuous full descent |
| crouch to prone | UT Dallas MCP_prone01 | 180–340 | low-stance descent |
| prone idle | UT Dallas MCP_prone01 | 384–416 | belly-down hold loop |
| prone crawl | UT Dallas MCP_prone01 | 1602–1676 | in-place belly crawl loop |
| prone to crouch | UT Dallas MCP_prone01 | 1760–1895 | continuous low get-up |
| prone to stand | UT Dallas MCP_prone01 | 1760–2000 | complete standing recovery |

ACCAD is CC BY 3.0. CMU reuse follows the official database terms. The
existing accepted berserk subset remains unchanged: CMU 54_13 and 120_02 plus
CMCD `KingKong2` under CC BY 4.0. The UT Dallas Motion Capture Database archive
publishes `MCP_prone01` under CC BY 4.0. The Motion-X++ staff derivative is
non-commercial ShareAlike material under CC BY-NC-SA 4.0 and is not relicensed
as MIT code.

The tracked deterministic runtime overlay is
`tools/eva_real_mocap_accepted_r02.json`. It replaces 20 weapon, crouch, prone,
crawl, transition and solved prone-rifle animations. The rejected
`tools/eva_real_mocap_weapon_contacts_r01.json` is deleted and remains
available only in Git history.

## Retarget and contact rules

1. Accepted human motion is retained at 60 Hz for exact review and exported to
   Gecko at 30 Hz.
2. Root height is exported as a real root position channel. The crouch no
   longer bends its knees while leaving the pelvis at standing height.
3. Crouch idle and crouch walk remove captured horizontal travel before loop
   closure. Entity movement remains gameplay-authoritative, while first/last
   root position and joint rotations close without a visible snap.
4. Knife light/heavy use the already reviewed ACCAD hook/cross body captures.
   The 26 visible Tiger finger controls retain the solved native-thumb
   opposition; the empty `thumb_tip` sockets are not treated as visible mesh.
5. Longinus thrust is a one-handed spear jab, matching the readable semantics
   of a trident attack. The ACCAD CrossRight capture supplies the foot load,
   hip/shoulder turn, extension and recovery; the lance remains on the native
   right-hand socket. An exact-mesh socket pass rotates the lance about that
   grip onto the EVA forward axis and then restores palm/surface contact. The
   left hand is not forced onto the shaft.
6. Crouched knife and Longinus actions reuse only the accepted upper-body
   weapon layer over the accepted CMU low stance.
7. Exact body grounding changes root height only. The UTD source-level pass
   needs at most `0.175315 m` of clearance. After the captured transition is
   matched to the Gecko stance edges, crouch-to-prone receives at most
   `0.244307 m` and prone-to-crouch `0.015788 m` of root-only lift; captured
   joint rotations remain unchanged.
8. The prone-rifle overlay is solved again on the accepted UTD body. The
   cannon socket is translated onto the trigger hand, the bore is aligned to
   runtime forward, and the support arm is solved to the fore-end with
   two-bone IK. The solved overlay is exported into the deterministic patch,
   rather than existing only in a Blender review file.
9. CMU 136_09 remains only for stand/crouch transition timing. Crouch idle and
   gait use 136_10; their captured lower body is combined with a symmetric
   forward low guard so neither hand crosses behind the EVA. A final composed
   IK pass places the left/right ankles on opposite sides at `-18/+18` model
   pixels instead of accepting the crossed retarget result.
10. Positional mocap has no captured finger articulation. Low stances install
    a compact native-thumb-aware curl after retargeting so Tiger's long finger
    plates do not fan into a false detached-mesh silhouette.

## Rejected and deliberately unpromoted

- Tuffles sword clips: running, leaping or dance-like motion rather than
  self-contained knife attacks.
- Bandai `slash_normal_001/002`: the source rest skeleton could not be
  transferred to the Tiger hierarchy without inverted leg chains.
- SFU Kendo: stable two-hand sweep, but not a Longinus thrust.
- ACCAD A7/A8/A10/A11 low chain: A7 is a one-knee kneel, while the prone and
  crawl endpoints do not form a coherent tactical chain on the Tiger rig.
- SFU `0007_Crawling001`: clean short portions exist, but longer cycles mix
  side support, kneeling and rolling; the short loop still reads as an arched
  side crawl on EVA proportions.
- CMU 111_03: crawling on knees, not prone locomotion.
- The first indexed UT Dallas archive request returned a truncated 1 MiB
  response and was rejected. The complete archived package endpoint was then
  recovered and produced a valid `2,862,144`-byte FBX. Only that complete,
  hash-recorded source is used.

## Gameplay scope

Input bindings, state switching, damage, cooldown, reach, AOE and server
authority are unchanged. R04 changes only client-side animation resources and
fills the posture clips already addressed by the existing stance controller.

Ignored review artefacts are under
`artifacts/motion_research/eva_action_r02_direct/` and
`artifacts/motion_research/eva_action_r03_utd_prone/`. Source and licence
notices remain in `docs/THIRD_PARTY_MOTION_NOTICES.md`; R04 reviews are under
`artifacts/motion_research/eva_action_r04_semantic_fix/`.

## Final local gates

- body low-stance audit: **not accepted**; numerical `14/0` from R04 is not a
  visual pass and must not be quoted as one;
- Longinus ready/thrust: exact runtime mesh and correct 1024x512 atlas reviewed
  as a one-handed guard/jab; forward-axis cosine is at least `0.999780` and
  right-hand surface distance is at most `0.12` Blender units. No false
  left-hand contact gate is applied;
- exact prone-rifle audit: right-hand surface distance at most `0.0000015`,
  left-hand distance at most `0.053818`, forward-axis cosine at least
  `0.999660`;
- every promoted loop and stand/crouch rotational and root-position seam is
  within `0.01` degrees/pixels;
- local high-detail pack validation, weapon-system contract, berserk contract,
  Python compilation, `git diff --check` and `gradlew build` pass;
- `runClient` logs Project SEELE initialization, ordinary attack runtime
  `3 clips / 50 bones / 243 frames`, all three local EVA triangle meshes, and
  no Project SEELE error/fatal line.

Review videos:

- weapon/crouch: `artifacts/motion_research/eva_action_r02_direct/EVA_R02_ACCEPTED_WEAPON_CROUCH_REVIEW.mp4` (`431` frames);
- UTD prone/crawl/rifle: `artifacts/motion_research/eva_action_r03_utd_prone/EVA_R03_UTD_PRONE_CRAWL_RIFLE_FINAL.mp4` (`236` frames, `15.73 s`).
- R04 final exact-resource review is invalid because it used the wrong body
  texture dimensions. The corrected model-only baseline is
  `artifacts/motion_research/eva_action_r04_semantic_fix/correct_runtime_atlas/EVA_IDLE_RUNTIME_MODEL_CORRECT.mp4`.
