# Project SEELE — Active Decisions

This file is intentionally short.  It records current implementation contracts
that must survive context compaction; historical discussion belongs in handoff
archives.

## 2026-08-18 — TV armament building, phase one

- EVA intrinsic equipment remains bare hands + Progressive Knife; Unit-00 also
  keeps its intrinsic N² device.
- The first external station carries one Pallet Rifle vertically.
- The sealed pod contains no copper-coloured exterior structure.  Its rifle is
  rotated 180 degrees only around the vertical axis.  A large split NERV logo
  belongs to the two front door leaves and travels sideways with them.
- The station is a persistent entity with a smooth ground-hatch/rise/pod-door/
  ready/empty/pod-door/lower/ground-close state machine.  A fully sealed armour
  pod rises first; only after it stops do two front doors reveal the vertical
  rifle.  It must not move terrain blocks per tick.
- An EVA receives the rifle only while piloted, within the physical pickup
  radius, while the station is READY and stocked.
- Completing a full return cycle replenishes the next rifle.  Formal Tokyo-3
  placement and command-room button wiring wait for visual approval.

## 2026-08-18 — EVA surface silo doors

- All three EVA surface heads use paired left/right sliding armour leaves.
- A split NERV logo spans the closed doors and follows each leaf while opening.
- Door animation is entity-rendered and follows actual launch/recovery height;
  it must not repaint the 31x31 shaft mouth one block row per tick.

## 2026-08-18 — Hangar observation relocation

- Personnel elevators remain at their current coordinates until the user
  supplies the new endpoints.
- The obsolete front upper observation storey at y=-386..-373 is retired.
  The lower y=-395 personnel frontage stays intact and owns three five-wide
  face bridges ending at z=148.
- The replacement rear observation hall uses floor y=-371, roof y=-363 and
  SEELE clear glass on the three wet-cage-facing panels at z=187.
- `S26-HANGAR-OBSERVATION-RELOCATION-R01` is applied to R28 with an exact
  region backup and must not be overwritten by the legacy gallery builder.

## 2026-08-18 — Compact-cage personnel lift relocation

- The former `(108,*,192)` and intermediate `(89,*,204)` lifts are retired.
  The final axis is `(93,*,204)`: lower walk `y=-442` opens south; upper walk `y=-370` opens
  north onto the observation floor block at `y=-371`.
- The complete lower branch moves from `x=104..112` to `x=89..97` through
  `z=197..270`; the `z=270` mouth remains open into the retained pyramid route.
- Only the launch-plant-facing shaft wall at `x=89` uses SEELE clear glass;
  the east/north/south shaft walls are reinforced deepslate.  The moving cage
  remains glass, and its floor selector belongs to the east wall at `x=95`.
- The removed S26 upper room remains retired, while the accidentally deleted
  `z=133` cage pressure fronts and shared ribs are restored.

## 2026-08-20 — Angel-model acquisition and Giant Rei

- The preferred Giant Naked Rei / Lilith-Rei source is the 13-part Cults3D
  sculpture recorded in `docs/ANGEL_MODEL_ACQUISITION.md`.  It is not ready
  for Minecraft as downloaded: the required pipeline is assembly, retopology,
  UV/material consolidation, full-body rigging, twelve-wing rigging, and an
  explicit Third Impact animation contract.
- Current high-detail Angel coverage is Ramiel, Sachiel and Lilith.  Israfel's
  reused Sachiel silhouette and the procedural Shamshel/Zeruel bodies remain
  placeholders, not accepted final models.
- Missing TV/EoE Angels are tracked in one acquisition ledger rather than
  being recreated ad hoc.  Paid print-only assets may be used for private
  evaluation but are never redistributed; official game rips are reference
  only and may not enter a release pack.

## 2026-08-20 — Escalators and moving walkways

- Create and Create: Escalated remain retired.  They are not candidates for
  NERV personnel circulation.
- Minecraft Transit Railway 4.0.5 for Forge 1.20.1 is the selected dependency.
  Its escalator blocks support inclined runs, horizontal moving walkways and
  reversible travel direction without Create; its later rail, aircraft,
  cable-car and lateral-lift systems are deliberately retained for future use.
- Every escalator replacement is a paired installation: one up and one down.
  Do not remove the last fixed emergency stair serving a level.
- Horizontal moving walkways belong only in confirmed long, straight
  corridors.  They supplement the normal walking floor and may not consume
  the entire corridor width or block doors, branches and emergency egress.
- No escalator or walkway is written into the authority map until its exact
  endpoints, direction, width and retained static route are locally surveyed
  and approved.
- The first approved horizontal trial is `x=45..84, y=-370, z=189..190` eastbound
  and `z=195..196` westbound.  It follows left-hand traffic and preserves all
  authored floor/light blocks plus six blocks of ordinary walking width.  The
  reversible S36 patch and exact region backup are under
  `artifacts/s36_mtr_walkways_20260820_234130`.
- S36 was superseded after visual review: its raised continuous run was removed.
  S37 recesses the steps into floor `y=-371` and follows the three measured
  observation-window bays exactly: EVA-00 `x=-30..6`, EVA-01 `x=12..48`,
  EVA-02 `x=54..90`.  Structural gaps `x=7..11` and `x=49..53` remain normal
  floor.  The reversible receipt and two exact region backups are under
  `artifacts/s37_mtr_three_bays_20260821_000141`.
- S38 installs the three later human-requested pairs without altering adjacent
  rooms: the `x=91..95, z=212..269` long corridor has north/south moving walks
  with `x=93` retained as ordinary floor; the `x=50..57` stair has a new
  west/down lane at `z=274..275` with the authored `z=273` stair retained; and
  the stair centred on `(28,-403,259)` has down/up lanes at `x=26..27` and
  `x=29..30`, retaining the complete `x=28` emergency stair.  Its reversible
  receipt and exact region backup are under
  `artifacts/s38_requested_mtr_escalators_20260821_004010`.
