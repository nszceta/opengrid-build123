# Adjacent-grid connector and connector slot delete tool

Kata: `opengrid-build123#wj3c` (parent `#enag`).

## Scope

- `build_connector_slot_delete_tool()` / `ConnectorSlotDeleteToolConfig` → `output/adjacent_grid_connector_slot_delete_tool.step`
- `build_adjacent_grid_connector()` / `AdjacentGridConnectorConfig` → `output/adjacent_grid_connector.step`
- How the slot is placed in built boards (`_connector_tool`, `_connector_z_base`, `_edge_slot_offsets`) for Full, Lite and Heavy, plus how the positive connector fits a built Full-board pocket and an official Full board.

Not in scope: snap slots, screw holes, chamfers, and the board frame profile. Other audit docs cover those.

## Sources

| id | source |
|---|---|
| ours | `src/opengrid_build123/opengrid.py:84-89` (constants), `:199-239` (configs), `:848-909` (builders), `:2361-2450` (board placement) |
| PDF | `../reference_docs/opengrid-tile-dimensions.pdf` p.1 ("Opengrid Raw Tile", A3, 08/10/25). Text extraction gives only scattered numbers. I rasterized the page (`pdftoppm -r 600`) and read it visually. |
| fork | `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/base.py:14-89` (`ConnectorCutter`), `:283-315` (placement), `constants.py:4-5` |
| QW | `../reference_repos/QuackWorks/openGrid/openGrid.scad:282-283,301-337` (placement), `:344-382` (`connector_cutout_delete_tool`), `:188-208` (Lite), `:231-267` (Heavy). The same tool is copied in `openGrid/openGrid-border.scad:121-154` and `Deskware/Deskware_Main.scad:1842-1870`. |
| OGP | `../reference_repos/opengrid-projects/openconnect_sturdy_shelf.scad:232-271` (BlackJackDuck `connector_cutout_delete_tool`, the same code as QW). No `lib/*.scad` file defines connector pockets. |
| BOSL2 | `../reference_repos/BOSL2/shapes2d.scad:101` (semantics of `rect` `corner_flip`) |
| official | David D's STEPs from Printables model 1214361. Peer ForkProvenance (kata `28fx`, `docs/dimension-audit/fork-provenance.md`) downloaded them to `~/.cache/fork-provenance/official/`; they are not in the repo. Files used here: `opengrid-edge-connector.step` (id 5051325), `opengrid-edge-connector-negative.step` (id 6110232), `opengrid-2x2.step` (id 5051182). |

**Authority.** The official STEPs come from the openGrid designer, so they are the tie-break for the pocket and the positive connector. The SCAD sources (QW/OGP) are a community re-implementation and differ from them. The comparison tables keep the mandated `ours | PDF | fork | SCAD` columns and add an `official` column.

### PDF coverage

The PDF does **not** dimension the adjacent-connector pocket or the positive connector. Detail D (SCALE 4:1, grid C7) shows concentric quarter arcs R2,05 and R3,3 at the raw-tile corner. A pocket centred on the seam would not appear as a quarter circle centred on the tile corner, so Detail D is not the pocket. [INFERENCE] R2,05 = Screw_Diameter 4.1/2 (QW `openGrid.scad:74`), so Detail D is the corner screw-hole quarter. The "2,4" in section A-A (grid E3) is the tile profile's top band (6.8 − 2 − 2.4 = 2.4 at the bottom). It is not the pocket height, although the value happens to be the same. Every PDF cell below is therefore "—" except tile thickness 6.8 (A-A).

## Method

The probe scripts were throwaway files outside the repo, run with `uv run python`. They are not committed.

1. **Delete tool**: I built `build_connector_slot_delete_tool()` and recorded `bounding_box()` and `volume`. I took the planar section `shape & Plane.XY.offset(1.2)` and listed every edge (type, radius, `arc_center`, endpoints). I measured chord width with `shape & Edge.make_line((x,-50,z),(x,50,z))` at depths x = 0, 0.1, 0.25, 0.5, 1.0, 1.0198, 1.2, 2.5, 4.0, 5.0, 5.09.
2. **Connector**: same probe on `build_adjacent_grid_connector()` at z = 1.1.
3. **Our STEP files**: `import_step(output/adjacent_grid_connector*.step)` bbox and volume match the built shapes (volume differences < 0.001 mm³).
4. **Our boards**: I built `GridConfig(kind=K, board_width=2, board_height=2, connector_holes=True, screw_mounting=NONE)` for K ∈ {Full, Lite, Heavy}. For each board:
   - vertical line probes at (28 − d, 0) for d = 0.5, 2.5, 4.5 give the pocket Z gaps; a control probe at y = 5 has no pocket;
   - a horizontal X probe along y = 0 at mid-pocket Z gives the depth;
   - Y chords at x = 28 − {0, 0.01, 0.02, 0.26, 1.03, 2.5} give the width.
5. **Fit in our Full board**: I translated our connector so its seam is at the board's +X edge (x = 28, y = 0) and centred it in Z (z 2.3..4.5). I measured `connector & board` volume and `connector.distance_to(board)`.
6. **Fork**: the fork imports `mr`, which is not installed, so I copied the `ConnectorCutter.__init__` geometry from `base.py:31-84` verbatim and built it. I recorded the section edges, chord widths at depth, and the boolean volume difference against our tool rotated into the fork frame.
7. **Official STEPs**:
   - I sectioned both connector STEPs at mid-height and listed their edges.
   - Our tool was compared with the official negative by boolean difference, after rotating the negative 180° and shifting x by +2.5 so its mouth is at x = 0.
   - On `opengrid-2x2.step` (+X edge at x = 1442, seam y = −1582) I measured the pocket with the same line probes as in step 4.
   - Fit checks with `&` volume and `distance_to`: our connector in the official board, the official positive in the official board, and the official positive in our Full board. Each connector was placed with its seam on the board edge at z 2.3..4.5.
8. **QW**: I evaluated QW geometry analytically from the SCAD source. With `xcopies(spacing=5.2)` + `left(0.1)`, the hull circles are r 2.6 at x = −2.7 and 2.5. The dimple circles are r 2.7 at (0, ±5.1). `half_of(RIGHT)` cuts at x = 0, and `translate(-2.55)` + `attachable(size x=5.1, anchor=LEFT)` puts that cut on the board edge. The flare rect is 1 × 4.8 with `rounding=[0,-.25,-.25,0], corner_flip=true`. Per BOSL2 `shapes2d.scad:101`, negative rounding with `corner_flip` makes spikes on the Y axis at the X− corners, i.e. an R0.25 flare and a 5.30 mouth.

Tolerance: 0.01 mm.

## Comparison

Coordinates: x = depth into the board from the board edge, y = lateral (along the edge), z = up.

### Delete tool / pocket profile

| feature | ours | PDF | fork | SCAD (QW / OGP) | official (negative STEP + 2x2 board) | verdict |
|---|---|---|---|---|---|---|
| main lobe | R2.6, centre x=2.5 (section arc r=2.6000 c=(2.5,0)) | — | R2.6, centre depth 2.5 (`base.py:31,71`) | R2.6, centre x=2.5 (`openGrid.scad:346,360-366`) | R2.6, centre 2.5 from the mouth | match |
| max pocket depth (tool) | 5.100 | — | 5.100 | 5.1 | 5.100 (negative bbox) | match |
| straight side half-width | 2.600, x 1.0198..2.498 | — | 2.600, depth 1.3629..2.5 | 2.6, x 1.0198..2.5 | 2.600, depth 1.363..2.5 | match (value); start depth: see shoulder row |
| boss (neck) arc | R2.7 at (0, ±5.1) | — | R2.7951 = 5√5/4 at (0, ±5.1) (`base.py:36,74`) | R2.7 at (0, ±5.1) (`openGrid.scad:347-348,369-371`) | **R2.7951** at (0, ±5.1) | **ours wrong**; SCAD differs from official; fork match |
| boss↔straight shoulder | sharp, x=1.0198 | — | R0.5 fillet, centre (1.3629, ±2.1) (`base.py:32,73`) | sharp | **R0.5 fillet**, centre (1.3629, ±2.1) | **ours wrong**; fork match |
| mouth rounding/flare | **none**: the 1.0 × 4.8 `Rectangle` (`opengrid.py:874-878`) lies inside the neck | — | R0.25, centre (0.25, ±2.5672) (`base.py:33,75-80`) | R0.25 flare off the R2.7 neck, centre (0.25, ±2.65) (`openGrid.scad:379`) | **R0.25**, centre (0.25, ±2.5672) | **ours wrong**; fork match |
| width at mouth (x=0) | 4.800 | — | 5.134 | 5.30 | 5.133 (board chord at the edge) | **ours wrong** |
| min neck width | 4.800 at x=0 | — | 4.634 at x≈0.27 | ≈4.81 | 4.636 at x=0.27 (board) | **ours wrong** (ours is 0.17 wider) |
| width at x=1.0 | 5.184 | — | 4.980 | 5.184 | 4.980 (board) | **ours wrong** |
| width at x≥1.36..2.5 | 5.200 | — | 5.200 | 5.200 | 5.200 | match |
| tool height | 2.400 | — | 2.4 (`base.py:24,84`) | 2.4 (`openGrid.scad:349,358`) | 2.400 | match |
| tool volume | 56.0269 mm³ | — | 55.5616 | — | 55.5616 (ours − official 0.4814, official − ours 0.0161 mm³; fork identical) | **ours wrong** |
| tool overshoot outside edge | 0.01 (`opengrid.py:2420-2450`) | — | 0 (`base.py:294,309`) | 0.005 (`openGrid.scad:308,315,325,332`) | n/a | match (≤0.01) |
| built pocket depth into board | 5.090 (material resumes at x=22.91 from edge 28) | — | 5.100 | 5.095 | 5.100 (1436.9 → 1442) | match |
| slot positions along edge | (i − n/2)·28, i=1..n−1 (`opengrid.py:2361-2362`) | — | `GridLocations(pitch, n−1)` (`base.py:295,310`) | `ycopies(spacing=28, …)` (`openGrid.scad:310,316,326,333`) | seam (2x2: one per edge at the centre seam) | match |

### Z placement in boards

| feature | ours | PDF | fork | SCAD (QW) | official | verdict |
|---|---|---|---|---|---|---|
| Full (6.8) pocket Z | 2.2..4.6 | 6.8 thickness (A-A); pocket not shown | 2.2..4.6 (`base.py:284`, `constants.py:5`) | 2.2..4.6 (`openGrid.scad:305,322`) | 2.2..4.6 (2x2 probe) | match |
| Lite (4.0) pocket Z | 0.6..3.0 | — | n/a (no Lite) | 0.595..2.995 (`:198-199,305`) | n/a (no Lite STEP) | match (Δ 0.005) |
| Heavy (13.8) pocket Z | **one pocket 5.7..8.1** (straddles the 0.2 gap) | — | n/a | **two pockets** 2.2..4.6 and 9.2..11.6 (`:239-247,258-267`) | n/a | **ours wrong** (fix `39p1`) |

### Positive connector

| feature | ours | PDF | fork | SCAD | official (`opengrid-edge-connector.step`) | verdict |
|---|---|---|---|---|---|---|
| overall L × W × T | 9.800 × 5.000 × 2.200 | — | n/a | n/a | 10.0 nominal (9.923 max with the tip notch) × 5.000 × 2.200 | **ours wrong** (L) |
| lobe | R2.5 centred 2.4 from the seam (tip 4.9) | — | — | — | R2.5 centred 2.5 from the seam (tip 5.0) | **ours wrong** |
| straight side half-width | 2.500 | — | — | — | 2.500 | match |
| boss-clearance arc | R2.8 at (∓0.1, ±5.1), no fillets | — | — | — | **R3.25 at (seam, ±5.5)** + R0.5 fillets at both ends | **ours wrong** |
| neck width at seam | 4.6036 | — | — | — | 4.500 | **ours wrong** |
| tip notch | none | — | — | — | one lobe tip has a V notch 0.6 deep (tip 5.0 → 4.4) with R0.5 fillets | **ours wrong** (missing) |
| volume | 94.9434 mm³ | — | — | — | 95.8668 mm³ | differs |
| fit in our Full pocket | no interference; min gap 0.068 | — | — | — | official positive in our pocket: no interference; min gap 0.090 | ok |
| fit in official 2x2 board | **interference 2 × 0.0318 mm³** at x 0.22..1.03, \|y\| 2.32..2.50 (neck/shoulder) | — | — | — | official positive in official board: no interference; min gap 0.057 | **ours wrong**: our connector does not fit official boards |
| seam dimple / detent | none | — | — | commented out only (`openGrid.scad:372-376`) | none on the edge connector | match (none) |

## Discrepancies

1. **Ours wrong: pocket profile.** Ours follows the SCAD profile (R2.7 boss, sharp shoulder) and leaves out the flare. The flare rectangle sits inside the neck and changes nothing, so `flare_width` has no effect. The official board and negative STEPs (identical to the fork `ConnectorCutter`) use:
   - an R2.7951 boss;
   - an R0.5 shoulder fillet;
   - R0.25 mouth rounding, giving a 5.133 mouth and a 4.636 neck.

   Ours has a 4.80 mouth and neck. Volume difference: 0.4814 / 0.0161 mm³.
2. **Ours wrong: positive connector.**
   - The official Edge Connector is 10.0 long, with R3.25 boss-clearance arcs at (seam, ±5.5), R0.5 fillets, a 4.50 neck and a 0.6-deep tip notch.
   - Ours is 9.8 long, with R2.8 arcs, no fillets, a 4.60 neck and no notch.
   - Our connector **interferes with official boards** (2 × 0.032 mm³ at the shoulder). The official connector fits both official boards and ours.
3. **Ours wrong: Heavy pocket Z.** Ours cuts one pocket across the 0.2 heavy gap (5.7..8.1). QW cuts two pockets, at 2.2..4.6 and 9.2..11.6. No official Heavy STEP was available.
4. **SCAD ≠ official.** QW/OGP use an R2.7 boss, no shoulder fillet, and a flare that gives a 5.30 mouth. That is a re-implementation and does not match the designer's STEPs. My earlier "fork wrong" verdicts, which were based on SCAD, are reversed: the fork `ConnectorCutter` matches the official geometry exactly.
5. **PDF:** it does not dimension the connector pocket or the connector (coverage gap).

## Proposed fix issues

- `opengrid-build123#jmq8` (filed by ForkProvenance; I added my fit measurements as a comment): match the delete tool and the positive connector to the official Edge Connector STEPs. Delete tool: R2.7951 boss, R0.5 fillet, R0.25 mouth rounding, 5.134 mouth. Positive: R3.25/R0.5 profile, 10.0 length, tip notch.
- `opengrid-build123#39p1` (filed by the Lite/Heavy audit; my duplicate `h79s` is closed): Heavy boards get two pockets, at 2.2..4.6 and 9.2..11.6.
- `opengrid-build123#0wy8`: closed, superseded by `jmq8`. Its 5.30 target came from SCAD and is not the official geometry.

## Resolutions

- `#jmq8`: the pocket is a port of the official negative (fork `ConnectorCutter`). The symmetric difference against `opengrid-edge-connector-negative.step` is 0 / 0 mm³ (V 55.5616). The Full 2×2 pocket region against official `opengrid-2x2.step` is 0 / 0 mm³. The positive connector is rebuilt from the official profile (R2.5 lobes, R3.25 reliefs at ±5.5, R0.5 fillets, 45° 0.6-deep notch). The symmetric difference against `opengrid-edge-connector.step` is 0 / 0 mm³ (V 95.8668). It has zero interference in the official 2×2 board and in our Full board (both orientations), our Lite board, and both Heavy pockets. The `dimple_radius`, `separation`, `flare_width` and `fit_clearance` fields were removed.
- `#39p1`: Heavy pockets are at z 2.2..4.6 and 9.2..11.6.
