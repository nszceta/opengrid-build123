# openGrid Full board — dimension audit

## Scope

- `open_grid()` and `build_open_grid(GridConfig(kind=BoardKind.FULL, ...))` in `src/opengrid_build123/opengrid.py`.
- `output/opengrid_board.step`. It is built from `examples/config.yaml` `board:`: Full 3x5, `chamfers: Everywhere`, `screw_mounting: Everywhere`, `connector_holes: true`.
- Features checked: pitch, thickness, outer frame width, snap-slot opening and wall profile (all Z breakpoints), corner blocks, ChamferMode chamfers, ScrewMounting holes and countersink, adjacent-connector side slot position, StackingMethod interface layer, and N x M extents.
- Out of scope: Lite/Heavy (`board-lite-heavy.md`), slot delete-tool shape (`adjacent-connector.md`), snap fit.

## Sources

| Key | Source |
| --- | --- |
| ours | `src/opengrid_build123/opengrid.py`. Constants :68-89. `GridConfig` :697-750. `open_grid` :753-775. `build_open_grid` :826-836. `_single_board` :2025-2033. `_board_lattice` :2044-2052. `_full_layers`/`_side_profile`/`_corner_profile` :2066-2104. `_max_profile_offset`/`_corner_offset` :2137-2143. `_tile_frame` :2146-2154. Chamfers :2215-2249. Screws :2252-2333. Connector holes :2336-2410. Stacking :2460-2482 |
| PDF | `../reference_docs/opengrid-tile-dimensions.pdf`, page 1 ("Opengrid Raw Tile", updated 08/10/25). Text extraction returns only loose dimension numbers, so all values were read from the drawing rasterized at 400 dpi (`pdftoppm`). Views used: Section A-A (wall profile), plan view with dims 24.7 / 20.5 / 1.5, Detail C (outer chamfer), Detail D with its side elevation (screw hole), Section B-B (diagonal section, corner chamfer 1.4 x 1.4) |
| fork | `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/constants.py:4-5`. `base.py`: `ConnectorCutter` :14-89, `BaseSnapSlotCutter` :92-211 (params :97-104, side profile :128-165, diagonal profile :167-197), `Base` :214-316 (chamfer :227-228, :271-275; slot cut :276-282; connector cut :283-315) |
| SCAD (QW) | `../reference_repos/QuackWorks/openGrid/openGrid.scad`. Screw params :74-78. Tile params :88-92. Stacking params :95-101, :111-113. Single Full :122. Full stack :127-134. `interfaceLayer` :153-157. `interfaceLayer2D` :159-187. `openGrid` :273-341 (connector holes :301-337). `connector_cutout_delete_tool` :344-383. `openGridTileAp1` :386-458 (profiles :410-438). `applyTileCornerModifications` :461-528 |
| SCAD (OP) | `../reference_repos/opengrid-projects/lib/opengrid_base.scad:4-7` (tile size and thickness) and :31 (`OG_MIN_WALL_WIDTH = 0.8`). This file has **no board generator**. `opengrid_framefit_hook_new.scad:63-78` repeats the QW tile constants. BOSL2 `distributors.scad:680-683` (`grid_copies` count and centering) |
| official | David D's official STEPs (Printables model 1214361), downloaded by peer audit ForkProvenance to `~/.cache/fork-provenance/official/`: `opengrid-2x2.step` and `opengrid-3x2.step` (Full boards with 4.2 corner chamfers and edge connector pockets, no screw holes). ForkProvenance found that the fork `Base` 2x2/2x3 has symmetric-difference volume 0 against these files (see `fork-provenance.md`) |

## Method

All values were measured on built geometry with `uv run python /tmp/bf/probe.py <mode>`. The script was throwaway and is not committed.

- **Extents:** `bounding_box()` and solid count for `open_grid(1,1)`, `open_grid(2,3)`, `open_grid(3,5)`, and `bd.import_step("output/opengrid_board.step")`. The STEP was also compared with a fresh `build_open_grid` of the yaml config. Volume 16346.9989 for both, symmetric-difference volume 0.
- **Wall profile:** `shape.intersect(Edge.make_line(...))` returns the material intervals along a line ("chord"). Chords along X at y=0 (mid-side) were taken at Z ∈ {0, 0.2, 0.4, 0.9, 1.4, 1.9, 2.4, 3.4, 4.4, 4.9, 5.4, 5.9, 6.4, 6.6, 6.8}. Z=0 and 6.8 were probed at ±1e-4. The XZ section at y=0 was also taken and its vertices listed.
- **Corner blocks:** chords along the tile diagonal from the tile corner (-14,-14) toward (14,14) at the same Z values.
- **Interior / outer walls:** chords on 2x3 at y=0 across the shared wall at x=0, and along Y at x=14.
- **Chamfers:** 2x3 with `ChamferMode.NONE/CORNERS/EVERYWHERE`, with and without `ScrewMounting.CORNERS`, and with `chamfer_top_left=False`. Probes were diagonal and axis chords from the outer corner (28,42), the edge node (0,42) and the interior node (0,14), at z=1e-4, 3.4 and 6.8-1e-4.
- **Screws:** hole positions came from cylindrical faces with r=2.05 on 3x3 and 4x3 boards for CORNERS, EVERYWHERE and BY_ROW_AND_COLUMN. The board is unfused, so each hole is split into quarter faces whose centroids sit ±1.45 from the node. A radial chord from node (-14,-14) was taken at 19 Z values (0…6.8). Cone and cylinder face Z ranges were listed. `_row_column_screw_positions` was compared with the BOSL2 `grid_copies` formula for W 2-7, H 2-5, cols/rows 1-3.
- **Connector slots:** solids of `board(connector_holes=False) - board(connector_holes=True)` for 1x1, 2x3 and 3x5, with their bounding boxes.
- **Stacking:** 2x3 `stack_count=2` with INTERFACE_LAYER and IRONING. Probes were per-solid bounding boxes, interface chords at z=7.1, and chords at the top and bottom faces to find which side the countersink is on.
- **Official STEPs:** each official board was recentred to bbox centre with Z min = 0. It was then compared with ours (`GridConfig(FULL, 2x2 / 2x3, chamfers=CORNERS, screw_mounting=NONE, connector_holes=True/False)`, tiles fused) using both boolean differences, with the bounding box of every residual piece listed.

Tolerance: 0.01 mm.

## Comparison table

Z is measured from the board bottom. "Wall" is the solid strip width measured from the tile edge inward on one tile. A shared interior wall is twice that.

| feature | ours (measured) | PDF (p.1) | fork | SCAD | verdict |
| --- | --- | --- | --- | --- | --- |
| Pitch / tile size | 28.0: 2x3 openings repeat at 28, shared walls at x=0, y=±14 | 28 (plan: 24.7 + R3.3 = 28.0; 20.5 + 3.3 + 4.2 = 28.0) | 28 (constants.py:4) | 28 (QW :88; OP opengrid_base.scad:4) | match |
| Thickness | 6.8 (bbox Z 0..6.8) | 6.8 (A-A) | 6.8 (constants.py:5) | 6.8 (QW :89; OP :5) | match |
| Extents 1x1 | 28.0 x 28.0 x 6.8, 1 solid | n/a | 28x28 (`Base` :265-270) | 28x28 (QW :285) | match |
| Extents 2x3 | 56.0 x 84.0 x 6.8, **6 solids** | n/a | 56x84, 1 solid | 56x84, union (QW :290-296) | dims match. Topology: ours wrong |
| Extents 3x5 / STEP | 84.0 x 140.0 x 6.8. STEP = fresh build, **15 solids** | n/a | 84x140, 1 solid | 84x140, union | dims match. Topology: ours wrong |
| Wall at Z=0 and Z=6.8 (face) | 1.10 (opening 25.80) | 1.1 (A-A "1,1") | 1.1 (`snap_cut_bottom_width` :97) | 1.1 = 1.5-0.4 (QW :420, :427) | match |
| Face chamfer, Z 0→0.4 and 6.8→6.4 | 1.1→1.5 over 0.4 (45°). Vertices (-12.9,0), (-12.5,0.4) | 0.4 x 0.4 (A-A "0,4" both axes) | 0.4 (:98) | 0.4 (QW :390, :421) | match |
| Capture lip, Z 0.4–1.4 and 5.4–6.4 | 1.50 (opening 25.00) | 1.5 (A-A "1,5"); lip height 1.0 | 1.5 = 1.1+0.4; height 1.0 (:99) | 1.5 = 0.8+0.7 (QW :400); Z 0.4..1.4 (QW :421-422) | match |
| Lip-to-waist chamfer, Z 1.4→2.4 and 5.4→4.4 | 1.5→0.8 over 1.0. 1.15 at Z 1.9/4.9. Vertices (-12.5,1.4), (-13.2,2.4) | 0.7 horizontal x 1.0 vertical; 145° | to 0.8 at Z 2.4 (:100-101) | Z 1.4→2.4 (QW :422-423) | match |
| Waist, Z 2.4–4.4 | 0.80 (opening 26.40), 2.0 tall | 0.8, 2.0 tall ("2"), top capture 2.4 | 0.8, 3.4-1.0 = 2.4 (:100-101, :150-157) | 0.8 (QW :389, :423-424); OP min wall 0.8 (:31) | match |
| Outer board edge frame | single strip, same profile: 0.8 at Z 3.4 (y -42..-41.2), 1.1 at faces | single strip (raw tile) | single strip (Box minus cutter) | single strip (tiles edge to edge) | match |
| Shared interior wall | 2.2 at faces / 3.0 at lip / 1.6 at waist | implied 2x | 2x | 2x | match |
| Corner block depth along diagonal | 4.17 at Z=0/6.8, 5.57 at Z 1.4–5.4, 1.4 x 1.4 chamfer | B-B section 1.4 x 1.4; Detail C 4.2 + 2.6 → 2.97+2.6 = 5.57 | 5.57 = √(2·4.2²)/2+2.6, bump 1.4 (:167-194) | cornerOffset 5.5698, chamfer 1.4 (QW :402-405, :431-438) | match |
| Corner block width | flats meet tile edges (±5.57 perpendicular) | not dimensioned | full-width slab (equivalent) | ±cornerOffset (QW :450-453) | match |
| Outer corner chamfer (CORNERS) | legs 4.20 (edge stops at 23.81 / 97.81). Diagonal cut 2.97. Same at Z 0/3.4/6.8 | 4.2 x 4.2 (Detail C) | 4.2, always on, all 4 corners (:227-228, :271-275) | `tileChamfer` = √(2·4.2²) rotated cube (QW :462-463, :481-494) | match |
| Per-corner chamfer flags | `chamfer_top_left=False` leaves (-28,42) square | n/a | none (all-or-nothing) | QW :465-470 | match (fork n/a) |
| Remaining corner wall after chamfer | 5.57-2.97 = 2.60 along diagonal | 2.6 (Detail C) | 2.6 (:103) | 2.6 (QW :393) | match |
| EVERYWHERE chamfer | diamond at every node incl. interior (0,14): axis 4.20, diagonal 2.97 | n/a | n/a | grid_copies at (W+1)x(H+1) nodes (QW :474-479) | match (fork coverage gap) |
| EVERYWHERE chamfer + CORNERS/EVERYWHERE screws | outer corners only. Interior node gets a Ø4.1 hole, no diamond | n/a | n/a | QW :474, :481 | match |
| Screw positions CORNERS | nodes inset 1 tile: 3x3 (±14,±14); 4x3 (±28,±14) | n/a | no screws (coverage gap) | QW :496-502 | match |
| Screw positions EVERYWHERE | all (W-1)(H-1) interior nodes; 4x3 x∈{-28,0,28}, y=±14 | n/a | n/a | grid_copies(T, size (W-2)T) (QW :504-509) | match |
| Screw positions BY ROW AND COLUMN | 3x3 cols=2 → x=-28 (tile centre). 128/216 configs differ from SCAD, 99/216 off-node | n/a | n/a | centred `grid_copies` + parity shift (QW :510-515; BOSL2 :680-683): 3x3 cols=2 → x=-14; 0/216 off-node | **ours wrong** |
| Screw through-hole | r 2.05 (Ø4.10), Z 0..4.26 | R2.05 (Detail D); straight to Z 4.55 | none | Ø4.1 (QW :74) | match (Ø) |
| Countersink cone | 90°: r 2.05 at Z 4.26 → 3.60 at Z 5.80 | 90°: R2.05 at Z 4.55 → R3.3 at Z 5.80 (1.25 tall) | none | 90°: Ø4.1→Ø7.2, h 1.54, Z 4.27..5.81 (QW :75, :78, :501) | vs SCAD: match (0.01 offset). vs PDF: spec ambiguous |
| Head counterbore | Ø7.20, Z 5.81..6.81 (1.0 deep) | **Ø6.6** (R3.3), 1.0 deep | none | Ø7.2, inset 1.0 (QW :75-76, :500) | spec ambiguous (PDF 6.6 vs QW 7.2) |
| Cone / counterbore junction | **0.01 annular lip** r 2.05..3.6 at Z 5.80..5.81 (chord at Z 5.805 hits r=2.05) | continuous | n/a | cone attached to cyl bottom (QW :500-501) | **ours wrong** |
| Adjacent-connector slot positions | 1x1 none. 2x3: bottom/top x=0, left/right y=±14. 3x5: x=±14, y∈{±14,±42}. All at shared walls | n/a | GridLocations(28, W-1) centred (:283-315) | ycopies/xcopies spacing T, l=(N-2)T or T-1 (QW :303-336) | match |
| Connector slot Z | Z 2.20..4.60 (2.4 tall, centred at 3.4) | n/a | centred Z 3.4, height 2.4 (:24, :284) | centre T/2, h 2.4 (QW :305, :322, :349) | match |
| Connector slot depth / width | depth 5.09 from edge (edge+0.01 tool offset), width 5.20 (2·2.6) | n/a | 5.1, R 2.6 (:31, :71) | 5.1 (2·2.6-0.1) at edge-0.005 → 5.095 (QW :352) | match. Shape is audited in adjacent-connector.md |
| Stack spacing (INTERFACE_LAYER) | boards Z 0..6.8 and 7.4..14.2; interface Z 6.9..7.3 (0.4) | n/a | n/a | spacing T+0.4+2·0.1 = 7.4; interface at T+0.1 (QW :128, :132) | match |
| Stack spacing (IRONING) | boards Z 0..6.8 and 7.0..13.8 | n/a | n/a | T+0+0.2 (QW :112-113, :128) | match |
| Stacked board orientation | not flipped. Every board has countersink Ø7.2 on top (Z 6.8/14.2) and Ø4.1 at bottom | n/a | n/a | every Full board `zflip()` (QW :129) | **ours wrong** |
| Interface footprint | wall 1.5/tile (3.0 shared), corner 5.57, **no chamfer cut, no screw holes** (solid at chamfered corner tips and screw nodes) | n/a | n/a | projection(cut) of board bottom: wall 1.1, corner 4.17, chamfers and Ø4.1 holes (QW :153-157, :176-185) | **ours wrong** |
| STEP vs config | output/opengrid_board.step = build of yaml config (vol 16346.9989, diff 0) | n/a | n/a | n/a | match |
| Whole board vs official STEP | 2x2: ours−official 0.563 mm³, official−ours 1.964 mm³. 2x3: 0.845 / 2.946 mm³. **Every residual piece sits inside a connector pocket** (Z 2.2–4.6, within 5.1 of the edge). Without connector holes: official−ours = 0 and ours−official = exactly the pocket volume (4 x 55.56 on 2x2) | official = ground truth | fork = official (vol diff 0, per ForkProvenance) | n/a | match outside pockets. Pocket shape: see adjacent-connector.md |
| Connector pocket depth vs official | ours 5.09, official 5.10 (0.125 mm³ slab, 5.2 x 2.4 x 0.01, at the inner end of each pocket) | n/a | 5.10 | 5.095 | match (at the 0.01 limit) |

## Discrepancies

1. **By Row and Column screw positions** (ours wrong). `_row_column_screw_positions` (:2282-2291) starts at the first interior node and then adds the parity shift. QuackWorks centres the grid with BOSL2 `grid_copies` and then shifts. With parity shift ≠ 0, our holes land on tile centres or mid-wall instead of nodes: 3x3 with cols=2 gives x=-28 instead of -14, and 2x3 with rows=2 gives y=0 instead of 14. Even-parity cases are not centred either: 2x4 with rows=3 gives y=-28 instead of 0.
   - Resolution: `_row_column_screw_positions` now uses the centred `grid_copies` count and pitch plus the parity shift. 3x3 cols=2 → x=-14; 2x3 rows=2 → y=14; 2x4 rows=3 → y=0. Matches a real OpenSCAD/BOSL2 run of QW :511-512 for all 315 configs W 1-7, H 1-5, cols/rows 1-3 (882 holes, 0 mismatches).
2. **Unfused board** (ours wrong, topology only). `_board_lattice` returns a `Compound` of per-tile solids. Later subtractions keep it that way, so the 3x5 STEP holds 15 touching solids. Connector slots and screw holes are split across 2–4 solids. All measured dimensions are correct. The fork and QW both produce one solid.
   - Resolution: `_board_lattice` fuses the tiles before the chamfer, screw and connector cuts. Full/Lite/Heavy 3x5 (Everywhere chamfers and screws, connector holes) → 1 solid each; STEP round trip of the yaml board → 1 solid, 84 x 140 x 6.8.
3. **Countersink sliver** (ours wrong, 0.01 mm). The cone top is at `thickness - inset` (5.80) and the counterbore bottom is at `thickness - inset + ε` (5.81). This leaves a 0.01 mm ring of material.
   - Resolution: the cone top is at `thickness - inset + ε`, so the cone spans Z 4.27..5.81 as in QW. Hole radius at Z 5.805 is now 3.595 (was material from r 2.05).
4. **Full stack orientation** (ours wrong). QW `zflip()`s every Full board in a stack, so countersinks face the bed. Ours leaves them facing up.
   - Resolution: `_stacked_boards` mirrors every Full board. 2x3 Corners/Corners stack 2: counterbore r 3.6 at Z 0.001 and 7.401, plain r 2.05 at Z 6.799 and 14.199.
5. **Interface layer footprint** (ours wrong). Ours uses a fixed widest footprint (1.5 / 5.57) with no chamfers or screw holes. QW uses a cut projection of the board face (1.1 / 4.17, with chamfers and holes). Ours overhangs the 1.1 mm contact faces by 0.4 mm per side and fills the chamfered corners.
   - Resolution: the interface layer is the extruded section of the board face it sits on (`_interface_layer`). At Z 7.1: wall 1.10, edge corner block 4.17, outer-corner diagonal 1.20 (4.2 chamfer cut), Ø4.1 screw holes.
6. **Screw head diameter** (spec ambiguous). PDF Detail D and its side elevation give a counterbore of R3.3 (Ø6.6), 1.0 deep, and a 1.25-tall 90° cone starting at Z 4.55. QW and ours default to Ø7.2, which puts the cone at 4.26–5.80. Depth, angle and Ø4.1 agree. `screw_head_diameter` is a user parameter, so only the default is in question. The opt-in `ScrewPreset` fastener presets (`apply_screw_preset`) replace the screw fields only when you choose one, so they do not change this default.
7. **Fork coverage gaps** (not errors). The fork has no screw holes, no ChamferMode (always 4 outer corners), no per-corner flags and no stacking. Every board dimension the fork does model matches the PDF: wall profile, corner blocks, 4.2 chamfer, connector Z and positions. No "fork wrong" findings for the Full board.
8. **opengrid-projects** has no board generator. `lib/opengrid_base.scad` only supplies 28 / 6.8 / 0.8, and these agree with ours.
9. **Official STEP cross-check.** Outside the connector pockets, our 2x2 and 2x3 Full boards (Corners chamfers, no screws) are identical to the official boards: zero volume in either boolean difference. This confirms the wall profile, corner blocks, 4.2 chamfers, extents and pocket placement and height against the designer's own geometry. The remaining 2–3 mm³ is pocket mouth/neck shape: ours has a narrower mouth than the official R2.6 / R0.5 / R2.7951 / R0.25 profile. That belongs to the adjacent-connector audit, not this one. The official boards have no screw holes, so they do not settle the Ø6.6 vs Ø7.2 head question.

## Proposed fix issues

- Compute By Row and Column positions as a centred grid, `(k-(n-1)/2)·c·T + shift` with `n = floor((W-2)/c)+1` (and likewise for rows), matching QW :510-515.
- Fuse the tile lattice (or build it from one solid) so each board is a single solid. Applies to all board kinds.
- Put the countersink cone top at `thickness - inset + ε` so it meets the counterbore.
- `zflip` every Full board in a stack. Build the interface layer from the board's face section, including chamfers and screw holes. Lite/Heavy stacking has the same defect.
- Not filed (spec ambiguous): decide whether the `screw_head_diameter` default should follow the PDF (6.6) or QuackWorks (7.2). Recommend a maintainer decision before changing anything.

## Slot dims for other audits

Full board, default 28 / 6.8. These were measured on built geometry and agree with PDF A-A, the fork `BaseSnapSlotCutter` and QW `openGridTileAp1`.

- **Opening across flats (mid-side, X or Y):**
  - Z 0: 25.80
  - Z 0.4–1.4: 25.00 (bottom capture lip)
  - Z 2.4–4.4: 26.40 (waist)
  - Z 5.4–6.4: 25.00 (top capture lip)
  - Z 6.8: 25.80
  - Linear between these values.
- **Wall-offset Z breakpoints** (offset from tile edge in parentheses): 0 (1.1) → 0.4 (1.5) → 1.4 (1.5) → 2.4 (0.8) → 4.4 (0.8) → 5.4 (1.5) → 6.4 (1.5) → 6.8 (1.1). The profile is symmetric about Z 3.4.
- **Lip depth:** 0.7 (1.5 − 0.8) between the capture lip and the waist. Chamfer runs 0.7 horizontal over 1.0 vertical (35° from vertical; PDF "145°").
- **Corner flats:** 4.17 from the tile corner along the diagonal at Z 0/6.8 and 5.57 at Z 1.4–5.4, with 1.4 x 1.4 chamfers. Opening across the corner flats is 31.26 at the faces and 28.46 at mid-depth (39.598 − 2·depth).
- **Adjacent-connector slot:** Z 2.2–4.6 (centred 3.4, 2.4 tall), centred on every shared wall along the board edge, depth about 5.09–5.1 from the edge.
