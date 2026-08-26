# GPT-5.6 Pro brief — original-aligned EVA combat motion system

You are the independent combat-movement researcher and action director for
Project SEELE. Do not accept the project's prior assumptions merely because
they are stated below. Search the web and primary/official catalogues wherever
possible, distinguish documented fact from inference, and give exact source
links, licences and motion identifiers.

## Project goal

Build a comfortable, high-end EVA combat system for an open-source Minecraft
Forge 1.20.1 project. The target is not Minecraft-quality animation and not a
generic mecha game. The body must combine athletic human mechanics, giant-scale
momentum, the original Evangelion work's living/biological movement and
unit-specific performance.

No official Evangelion animation, model, texture, screenshot, audio or camera
sequence may be downloaded or copied. High-level action semantics and critical
analysis may be used to create new Project SEELE choreography.

## Correction that triggered this review

The first ordinary-attack prototype used ACCAD `Male2_E1_JabLeft` and
`Male2_E4_CrossRight`. It was rejected:

1. a sport-boxing jab/cross reads unlike the original EVA neutral combat
   vocabulary;
2. the skeleton endpoints stayed connected, but contact repair rotated the
   ankles about 84/130 degrees from baseline, expanding the visible rigid-mesh
   shin/foot seam by about 0.050/0.056 body heights.

Do not recommend merely polishing that combo.

## Local candidate corpus already available

- ACCAD Male-2 CC BY 3.0: high/mid blocks, dodges, advances, front/push/side/
  roundhouse/spinning kicks, leaps, crawls, punches and extended sequences.
- CMU official reuse terms, selected 120 Hz BVH conversions:
  - paired pull/resist: subjects 18 and 19, trials 03-06;
  - run/leap and dive/roll: 49_04-05 and 127_23-24;
  - jump kicks: 90_05-07;
  - martial/front kicks: 135_04/07 and 144_05/06/09/10;
  - blocks/lunges/spin reaches/reaches: 144_07/08/11/12/15-18/22-29;
  - 141_14 punch-and-kick sequence, reference only.
- 100STYLE CC BY 4.0 locomotion foundation.
- ProtoMotions/Isaac Lab/MuJoCo physical-control research path exists, but no
  EVA production tracker has been trained yet.

## What to research and deliver

### A. Original combat vocabulary

Create an encounter-by-encounter semantic action catalogue for TV series, The
End of Evangelion and relevant Rebuild fights. At minimum cover Unit-00/01/02,
Sachiel, Shamshel, Ramiel, Gaghiel, Israfel, Sahaquiel, Bardiel, Zeruel, Arael,
Armisael and the Mass Production Evas.

For each encounter identify:

- approach and support mechanics;
- wards, blocks, grabs, kicks, throws, weapon actions and recoveries;
- which beats belong in free combat;
- which beats should be target-specific finishers;
- unit/pilot style;
- what must not be copied frame-for-frame;
- what makes the motion feel like EVA rather than sport boxing, martial-arts
  kata, generic robot combat or weightless anime spectacle.

Do not claim that EVAs never punch. Determine how punches are actually used and
why that differs from a neutral boxer 1-2.

### B. Free-combat combo grammar

Design a branching, contact-aware graph containing at least:

- forearm/open-hand wards;
- body entry and shoulder/body ram;
- two-hand shove;
- front/push kick and one lower-line kick;
- clamp/grab, pull, wrench, restraint and release;
- forward pounce with hit, miss, four-point landing and destructive-collision
  outcomes;
- contextual mounted strikes;
- separate Unit-00, piloted Unit-01, Unit-02 and berserk Unit-01 styles.

For every edge specify range, support, contact, COM/momentum, interrupt window,
miss recovery and damage-contact requirements. The graph may never reset to a
canonical guard between every input.

### C. Target-specific finishers

Propose recognisable but newly choreographed paired/multi-actor finishers for
the encounters above. Specify participants, typed contact anchors, trigger
conditions, abort conditions, target damage states, camera independence and
physical/network authority. Prioritise the first three vertical slices.

### D. Exact motion sources

Search for the best legally usable source motions and paired-interaction data.
Give exact clip/trial IDs and official licence URLs. Check the local ACCAD/CMU
list first, but search further sources such as Cologne Motion Capture Database,
AddBiomechanics and other university/open datasets. Separate:

- distributable production source;
- research/reference only;
- unusable or licence-uncertain.

Do not recommend commercial game animations or official EVA animation simply
because the project is non-commercial.

### E. Production method

Give a concrete external-3D workflow for:

- source segmentation and contact labels;
- retarget onto a long-limbed EVA rig;
- evaluated-mesh joint continuity, not only bone continuity;
- paired interaction graphs;
- contact-aware physics tracking;
- continuous interruption and transition selection;
- 3D review evidence and automatic gates.

Explain which parts can use deterministic motion matching now and which need
trained physical tracking later. Avoid a vague “use RL” answer.

### F. Immediate execution list

End with:

1. the first 12 free-combat fragments to build;
2. the first three finishers to build;
3. exact source files for each;
4. the first paired-contact experiment;
5. numerical acceptance gates;
6. routes we should stop investing in.

The result must be detailed enough that Codex can execute it without inventing
missing choreography. Do not return a mood board or a generic list of attacks.
