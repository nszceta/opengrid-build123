# Dimension audit: openGrid Lite / Heavy boards and fill-space modes

Kata: `opengrid-build123#tbp8` (parent `#enag`).

## Scope

- `open_grid_lite()`, `open_grid_heavy()` (`src/opengrid_build123/opengrid.py:778-823`)
- Lite and Heavy profile construction: `_lite_layers`, `_heavy_layers`, `_side_profile(heavy_profile=True)` (`opengrid.py:2066-2134`)
- Lite adhesive base (`_adhesive_base`, `opengrid.py:2453-2457`), thickness selection (`_selected_thickness`, `opengrid.py:2036-2041`), connector slot Z (`_connector_z_base`, `opengrid.py:2400-2410`), screw tools for Lite/Heavy (`opengrid.py:2306-2333`)
- `build_fill_space()` with `FillSpaceMode.COMPLETE_TILES_ONLY` and `FILL_AVAILABLE_SPACE` (`opengrid.py:839-845`, `2496-2631`)
- Lite/Heavy stacking only where it differs from Full (Full stacking belongs to `#6v1j`).

Out of scope: Full board profile itself (`#6v1j`), connector slot plan shape (`#6v1j` / adjacent connector audit).

## Sources

| Key | Source |
|---|---|
| PDF | `../reference_docs/opengrid-tile-dimensions.pdf` page 1 ("Opengrid Raw Tile", A3, 08/10/25). Text extraction gives the Full tile callouts only: 6,8 / 2,4 / 1,1 / 0,4 / 1,5 / 0,8 / 0,7 / 4,2 / 2,6 / 1,4 / 28 (not extracted as a single value). No Lite, Heavy, adhesive base or fill-space dimensions are on the sheet. |
| SCAD (QW) | `../reference_repos/QuackWorks/openGrid/openGrid.scad` at `e0c1cb7`. `openGridLite` :188-229, `openGridHeavy` :231-271, `openGrid` connector Z :282-283,305,322, tile profile :386-458 (Heavy profile :410-417, standard :418-429, corner :431-438), `applyTileCornerModifications` :461-531, `FillSpaceFullTiles` :534-605, `FillSpaceClipOneSide` :607-711, stacking :127-150, `interfaceLayer2D` :159-187. |
| SCAD (QW border) | `../reference_repos/QuackWorks/openGrid/openGrid-border.scad` :18-51 (Lite thickness 4, Full 6.8, border thickness ≥ 5.2). |
| SCAD (ogp) | `../reference_repos/opengrid-projects/lib/opengrid_base.scad:5-7` (`OG_STANDARD_THICKNESS = 6.8`, `OG_LITE_THICKNESS = 4`, `OG_LITE_BASIC_THICKNESS = 3.4`). No board builder, no Heavy. |
| fork | `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/` — `constants.py:5` `OPEN_GRID_BASE_HEIGHT = 6.8`; grep for `lite`/`heavy`/`fill` in `opengrid/` gives no matches. The fork has no Lite, Heavy, adhesive base, or fill-space. Every row below is a fork coverage gap (`—`). This is not a match. |
| official STEP | David D's Printables model 1214361 `opengrid-2x2.step`, downloaded by ForkProvenance to `~/.cache/fork-provenance/official/`. The set has only Full boards; it contains no Lite, Heavy, or fill-space files. |

QuackWorks commit check: `git -C ../reference_repos/QuackWorks log --stat 6123129..e0c1cb7` shows that `5c84f2e`/`2c24ea1` (merged as `cd59620` "fix/lite-snap-click-hole-bridge") change only `openGrid/opengrid-snap.scad` (2+1 lines), and `9eeaf78` removes a submodule gitlink. `openGrid.scad` and `openGrid-border.scad` are unchanged in that range, so the Lite **board** is not affected. The Lite-snap change belongs to the snap-body audit.

## Method

All "ours" values were measured on built geometry, using throwaway scripts in `/tmp` run with `uv run python`. Nothing was committed.

- **Section probes.** `probe(shape, z)` intersects the built solid with `bd.Edge.make_line(p0, p1)` and adds up the lengths of the edges that result:
  - side wall offset: line from (-14.001, 0, z) to (0, 0, z) on a 1×1 board centred at the origin
  - corner block diagonal extent: line from (-14.001, -14.001, z) to (0, 0, z)

  Boards: `open_grid_lite(1,1)`, `open_grid(1,1)` (for reference), and `open_grid_heavy(1,1)`. The Lite board was probed at 9 Z values, Full at 15 and Heavy at 29.
- **Connector slot Z.** `open_grid_lite(2,2,connector_holes=True)`, `open_grid_heavy(2,2,connector_holes=True)`, and Lite 3×3 with and without `add_adhesive_base`. A 1 mm line at the left board edge (x -42.001 to -41 or -28.001 to -27, y on the slot axis) was sampled every 0.05 mm in Z. A slice with zero solid length counts as void.
- **Screw features.** Lite 3×3 `ScrewMounting.CORNERS` with and without adhesive base, and `open_grid_heavy(3,3,CORNERS)`. The screw is at (14, 14). A radial line from (14, 14.3, z) to (17.7, 14.3, z) was used; y is offset by 0.3 so the probe is not on the coincident face between two cells. For a hole of radius r, solid length = 3.7 − √(r² − 0.09). Values seen: 1.672 means r = 2.05, and 0.1125 means r = 3.6.
- **Fill space.** `build_fill_space(GridConfig(kind=LITE, fill_space_mode=…, space_width=100, space_depth=70, max_tile_width=3, max_tile_depth=3, no chamfers/screws/holes))`. The script measured `bounding_box()` of the compound and of each child.
- **Stacking.** `build_open_grid(Lite 1×1, stack_count=2)` with the side-offset probe.
- **Exported STEP.** `output/opengrid_board.step` imports with bbox 84×140×6.8 (Full 3×5). No Lite or Heavy STEP is exported, so the Lite and Heavy results come from geometry built in the probe scripts only.
- **Official Full board cross-check.** I imported `~/.cache/fork-provenance/official/opengrid-2x2.step` (56×56×6.8) and ran the same line probes on it:
  - side wall of the lower-left cell, at 14 Z values
  - interior-node corner block: from the cell centre to the board centre

  Side offsets: z 0.001 → 1.101, 0.4 → 1.5, 1.4 → 1.5, 1.9 → 1.15, 2.4 → 0.8, 2.8 → 0.8, 3.4 → 0.8, 4.4 → 0.8, 4.9 → 1.15, 5.4 → 1.5, 5.9 → 1.5, 6.4 → 1.5, 6.6 → 1.3, 6.799 → 1.101.

  Corner block: z 0.001 → 4.1708, 0.7 → 4.8698, 1.4 to 5.4 → 5.5698, 6.1 → 4.8698, 6.799 → 4.1708.

  These are identical to our `open_grid(1,1)` and to the QW standard profile. The official board's outer corners are chamfered, so the corner-block probe was taken at an interior node. Because Lite is the top 4.0 mm of this profile (official z 2.8..6.8), the Lite profile rows also agree with the official board. QW Heavy puts this same Full face lip on both outer faces, while ours does not (`#gqyy`).

The SCAD values were derived by hand from the QW profile polygons (`[x=wall offset, y=z]`) and transforms. OpenSCAD was not run.

Derived constants (all sources agree):
- max wall offset = 0.8 + 0.7 = 1.5
- face offset = 1.5 − 0.4 = 1.1
- corner offset c = √(4.2²/2) + 2.6 = 5.5698
- corner chamfer = 2.4 − 1 = 1.4, so the corner value at a face is 4.1698

## Comparison table

Tolerance is 0.01 mm. Z is measured from the board bottom (z = 0). "—" in the fork column means the fork has no implementation.

| feature | ours | PDF | fork | SCAD | verdict |
|---|---|---|---|---|---|
| Lite thickness | 4.000 (bbox z 0..4.0) | n/a (p.1 shows Full 6.8 only) | — | 4 (QW :90, :192; ogp `opengrid_base.scad:6`; QW border :43) | match |
| Lite = top 4.0 of the Full tile (cut at Full z = 2.8) | side offset z = 0.001 → 0.80, 1.6 → 0.80, 2.1 → 1.15, 2.6 → 1.50, 3.1 → 1.50, 3.6 → 1.50, 3.8 → 1.30, 3.999 → 1.101 | Full profile p.1 (2.4 / 1 / 0.4 / 1.5 / 1.1 / 0.8) | — | `top_half(z=6.8−4)` of `openGrid`, shifted down (QW :198-208): (0, 0.8) (1.6, 0.8) (2.6, 1.5) (3.6, 1.5) (4.0, 1.1) | match |
| Lite corner block | diag 5.5698 for z ≤ 2.6, then 5.0698 at 3.1, 4.5698 at 3.6, 4.1708 at 3.999 | 4.2 / 2.6 / 1.4 p.1 | — | corner profile top half (QW :431-438): 5.5698 → 4.1698 over z 2.6..4.0 | match |
| Lite backing face (bottom) | flat back, offset 0.8, no bottom chamfer | n/a | — | same (cut plane at Full z = 2.8 lies in the 0.8 region) | match |
| Lite connector slot Z (no adhesive) | void z 0.60..3.00 (sampled 0.65..2.95 at 0.05 steps) | n/a | — | centre = 6.8 − 2.41/2 − 1 = 4.595 in Full coordinates, so 1.795 in Lite; tool height 2.4 gives 0.595..2.995 (QW :282-283, :305, :349) | match (0.005) |
| Lite screw counterbore and countersink (no adhesive) | r = 2.05 to z ≈ 1.46, cone to r = 3.6 at 3.0, counterbore r = 3.6 from 3.0 to 4.0 | n/a | — | `openGrid` at 6.8 then top half: inset 1.0, cone h = tan 45°·1.55 − 0.01 = 1.54, giving the same Z (QW :496-502) | match |
| Adhesive base thickness and position | slab z −0.6..0, full footprint, chamfers cut | n/a | — | 0.6 (QW :84), below the lattice (QW :210-228) | match |
| Adhesive base: connector slot Z | void z 1.20..3.60 (moved up by 0.6) | n/a | — | unchanged 0.595..2.995: the slot is cut in `openGrid` before the base is added (QW :198-212) | ours wrong (`#4r8a`) |
| Adhesive base: screw counterbore depth | counterbore only z 3.6..4.0 (0.4 deep), cone moved up by 0.6 | n/a | — | 1.0 deep (z 3.0..4.0), the same as without a base | ours wrong (`#4r8a`) |
| Adhesive base: screw hole through the base | base solid at screw axis (0.6 of solid on the axis line) | n/a | — | `applyTileCornerModifications(Tile_Thickness=0.6)` is subtracted from the base, which gives a Ø7.2 hole through the slab (QW :217-224, :500) | ours wrong (`#4r8a`) |
| Heavy total thickness | 13.800 (bbox) | n/a | — | 2 × 6.8 + 0.2 = 13.8 (QW :91-92, :236-267) | match |
| Heavy built as 2 stacked Full-thickness halves plus a gap | halves 0..6.8 and 7.0..13.8, gap 6.8..7.0 | n/a | — | upper `up(0.1)`, lower `mirror` + `down(0.1)`, gap = `linear_extrude(0.2) projection(cut)` (QW :238-267) | match (structure) |
| Heavy outer-face capture lip (z 0..2.4 and 11.4..13.8) | **no lip**: side offset 0.80 for z 0.001..4.4 and 9.4..13.799 | Full lip shape p.1 (0.4 / 1 / 1.5 / 1.1) | — | the Heavy profile (QW :410-417) has the lip at the half's z = 6.8 end, and both halves put that end on the outer face: z 0 → 1.1, 0.4 → 1.5, 1.4 → 1.5, 2.4 → 0.8; mirrored at the top | ours wrong (`#gqyy`) |
| Heavy middle (z 4.4..9.4) | lip at the middle: 4.9 → 1.15, 5.4 → 1.5, 6.4 → 1.5, 6.79 → 1.11, 7.01 → 1.11, 7.4 → 1.5, 8.4 → 1.5, 9.4 → 0.8 | n/a | — | 0.80 throughout (z 2.4..11.4) | ours wrong (`#gqyy`) |
| Heavy gap layer (6.8..7.0) side offset | 1.10 | n/a | — | 0.80: projection of the half's z = 0 face, where the Heavy profile is 0.8 (QW :248, :411-412) | ours wrong (`#gqyy`) |
| Heavy corner block | 4.17 at z = 0, 6.8..7.0 and 13.8, 5.5698 in between | 4.2 / 2.6 / 1.4 p.1 | — | corner profile (unchanged for Heavy) on each half, chamfered at both ends: 4.1698 at 0, 6.8, 7.0, 13.8; gap 4.1698 | match |
| Heavy connector slots | 1 slot per edge position, void z 5.70..8.10 (centre 6.9, crosses the gap) | n/a | — | 2 slots per position, one per half, at `Tile_Thickness/2` of each 6.8 half (QW :305, :322, :246, :266; the gap has `Connector_Holes=false` :256): z ≈ 2.195..4.605 and 9.195..11.605 | ours wrong (`#39p1`) |
| Heavy screw counterbore and countersink | top face only (cone z 11.46..12.8, counterbore 12.8..13.8); bottom face has a plain Ø4.1 hole | n/a | — | both outer faces: each half gets `applyTileCornerModifications`, and the lower half is mirrored (QW :238-267) | ours wrong (`#tc3s`) |
| Heavy `heavy_tile_thickness` parameter | used only for tool sizing; the lattice is 2·`tile_thickness` + `heavy_tile_gap` | n/a | — | `Heavy_Tile_Thickness` is used only for the attachable size and the clip cube; the halves are hard-coded to 6.8 (QW :234, :236) | spec ambiguous (the parameter is redundant in both; inconsistent if changed) |
| Fill: Complete Tiles Only, 100×70, max 3×3 | one 3×2 board, bbox x −42..42, y −28..28 | n/a | — | `floor(100/28)=3`, `floor(70/28)=2`, which gives only the "bottom edge" tile 3×2 placed at `[0·33, 0·33]`, centred (`anchor=BOT` centres XY) (QW :534-605) | match |
| Fill: Complete Tiles Only placement pitch | tile centres at `cell_index·(28+5)` (whole board centred on that point) | n/a | — | same `translate([x*spacing_x, …])` with spacing = 28 + 5 on cell indices (QW :554-559). For max-size boards the visible gap is 8·33 − 224 = 40 mm, not 5 mm | match (faithful copy of a QW quirk; spec ambiguous) |
| Fill: Complete Tiles Only, adhesive base | `_base_tile` keeps `add_adhesive_base` | n/a | — | `place_tile` → `openGridLite(...)` without `Add_Adhesive_Base`, so no base (QW :577-584) | spec ambiguous (ours is arguably better; minor) |
| Fill: Fill Available Space, 100×70, max 3×3 | 2 boards: [0,84]×[0,84] (3×3) and [89,117]×[0,84] (1×3); overall 117×84; the edge is a whole cell | n/a | — | every board is a max-size 3×3 board at `i·(84+5)`, intersected with `cube([100+1·5, 70+0·5, …])`. Result: [0,84]×[0,70] and [89,105]×[0,70]. The trimmed edge cuts through cells (partial cells, open edge) and the board widths add up to exactly 100×70 (QW :607-711) | ours wrong (`#nc3a`) |
| Fill: Fill Available Space edge-trim method | ceil to whole cells (`_fill_available_space`, `_tile_runs`) | n/a | — | mm-exact clip with intersection | ours wrong (`#nc3a`) |
| Lite stacking orientation | both copies have the same orientation (bottom offset 0.8 / top 1.1 / next bottom 0.8) | n/a | — | alternating `anchor`/`orient` per `$idx`, so like faces meet (QW :136-142); Heavy the same (:144-150) | ours wrong (`#r3v1`) |
| Lite/Heavy stack interface layer footprint | fixed footprint with offset 1.5 / corner 5.5698 at z 4.1..4.5 | n/a | — | `projection(cut)` of the adjacent board face, 0.01 inside (QW :159-187) | ours wrong (`#r3v1`) |
| openGrid border / edge-trim strips | not implemented | n/a | — | `openGrid-border.scad` (Lite 4 / Full 6.8 border sticks, ≥ 5.2 thick) | n/a-coverage gap (ours and fork) |
| Lite/Heavy STEP export | none in `output/` (`opengrid_board.step` is Full 3×5) | n/a | — | — | n/a-coverage gap |

## Discrepancies

1. **The Heavy profile is inverted (ours wrong).** On our Heavy board the snap capture lip is at the internal middle (z 4.4..9.4), and both outer faces have a plain 0.8 wall. QuackWorks puts the lip on each outer face and keeps the middle at 0.8. As built, snaps cannot be captured on either face. Our gap layer is also 1.1 instead of 0.8.
2. **Heavy connector slots (ours wrong).** We cut one 2.4 slot centred on the gap. QuackWorks cuts one slot centred in each 6.8 half.
3. **Heavy screw features (ours wrong).** Our counterbore and countersink are on the top face only. QuackWorks has them on both faces.
   - Resolution (`tc3s`): `_screw_tool(both_faces=True)` mirrors the head tools about the board mid-plane for Heavy. 3x3 Corners: r 3.6 at Z 0..0.99 and 12.81..13.8, cone to r 2.05 by Z 2.53 / from Z 11.27, r 2.05 in the middle.
4. **The Lite adhesive base moves features (ours wrong).** `_selected_thickness` adds 0.6 before the slot and screw tools are positioned. This moves the slot up by 0.6, reduces the counterbore depth to 0.4, and moves the countersink up. The adhesive slab is also not drilled; QuackWorks cuts a Ø7.2 hole through it.
5. **Fill Available Space overshoots (ours wrong).** We round up to whole cells, so the output is larger than the requested space: 117×84 vs 105×70 including spacing for the 100×70 probe, and 336 mm vs 330 mm wide for the 330×500 default. QuackWorks trims to the exact mm, which leaves partial cells on the far edges.
6. **Lite/Heavy stacking (ours wrong).** We do not flip alternate boards, and the interface layer is a fixed footprint, not the projection of the adjacent face.
   - Resolution (`r3v1`): odd-index Lite/Heavy boards are mirrored, and each interface is the section of the board below at 0.01 under its top face. Lite 1x1 stack 3: side offset 0.80 / 1.10 (board 0), interface 1.11, 1.10 / 0.80 (board 1), interface 0.80, 0.80 / 1.10 (board 2). Heavy interface: 1.11 wall with r 3.6 counterbores. QW builds the Heavy interface from `openGridLite` (QW :149), so its odd-index Heavy interface is a Lite back face (0.8). Ours uses the real Heavy face.
7. **The fork is not a source for anything in this audit.** It has no Lite, Heavy, or fill-space code (coverage gap). The PDF documents only the Full raw tile. The Lite and Heavy values come only from the SCAD sources and the shared Full profile.
8. **Spec ambiguous.**
   - `heavy_tile_thickness` is redundant with 2·`tile_thickness` + gap. This is the same in QW.
   - The Complete Tiles Only pitch is `cell_index·(tile+spacing)`, which gives 40 mm gaps between max-size boards. This is a QW quirk that we copy faithfully.
   - Complete Tiles Only keeps the adhesive base in ours, but QW drops it.

## Proposed fix issues

All filed with `--label fix --related tbp8`:

- `opengrid-build123#gqyy`: Heavy capture lips on the wrong faces. Mirror the order of `_heavy_layers` so the lip is at z = 0 and z = 13.8, and set the gap to offset 0.8.
- `opengrid-build123#39p1`: Heavy connector slots. Cut two slots per position, one per half, at each half's mid-height. Cut none in the gap.
- `opengrid-build123#tc3s`: Heavy screw countersink and counterbore on both outer faces.
- `opengrid-build123#4r8a`: Lite adhesive base. Position the slot and screw tools with `lite_tile_thickness`, not lattice + base, and cut Ø7.2 screw holes through the base.
- `opengrid-build123#nc3a`: Fill Available Space. Use max-size boards at `i·(max·tile + spacing)` and clip them to the mm extents, matching `FillSpaceClipOneSide`.
- `opengrid-build123#r3v1`: Lite/Heavy stacking. Flip alternate boards and use the face projection as the interface layer.

Filed by the Full-board audit (`#6v1j`). These also apply to Lite and Heavy because they share the same code paths; they are referenced here, not filed again:

- `opengrid-build123#xe32`: Full stacking zflip and interface footprint (related to `#r3v1`).
- `opengrid-build123#ht1x`: boards are unfused per-tile compounds (N×M solids). This is why the probes in this audit keep off the cell-boundary planes (see Method).
- `opengrid-build123#ma55`: a 0.01 mm sliver of material between the countersink cone and the head bore.
- `opengrid-build123#eb3b`: screw positions for By Row and Column are off the grid nodes.

## Resolutions

- `#gqyy`: `_heavy_layers` now mirrors the lower half and offsets the upper half. Measured on Heavy 1×1 side offset: z 0→1.10, 0.4→1.5, 1.4→1.5, 2.4..11.4→0.8 (gap 0.8), 12.4→1.5, 13.4→1.5, 13.8→1.10.
- `#39p1`: `_connector_z_bases` cuts one slot per Full half. Heavy 2×2 probe 2.5 mm in from the edge: voids z 2.2..4.6 and 9.2..11.6; solid elsewhere, including the gap.
- `#4r8a`: Lite tools use `lite_tile_thickness`, and `_adhesive_base` applies the corner modifications. Lite 3×3 with base: slot void z 0.6..3.0, counterbore z 3.0..4.0, screw axis open from z −0.6 to 4.0 (Ø7.2 hole through the base).
- `#nc3a`: `_fill_available_space` ports `FillSpaceClipOneSide`. 100×70, max 3×3: boards [0,84]×[0,70] and [89,105]×[0,70].
