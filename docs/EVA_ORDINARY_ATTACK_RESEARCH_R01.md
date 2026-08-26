# Project SEELE — EVA ordinary-attack research R01

Date: 2026-08-27

Status: **external 3D candidate accepted for human review; not integrated into
Minecraft**.

## 1. Why the existing attack was rejected

The current `animation.eva_unit01.melee` and `melee_left` are five-pose
procedural claw/rake animations authored in `make_tiger_unit01_pack.py`. They
are not motion capture. The older external Quaternius punch candidates were
also rejected: their target audits reached approximately 177 degrees at an
elbow and 46 degrees of finger-chain direction error. Neither source may be
used as the new ordinary attack.

## 2. Sources and licence boundary

- Ohio State ACCAD Open Motion Data, Male-2 Martial Arts Punches and General
  motion, CC BY 3.0:
  https://accad.osu.edu/research/motion-lab/mocap-system-and-data
- Exact official punch catalogue:
  https://accad.osu.edu/sites/accad.osu.edu/files/ACCAD_mocap_Data_Male2_MartialArtsPunches.pdf
- DFKI hand reference used only to solve an anatomical fist on the existing
  EVA finger bones, CC BY 4.0; local provenance is stored in
  `dfki_inescop_pair_of_protector_grasp_point_c_spherical_set0_reference.json`.
- Transition method references: David Bollo, *Inertialization: High-Performance
  Animation Transitions in Gears of War 4*; Ubisoft Learned Motion Matching.

No Evangelion production animation, game animation, screenshot, audio or
official model was copied.

## 3. Source screening

All sixteen ACCAD Male-2 punch files were measured on the original performer
before retargeting. Eleven passed the first biomechanics gate. The initial
ordinary-attack shortlist was:

| Rank | Source | Contact elbow | Guard-to-head | Pelvis/chest turn | Peak fist |
|---:|---|---:|---:|---:|---:|
| 1 | `Male2_E1_JabLeft` | 156.2° | 0.371 m | 12.7° / 21.8° | 5.35 m/s |
| 2 | `Male2_E3_CrossLeft` | 163.5° | 0.374 m | 45.0° / 79.7° | 7.17 m/s |
| 3 | `Male2_E4_CrossRight` | 150.2° | 0.372 m | -48.3° / -89.4° | 8.68 m/s |
| 4 | `Male2_E2_JabRight` | 151.7° | 0.383 m | -8.0° / -18.5° | 6.22 m/s |

`E1 JabLeft` and `E4 CrossRight` form the accepted first 1–2 family: the jab
is economical and readable; the cross carries the visible hip/chest power
needed for an EVA rather than looking like an isolated Minecraft arm swing.

The apparently attractive continuous `Male2_Extended_2` segment was tested and
rejected. Its first detected event was not a clean forward boxing strike after
retarget: fist direction error was about 42.6 degrees, guard distance about
0.56 body heights, feet crossed, and both feet travelled more than one body
height. It is not a shortcut for the combination.

## 4. Accepted target construction

The candidate is built on the current private 64-bone EVA rig, never on the
older 63-bone idle rig:

1. Normalize each ACCAD strike to the actual fist path, not capture-world root
   travel or an assumed body axis.
2. Retarget complete pelvis, torso, both arms, both legs and feet using the
   same ACCAD-aware direction solver as R32 locomotion.
3. Lock ground contacts with two-bone IK. Enforce a minimum 0.24-H combat
   stance, stable sagittal knee poles and a 0.985 leg-extension cap.
4. Resample 30 Hz capture to 60 Hz before runtime export.
5. Apply a measured anatomical fist to the existing index/middle/ring/little
   and original thumb bones. No extra thumb or duplicated finger geometry is
   created.
6. Retiming is limited to 1.25x. The rejected 1.4x trial produced roughly
   38–41 degrees of world finger/forearm travel per 60 Hz frame.

Final individual timing:

| Action | Frames @ 60 Hz | Duration | Contact | Contact time |
|---|---:|---:|---:|---:|
| left jab | 46 | 0.75 s | ~23 | ~0.37 s |
| right cross | 51 | 0.83 s | ~22 | ~0.35 s |

Target-space strike-direction error is 0.22 degrees for the jab and 1.66
degrees for the cross. Contact elbow angles remain 156.2 and 150.2 degrees.
The non-striking hand remains guarded; target guard-to-head distance is 0.285 H
for the jab and 0.121 H for the cross.

## 5. Contact-aware transition result

Simple cross-fades and raw inertialization were rejected because they moved
both feet across the ground. R19 uses separate pose and contact rules:

- neutral-to-jab: 17-frame Hermite body transition; right foot is planted and
  left foot performs a 0.016-H step;
- jab-to-cross: short inertialized upper-body redirection; right foot is
  planted and left foot performs a 0.025-H step;
- cross-to-neutral: right foot remains planted and left foot returns with a
  0.036-H step;
- world-root correction is a smooth cubic path; pelvis-local capture is never
  used as a second world root.

Final contact audit (`EVA_ORDINARY_ATTACK_REVIEW_ACCEPTED_R19`):

| Phase | Support travel | Moving-foot travel/lift | Max root step |
|---|---:|---:|---:|
| neutral → jab | 0.0137 H | 0.0602 H / 0.0163 H | 0.0120 H |
| jab | 0.0078 H | 0.0324 H / 0.0287 H | 0.0138 H |
| jab → cross | ~0.0000 H | 0.1234 H / 0.0249 H | 0.0064 H |
| cross | 0.0095 H | 0.0550 H / 0.0483 H | 0.0079 H |
| cross → neutral | ~0.0000 H | 0.0621 H / 0.0356 H | 0.0056 H |

All contact gates pass. The highest non-striking-joint frame step is about
8.43 degrees at 60 Hz. The larger peaks belong to the intentionally fast
striking forearms, not to a knee/root discontinuity. Fist shape is constant in
palm space, PIP range is approximately 68.9–87.7 degrees, DIP range 40–45
degrees, and the original thumb closes across the fist.

## 6. Proposed runtime semantics (not yet implemented)

- First primary-attack input selects the left jab.
- A second input during the post-contact branch window selects the right cross.
- No second input follows the captured jab recovery and contact-aware return.
- Direction changes before commitment may rebuild the target; after commitment
  the remaining momentum must be carried rather than resetting the clip.
- Damage must ultimately derive from fist/body contact and impulse. The current
  immediate forward AABB is retained only until the physical combat layer is
  ready and must not be presented as final combat.
- Runtime animation must not overwrite locomotion root authority. Foot-contact
  and body-state data travel with the candidate.

## 7. Review artefacts

- `artifacts/motion_research/accad_combat/EVA_ORDINARY_ATTACK_REVIEW_ACCEPTED_R19.blend`
- `artifacts/motion_research/accad_combat/EVA_ORDINARY_ATTACK_REVIEW_ACCEPTED_R19_multiview.mp4`
- `artifacts/motion_research/accad_combat/EVA_ORDINARY_ATTACK_REVIEW_ACCEPTED_R19_keyposes.png`
- `artifacts/motion_research/accad_combat/EVA_ORDINARY_ATTACK_REVIEW_ACCEPTED_R19_CONTACT_AUDIT.json`
- `artifacts/motion_research/accad_combat/EVA_ORDINARY_ATTACK_REVIEW_ACCEPTED_R19_ACTIVITY.json`
- `artifacts/motion_research/accad_combat/ACCAD_ORDINARY_ATTACK_SOURCE_AUDIT_R02.json`

R19 is ready for human 3D/video review. It is not yet approved for Minecraft
integration.
