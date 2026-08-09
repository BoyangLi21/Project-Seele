---
name: minecraft-reference-builder
description: Research, plan, construct, capture, and visually refine a named real or fictional building in Minecraft through Project SEELE MCP. Use when a user asks to search exterior or interior reference images, reconstruct a landmark such as a film/anime/game building, improve likeness, create a source-backed voxel blueprint, build a large enterable structure, or compare an in-game construction with visual references.
---

# Minecraft Reference Builder

Build recognizable Minecraft architecture from evidence instead of relying on
name recognition alone. Keep research read-only until the reference manifest,
scale, site, batches, and visual gates are coherent.

## Required workflow

### 1. Establish the target version

Identify the exact building, adaptation/version, desired scale, required
interiors, and whether the user authorized construction. If several versions
have materially different silhouettes, ask one focused question unless the
request already chooses one. Never imply exact canonical dimensions when none
are published; label Minecraft-scale estimates as estimates.

### 2. Research exterior and interior evidence

Use web image search and direct-page browsing when available. Search separately
for the building name plus `exterior`, `front`, `side`, `rear`, `aerial`,
`interior`, `floor plan`, and signature room/feature names. Gather 6–12 useful
views across at least three pages where the source material permits it.

Prefer official descriptive pages, licensed promotional stills, production
design material, or well-sourced reference pages. Use fan builds only as
secondary Minecraft technique references, never as proof of canon. Record each
source URL and what it establishes. Distinguish `verified`, `cross-checked`,
and `inferred` features. Cite source pages in the user-facing research summary.

Do not commit, redistribute, trace, or package copyrighted art, screenshots, or
textures. Retain URLs and derived architectural facts only. If browsing or image
search is unavailable, ask the user to attach reference images rather than
pretending that memory is sufficient.

### 3. Create and validate the reference manifest

Read [references/blueprint-schema.md](references/blueprint-schema.md) and create
`run/mcp-references/<slug>/blueprint.json`. This path is ignored by Git. Include
source roles, confidence, signature features, Minecraft dimensions, coordinate
frame, room program, palette roles, batch bounds, and acceptance views.

Resolve `scripts/validate_blueprint.py` relative to this `SKILL.md`, then run:

```bash
python3 <skill-root>/scripts/validate_blueprint.py run/mcp-references/<slug>/blueprint.json
```

Resolve every validation error before mutation. Summarize the chosen silhouette,
scale, floor heights, entrance direction, uncertain features, and the five most
important likeness cues for the user.

### 4. Inspect the live world

Call `minecraft_session`, `minecraft_seele_status`, and `minecraft_buildsite`.
Stop if `genericMcpMutationAllowed` is false, the requested site is unsafe, the
terrain/water area is insufficient, or an existing structure would be covered.
Protected SEELE facility and recovery saves always remain under the repository's
deterministic map-editing protocol.

### 5. Build in reversible evidence-shaped batches

Map the reference hierarchy into three scales:

- Primary: footprint, massing, silhouette, axes, deck/roof heights.
- Secondary: facade rhythm, major openings, wings, towers, fins, bridges.
- Tertiary: trim, signage, lighting, furniture, railings, props.

For every independent batch:

1. Call `minecraft_preview_build_plan`.
2. Inspect resolved origin, bounds, materials, block count, and preview blocks.
3. Execute the returned same `planId` only after the preview is coherent.
4. Poll `minecraft_batch_status` until `complete` or `failed`.
5. On failure or a materially wrong result, call `minecraft_undo_last_batch`,
   correct the plan, preview again, and then execute.

Use frame-and-infill construction and preserve usable internal volume. Curved
forms need stepped contours, not enclosing rectangular masses. Waterline shells
must be sealed before clearing interior water. When the user already authorized
construction in a disposable world, safe preview completion is enough; do not
ask for duplicate approval.

### 6. Perform multi-view visual gates

After primary massing, after the envelope, and after final details, inspect the
rendered result. Ask the player to stand at a named view, then call
`minecraft_capture_view` with a matching `viewLabel`. The tool captures the
current world view only; it does not move the player or camera.

For a large reference build, capture at least:

- front three-quarter at silhouette-reading distance;
- opposite side or rear three-quarter;
- elevated or roof/deck view when relevant;
- main entrance/interior circulation;
- one signature room or feature.

Compare each capture against the manifest, not against vague overall feeling.
Score silhouette, proportions, color blocking, opening rhythm, signature
features, interior legibility, and lighting. List concrete mismatches with
coordinates or facade regions. Apply small previewed correction batches; do not
erase an accepted build and start over unless the user requests it.

### 7. Report completion honestly

Report source coverage, assumptions, exact constructed bounds, batch/job IDs,
captured views, corrections, and remaining uncertainties. A build is complete
only when required rooms are enterable, circulation works, water-sensitive
volumes are dry, no batch failed, and the manifest's visual gates have evidence.

## Tool availability

The Project SEELE MCP tools come from the repository's `.codex/config.toml` or
the `project-seele-builder` plugin. If the tools are absent, explain how to trust
the repository/restart Codex or install the plugin; do not substitute arbitrary
chat commands or direct save-file editing.
