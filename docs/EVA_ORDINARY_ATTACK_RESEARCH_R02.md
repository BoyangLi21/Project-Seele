# Project SEELE — EVA ordinary attack research R02

Date: 2026-08-27

Status: **one rebuilt right-side candidate passes the topology-aware physical
gate and is isolated in Motion Lab; no gameplay promotion or final human
approval yet**.

## Product-order correction

Paired interactions are frozen. The earlier left ward, right ward and right
push-kick review set was removed after human review rejected all three. Their
physical metrics remain only to stop the project from repeating that route.

The ordinary-attack target is not a boxing 1–2. It is a shoulder-supported,
open-hand/forearm batter that can branch from actual contact. Punches remain
reserved for committed brawls, grapples and mounted/contextual impacts.

## Source search and rejects

- CMU `02_05`, `56_03–06`, `111_19`, `113_13` and `143_23` were downloaded
  from the documented CMU BVH conversion after checking the official CMU
  reuse terms.
- CMU `111_19` and the promising `56_03` smash sequence failed EVA retarget by
  `0.11–0.23 H`; they are rejected, not repaired by lowering thresholds.
- ACCAD `Extended_2` frames 235–410 is a coherent continuous boxing sequence,
  but remains the wrong ordinary EVA vocabulary.
- ACCAD `Extended_3` contains dynamic kick/strike sequences, but its contact
  coverage and style are not accepted.
- CMU subject 81 high-object/heavy-object pushes were screened as possible
  two-hand body attacks. Direct EVA retargets failed at roughly `0.11 H`
  landmark P95 and are rejected.
- Bandai Namco Research Motiondataset-1 `punch_normal_002` and
  `slash_normal_002` were screened from the professional game-mocap set under
  CC BY-NC 4.0. The lunge strike and two-hand swing both failed direct EVA
  retarget at roughly `0.096 H` and `0.109 H` P95 respectively. Neither is a
  runtime asset. The BVH landmark exporter now recognizes this skeleton so
  future windows can be rejected or accepted without manual bone renaming.
- A direct right-batter to left-batter blend fails: 7/12/18-frame bridges have
  maximum tangent steps `0.71/0.47/0.34 rad`. No generic cross-fade is used.

## False-positive audit correction

R17, R24 and the later R29 recovery are rejected. The old gate did not check
left/right hand order, cross-arm clearance, non-ground self contacts or knee
bend branches. Worse, generated transition FK was copied into the desired
landmarks, making the recovery self-validating. R29 reaches a minimum hand
lateral gap of `-0.08964 H` and therefore contains a real hand-order crossing.
R24 contains 17 palm/knuckle self contacts.

The corrected gate now keeps transition targets independent, checks physical
self contacts, hand/wrist/elbow ordering, cross-arm segment clearance, leg
ordering and knee bend-branch continuity.

## Accepted physical candidate

The rebuilt right batter freezes the non-striking arm in a torso-relative
guard, resolves the striking wrist/hand against an explicit right-side target,
and returns over the same already-screened pose path. It creates no new
interpolated recovery poses.

| Candidate | Effector P95 | Articulation P95 | Hand gap | Arm clearance | Self contacts | Failures |
|---|---:|---:|---:|---:|---:|---:|
| right guarded batter R06 | `0.01581 H` | `0.02899 H` | `0.07367 H` | `0.22593 H` | `0` | `0` |

The Tiger review rig now contains 23 bridge bones instead of the old 16-bone
collapse. Neck, both clavicles, both wrists and both ankles exist as explicit
intermediate nodes; physical global deformation is converted through that
matching hierarchy before Minecraft/Blender applies it.

## Runtime rotation-encoding correction

R06 passed the physical topology gate but its first visual export is rejected.
The export wrote the desired runtime rotation directly into the authored
Bedrock quaternion. Gecko then applied its authored-Euler convention
`(-X, -Y, +Z)` a second time. The physical pose therefore remained valid while
the displayed upper-arm and forearm segments were nearly reversed, producing
the obvious arms-through-head crossing in the review video.

This was identified by comparing rendered bone-segment directions against the
same-frame physical body directions, rather than by another visual offset:

| Segment | Broken export dot | Corrected R08 dot |
|---|---:|---:|
| upper arm to forearm | approximately `-0.94` | at least `+0.9968` |
| forearm to wrist | approximately `-0.98` | at least `+0.9996` |

R08 keeps the accepted R06 physical state sequence unchanged. It first maps
physical deformation into runtime space and then applies the inverse Gecko
Euler encoding when writing authored quaternions. A positive near-one segment
direction dot is now a required export regression check; a physical audit by
itself is not sufficient evidence for visual correctness.

## Review artefacts

- `artifacts/motion_research/ordinary_attack_r03/rebuild_r01/RIGHT_BATTER_REBUILT_R08_REVIEW.blend`
- `artifacts/motion_research/ordinary_attack_r03/rebuild_r01/RIGHT_BATTER_REBUILT_R06.npz`
- `artifacts/motion_research/ordinary_attack_r03/rebuild_r01/EVA_ORDINARY_BATTER_RIGHT_MAPPING_FIXED_R08_TWO_VIEW.mp4`

The two-view files are for human screening only. They are not runtime assets.
Promotion still requires human acceptance and a contact-driven damage test.

## Isolated Minecraft review

The rebuilt right candidate is available only in `SEELE_EVA_MOTION_LAB`; normal
combat input and the R28 save are unchanged. Start `tools\start_motion_lab.bat`,
then use:

```mcfunction
/seele motionlab reset
/seele motionlab camera
/seele motionlab demo unit01 stop
/seele motionlab demo unit01 batter_right
```

The rejected left command has been removed. The right command plays once and
returns to its opening guard; execute `stop` before replaying.
The chat acknowledgement must begin `STRICT ORDINARY ATTACK PHYSICAL REVIEW`.
The resource is `assets/projectseele/motion/eva_ordinary_attack_review_v1.json`
with 1 clip, 23 bridge bones and 104 frames. `batter_right` uses rebuilt R06.
Its runtime visual encoding is the corrected R08 export described above.

## Body-entry follow-up

ACCAD QuickAdvance upper-body mechanics layered over the stable lower body
produced an in-place moving guard candidate at effector/articulation P95
`0.01435/0.01417 H`, drift `0.00055/0.00185 H`, with zero strict failures.
It is not promoted as a ram because replacing its 28° source-root lean with the
stable root makes it read as an upright guard.

A second experiment preserved the source-root lean and allowed the leg chains
to compensate. It failed badly: right contact drift remained `0.04356 H`,
along with manifold, clearance, speed and penetration failures. That branch is
rejected. A real body ram must come from a dynamic physical controller or a
new capture whose support mechanics are compatible with the EVA rig; the
project will not fake it by writing root motion.

## Pounce search

ACCAD B18 frames 40–91 was retimed 1.25× and contact-resolved to R36. It then
passed the pounce numerical gate at effector/articulation P95
`0.01968/0.03263 H`, drift `0.00212/0.00152 H`, with zero strict failures.
High-detail review nevertheless rejected it: the source is a human upright
leap with arms extended, not a predatory EVA forward pounce. It is not added to
Minecraft. The already-rejected B18 landing discontinuity remains excluded.
