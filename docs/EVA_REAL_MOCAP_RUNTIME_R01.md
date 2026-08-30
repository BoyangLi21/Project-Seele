# Project SEELE — EVA real-human combat and posture runtime R03

Status: **R03 weapon, crouch, prone, crawl and posture-transition captures
passed exact-mesh review; the final client-load review is recorded below**.

The 2026-08-28 in-game review rejected the original CMU 02 weapon clips and
the ACCAD kneel/prone/crawl chain. R02 replaced the weapon and crouch subset;
R03 adds a complete UT Dallas prone capture and re-solves the rifle contact.
Neither revision repairs rejected body motion with hand-authored poses.

## R02 promoted capture windows

| Runtime action | Source | Source frames | R02 use |
|---|---|---:|---|
| Progressive Knife light | ACCAD Male2 E6 HookRight | 16–56 | right-hand horizontal cut |
| Progressive Knife heavy | ACCAD Male2 E4 CrossRight | 5–45 | committed straight thrust |
| Longinus thrust | ACCAD Male2 E4 CrossRight | 5–45 | full-body drive plus exact two-hand shaft solve |
| stand to crouch | CMU 136_09 Walk Crouched | 51–230 | continuous standing-height to low stance |
| crouch idle | CMU 136_09 Walk Crouched | 211–260 | settled low stance loop |
| crouch walk | CMU 136_09 Walk Crouched | 911–1055 | in-place tactical crouch gait loop |
| stand to prone | UT Dallas MCP_prone01 | 100–340 | continuous full descent |
| crouch to prone | UT Dallas MCP_prone01 | 180–340 | low-stance descent |
| prone idle | UT Dallas MCP_prone01 | 384–416 | belly-down hold loop |
| prone crawl | UT Dallas MCP_prone01 | 1602–1676 | in-place belly crawl loop |
| prone to crouch | UT Dallas MCP_prone01 | 1760–1895 | continuous low get-up |
| prone to stand | UT Dallas MCP_prone01 | 1760–2000 | complete standing recovery |

ACCAD is CC BY 3.0. CMU reuse follows the official database terms. The
existing accepted berserk subset remains unchanged: CMU 54_13 and 120_02 plus
CMCD `KingKong2` under CC BY 4.0. The UT Dallas Motion Capture Database archive
publishes `MCP_prone01` under CC BY 4.0.

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
5. Longinus uses the accepted right-cross drive, keeps its shaft on the EVA
   forward axis and solves the left clavicle/upper-arm/forearm chain against
   the exact animated lance surface. No child-limb translation is introduced.
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
authority are unchanged. R03 changes only client-side animation resources and
fills the posture clips already addressed by the existing stance controller.

Ignored review artefacts are under
`artifacts/motion_research/eva_action_r02_direct/` and
`artifacts/motion_research/eva_action_r03_utd_prone/`. Source and licence
notices remain in `docs/THIRD_PARTY_MOTION_NOTICES.md`.

## Final local gates

- exact body audit: knife `2/0`, Longinus `1/0`, crouch chain `3/0`, final UTD
  prone/crawl/rifle review `8/0` (clips/failures);
- exact Longinus audit: right-hand surface distance at most `0.000001`,
  left-hand distance at most `0.017129`, forward-axis cosine at least
  `0.999780`;
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
