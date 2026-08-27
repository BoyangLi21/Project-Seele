# Project SEELE — EVA real-human combat and posture runtime R01

Status: **implemented in the current Gecko visual runtime, with server damage,
cooldown, navigation and hit zones unchanged**.

This pass replaces authored placeholder body motion for the Progressive Knife,
Longinus thrust, crouch/prone locomotion and Unit-01 berserk presentation with
selected public real-human motion capture. It does not import Evangelion
footage, audio or official animation.

## Promoted capture windows

| Runtime action | Source | Source frames | Runtime duration |
|---|---|---:|---:|
| knife strike | CMU 02_09 | 441–571 | 1.083 s |
| heavy knife strike | CMU 02_07 | 1401–1561 | 1.333 s |
| Longinus thrust | CMU 02_08 | 741–901 | 1.333 s |
| crouch idle | ACCAD Male2 A7 | 463–511 | 0.400 s loop |
| stand to crouch | ACCAD Male2 A7 | 177–353 | 1.467 s |
| crouch walk | CMU 136_09 | 911–1055 | 1.200 s loop |
| prone idle | ACCAD Male2 A8 | 125–141 | 0.533 s loop |
| crouch to prone | ACCAD Male2 A8 | 71–127 | 1.867 s |
| prone to crouch | ACCAD Male2 A10 | 23–78 | 1.833 s |
| crawl | ACCAD Male2 A11 | 221–282 | 2.033 s loop |
| berserk roar | CMU 54_13 | 1041–1291 | 2.083 s |
| berserk run | CMU 120_02 | 405–619 | 1.783 s loop |
| right / left claw | CMCD `KingKong2` | 630–710 / 680–750 | 1.333 / 1.167 s |
| berserk pounce | CMCD `KingKong2` | 330–510 | 3.000 s |

CMU reuse follows the official database FAQ. ACCAD is CC BY 3.0. CMCD is
CC BY 4.0. Source notices are recorded in `docs/THIRD_PARTY_MOTION_NOTICES.md`.

## Runtime and constraint pipeline

1. Source windows are normalized and sampled at 60 Hz.
2. Segment directions are retargeted to the Tiger skeleton. Uncaptured axial
   twist is parallel-transported from the prior frame, avoiding 85–180 degree
   branch flips without inventing a second hand or limb.
3. Gecko curves are exported at 30 Hz. Loop drift is distributed geodesically
   through the cycle, so all promoted loops have a zero-degree first/last
   rotational seam.
4. Crouch/prone transition endpoints are blended over 0.35 s to the exact
   adjacent stance. All six runtime transition edges now differ by 0 degrees.
5. Knife, rifle and Longinus are checked against the exact Tiger and weapon
   triangle meshes. Longinus keeps its right grip and forward axis while a
   target-constrained left clavicle/arm solve reaches the shaft without
   translating or detaching a limb bone.

The checked-in animation JSON remains a transitional visual layer. The roadmap
physics skeleton is still the future authority for root movement, contact,
damage and rendering; this work does not claim Gecko clips are physical ground
truth.

## Gameplay wiring

- Left-click knife and Longinus attacks select standing, crouched or prone
  variants from the same real capture body motion.
- Crouch/prone input triggers real stand/crouch/prone transition clips; direct
  stand-to-prone and prone-to-stand requests chain through the matched crouch
  boundary.
- Berserk navigation uses the real gorilla-style run, real left/right swipes
  drive the existing alternating claw damage, and the pounce is a distance-
  gated visual anticipation. Damage and navigation remain server-authoritative.
- Existing melee damage, cooldown, reach, AOE and configuration values are not
  changed by this pass.

## Final local gates

- exact body lab: 27 clips, 0 failures;
- exact weapon lab: 13 weapon poses, 0 failures;
- maximum reviewed Longinus distances: right hand 0.092, left hand 0.018;
- Longinus forward-axis cosine: at least 0.9998;
- prone rifle distances: right hand 0.042, left hand 0.019;
- all promoted loop seams: 0 degrees;
- all crouch/prone transition boundary errors: 0 degrees.

The ignored review authority is
`artifacts/motion_research/eva_real_actions_r01/final/EVA_REAL_RUNTIME_ALL_FINAL.blend`.
The tracked deterministic inputs are `tools/eva_real_mocap_r01.json` and
`tools/eva_real_mocap_weapon_contacts_r01.json`.
