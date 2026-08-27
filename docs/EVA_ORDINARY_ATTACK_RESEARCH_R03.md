# Project SEELE — EVA ordinary attack R03

Date: 2026-08-27

Status: **one isolated right-palm thrust is ready for human review; it is not
normal-gameplay authority**.

## Rejection carried forward

R12 is rejected. It proved the Tiger `-Z` front-axis contract but read as a
two-handed presenting gesture rather than an attack. Existing database clips
named `punch_jab`, `punch_cross` and `punch_hook` were also re-screened from a
real front camera. Their names were not trusted: they respectively read as a
wave, an overhead/backward gesture and a kick. None was promoted.

## R05 review action

R05 is one readable action with no combo or hidden second strike:

- both feet remain planted in the screened wide stance;
- the left palm stays close to the head and upper chest as a guard;
- the right palm retracts, then drives along Tiger runtime `-Z` front;
- pelvis, abdomen and thorax turn into the strike;
- the upper body leans into contact and returns to the opening guard;
- duration is `0.7833333 s` (`48` frames at `60 Hz`).

The action is intentionally an open-palm thrust rather than sport boxing. It
is isolated in Motion Lab until human approval.

Review artefact:

- `artifacts/motion_research/ordinary_attack_r04/EVA_ORDINARY_PALM_THRUST_R05_TWO_VIEW.mp4`

Minecraft review:

```mcfunction
/seele motionlab reset
/seele motionlab camera
/seele motionlab demo unit01 stop
/seele motionlab demo unit01 attack_right
```
