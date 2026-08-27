# Project SEELE — EVA ordinary attack research R02

Date: 2026-08-27

Status: **two single-action physical candidates pass; no Minecraft integration
or final human approval yet**.

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
