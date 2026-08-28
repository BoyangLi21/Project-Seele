# Project SEELE — EVA real-human combat and posture runtime R02

Status: **R02 weapon and crouch candidates passed exact-mesh and client-load
review; prone/crawl replacement remains rejected and is not promoted**.

The 2026-08-28 in-game review rejected the original CMU 02 weapon clips and
the ACCAD kneel/prone/crawl chain. R02 does not repair those clips with manual
poses. It replaces only the actions for which a different real-human capture
and an exact Tiger-mesh review produced a readable result.

## R02 promoted capture windows

| Runtime action | Source | Source frames | R02 use |
|---|---|---:|---|
| Progressive Knife light | ACCAD Male2 E6 HookRight | 16–56 | right-hand horizontal cut |
| Progressive Knife heavy | ACCAD Male2 E4 CrossRight | 5–45 | committed straight thrust |
| Longinus thrust | ACCAD Male2 E4 CrossRight | 5–45 | full-body drive plus exact two-hand shaft solve |
| stand to crouch | CMU 136_09 Walk Crouched | 51–230 | continuous standing-height to low stance |
| crouch idle | CMU 136_09 Walk Crouched | 211–260 | settled low stance loop |
| crouch walk | CMU 136_09 Walk Crouched | 911–1055 | in-place tactical crouch gait loop |

ACCAD is CC BY 3.0. CMU reuse follows the official database terms. The
existing accepted berserk subset remains unchanged: CMU 54_13 and 120_02 plus
CMCD `KingKong2` under CC BY 4.0.

The tracked deterministic runtime overlay is
`tools/eva_real_mocap_accepted_r02.json`. It replaces 13 standing/crouched
weapon and crouch animations. The rejected
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
7. Exact body grounding changes root height only. Maximum lift is `0.03401 m`
   for weapon strikes and `0.08422 m` for crouch locomotion; captured joint
   rotations and weapon contacts remain unchanged.

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
- UT Dallas `MCP_prone01`: the archived project states CC BY 4.0 and names a
  dedicated prone-crawl FBX, but the live site database is broken and the only
  archived payload is truncated at 1 MiB. The damaged file is not used.

Prone idle, prone rifle, crawl, crouch-to-prone and prone-to-crouch therefore
remain on the last stable pre-R01 catalogue. R02 makes no claim that those
actions have been replaced or approved.

## Gameplay scope

Input bindings, state switching, damage, cooldown, reach, AOE and server
authority are unchanged. R02 changes only client-side animation resources and
restores the accepted stand/crouch transition clips required by the existing
stance controller.

Ignored review artefacts are under
`artifacts/motion_research/eva_action_r02_direct/`. Source and licence notices
remain in `docs/THIRD_PARTY_MOTION_NOTICES.md`.

## Final local gates

- exact body audit: knife `2/0`, Longinus `1/0`, crouch chain `3/0`
  (clips/failures);
- exact Longinus audit: right-hand surface distance at most `0.000001`,
  left-hand distance at most `0.017129`, forward-axis cosine at least
  `0.999780`;
- every promoted loop and stand/crouch rotational and root-position seam is
  within `0.01` degrees/pixels;
- local high-detail pack validation, weapon-system contract, berserk contract,
  Python compilation, `git diff --check` and `gradlew build` pass;
- `runClient` logs Project SEELE initialization, ordinary attack runtime
  `3 clips / 50 bones / 243 frames`, all three local EVA triangle meshes, and
  no Project SEELE error/fatal line.

The 431-frame review video is
`artifacts/motion_research/eva_action_r02_direct/EVA_R02_ACCEPTED_WEAPON_CROUCH_REVIEW.mp4`.
