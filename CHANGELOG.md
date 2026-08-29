# Changelog

All notable changes from the upstream [Solstice245/scstudio](https://github.com/Solstice245/scstudio)
baseline are recorded here, as required by GPL-2.0 §2(a).

## [1.1.0] - 2026-08-29

Baseline: upstream `dc23f5c` ("License under GPLv2").

### Fixed

- **`sc_import.py` — vertex weld guard compared a vertex against itself, silently
  discarding geometry.** In `scm_mesh`, the check intended to exclude coincident
  vertices that differ in tangent or UV — which is how hard edges and UV seams are
  represented — compared `sv0` to `sv0` rather than `sv0` to `sv1`. The condition was
  therefore always false and the exclusion never ran, so every coincident vertex was
  welded. Welding vertices that should stay separate merges distinct triangles into
  identical ones, and the duplicates are then discarded, so meshes lost geometry with
  no warning and a zero exit code.

  Measured across a 548-unit Supreme Commander corpus: 40 units lost triangles, the
  worst at 16.3%. After the fix, 34 of those 40 convert with zero loss, 2,523 of 2,826
  lost triangles are recovered (89.3%), and 129 units improved in total — many had been
  losing small amounts below any reporting threshold.

### Added — Blender 5.1 compatibility

- **Action F-Curve API.** Blender 4.4+/5.x removed `action.fcurves.new`. Added an
  `action_fcurve_new` shim that falls back to `fcurve_ensure_for_datablock` and creates
  the animation-data link the newer API requires. The shim keeps the old path for
  earlier Blender versions.
- **EDGE_SPLIT modifier.** Removed in Blender 5; the call is now guarded.
- **Material import.** Added `read_bp_materials`; materials generate without requiring
  a blueprint.
- **`sc_io.py`** carries the bulk of the format and API updates.

### Unchanged from upstream

`__init__.py` (apart from `bl_info` metadata) and `sc_export.py` are otherwise
byte-identical to upstream. Export remains the untested half of the addon.
