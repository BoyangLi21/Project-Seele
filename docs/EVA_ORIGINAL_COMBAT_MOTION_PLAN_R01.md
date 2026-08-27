# Project SEELE — original-aligned EVA combat motion plan R01

Date: 2026-08-27

Status: research and external-3D production plan; no new combat motion in this
document is approved for Minecraft integration.

## 1. Corrected interpretation

An EVA may punch, but it does not normally fight like a sport boxer. In the
Sachiel encounter the recognisable sequence is a committed charge, two-arm
control, arm breaking, a kick, a mount and repeated close strikes. Israfel is
finished by a paired flying kick. Sahaquiel is caught and restrained by three
Evas before the knife finish. Arael is defeated by a full-body javelin throw.
The End of Evangelion's Unit-02 sequence is described academically as weighted
swings and blowback combined with messy grappling and efficient executions,
not a clean ring combination.

These are action-semantic observations only. Project SEELE does not copy
official animation frames, models, audio, screenshots, timing or cameras.

Sources used for action semantics:

- [Sachiel battle summary](https://evangelion.fandom.com/wiki/Sachiel)
- [Episode 9 / Israfel synchronized finish](https://evangelion.fandom.com/wiki/Episode%3A09)
- [Sahaquiel three-EVA catch and knife finish](https://evangelion.fandom.com/wiki/Sahaquiel)
- [Arael / Spear of Longinus throw](https://evangelion.fandom.com/wiki/Spear_of_Longinus)
- [The End of Evangelion embodied-performance analysis](https://www.stockholmuniversitypress.se/en/chapters/65/files/976c98ac-8a93-4197-843c-d1e2d77459c4.pdf)

The source hierarchy is therefore:

1. whole-body entry and support;
2. ward, control or target acquisition;
3. one committed impact, kick, throw or weapon action;
4. contact-dependent continuation;
5. visible recovery, pursuit or disengagement.

A neutral `jab -> cross -> reset` loop is excluded.

## 2. Free-combat grammar

Free combat is assembled from short, contact-labelled motion fragments. It is
not a list of long clips bound one-to-one to keys.

The current machine-readable prototype is
`tools/eva_combat_action_graph_r01.json`; its structural validator passes
thirteen nodes and twenty-one conditional edges with no missing hit/miss
resolver. It is a
controller contract, not evidence that the motions are already finished.

| Family | Purpose | Required contacts | Miss / interruption result |
|---|---|---|---|
| forearm/open-hand ward | redirect an incoming limb or make space | forearm/palm to target limb | guard remains open; short step or recoil |
| body entry | close distance behind a ward | support plant, optional shoulder/torso contact | brake step, collision brace or pounce branch |
| two-hand shove | move an already controlled target | both palms/forearms and both support feet | hands retract while pelvis continues briefly |
| push/front kick | create distance or expose the core | one support patch, striking sole/heel | recoil leg and recovery step; never snap to idle |
| low kick / reap | disrupt support | plant plus lower-leg/ankle target | pivot recovery or stumble if it misses |
| clamp / grab | convert contact into control | one or two palm contacts plus low relative speed | compliant six-DOF grip or release |
| pull / arm wrench | move or disable a grabbed limb | paired hand/limb anchors | grip breaks naturally when force budget is exceeded |
| shoulder/body ram | high-momentum close entry | shoulder/chest target and rear-leg drive | bounce, brace or fall according to impulse |
| forward pounce | rapid pursuit and contact acquisition | launch plant, flight, target/ground landing envelope | target catch, braced four-point landing, roll or miss recovery |
| mounted strike | contextual close finish, not neutral attack | knees/feet/pelvis support on ground/target | target reaction changes subsequent strike path |
| grounded stomp | contextual pressure on an already grounded target | single support, striking sole and target surface | ground recoil, balance step or target-dependent continuation |

### Input and comfort contract

- The input buffer is about 120 ms, but it stores intent rather than an
  animation identifier.
- Before commitment, a new direction or guard request may rebuild the future.
- After launch/impact commitment, remaining momentum must be discharged through
  contact, recovery step, fall or target motion.
- The next branch is selected from actual pose, COM velocity, support, range,
  facing and target contact. It never restarts from a canonical guard frame.
- No branch may wait for an unrelated long clip to finish. Contact and recovery
  windows are explicit.
- A miss is a real authored/controlled outcome, not the same strike continuing
  through empty air until its original duration expires.

## 3. First playable combination families

These are graphs, not mandatory fixed sequences.

### Piloted Unit-01 — urgent brawler

```text
forearm ward
  -> committed body entry
      -> push kick when target remains outside grab range
      -> shoulder/body ram when momentum is already committed
      -> two-hand clamp when target contact is established
          -> arm wrench / low reap / shove / wall pin according to target support
```

It should look powerful and occasionally improvised. The pilot is not a boxer,
but body mechanics remain connected and readable.

### Unit-00 — defensive restraint

```text
brace or high ward
  -> outside deflection
      -> two-hand shove
      -> limb restraint if the opponent continues forward
      -> disengage step when the threat leaves range
```

Small anticipation, efficient travel and clear support are favoured over
flourish.

### Unit-02 — technically aggressive

```text
angle step + outside ward
  -> low/front kick
      -> lateral pursuit
      -> high kick or Progressive Knife draw branch
```

The silhouette is decisive and athletic. Spinning actions are contextual and
must preserve a visible plant; they are not repeated spectacle moves.

### Berserk Unit-01 — predatory contact

```text
low pursuit / pounce
  -> two-hand clamp
      -> wrench / throw / mount
          -> maul, tear, grounded stomp or bite contact family
```

This family uses lower COM, hand/foot support, spinal participation and sudden
commitment. Random joint noise, limp ragdolling and generic animal crawl are
rejected.

## 4. Forward pounce design

The pounce is a first-class traversal/contact action:

1. rear/lead-foot compression and target lock;
2. pelvis-led launch with both arms preparing for contact;
3. short airborne steering limited by angular momentum and available landing;
4. one of four resolutions:
   - chest/shoulder collision and clamp;
   - two-hand target catch with feet arriving later;
   - four-point braced ground landing;
   - miss, roll/step recovery or destructive collision.

ACCAD `B18_WalkToLeapToWalk` frames 40–91 now provide the first accepted
launch/flight reference. Its source landing around frames 92–93 contains a
real lower-body discontinuity and is rejected rather than smoothed. CMU
`49_04`, `49_05`, `127_23` and `127_24` remain trajectory/contact-order
references. The final pounce needs project-authored target contacts and
physical tracking; dataset labels do not make any capture an EVA action.

## 5. Contextual finishers

Finishers live outside the free-combat search domain. Each uses a paired or
multi-actor interaction rig, target-specific anchors and a failure/abort path.

Ten detailed interaction graphs with 47 contact-labelled stages are stored in
`tools/eva_contextual_finisher_graphs_r01.json`. Their structural validator
passes; all ten still correctly report their target rigs as pending.

| Encounter | Recognisable high-level beats | Runtime gate | Production method |
|---|---|---|---|
| Sachiel | AT-field breach, two-arm control, arm wrench/break, kick-away, leap/mount, core assault | Sachiel staggered, field neutralised, both arms reachable | paired interaction graph plus physical target; original Project SEELE timing/camera |
| Shamshel | tentacle control, close advance under pressure, committed Progressive Knife core thrust | knife equipped, core exposed, cable/tentacle contacts valid | target spline/tentacle constraints plus knife contact solve |
| Ramiel | shield/cover coordination and positron shot | Operation Yashima state, charge and aim solved | existing weapon system plus cinematic coordination; no generic melee |
| Gaghiel | unstable ship traversal, mouth restraint and internal attack resolution | naval encounter state and jaw anchors | multi-body paired scene; not a reusable free combo |
| Israfel | two-EVA synchronized approach and paired flying kick | both units alive, timing/synchronisation and both cores exposed | two-character future constraints and shared landing timeline |
| Sahaquiel | sprint interception, Unit-01 catch, three-EVA load sharing, core exposure and knife finish | all required units/roles present | three-character interaction graph with falling target load |
| Bardiel | close grapple, neck/head restraint and dummy-plug execution | story/dummy route only | paired physical grapple; deliberately uncomfortable, not player neutral combo |
| Zeruel | desperate close entry, limb control/tear, berserk pursuit and devour outcome | berserk/story outcome and target anatomy available | physical paired sequence with target damage states |
| Arael | retrieve, brace and full-body Lance javelin throw | Unit-00, Lance equipped, orbital target solution | long-object inertia and release trajectory; Unit-00 signature finisher |
| Leliel | internal brace, tear a rupture, four-point emergence and weighted rise | absorbed Unit-01, destructible internal volume, berserk story trigger | volume-contact solve plus crawl/recovery; no free-combat activation |
| Armisael | restraint/fusion crisis and Unit-00 sacrifice | explicit story choice only | authored multi-phase event, never a normal combat input |
| Mass Production Evas | Unit-02 running executions, heavy swings/blowback, grapples, knife/weapon improvisation | EoE scenario, battery pressure and multiple targets | contact-driven kill graph with target handoff, not one long montage clip |

The target is recognition through action logic, not frame-perfect reproduction.

The executable first-wave order, exact source windows and current pass/block
state are maintained in `docs/EVA_COMBAT_FIRST_12_BUILD_QUEUE_R01.md`. Actions
with no valid open paired source use the project-owned multi-view recording
plan in `docs/EVA_PROJECT_MOCAP_CAPTURE_PLAN_R01.md` rather than invented AI
keyframes.

## 6. Source data selected for external screening

### Existing ACCAD CC BY 3.0 candidates

- wards/deflections: `Male2_E11_BlockLeftHigh`,
  `E13_BlockRightHigh`, `E15_BlockLeftMiddle`, `E16_BlockRightMiddle`;
- evasive entries: `E19_DodgeLeft`, `E20_DodgeRight`, `E4_QuickAdvance`,
  `E7_SuperFastAdvance`;
- kicks: `G2_FrontKick`, `G17/G18_PushKick`, selected side/roundhouse kicks;
- pounce/traversal ingredients: `B18_WalkToLeapToWalk`,
  `C19_RunToJumpToWalk`, `A11_Crawl` as reference only;
- continuous martial captures are segmented before use; their labels do not
  bypass biomechanics review.

### Newly fetched CMU source seed

The reproducible seed is built by
`tools/fetch_eva_original_combat_seed.ps1`. It contains 38 BVH source
candidates with hashes and official catalogue snapshots:

- paired pull/resistance: `18_03-06` with matching `19_03-06`;
- run/leap and dive/roll: `49_04-05`, `127_23-24`;
- aerial kick references: `90_05-07`;
- front/roundhouse references: `135_04`, `135_07`;
- blocks, reaches, lunges and front kicks: selected `144_05-29`;
- `141_14` remains broad sequence/reference data, never an auto-approved combo.

The [CMU official site](https://mocap.cs.cmu.edu/) permits copying,
modification and redistribution and asks for acknowledgement. The corrected
source audit (with capture-edge import spikes excluded) produced 16 initial
shortlists, four pounce references, three aerial-kick references, eight
paired-review items, two contact-repair-required candidates, four source
rejects and one broad reference-only sequence. Automatic screening is not
aesthetic acceptance.

Research-only or non-distributable datasets stay outside the production corpus.
CMU/ACCAD sources provide biomechanics; project-specific contact design remains
our work.

### Expanded CMU paired-contact shortlist

The official CMU human-interaction catalogue exposed several better transition
sources than generic fight clips. They were downloaded with the same licence
evidence and hash manifest and screened in shared source space:

- `20_10/21_10`: 360-degree two-person whip, right hand/wrist contact for about
  `0.67 s`; arm-wrench and pivot/throw reference;
- `22_05/23_05`: left/right hands placed on opposite shoulders; first
  two-hand clamp and shove-setup reference;
- `22_12/23_12`: one actor stumbles into the other; shoulder/body collision,
  miss-brace and stagger reference rather than damage ground truth;
- `22_17/23_17`: rush-up arm wrestle with about `0.73 s` mutual hand contact;
  grip-strength and break reference;
- `22_01/23_01` and `22_02/23_02`: one-/two-hand pull-up interactions for
  grounded-target recovery and lift constraints;
- `22_10/23_10` and `22_11/23_11`: shelter/support interactions retained for
  protective cover and Sahaquiel load-sharing reference.

Exact windows and measured contact envelopes are in
`tools/eva_paired_interaction_source_catalog_r01.json`. None authorizes playing
the cooperative post-contact motion after a real target resists.

### Cologne Motion Capture Database CC BY 4.0 supplement

The [official CMCD licence page](https://mocap.web.th-koeln.de/about.php)
licenses its BVH/C3D motion and annotations under CC BY 4.0. A reproducible
private seed is fetched by `tools/fetch_cmcd_eva_combat_seed.ps1`; its manifest
records URLs, byte counts and SHA-256 hashes for eight files.

The corrected original-skeleton screen reports four paired-review actors, one
aerial-kick reference and three reference-only sequences. The jump-kick audit
was fixed to select a strike during actual two-foot flight rather than prefer a
planted-foot event; its aerial foot reaches about `0.726 H`.

Shared-space review narrows the paired material further:

- the 2018 Safari/Dschungel pair contains sustained two-hand contact around
  source frames 1033–1144. It is useful for hand fighting, second-hand attach
  and release, not for default striking;
- the 2019 Eunuche/Nussknacker pair contains only a very short foot-to-hand
  envelope around frames 823–827. It remains a kick/block timing reference,
  not an accepted paired attack;
- the forward roll, hit/tumble/fall and `KingKong2` sequences remain segmented
  references. `KingKong2` is explicitly a negative example: ape imitation is
  not automatically berserk EVA motion.
- `Take_2019-01-09_N_Nussknacker3` frames 340–390 is the first right low-line
  kick shortlist: its event is at frame 363, swing height is about `0.229 H`,
  the opposite foot is planted and its local support travel is about `0.073 H`.
  It is not yet a reap because there is no target-leg contact. ACCAD G8 was
  removed from that role after measurement showed a `0.714 H` high roundhouse.

## 7. Interaction implementation

Free action and cinematic interaction share one physical contract:

- physical skeleton/root is authoritative;
- target limbs, core, jaw, tentacles and weapons expose typed contact anchors;
- a paired action is represented by an interaction graph of relative body
  landmarks, not two independent clips;
- target scale and morphology are solved before the first committed contact;
- server damage comes from contact impulse and target region;
- the cinematic camera is optional presentation and never repairs bad body
  mechanics.

The research basis is consistent with
[simulation and retargeting of multi-character interactions](https://arxiv.org/abs/2305.20041),
which preserves relationships between interaction landmarks, and with
[MaskedMimic](https://research.nvidia.com/labs/par/maskedmimic/), which treats
partial body/contact objectives as constraints for physical control. These are
method references, not permission to copy their training data or models.

### Physical-rig checkpoint R01

The strict grounding revision invalidated the first pass, whose horizontal
drift test had omitted absolute sole height. After re-export, short action
windows and sparse whole-window contact/manifold optimization, the left ward
(frames 10–26), right ward (8–23) and ACCAD G18 right push kick (23–48) now
pass the whole kinematic gate. B18 pounce launch and the shared-frame CMU
`18_05/19_05` grab attach remain useful source/contact references but are
blocked from promotion. The pair still stops at attachment: post-contact
pulling is reserved for a bounded physical grip constraint.

These are kinematic references, not a trained policy and not Minecraft-ready
animations. Exact metrics, rejected variants and the R03 hand-bind correction
are recorded in `docs/EVA_COMBAT_PHYSICAL_RETARGET_R01.md`.

## 8. Mandatory quality gates

Existing contact, joint-limit, self-intersection and root-continuity checks
remain. Combat adds:

- evaluated shin/foot surface seam growth `<= 0.005 H` over the model's neutral
  baseline;
- evaluated forearm/hand and upper-arm/shoulder seam checks using the same
  method;
- bone endpoints alone never count as mesh continuity evidence;
- support-foot accumulated travel `< 0.005 H` and P95 speed `< 0.02 H/s`;
- intended contact point error `<= 0.01 H`;
- paired anchor error `<= 0.01 H` at contact and `<= 0.02 H` during struggle;
- no damage without a new closing contact and threshold impulse;
- no re-damage while one contact pair remains continuously closed;
- pre-commit redirect response P95 `<= 40 ms`;
- no target/root teleport on hit, miss, cancel or finisher abort;
- every attack must provide front, side, rear-three-quarter, follow and
  target-relative 3D evidence at 1.0x and 0.25x.

R19 fails this contract: its hierarchy remained connected, but the visible
ankle seam grew roughly `0.050/0.056 H` because relative ankle rotation reached
about `84/130 degrees`.

### Current ankle-rig blocker

The present 64-bone review rig has one rigid `shin -> foot` joint and no
separate ankle pitch/roll, ball or toe chain. A left-ward experiment proved
that this is not a cosmetic problem:

- locking both feet produced excellent low-foot speed (about
  `0.00004/0.00002 H/s`) but grew the visible seam by roughly
  `0.030/0.023 H`;
- capping visual ankle delta to five degrees made the seam-growth gate pass,
  but increased low-foot/toe P95 speed to about `0.22 H/s` and introduced false
  airborne frames;
- an overlaid dark joint volume and simple boundary-weight smearing were tried
  locally and rejected because they hid rather than solved the missing
  articulation.

No combat retarget using this leg chain can be promoted. The production rig
must add explicit ankle pitch/roll, ball and toe bodies plus a genuinely
skinned flexible joint region. Contact locking then targets heel, forefoot and
toe patches rather than rotating one rigid foot shell around a single pivot.

The machine-readable physical-to-visual contract is
`tools/eva_physical_visual_rig_contract_r01.json`. Auditing the R19 rig reports
nine missing production bones: `ankle_l/r`, `toe_l/r`, `clavicle_l/r`,
`wrist_l/r` and `neck`. Eleven flexible interfaces are consequently blocked.
This also explains the earlier shoulder, wrist and head/torso failures; the
ankle is simply the first one exposed by the new mesh-level test.

## 9. Production order

1. **Physical skeleton done, visual bind still blocked:** the 41-DOF R03
   physical model has ankle pitch/roll, toe, clavicle, neck and wrist
   articulation and passes axis/mirror/model checks. The Minecraft visual mesh
   still needs the corresponding genuinely skinned bones and mesh-seam gate.
2. Make the evaluated-mesh seam audit part of every retarget CI run.
3. Continue original-skeleton review beyond the first shortlists; preserve
   exact provenance, event windows and explicit rejects.
4. **First physical references done:** both wards and the right push kick pass
   the strict contact-manifold gate. Continue the pounce whole-window solve;
   add the left kick only after it independently passes (never by mirroring).
5. **Paired relative attach found, grounding pending:** CMU `18_05/19_05`
   frames 165–219 preserve shared spacing and close the hand/elbow envelope,
   but both actors must be re-solved against the ground before promotion.
6. Build the compliant two-body grip experiment only from a newly grounded
   terminal state; test resistance, break force, falls and deterministic replay.
7. Build `ward -> entry -> kick/grab/ram/reap` as a continuous branch graph and
   test all miss, block, collision and interruption outcomes.
8. Build all four pounce resolutions from the accepted launch rather than
   importing the corrupt source landing.
9. Author the Sachiel finisher prototype on a dedicated target rig, then the
   Israfel and Sahaquiel multi-actor gates.
10. Add Unit-00 and Unit-02 style selection layers without changing mechanics.
11. Integrate only human-approved, physically tracked results into Minecraft.
