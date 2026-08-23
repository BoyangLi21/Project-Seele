# Project SEELE — Angel model acquisition ledger

Updated: 2026-08-20.  This is a sourcing ledger, not proof that an asset has
been downloaded, licensed for redistribution, optimized, rigged, or accepted
in game.  Every selected asset still needs a source archive, author/license
record, conversion receipt, visual review, and final attribution entry.

## Current project coverage

| Subject | Current state | Final-model status |
|---|---|---|
| Ramiel | Native procedural octahedron/deformation renderer | Retain; no external mesh needed |
| Sachiel | Local high-detail external model (`external-assets/incoming/sachiel.zip`) | Present; still needs final visual acceptance |
| Lilith | Local Solodovnykov/Kiki conversion | Present; separate from Giant Rei |
| Israfel | Reuses the Sachiel-derived silhouette | Placeholder; must be replaced |
| Shamshel | `ColossalHumanoidRenderer` procedural body | Placeholder; must be replaced |
| Zeruel | `ColossalHumanoidRenderer` procedural body | Placeholder; must be replaced |
| Mass Production EVA | Local high-detail model | Present; EoE vessel, not an Angel |

## Priority acquisition queue

### P0 — replace visible placeholders

| Subject | Preferred candidate | Format / terms | Conversion work |
|---|---|---|---|
| Shamshel | [Epic3DCreations seven-Angel bundle](https://cults3d.com/en/users/Epic3DCreations/bundles/angeles-evangelion) or [standalone Cults flying Shamshel](https://cults3d.com/en/3d-model/art/evangelion-shamshel-flying) | Paid STL; private evaluation only unless separate permission is obtained | Retopology; central body rig; articulated tail; two energy-whip sockets |
| Israfel | [Epic3DCreations Israfel](https://cults3d.com/en/3d-model/art/septimo-angel-israfel) | Nine-part paid STL; private evaluation only unless separately licensed | One clean humanoid rig plus deterministic split into Alpha/Beta bodies; shared-core contract |
| Zeruel | [Tigerar1 Zeruel](https://sketchfab.com/3d-models/none-9d7803809f7f45d6afb7022dd6c6419e) | Downloadable, CC BY-SA; about 2.4k faces | Rebuild paper-arm topology, eye-beam sockets, core and damage states; preserve attribution/share-alike |

The [Models Resource Shamshel](https://models.spriters-resource.com/psp/evangelionshingekijoban3ndimpact/asset/301435/)
and the Evangelion Jo Zeruel are useful proportion/texture references only.
They are official-game extractions and must never enter the distributable mod.

### P1 — solid-body Angels not yet implemented

| Angel | Candidate | Format / terms | Intended implementation |
|---|---|---|---|
| Gaghiel | [TrebleExtension Gaghiel](https://sketchfab.com/3d-models/none-0f4a0b12ff804e9cb76c0765782ff152) | Downloadable CC BY; about 146.5k faces | Retopologize and rig spine, jaw, fins and swimming body; ocean encounter |
| Sandalphon | [StarlightLambda64 Sandalphon](https://sketchfab.com/3d-models/none-39667c0aa572421a967fb5f44604ed1f) | Downloadable Free Standard; 368 faces | Use as proportion seed, then rebuild lava larva/adult states and heat shader |
| Matarael | [Epic3DCreations bundle](https://cults3d.com/en/users/Epic3DCreations/bundles/angeles-evangelion) or [StarlightLambda64 Matarael](https://sketchfab.com/3d-models/none-5145c106569d42c399d4c70e6bf45cad) | Paid STL or downloadable Free Standard low-poly | Four-leg rig, underside eye/core and corrosive-fluid emitter |
| Sahaquiel | [Epic3DCreations bundle](https://cults3d.com/en/users/Epic3DCreations/bundles/angeles-evangelion) or [StarlightLambda64 Sahaquiel](https://sketchfab.com/3d-models/none-706e3ac7b74b401caf9cae9f0c0162d9) | Paid STL or downloadable Free Standard, 780 faces | Orbital body, falling deformation, AT-field impact and catch sequence |
| Bardiel / EVA-03 | [Tigerar1 EVA Unit-03](https://sketchfab.com/3d-models/evangelion-unit-03-a16b14e3d34d45c9aa26611ee884d9d7) | Downloadable CC BY-SA; about 4.6k faces | Reuse the EVA humanoid rig; add infection veins, telescoping limbs and possessed poses |
| Tabris / Kaworu | [Dean Kaworu fanart](https://sketchfab.com/3d-models/kaworu-nagisa-fanart-b5eb0d034e0c46d78b43bdcfc0ea8e58) | Downloadable CC BY; about 9k faces | Humanoid rig, hovering/AT-field animation and Terminal Dogma sequence |

For Bardiel, the [official-game extracted Bardiel](https://models.spriters-resource.com/psp/evangelionshingekijoban3ndimpact/asset/302016/)
is reference-only and cannot ship.

### P2 — Angels whose identity is primarily an effect

| Angel | Candidate / approach | Decision |
|---|---|---|
| Ireul | No useful stable-body model found | Implement as a procedural biological circuit/infection spreading over authored surfaces; do not force it into a humanoid mesh |
| Leliel | [Nicolas Sazo Leliel](https://sketchfab.com/3d-models/none-f8cf4aca42684e0d85a0f5a33d186de8) (downloadable CC BY, about 2.9k faces) | Mesh may seed the striped sphere; the actual body is the planar shadow/Dirac Sea and should remain an effect system |
| Arael | No downloadable production-quality candidate found | Build as orbital light-body, halo and directed mind-beam; a conventional mesh is unnecessary |
| Armisael | [Fllocox 3D interpretation](https://www.reddit.com/r/evangelion/comments/jo6aca/evangelion_angels_in_3d_armisael/) is reference only | Use a procedural luminous double helix/ribbon with deformation and parasitic fusion states |

### Story/Impact assets

| Subject | Candidate | Status and work |
|---|---|---|
| Adam embryo | [Sample A-01 / Adam](https://cults3d.com/en/3d-model/art/sample-a-01-adam-from-neon-genesis-evangelion) | Paid STL candidate for the Bakelite case/hand-implant story prop; retopology needed |
| Giant Naked Rei / Lilith-Rei | [Cults3D Evangelion Rei/Lilith sculpture](https://cults3d.com/en/3d-model/game/evangelion-3d-print-model) | **Preferred source.** Thirteen STL parts, roughly 25 cm high x 35 cm wide, white Rei + red core + twelve wings. Assemble, retopologize, texture, rig body and all wings, then author Third Impact scale/pose/dissolution animation |
| Giant Rei fallback body | [White-haired Rei sculpt](https://sketchfab.com/3d-models/white-haired-rei-ayanami-sculpt-8acc21f5773b4b0f929ce4ad182dea8e) | Downloadable CC BY FBX but about 1.47M faces and unrigged; reference/retopology fallback, not direct game input |

## Acquisition rules

1. Prefer author-created CC BY / CC BY-SA fan models with explicit download
   and attribution terms.  Preserve author, URL, license text and original
   archive hash.
2. Cults Personal Use / print-only files are private evaluation inputs only;
   do not put them in GitHub, a public resource pack, or a server/client pack
   distributed beyond licensed users.
3. Official-game rips from Models Resource are geometry references only under
   the project's compliance rules.  They may guide proportions but are not
   import sources.
4. No STL is considered game-ready.  A selected solid-body Angel must pass:
   manifold cleanup, retopology/poly budget, UV/material consolidation,
   canonical bone mapping, hit/socket contract, animation preview and in-game
   visual approval.
5. Ireul, Leliel, Arael and Armisael should not be delayed while searching for
   conventional character meshes; their canonical appearance depends more on
   procedural effects and encounter staging than on a skinned body.
