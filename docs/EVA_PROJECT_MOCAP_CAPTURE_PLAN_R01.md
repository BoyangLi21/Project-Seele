# Project SEELE — project-owned EVA mocap capture plan R01

Date: 2026-08-27

Status: production-data plan for actions that open datasets do not contain with
the required contact semantics. No recording has been performed yet.

## Tool choice

Primary route: local multi-view OpenCap processing plus the existing Blender /
41-DOF retarget and contact audit.

- [OpenCap Core](https://github.com/opencap-org/opencap-core) is Apache-2.0 and
  produces 3D marker positions plus OpenSim joint kinematics from two or more
  near-synchronized videos.
- Multi-view capture is preferred over monocular recovery for pounce depth,
  foot plants, grapples and weapon contacts.
- The performers, project and consent form must make the captured videos and
  derived motion explicitly available to Project SEELE under CC BY 4.0 or CC0.
- Blender is suitable for cleanup and review; Blender's licence does not claim
  ownership of artwork/data produced with it.

Secondary preview route: PoseCap/GVHMR can quickly check a single-camera take,
but SMPL/SMPL-X body models are registration-gated and may not be redistributed.
They are not the canonical production or archival representation. The project
stores only its own normalized landmarks/physical-rig result when permitted.

## Capture volume

- two or preferably three fixed 60/120 fps cameras with intersecting views;
- shared clap/flash plus frame-level synchronization;
- calibrated floor plane and a measured 1 m reference;
- shoes with stable, visible heel/forefoot/toe regions;
- padded target dummy with marked wrist, elbow, shoulder, torso, pelvis, knee,
  ankle, neck and core regions;
- foam knife, spear and long staff with measured rigid-body marker points;
- no loose clothing obscuring hips, knees, ankles, clavicles or wrists;
- at least three clean takes and two intentionally interrupted takes per shot.

## First missing shot list

Each take begins from relaxed locomotion or a prior accepted fragment, not a
martial-arts display pose.

1. **Low reap against a real target leg** — outside plant, shin/instep contact,
   target support loss, attacker pivot recovery; hit and miss takes.
2. **Two-hand shove with resistance** — both palms established before rear-leg
   drive; light/heavy target resistance and sudden release.
3. **Shoulder/body ram** — braced target, yielding target, complete miss and wall
   collision; measure both actors' impulse response.
4. **Forward pounce to two-hand clamp** — launch, chest/shoulder contact, hands
   close, feet arrive later; target stays upright and target falls variants.
5. **Pounce miss to four-point landing** — palms then feet/knees without a
   canonical jump-landing pose.
6. **Pounce miss to roll/step recovery** — three approach angles and an obstacle
   invalidating the original landing.
7. **Mounted restraint to impact** — grounded target pad, stable knees/feet or
   pelvis support, short committed forearm/hand impacts rebuilt after every
   target reaction.
8. **Grip attach, wrench and natural break** — wrist/elbow anchors, target pulls
   in three directions, grip exceeds a declared force budget.
9. **Heavy two-hand weapon swing** — anticipation, rear-to-front support,
   impact pad, blowback, deflection and miss.
10. **Progressive Knife thrust and slash contacts** — guard, target parry,
    penetration stop, deflection and recovery without wrist collapse.
11. **Full-body javelin throw** — carry, windup, release, follow-through and
    failed/late release; long rigid prop required.
12. **Grounded target lift/assist and forced rise** — one-hand and two-hand
    grips, target cooperation/resistance, partial rise and failed lift.

## Event labels recorded at source rate

```text
L/R_FOOT_STRIKE  L/R_FOOT_FLAT  L/R_TOE_OFF
L/R_HAND_CONTACT L/R_FOREARM_CONTACT SHOULDER_CONTACT BODY_CONTACT
TARGET_LIMB_CONTACT GRAB_ATTACH GRAB_RELEASE GRIP_BREAK
TAKEOFF APEX LAND SLIP_START SLIP_END
WEAPON_CONTACT WEAPON_DEFLECT WEAPON_RELEASE
IMPACT TARGET_SUPPORT_BREAK RECOVERY_READY ABORT
```

Contact labels are reviewed on synchronized video and 3D landmarks. Automatic
foot-height heuristics may propose events but cannot approve them.

## Required deliverables per take

- raw synchronized videos and calibration;
- performer/project release and chosen data licence;
- camera/intrinsic/extrinsic manifest and checksums;
- OpenCap/OpenSim output plus normalized `+X forward, +Y left, +Z up` landmarks;
- rigid prop trajectory where applicable;
- contact/event annotation;
- source, physical-rig and evaluated-mesh 3D viewers;
- strict metric report and failure montage;
- an explicit statement that the take is source data, a kinematic candidate or
  a physically tracked result.

## Acceptance boundary

Project-owned mocap supplies human mechanics and contact intent. It does not
become a final clip to play. The 41-DOF controller must still reproduce it under
mass, torque, terrain, target and interruption variation, and the next action
must be rebuilt from the actual resulting state.
