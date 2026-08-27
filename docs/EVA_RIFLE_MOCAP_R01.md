# Project SEELE — Pallet Rifle human-mocap stance R01

Date: 2026-08-27

## Source decision

The source is CMU Graphics Lab subject 80, trial 03, officially indexed as
`shooting a gun`. It is a real 120 Hz human motion-capture take. CMU permits
copying, modification and use in products; the ignored local BVH has SHA-256
`604C89ED2C293FDF36A5B7375EB43BEB769A7F59D0B6CFE70136A004A4F2479C`.

CMU 79_96 was screened independently and rejected for the Pallet Rifle. Its
active poses do not preserve the characteristic long-gun separation between a
rear trigger hand and forward support hand.

In the accepted 80_03 long-gun window, the support hand remains about `0.30 H`
farther downrange than the trigger hand. The captured local upper-torso pose at
the selected stable frame is transferred as authored XYZ degrees
`[4.67256, 2.36232, -3.90043]`.

## Target-rig treatment

Only the captured torso lean and shoulder-line intent are transferred
directly. Human limb lengths cannot preserve the existing Pallet Rifle grip on
the asymmetric Tiger rig, so the reviewed target-specific arm solve remains
responsible for the rear grip, fore-end and muzzle direction.

The 0.18-second automatic-fire layer now recoils around the same captured
torso pose and returns to it. It no longer changes weapon family or substitutes
the positron-cannon stance during a Pallet Rifle shot.

No firing damage, range, cooldown, spread or ammunition value changes are part
of this revision.
