# Project SEELE — EVA ordinary attack R03

Date: 2026-08-27

Status: **R05 rejected: hand-authored target poses are prohibited for this
task and have been removed from the runtime review resource**.

## Rejection carried forward

R12 is rejected. It proved the Tiger `-Z` front-axis contract but read as a
two-handed presenting gesture rather than an attack. Existing database clips
named `punch_jab`, `punch_cross` and `punch_hook` were also re-screened from a
real front camera. Their names were not trusted: they respectively read as a
wave, an overhead/backward gesture and a kick. None was promoted.

## Rejected R05 review action

R05 attempted one readable action with no combo or hidden second strike:

- both feet remain planted in the screened wide stance;
- the left palm stays close to the head and upper chest as a guard;
- the right palm retracts, then drives along Tiger runtime `-Z` front;
- pelvis, abdomen and thorax turn into the strike;
- the upper body leans into contact and returns to the opening guard;
- duration is `0.7833333 s` (`48` frames at `60 Hz`).

Human review correctly rejected it because the body motion was assembled from
hand-authored arm targets rather than directly transferred from the original
capture skeleton. Its authoring tool and runtime clip have been removed.

Review artefact:

- `artifacts/motion_research/ordinary_attack_r04/EVA_ORDINARY_PALM_THRUST_R05_TWO_VIEW.mp4`

Minecraft review:

```mcfunction
/seele motionlab reset
/seele motionlab camera
/seele motionlab demo unit01 stop
/seele motionlab demo unit01 attack_right
```
