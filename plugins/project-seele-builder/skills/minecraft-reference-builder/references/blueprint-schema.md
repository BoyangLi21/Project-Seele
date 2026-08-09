# Reference blueprint schema

The blueprint is a small source-of-truth document for one reconstruction. Keep
it under `run/mcp-references/<slug>/blueprint.json`; never store downloaded
reference images in the repository.

## Required shape

```json
{
  "schemaVersion": 1,
  "slug": "baratie-anime",
  "target": {
    "name": "Baratie",
    "version": "anime exterior with inferred functional interior",
    "scalePolicy": "minecraft-estimate"
  },
  "sources": [
    {
      "url": "https://example.invalid/reference-page",
      "kind": "official-description",
      "views": ["front-three-quarter", "side"],
      "establishes": ["fish-head bow", "red-white roof"],
      "confidence": "verified"
    }
  ],
  "dimensions": {"length": 72, "width": 42, "height": 38},
  "coordinateFrame": {
    "originMeaning": "waterline center",
    "forward": "+z",
    "entranceSide": "starboard"
  },
  "palette": {
    "hull": "minecraft:dark_oak_planks",
    "roofPrimary": "minecraft:red_concrete"
  },
  "signatureFeatures": [
    {"name": "fish-head bow", "confidence": "verified", "priority": 1}
  ],
  "rooms": [
    {"name": "main dining room", "level": 1, "minimumClearHeight": 4}
  ],
  "batches": [
    {"name": "sealed hull", "bounds": {"min": [-36, -8, -21], "max": [36, 4, 21]}}
  ],
  "acceptanceViews": [
    {"label": "front-three-quarter", "checks": ["silhouette", "bow", "roof bands"]}
  ],
  "uncertainties": ["Back-of-house room placement is inferred."]
}
```

## Evidence rules

- `sources` needs at least three distinct HTTP(S) pages.
- Cover at least one exterior view and one interior view. If no canonical
  interior exists, state that explicitly in `uncertainties` and use a
  functional inferred interior.
- Allowed confidence values are `verified`, `cross-checked`, and `inferred`.
- Dimensions are positive Minecraft block counts, not unsupported canon claims.
- Every high-priority signature feature should appear in an acceptance view.
- Each batch has explicit local bounds so preview results can be compared with
  the blueprint before execution.
- Acceptance checks are observable properties, not adjectives such as "good".
