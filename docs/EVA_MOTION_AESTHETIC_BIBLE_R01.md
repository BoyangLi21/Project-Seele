# Project SEELE — EVA Motion Aesthetic Bible R01

Date: 2026-08-26

This document is a hard review contract, not a mood board. A motion that is
technically valid but violates the silhouette or biomechanics below is rejected.

## 1. Core interpretation

An EVA is not a conventional robot and not a normal person wearing armour. Its
motion must combine three layers:

1. **Athletic human mechanics.** Pelvis, spine, clavicles, scapulae, shoulders,
   hands and feet participate in one connected kinetic chain.
2. **EVA anatomy and silhouette.** Long limbs, narrow waist, large shoulder
   pylons and armour geometry change the readable outline without turning the
   body into hinged machinery.
3. **Giant-scale consequence.** Acceleration can be explosive, but stopping,
   landing, impact and redirection must reveal momentum through ground reaction,
   follow-through and environmental response.

“Heavy” never means universally slow. The original EVAs often accelerate like
sprinters or predators. Scale is communicated at contact and redirection, not by
putting every animation in slow motion.

## 2. Whole-body rules

### Pelvis and centre of mass

- The pelvis initiates locomotion and direction changes; feet do not drag the
  torso through space.
- During forward acceleration, the whole body inclines from ankles and hips.
  Folding only at the waist is rejected.
- During braking, the support foot reaches ahead of the COM, the pelvis lowers,
  and the torso counterbalances. A speed curve without this pose change is not
  an EVA stop.
- Lateral changes require a visible plant, pelvis shift and inside/outside leg
  loading. Sliding the root sideways is rejected.

### Spine, chest and shoulders

- Lumbar and thoracic motion are distributed. A single rigid torso or one sharp
  bend creates the “two disconnected body pieces” failure.
- Chest rotation counterbalances the pelvis during gait and amplifies attack
  preparation and follow-through.
- Clavicles and scapulae must keep arms physically attached to the torso. Any
  gap, collapsed shoulder or upper arm entering the chest rejects the motion.
- Shoulder pylons are visual children of the thorax/shoulder system; they may
  exaggerate silhouette but may not drive arm kinematics.

### Legs and feet

- Knee direction follows the foot and hip plane. Valgus collapse, bowing and
  persistent toe-out are hard failures.
- Foot strike occurs near the projected COM for running. Reaching far ahead on
  every stride produces braking and a floating “mocap treadmill” look.
- Heel/forefoot/toe contact must be labelled. A planted patch may not slide more
  than the review threshold.
- Swing feet require terrain clearance; stance feet require contact locking.
- The EVA foot is stylised, but the underlying ankle and toe roll must remain
  biologically readable.

### Arms and hands

- Arm swing comes from the shoulder girdle and chest, not isolated humerus
  pendulums.
- Elbows maintain a plausible plane and never invert or appear detached.
- Weapons are constrained by palm contact and hand spacing. The weapon must not
  be repaired by moving the hands independently after retargeting.
- Fingers are a separate grip layer. Full finger dynamics are not required for
  locomotion, but the retained thumb and added fingers must form one hand rather
  than duplicated anatomy.

### Head and gaze

- Mouse look first affects eyes/head and then neck/thorax within anatomical
  limits. The pelvis turns only when locomotion or accumulated yaw requires it.
- Fast running reduces independent head motion; gaze stabilisation may oppose
  chest oscillation but cannot make the head look detached.

## 3. Weight and timing

Weight is judged through cause and consequence:

- anticipation before high impulse;
- a readable support foot before COM redirection;
- delayed chest/arm follow-through after pelvis braking;
- landing compression followed by recovery, not a one-frame height snap;
- momentum remaining after an attack is cancelled;
- contact noise, dust and environment deformation added by gameplay, not baked
  into the skeleton;
- no periodic vertical bob added merely to suggest mass.

Fast EVA motion should feel dangerous because the body commits momentum, not
because controls are delayed.

## 4. Locomotion review

### Idle and alert

- Idle is asymmetrical and alive, with subtle breathing and balance correction.
- Alert stance lowers COM slightly and frees the arms; it is not a symmetric
  mannequin pose.
- No visible foot skating or perpetual swaying.

### Start

- First intent produces a weight shift before or with the first step.
- Sprint start has a strong forward lean, rear-leg drive and aggressive arm
  action. It must not begin at full cyclic run pose.
- Start may be interrupted and redirected without returning to idle.

### Walk, run and sprint

- Walk is purposeful, not casual civilian strolling.
- Run is an athletic locomotion family with coherent pelvis/chest
  counter-rotation and neutral foot progression.
- Sprint lengthens flight and stride while preserving landing under control.
- Unit motion must remain readable from front, side and three-quarter cameras.

### Stop and turn

- Stops have short, medium and emergency variants selected by momentum.
- 90-degree and 180-degree turns require a plant and continuous facing change.
- Turn-in-place is separate from moving pivots and cannot rotate the body on a
  single planted Minecraft point without foot adjustment.

### Jump and landing

- Take-off impulse comes from hip, knee and ankle extension.
- Airborne pose follows take-off velocity; it is not a long looping jump clip.
- Landing selection depends on vertical speed, horizontal speed and ground
  normal.
- Hard landing may require one hand or a follow-up step. Perfect two-foot
  symmetry is not the default.

### Obstacles

- Block geometry is sampled before committing the step.
- Low obstacles use step-over or longer stride; medium obstacles use vault or
  climb; impossible obstacles cause a braced stop or collision response.
- Contact points for hands and feet are explicit constraints, not visual guesses.

## 5. Combat review

### Empty hand

- Punches begin from foot/pelvis/chest and terminate through shoulder, elbow and
  fist. An isolated Minecraft arm swing is rejected.
- The non-striking hand guards, counterbalances or controls the opponent.
- Elbow and knee attacks require close-range body positioning; they must not be
  substituted for every right-click attack.
- Kicks include plant preparation, pelvis rotation, recoil and recovery step.
- Continuous combinations are selected from the actual ending pose and momentum.

### Progressive knife

- Knife guard is compact and slightly higher than the rejected low-hand pose.
- Slashes use torso and shoulder rotation with a protected opposite side.
- Thrusts align wrist, forearm and blade while preserving reach limits.
- Contact produces deflection/follow-through; the weapon does not pass through
  the target on a fixed timeline.

### Rifle

- Stock/receiver, support hand, firing hand and shoulder/chest form one constrained
  structure.
- Locomotion while aiming shortens stride and stabilises the upper body without
  freezing the pelvis.
- Aim pitch is distributed through shoulder, thorax and neck; arms do not detach
  to chase the muzzle.
- Muzzle position and projectile origin derive from the same weapon transform.

### Spear / Lance of Longinus

- The lance is a long rigid body with large rotational inertia. Hands establish
  leverage before the torso turns.
- Sweeps require stance width and follow-through; thrusts require rear-leg drive.
- The left arm may not cross through the chest and the right elbow may not invert.

### Grapple and berserk

- Grabs require palm contact and a constrained opponent/body point.
- Pushes, throws and struggles preserve both bodies’ support and momentum.
- Berserk motion is animalistic but anatomically connected: lower COM, spinal
  flexion, hand/foot contact and sudden directional commitment. Random joint
  noise is not berserk motion.

## 6. Unit style layer

Base mechanics remain shared; style is a controlled additive/selection layer.

- **Unit-00:** restrained, economical and defensive; smaller anticipations and
  clearer bracing.
- **Unit-01, piloted:** inexperienced or urgent depending on context; power is
  present but control is not always polished.
- **Unit-01, berserk:** predatory low posture, aggressive spinal participation,
  hand contact and committed pursuit.
- **Unit-02:** assertive, technically cleaner and more aggressive; stronger
  silhouette, decisive plants and weapon handling.

These are direction notes, not excuses to distort biomechanics.

## 7. Automatic rejection rules

A candidate is rejected before subjective review if any of the following occurs:

- unintended mirror or determinant below zero;
- wrong travel direction;
- hard joint-limit violation;
- non-adjacent self-intersection;
- shoulder/arm separation or limb entering the torso;
- persistent foot yaw outside the intended progression angle;
- stance-foot sliding above threshold;
- root discontinuity or teleport at a transition;
- weapon/hand constraint error above threshold;
- render root leaving the authoritative collision/culling root;
- duplicated thumb or floating finger geometry.

Subjective rejection also applies to generic robot gait, casual civilian walk,
symmetrical puppet motion, unnecessary acrobatics, low unreadable guard, or any
motion whose silhouette contradicts the intended EVA scene.

## 8. Review views and evidence

Every accepted motion must provide:

- interactive 3D viewer with scrubber;
- front, side, rear three-quarter and moving follow views;
- reference ghost and retargeted EVA shown together;
- root trajectory, COM, feet, contact normals and support polygon;
- 1.0x and 0.25x playback;
- transition entry and exit from at least four different preceding poses;
- numerical report for contacts, limits, penetration and continuity.

Minecraft screenshots are not an animation acceptance tool. Minecraft integration
begins only after this external review passes.

## 9. Candidate scoring

Score each source clip out of 100:

- 30 biomechanics and contact clarity;
- 25 EVA silhouette/style potential;
- 15 transition usefulness and root trajectory;
- 10 skeleton/format quality;
- 10 retarget feasibility;
- 10 licence and redistribution certainty.

Any hard rejection rule overrides the score. A main-library candidate requires
80 or more; 70–79 is supplemental; below 70 is reference-only or rejected.

## 10. Provisional first external-3D set

The following CMU clips are downloaded as candidates, not accepted motions:

1. `127_04` — walk to run;
2. `127_05` — run to quick stop;
3. `127_13` — running side-step left;
4. `127_14` — running side-step right;
5. `127_15` — running turn left;
6. `127_16` — running turn right;
7. `127_21` — run, jump, stop, run;
8. `16_08` — run/jog and sudden stop;
9. `140_01` — prone/face-down get-up;
10. `140_08` — supine/back get-up.

They are useful because they contain transitions and contact changes, not because
CMU capture automatically has EVA style. Retarget, contact repair and style
selection remain mandatory.

## 11. Performance principle confirmed by production references

The adopted interpretation is that an EVA is animated from human/biological
performance outward. Armour thickness, pylons and silhouette modify the visual
read, but they do not create a robot-style hinge vocabulary. This document does
not authorize frame copying from official EVA footage; it translates the
high-level performance principle into original Project SEELE motion direction.

The working rhythm is:

```text
pelvis initiates
  -> lower spine carries momentum
  -> thorax reacts or counter-rotates
  -> scapula and arm accelerate
  -> head resolves gaze
```

At giant scale, a fast action remains fast. Scale is read from the duration and
ordering of compression, plant, impulse, follow-through and environmental
reaction. Dust, camera shake and hit-stop may support that chain but cannot
replace it.

## 12. Continuous selection and interruption

The finished controller must not behave like a key that starts a canned clip.
At each search/update step it evaluates the actual ending pose, root velocity,
COM, planted contacts and desired future trajectory. The selected next frame is
constrained by domain, stance, weapon, support mode, obstacle envelope and
interrupt class.

- A start can redirect into locomotion without returning to idle.
- A run can enter a real braking or pivot plant selected for current momentum.
- A jump is interrupted only through physically plausible airborne/landing
  outcomes, never by snapping to a ground clip.
- A strike can be cancelled before commitment; after commitment, remaining
  momentum must be dissipated through recoil, recovery, contact or imbalance.
- A hit reaction begins at the contacted region, then affects support and COM.
- A fall and get-up start from the actual contact configuration.

Inertialization removes harmless pose/velocity discontinuities but never blends
through a strike, foot plant, landing, grab or impact event. Root warping is a
small target adaptation inside declared windows, not a substitute for missing
turns, climbs, weapon contacts or paired motion.

## 13. Expanded motion direction

### Breathing and alert

Breathing is not a sine-wave chest scale. Pelvis weight, thorax volume,
scapulae and neck have related but non-identical phases. Alert attention may
freeze partway through a breath. Damaged breathing changes support and shoulder
guard, not only playback speed.

### Braking

Braking begins before the final planted step: COM lowers, a braking foot reaches
ahead, pelvis continues briefly, and thorax/arms/weapon overshoot. An emergency
stop may add a corrective step. If the root stops before the body reacts, the
motion is rejected.

### Directional turning

Moving turns require an arcing root trajectory, explicit inside/outside support
roles and an exit strike into the new path. In-place turns require a pivot foot,
a lifted/free foot and a settling step. Left/right lead variants are separate
assets, not mirrored blindly.

### Fall and recovery

The causal sequence is support loss, attempted rescue step, ordered hand/knee/
forearm/body contact, remaining mass arrival, and a contact-compatible recovery.
Blending directly into a floor pose or pulling the root back under the pelvis is
a hard failure.

### Grapple

Paired grappling shares anchors and time. The combined COM and both support
polygons govern the exchange. Two unrelated solo clips played together cannot
represent pulling, resisting, throwing or escaping.

### Environment destruction

The body or weapon must establish contact before the environment fails. The EVA
shows resistance or recoil, and debris propagation follows the contact impulse
with a short scale-appropriate delay. Destruction particles appearing after an
unaffected canned swing fail the motion review.

## 14. Canonical rig requirements

The retarget/control skeleton must expose a genuine distributed trunk and
contact-capable limbs:

- `world_root`, `pelvis`, four spine segments, chest, two neck segments, head;
- clavicle and scapula before each shoulder;
- upper arm, forearm, wrist, hand and optional finger chains;
- thigh, shin, ankle, ball and toe;
- foot/hand IK targets and knee/elbow poles;
- independent weapon body, support/grip points, tip and butt;
- independent front/rear spear grips and spear tip.

Armour and shoulder pylons are visual children/secondary bones. They do not
participate in the human retarget solve. Missing feet, toes, clavicles, scapulae,
neck or wrists must be fixed in the rig before a corresponding movement family
can be accepted.

## 15. Source-to-style contract

Mocap provides contact order, momentum and connected human mechanics. It does
not provide the final EVA performance automatically. After retarget and contact
repair, the style pass may adjust pelvis lead, thorax delay, stance, outline,
timing and appendage follow-through, but every style edit must be followed by a
new contact/penetration solve and the same numerical gates.

The first ten production slices are therefore locomotion/control foundations:
alert idle, walk, jog/run, predatory sprint, sprint start, hard stop, moving
90-degree turns, in-place 180-degree turns, jump with three landing weights, and
directional imbalance/fall/prone recovery. Punching begins only after these pass.
