# Project SEELE — EVA ordinary attack research R02

Date: 2026-08-27

Status: **two single-action physical candidates pass and are isolated in
Motion Lab; no gameplay promotion or final human approval yet**.

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

## Accepted physical candidates

Both actions use ACCAD backfist biomechanics only as an upper-body prior. The
lower body and authority root come from an independently audited stable combat
stance, retimed to the same duration. The lateral strike arc is then redirected
into a forward diagonal target and solved on the 41-DOF rig. Upper and lower
goals remain independent in the audit; targets are not replaced with measured
output to hide error.

| Candidate | Contact yaw | Effector P95 | Articulation P95 | L/R drift | Strict failures |
|---|---:|---:|---:|---:|---:|
| right diagonal batter R17 | `-27.5°` | `0.01725 H` | `0.03755 H` | `0.00069 / 0.00179 H` | 0 |
| left diagonal batter R24 | `+28.2°` | `0.01648 H` | `0.03062 H` | `0.00056 / 0.00148 H` | 0 |

The current Tiger review exporter now computes each physical body's world
deformation relative to its own bind, maps that deformation to the Tiger
authored basis, then derives visual local rotations from the visual parent
chain. Directly copying physical local joint deltas was mathematically wrong
because the physical and visual bind axes differ.

## Review artefacts

- `artifacts/motion_research/ordinary_attack_r02/EVA_ORDINARY_ATTACK_RIGHT_R17_TWO_VIEW.mp4`
- `artifacts/motion_research/ordinary_attack_r02/EVA_ORDINARY_ATTACK_LEFT_R24_TWO_VIEW.mp4`
- `artifacts/motion_research/ordinary_attack_r02/EVA_DIAGONAL_BATTER_RIGHT_R17_60HZ.mp4`
- `artifacts/motion_research/ordinary_attack_r02/EVA_DIAGONAL_BATTER_LEFT_R24_60HZ.npz`

The two-view files are for human screening only. They are not runtime assets.
Promotion still requires human acceptance, an interrupt/recovery graph and a
contact-driven damage test.

## Isolated Minecraft review

The two candidates are now available only in `SEELE_EVA_MOTION_LAB`; normal
combat input and the R28 save are unchanged. Start `tools\start_motion_lab.bat`,
then use:

```mcfunction
/seele motionlab reset
/seele motionlab camera
/seele motionlab demo unit01 stop
/seele motionlab demo unit01 batter_right
```

For the left candidate, replace the final argument with `batter_left`. Each
command plays once and holds the terminal pose; execute `stop` before replaying.
The chat acknowledgement must begin `STRICT ORDINARY ATTACK PHYSICAL REVIEW`.
The resource is `assets/projectseele/motion/eva_ordinary_attack_review_v1.json`
with 2 clips, 16 collapsed visual bones and 144 frames.

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
