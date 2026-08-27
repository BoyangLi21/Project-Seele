# Project SEELE — combat transition audit R01

Date: 2026-08-27

Status: first physical-reference transition experiment; no combo is approved
for runtime or Minecraft integration.

## Test

The first attempted branch was:

```text
left forearm ward -> right push kick
```

Both endpoint actions independently pass the strict physical-rig/contact gate.
`tools/compose_eva_physical_transition.py` aligned the second root to the first,
preserved endpoint velocities with cubic Hermite interpolation, slerped the
free-root orientation and selected the common left support foot.

## Result

The direct transition is rejected:

| Transition | Duration at 60 Hz | Max tangent step | Result |
|---|---:|---:|---|
| 7 frames | 0.117 s | 0.5756 rad | reject |
| 12 frames | 0.200 s | 0.3606 rad | reject |
| 18 frames | 0.300 s | 0.2468 rad | numerical step clears, but delay is too long and pose gap remains |

The second action required about `-0.9193 rad` (`-52.7°`) yaw alignment. Raw
endpoint differences include approximately pi radians in right-shoulder twist,
`2.69 rad` shoulder flex and `2.04 rad` right-hip flex. This is not a small seam
that inertialization should hide; it is a missing physical action between two
different tactical poses.

The correct graph remains:

```text
ward -> body entry -> kick / grab / ram
```

not `ward -> kick` by arbitrary blending.

## Intermediate-source tests

- ACCAD E4 `QuickAdvance` frames 36–75 looks like useful rapid stepping, but
  its best grounded manifold solve leaves aggregate effector P95 at
  `0.03097 H`, worst left toe about `0.04374 H`.
- CMU 144_17 lunge frames 2170–2260 has a more readable guarded lunge, but its
  solve leaves aggregate effector P95 around `0.03702 H`, worst left ankle
  about `0.05028 H`, and needs over `0.20 m` root correction on the 4 m proxy.
- Neither source is promoted or used to conceal the transition gap.

## Required replacement

Record a project-owned entry that starts from the final left/right ward poses
and ends in each permitted branch-ready support state:

1. ward to left-support right push kick;
2. ward to palm/forearm grab range;
3. ward to shoulder/body ram commitment;
4. aborted entry to brake step;
5. entry interrupted by target collision.

Every take must include the exact prior endpoint and next-action target pose,
not generic martial-arts ready stances. The capture plan is
`docs/EVA_PROJECT_MOCAP_CAPTURE_PLAN_R01.md`.

## Comfort rule established

Inertialization is allowed to remove a small residual pose/velocity seam. It is
not allowed to invent a missing 50-degree turn or hold input for 300 ms while a
character morphs between unrelated poses. When endpoint search finds no short,
contact-compatible pair, the action graph needs a real intermediate motion.
