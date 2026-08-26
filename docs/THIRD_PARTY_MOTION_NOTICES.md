# Project SEELE — Third-Party Motion Notices

This file records motion sources evaluated by the external 3D pipeline. Raw
source files and private review renders are not committed to the public mod.
Promotion into a release pack additionally requires a per-clip provenance and
QA record.

## 100STYLE Dataset

- Creators: Ian Mason, Sebastian Starke and Taku Komura.
- Official page: https://www.ianxmason.com/100style/
- Archive record: https://zenodo.org/records/8127870
- Licence: Creative Commons Attribution 4.0 International.
- Licence text: https://creativecommons.org/licenses/by/4.0/
- Local use: strict allowlist selection, official-frame trimming, coordinate
  normalization, retargeting to the Project SEELE review skeleton, contact
  detection/repair and private QA rendering.
- Modifications must be identified whenever a derived clip is distributed.

## ACCAD Open Motion Project

- Creator/attribution party: Advanced Computing Center for the Arts and
  Design, The Ohio State University.
- Official page: https://accad.osu.edu/research/motion-lab/mocap-system-and-data
- Licence: Creative Commons Attribution 3.0 Unported.
- Licence text: https://creativecommons.org/licenses/by/3.0/
- Local use: exact-package download, source inventory, evaluated-axis
  normalization, retarget experiments, contact analysis and private QA.
- Distributed derivatives must give appropriate credit and identify changes.

## CMU Graphics Lab Motion Capture Database

- Creator/attribution party: Carnegie Mellon University Graphics Lab.
- Official page: https://mocap.cs.cmu.edu/
- Terms evidence: https://mocap.cs.cmu.edu/faqs.php
- Terms summary: the official FAQ permits copying, modification and
  redistribution without permission and permits embedding in products, but
  prohibits directly selling the data even after format conversion.
- ML training permission is not stated expressly and remains unverified.
- Local use: exact-trial research candidates only; no whole-library ingestion.

## Quaternius Universal Animation Library 2

- Creator: Quaternius.
- Official page: https://quaternius.com/packs/universalanimationlibrary2.html
- Licence: CC0 1.0.
- Local role: import/viewer/runtime placeholder QA only. These authored,
  stylised animations are not accepted as EVA biomechanics evidence.

## Code-only architecture references

The MIT-licensed JLPM22 MotionMatching implementation may be studied or
adapted with its copyright and licence notice:
https://github.com/JLPM22/MotionMatching

Its sample motion files and the separate Environment-aware Motion Matching
dataset are not assumed to inherit the code licence. They require independent
data provenance before use.
