# Project SEELE — first 12 EVA combat fragments R01

Date: 2026-08-27

Status: source/production queue. A row is not a runtime animation unless its
status explicitly says the strict physical-rig gate passed.

## Ordered queue

| # | Fragment | Exact source window | Intended use | Current status |
|---:|---|---|---|---|
| 1 | left forearm/open-hand ward | ACCAD `Male2_E11_BlockLeftHigh`, frames 10–40 | left deflection, entry permission | source accepted; grounded whole-window solve blocked |
| 2 | right forearm/open-hand ward | ACCAD `Male2_E13_BlockRightHigh`, frames 5–35 | right deflection, entry permission | source accepted; grounded whole-window solve blocked |
| 3 | committed body entry | ACCAD `Male2_E4_QuickAdvance`, provisional frames 36–75 | close range behind guard, shoulder/clamp branch | exact contact segmentation pending |
| 4 | right push kick | ACCAD `Male2_G18_PushKickRight`, frames 23–48, event 34 | create distance, expose core, stop pursuit | **strict grounded kinematic gate passed; human 3D review pending** |
| 5 | left push kick | ACCAD `Male2_G17_PushKickLeft`, provisional frames 60–105, event 73 | mirrored mechanic without synthetic mirroring | source contact repair and physical solve pending |
| 6 | right low-line kick | CMCD `Take_2019-01-09_N_Nussknacker3`, frames 350–385, event 363 | attack support leg, prepare pounce | source accepted; physical solve misses upper-body gate |
| 7 | elbow grab attach | CMU `18_05/19_05`, frames 165–219, contact about 205 | convert limb contact to grip constraint | relative pair envelope passed; individual grounding blocked |
| 8 | two-hand shoulder clamp | CMU `22_05/23_05`, frames 59–245 | clamp, shove setup, jaw/torso restraint basis | source shared-contact gate passed; overlap segmentation pending |
| 9 | arm wrench/pivot | CMU `20_10/21_10`, frames 67–145 | wrench, turn, throw or grip break | source shared-contact gate passed; semantics only |
| 10 | shoulder/body collision | CMU `22_12/23_12`, frames 3–167 | shoulder ram, miss brace, target stagger | source shared-contact gate passed; never damage ground truth |
| 11 | forward pounce launch | ACCAD `Male2_B18_WalkToLeapToWalk`, frames 40–91 | pursuit into clamp, mount or ground resolver | source launch accepted; grounding/contact-speed solve blocked; source landing rejected |
| 12 | mutual grip/strength contest | CMU `22_17/23_17`, frames 197–283 | opposed grip, resistance and break-force reference | source shared-contact gate passed; physical constraint pending |

ACCAD G8 is deliberately absent from the low-line slot. It reaches about
`0.714 H` and is a high roundhouse, not a reap. A true target-leg reap remains
project-mocap or new-open-source work.

## First free-combat branch set

The following are possible paths, not canned combos:

```text
left/right ward
  -> body entry
      -> push kick                 when target stays outside hand range
      -> low-line kick             when support leg is exposed
      -> shoulder ram              when forward momentum exceeds braking room
      -> grab attach               when palm/forearm contact closes safely
          -> two-hand clamp/shove  when second palm reaches torso/shoulder
          -> arm wrench            when a limb anchor and pivot support exist
          -> pounce/mount          only after target knockdown is confirmed
```

Every arrow is gated by actual support, COM velocity, range, facing, terrain and
contact. A miss produces a brake step, pivot recovery, collision brace, roll or
fall. No edge resets to a neutral pose and no cooperative paired capture plays
past `GRAB_ATTACH` against a resisting live target.

## Unit emphasis

- Unit-00: ward, two-hand clamp, shove, arm restraint, protective support.
- Piloted Unit-01: urgent body entry, ram, push kick, grab and improvised
  continuation.
- Unit-02: angle change, low-line/push kick, quick pursuit and knife branch.
- Berserk Unit-01: ram or low pursuit into pounce, clamp, wrench, mount and
  target-specific maul/tear/bite logic.

## Promotion gate

Promotion requires all of the following on the 41-DOF physical skeleton:

- explicit full-source height and coordinate provenance;
- effector P95 `<= 0.02 H`, every ordinary effector P95 `<= 0.03 H`;
- articulation-guide P95 `<= 0.05 H`, individual `<= 0.06 H`;
- stable patch drift `<= 0.005 H`, speed P95 `<= 0.02 H/s`;
- stable sole mean absolute clearance `<= 0.002 H`, P95 `<= 0.005 H`;
- maximum penetration `<= 0.004 H`;
- combat root step `<= 0.025 H`, tangent step `<= 0.25 rad`;
- evaluated visual-mesh seam, self-collision and human 3D review;
- post-contact physical tracking, interruption and target-reaction tests;
- no runtime write to the authority free root.
