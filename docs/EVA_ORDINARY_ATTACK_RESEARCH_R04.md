# Project SEELE — direct-capture ordinary attack R04

Date: 2026-08-27

Status: **raw ACCAD capture directly connected to the active Tiger rig in the
isolated Motion Lab; human approval still required**.

## Source and transfer contract

The source is ACCAD `Male2_E4_CrossRight`, source frames `5–45`, resampled from
the original `30 Hz` capture to `60 Hz` without invented poses. The runtime
clip has `81` frames and lasts `1.3333333 s`.

The transfer uses normalized source landmark positions and the active Tiger
geometry pivots directly:

- source `+X` forward -> Tiger runtime `-Z` forward;
- source `+Y` left -> Tiger runtime `-X` left;
- source `+Z` up -> Tiger runtime `+Y` up;
- pelvis, abdomen, thorax, neck, head, both clavicles, shoulders, elbows,
  wrists, hips, knees, ankles and feet retain the captured frame timing;
- target limb lengths replace human limb lengths, but source joint directions
  are not edited.

There are zero manual pose keyframes, no IK correction, no physics projection,
no joint-limit projection and no smoothing filter. Because landmark capture
does not contain axial-roll channels, each target bone chooses one fixed twist
branch at frame zero and keeps it for the whole clip. This resolves an
otherwise ambiguous 180-degree roll without changing any joint direction.

## Measured result

- minimum source/target segment-direction dot: `0.9999233191`;
- maximum local 60 Hz step: `27.57396°`, right forearm at source contact;
- active target bones: `24`, including explicit neck, clavicles, wrists and
  ankles that the obsolete retargeter incorrectly collapsed;
- detached target joints in the true-front/side render: `0`.

The current Tiger geometry already contains every major joint needed by this
capture, so this pass required a retargeter replacement rather than a mesh
change. ACCAD has no finger capture; hand and finger articulation therefore
remain neutral and are not fabricated.

## Review

Synchronized raw-human plus EVA comparison:

- `artifacts/motion_research/ordinary_attack_r05/EVA_E4_RAW_HUMAN_DIRECT_RIG_R04_COMPARISON.mp4`

Minecraft:

```mcfunction
/seele motionlab reset
/seele motionlab camera
/seele motionlab demo unit01 stop
/seele motionlab demo unit01 attack_right
```
