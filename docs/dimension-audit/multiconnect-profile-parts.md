# Multiconnect dovetail profile parts — dimension audit

Kata: `opengrid-build123#710h` (parent `#enag`).

## Scope

The audit covers these builders in `src/opengrid_build123/opengrid.py` and their STEP exports:

| Builder | STEP export(s) |
|---|---|
| `build_multiconnect_profile()` (`opengrid.py:1042-1057`, `_dimensions_to_multiconnect_coords` `:1249-1264`, presets `:1190-1223`) | — (2D points) |
| `build_multiconnect_rail()` (`:1082-1100`) | `output/multiconnect_rail.step`, `output/multiconnect_connector_rail.step` |
| `build_multiconnect_part()` (`:1060-1079`) for every `MulticonnectPartKind` | `output/multiconnect_connector_{round,rail,double_sided_round,double_sided_rail,rail_delete_tool}.step`, `output/multiconnect_receiver_{open_ended,passthrough}.step`, `output/multiconnect_backer_{open_ended,passthrough}.step` |
| `build_multiconnect_delete_tool()` (`:1103-1107`, `_multiconnect_slot_tool` `:1322-1337`) | `output/multiconnect_delete_tool.step` |
| `build_multiconnect_receiver()` (`:1110-1127`) | `output/multiconnect_receiver.step` |
| `build_multiconnect_backer()` (`:1130-1150`) | `output/multiconnect_backer.step` |

Profiles checked: Standard, Jr., Mini. I also checked the Multipoint Beta profile points. Rounding modes checked: None, One Side, Both Sides.

Out of scope: the Multiconnect round head and screw (`#588a`) and the multiConnect snap (`#kv84`).

## Sources

- **SCAD (primary reference; our code cites it at `opengrid.py:646-648`)**: `../reference_repos/QuackWorks/Modules/multiconnectGenerator.scad` (QW `e0c1cb7`). This file has the specs at `:114-118`, the offset rule at `:133-139`, `dimensionsToCoords` at `:296-303`, the part branches at `:149-247`, `roundedEnd` at `:250-267`, and `rail` at `:269-288`.
- SCAD (secondary): `../reference_repos/QuackWorks/Modules/multiconnectSlotDesignBOSL.scad` (`slotStandardPath` / `connectorStandardPath` at `:102-103`, on-ramp `r1 = maxX+1.75` at `:211`, minimum width of one slot at `:107`). Also `../reference_repos/QuackWorks/Modules/multiconnectSlotDesign.scad` (legacy slot profile with depth 5 at `:52`, v2 snap triangle 0.4 × 8 at `:70-73`, on-ramp r 12 → 10.15 at `:95`, minimum width of one slot at `:36`).
- SCAD pitch for openGrid: `../reference_repos/QuackWorks/VerticalMountingSeries/MulticonnectHook.scad:71` (`"Multiconnect - openGrid" ? 28`). The generator default `Grid_Size = 25` is the Multiboard pitch (`multiconnectGenerator.scad:53-54`).
- Tie-break SCAD: `../reference_repos/opengrid-projects/lib/*.scad` and `../reference_repos/QuackWorks/openGrid/*.scad` have no Multiconnect dovetail geometry. The only mention is a credit comment at `opengrid-projects/lib/openconnect_lib.scad:8`. Result: no tie-break source exists.
- **Fork (claim under test)**: `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/constants.py:4,11-25` and `opengrid/multiconnect.py`. The relevant classes are `Slot` (`:9-59`), `SlotCutter` (`:225-257`, clearances 0.3 / 0.2121 / −0.0621), `SnapInSlotCutter` (`:260-328`, triangle inset 0.6 at `:268`) and `SlotOpeningCutter` (`:331-364`, `top_radius_clearance = 1` at `:341`).
- **Official STEPs (extra ground truth)**: David D's Printables model 1214361. Peer `ForkProvenance` downloaded them to `~/.cache/fork-provenance/official/` (IDs in `ids.txt`). I used `slot.step`, `slot-negative.step`, `round.step`, `round-negative.step`, `half-round*.step`, `slot-opening.step` and `snap-in-slot-negative.step`.
- PDF: `../reference_docs/openGrid Multiconnect Thread Docs.pdf`, p.1. The text barely extracts, so I rasterized the page and read it. The page shows only the **thread** cross-section (Negative 14.5 / 12.9, Positive 14, pitch flanks 0.5 / 1 / 0.8 / 0.2). It has **no dovetail dimensions**, so every dovetail row shows "—" in the PDF column.
- PDF: `../reference_docs/opengrid-tile-dimensions.pdf`, p.1 (rasterized). This is the tile cross-section only, with no Multiconnect content.

### QuackWorks `MultiConnectOpenSCAD` submodule removal

QW commit `9eeaf78` (merged in `e0c1cb7`) deleted a gitlink `MultiConnectOpenSCAD`. Commit `6123129` lists it as `160000 commit ab23fbc…`, which is QuackWorks' own commit. No `.gitmodules` file ever existed, so the gitlink had no content. All three files used here are ordinary tracked blobs in `QuackWorks/Modules/` (`git ls-files -s` gives mode `100644`), and they are unchanged across `6123129..e0c1cb7`. Peer `#vxhr` confirmed the same result. **No reference in this audit came from the submodule.**

## Method

1. **Built our geometry.** I ran `uv run python` scripts from `~/.cache/mc-audit/` and `/tmp/` (throwaway, not committed). Config: `MulticonnectConfig(length=50, width=75, grid_size=28)`, the `examples/config.yaml:203-269` defaults. For each profile and part kind I took the `bounding_box()`, the volume and the profile points. I took sections of the built shapes: X-extent versus Y at mid-length, cavity X-intervals versus Y and Z, dimple and ramp runs swept along Z in 0.1–0.25 mm steps, and backer slot solids from `envelope − part`.
2. **Rendered the SCAD reference.** I used OpenSCAD 2021.01 (AppImage) with `OPENSCADPATH=../reference_repos` (BOSL2). Renders used `-D Grid_Size=28 Width=75 Length=50` (also `Length=150` for the ramp checks), for Standard / Jr. / Mini and all nine part types. Two upstream defects needed patches in a `/tmp` copy:
   - `multiconnectGenerator.scad:101` calls `GeneratePart(Select_Profile, Select_Part_Type, Dimples, OnRamps)` positionally, but the module signature at `:110` is `GeneratePart(Width, Length, Select_Profile, …)`. **As shipped, the file renders an empty object** (I verified this: "Current top level object is empty"). I replaced the call with named arguments.
   - The round connectors pass `spin=[90,0,0]` (`:151,164`), which current BOSL2 rejects (`is_finite(spin)` assertion). I removed it and compared the result modulo that rotation.
   - I exported STL files and sliced them with `trimesh` + `shapely`, using the same section code for our tessellated shapes (tolerance 0.002 mm).
3. **Probed the official STEPs** with `bd.import_step` (bounding box, vertex list, face types).
4. **Checked the exported STEPs.** I imported all 13 `output/multiconnect_*.step` dovetail files and compared them to fresh builds. The bounding-box delta was 0.0000 for every file and every volume was identical, so the exports are current.

**Frame conventions.** Our rail, connectors and delete tool equal the SCAD part rotated 180° about X: our Z=0 end is SCAD's TOP end, and our head face Y=0 is SCAD's BACK. Our receivers and backers equal the SCAD part translated by +3.075 Y and +L/2 Z (SCAD is centred). I verified both mappings with the open-ended cavity (closed end at +Z in both) and the dimple/ramp positions.

The SCAD round ends use `$fn=25`, so SCAD Z-extents come out 0.02–0.06 mm short (for example 69.941 vs 70). These differences are faceting artifacts and are not counted as discrepancies. Tolerance is 0.01 mm.

## Comparison

| feature | ours | PDF | fork | SCAD | verdict |
|---|---|---|---|---|---|
| Standard male profile pts (r, D1, D2, D3 = 10, 1, 2.5, 0.5) | (10,0)(10,1)(7.5,3.5)(7.5,4)(0,4) — `opengrid.py:1190-1198,1257-1264` | — (thread drawing only, p.1) | `Slot` widths 20/15, heights 1/2.5/0.5 (`constants.py:11-22`); official `slot.step` / `round.step` vertices identical | `standardSpecs` `multiconnectGenerator.scad:115`, `dimensionsToCoords` `:296-303`; BOSL `connectorStandardPath` `:103` | match |
| Standard negative profile (offset 0.15, bevel 2·sin45·0.15 = 0.2121) | (10.15,0)(10.15,1.2121)(7.65,3.7121)(7.65,4.15) | — | `SlotCutter` 20.3 / 15.3, 1.2121, top 0.4379 → 4.15 (`multiconnect.py:230-253`); official `slot-negative.step` / `round-negative.step` identical | `:296-303` with offset; BOSL `slotStandardPath` `:102` | match |
| Legacy slot depth 5 (`multiconnectSlotDesign.scad:52`) | 4.15 | — | 4.15 | 5.0 legacy vs 4.15 generator / BOSL | spec ambiguous (legacy file only; extra depth sits outside the face) |
| Jr. profile (5, 0.6, 1.2, 0.4, off 0.16) | male (5,0.6)(3.8,1.8)(3.8,2.2); negative (5.16,0.8263)(3.96,2.0263)(3.96,2.36) | — | n/a | `jrSpecs` `:116`; rendered bbox matches (rail 10×2.2, receiver 15.32×4.36×50) | match |
| Mini profile (3.2, 1, 1.2, 0.4, off 0.16) | male (3.2,1)(2.0,2.2)(2.0,2.6); negative (3.36,1.2263)(2.16,2.4263)(2.16,2.76) | — | n/a | `miniSpecs` `:117`; rendered bbox matches (rail 6.4×2.6, receiver 11.72×4.76×50) | match |
| Multipoint Beta profile points | (7.9,0.4)(5.7,2.6)(5.7,3.0) / offset 0.15 | — | n/a | `:118` | match |
| Offset applied to part kinds | delete tool, receivers, backers (`:1239-1246`) | — | cutters only | `isOffset` `:133-139` | match |
| Connector Rail bbox, L=50, Both Sides | 20 × 4 × 70 (Z −10…60) | — | `Slot` length fixed 28 + `half-round` 10 (official) | 20 × 4 × 69.94 (faceted 70) | match |
| Rounding None / One Side / Both Sides (rail) | Z 50 / 60 / 70; One Side cap at our Z<0 = SCAD TOP | — | n/a | 50 / 59.97 / 69.94; One Side caps TOP (`:158-160`) | match |
| Delete tool bbox (Both Sides, ramps) | 23.293 × 4.15 × 70.3 | — | n/a | 23.300 × 4.19 × 70.24. The Y 4.19 is the ramp cylinder `h=maxY+0.04` overshoot (`:245`); the Z difference is faceting | match |
| Delete tool, rounding None: length | **50.02** (Z 0…50.02; `length + 2·EPS`, `:1325`) | — | n/a | 50.00 (`rail(Length)` `:241`) | ours wrong (cosmetic, 0.02 overshoot at the uncapped end of the exported tool) |
| Connector Round | 20 × 4 × 20 | — | official `round.step` r10 × 4 | 20 × 4 × 19.94 | match |
| Double-sided Round / Rail: overall | 20 × **8** × 20 / 20 × 8 × 70 | — | n/a | 20 × 7.99 × … (0.01 `overlap`, `:165-167,175`) | match (0.01 overlap artifact) |
| **Double-sided join face** | joined at the **head** (wide, r10) face. Section: X half-width 7.5 at Y=±3.95, 10.0 at Y=0 → stem-head∣head-stem (`_multiconnect_double_sided` `:1318-1319` rotates about Z) | — | n/a | joined at the **stem** (FRONT, r7.5) face: half-width 10 at both outer faces, 7.5 at the middle → head-stem∣stem-head (`attach(FRONT, FRONT)` `:167,175`) | **ours wrong** — part cannot engage two receivers |
| Dimple shape | **inverted frustum**: r≈0.51 at the head face, widening to r 1.0 at depth 0.495, tip outside the part (`bd.Cone(r, 0, r+EPS)` with base pointing inward, `:1345-1347`). Measured chord: 1.0 mm at depth 0.05, 1.6 at 0.3, none at 0.6 | — | no dimple in `Slot`; official `slot.step` / `round.step`: r 1.05 at the face → r 0.05 at 1 mm depth | `cylinder(h=1, r1=1, r2=0)` base at the face (`:262,284`). Measured chord: 1.8 / 1.2 / 0.6 at depth 0.05 / 0.3 / 0.6 | **ours wrong** (affects rail, round, double-sided, delete tool, and receiver/backer bumps) |
| Dimple spacing / origin on rail and delete tool | every 28 from our Z=0 end (= SCAD TOP): Z 0, 28 (`:1353-1358`) | — | n/a | `zcopies(spacing=Grid_Size, sp=-L+L%G)` from the TOP end (`:283`): SCAD 25, −3 → our 0, 28 | match |
| End-cap dimples (Both Sides) | none on the far cap (Z=L); near cap shares the Z=0 rail dimple | — | official `slot.step` has a dimple at the slot / half-round junction (y=65.5) | every `roundedEnd` has a dimple at its centre (`:261-262`); rendered rail has a dimple at SCAD −25 (= our Z 50) | **ours wrong** (missing dimple at Z=L) |
| On-ramp cone | r 11.65 at the open face → 10.15 at depth (`radius+1.5`, `:1365`); measured 11.625–11.646 (clipped by EPS) | — | `SlotOpeningCutter` r 10.15 → 11.0 over 4.15 (`:340-350`); official `slot-opening.step` r 10.15 → 11.0, h 4.15 | generator `maxX+1.5` = 11.65 (`:192`); BOSL `+1.75` = 11.9 (`:211`); legacy 12 → 10.15 (`multiconnectSlotDesign.scad:95`) | spec ambiguous (ours = generator; official / fork = 11.0) |
| On-ramp positions, delete tool | Z 28, 84, 140 (L=150); 28 (L=50) | — | n/a | rendered SCAD −65, −9, 47 (L=150) → our 140, 84, 28; −3 (L=50) → 28 | match |
| On-ramp spacing | `grid_size · every_n` = 56, start 28 | — | n/a | `onRampEveryNHoles·Grid_Size`, offset `:129-130` | match |
| Receiver Open-Ended block | 25.3 × 6.15 × 50; slot floor Y=2.0; cavity Z 0…47.5 (top wall 2.5); open end at Z=0 | — | n/a | 25.3 × 6.15 × 50; cavity deep extent SCAD −25…22.25 (+25 → 0…47.25, 0.25 sampling) (`:184-186`) | match |
| Receiver Passthrough block / cavity | 25.3 × 6.15 × 50; cavity through Z 0…50; widths at Y match (10.15 floor, 7.65 mouth) | — | n/a | identical bbox; cavity intervals identical where no ramp present | match |
| **Receiver / backer Open-Ended: dimple bumps** | bump at Z 15.35 only (tool origin at the open end: `-(w/2+top_wall)` shift `:1172-1175` plus dimple origin at tool Z=0) → 22 mm below the seat | — | n/a | bumps at our Z 37.35 (rail top = connector seat) and 9.35 (every 28 from the closed end) | **ours wrong** — no detent where the connector seats |
| **Receiver / backer Open-Ended: on-ramps** (L=150) | ramp centres Z 71.35, 127.35 (start `offset+spacing` from the open end, `:1380-1390`) | — | n/a | ramp centres our Z 53.38 and a partial one at −2.62: 84 and 140 below the rail top (`inset=-maxX+spacing+offset` from TOP, `:192,207`) | **ours wrong** |
| Receiver / backer Passthrough: dimples and ramps | measured from Z=0 (ramp 28, 84, 140; dimple 0) | — | n/a | measured from Z=L (rendered: ramp −3 → our 22; dimple at our 49.55) | match up to a rigid 180° turn about Y (part is X-symmetric); convention differs from open-ended |
| Backer slot pitch / count (W=75, G=28) | 2 slots, centres X ±14, pitch 28 (`:1138,1393-1395`) | — | slot length = `OPEN_GRID_UNIT_SIZE` 28 (`constants.py:4,17`) | `xcopies(n=floor(W/G), spacing=G)` (`:200,215`); rendered solid intervals identical: (−37.5,−24.15)(−3.85,3.85)(24.15,37.5) at the floor, (−21.65)(±6.35)(21.65) at the mouth | match |
| Backer pitch for W=84 / W=56 / G=25 | 3 @ 0, ±28 / 2 @ ±14 / 3 @ 0, ±25 | — | n/a | same `floor(W/G)` centred | match |
| Backer W < G | widened to G, one slot (`effective_width`, `:1139`) | — | n/a | generator: body W wide, **0 slots**; BOSL `:107` and legacy `:36` force one slot | spec ambiguous (ours follows BOSL / legacy) |
| openGrid pitch default | 28 (`_DEFAULT_TILE_SIZE` `:69`) | — | 28 (`constants.py:4`) | generator default 25 (Multiboard); openGrid variants 28 (`MulticonnectHook.scad:71`) | match (openGrid) |
| Multiconnect v2 snap triangles | not modelled | — | `SnapInSlotCutter` inset 0.6 × 8 at 0.795 (`:265-268`); official `snap-in-slot-negative.step` inset 0.6 (x −35.15 → −34.55), length 8 | legacy `multiconnectSlotDesign.scad:70-73` inset **0.4** × 8 | n/a-coverage gap (fork matches official; legacy SCAD 0.4 disagrees) |
| STEP exports vs builders | all 13 files: bbox Δ 0.0000, volume equal | — | — | — | match |

## Discrepancies

1. **Double-sided connectors are mirrored on the wrong face (ours wrong).** `_multiconnect_double_sided` (`opengrid.py:1318-1319`) unions the shape with a copy rotated 180° about Z. The rail's head (wide) face is Y=0, so the copy joins head-to-head. SCAD joins stem-to-stem (`multiconnectGenerator.scad:162-181`). Measured result: ours is 7.5 mm half-width at both outer faces, while SCAD is 10 mm. This affects `multiconnect_connector_double_sided_{round,rail}.step`.
2. **Dimple cone is inverted (ours wrong).** In `_multiconnect_dimples` (`:1342-1350`), `Cone(r, 0, r+EPS, rotation=(90,0,0))` places the base inward. The result is an undercut pocket: r 0.51 at the face, r 1.0 at depth 0.495. SCAD (`:262,284`) and official STEPs have a pocket r≈1 at the face tapering to ~0 at 1 mm. The same function shapes the rail, round, double-sided and delete-tool pockets, and the receiver/backer bumps.
3. **No dimple on the far rounded end (ours wrong).** SCAD `roundedEnd` carries a dimple (`:261-262`), and official `slot.step` has one at the slot / half-round junction. Our end caps have none, so a Both-Sides rail / delete tool lacks the Z=L dimple.
4. **Open-ended receiver/backer tool runs in the wrong direction (ours wrong).** SCAD measures dimples and ramps from the closed (top) end of the slot. We measure them from the open end, because the shared slot tool keeps its origin at the open end. Consequences: no detent at the connector seat (Z 37.35 for L=50), and ramps 18 mm off the grid-aligned positions for L=150. Passthrough parts are congruent under a 180° turn, but the convention is inconsistent.
5. **Delete tool overshoot (ours wrong, cosmetic).** The standalone delete tool's straight section is `length + 0.02` (`:1325`), so with rounding None/One Side the export is 50.02 / 60.17 long instead of 50 / 60.15.
6. **On-ramp mouth radius (spec ambiguous).** Ours = generator 11.65. BOSL 11.9 and legacy 12. Official `slot-opening.step` and fork `SlotOpeningCutter` use 11.0.
7. **Backer width < grid (spec ambiguous).** Ours forces one slot and a 28-wide body, matching BOSL/legacy. The generator produces no slot.
8. **Upstream SCAD defects (not ours).** `multiconnectGenerator.scad:101` vs `:110`: the positional call renders nothing. `spin=[90,0,0]` (`:151,164`) fails with current BOSL2. Neither is relevant to our geometry, but anyone re-rendering the reference needs both patches.
9. **Fork vs sources.** The fork's Standard profile and clearances match SCAD and the official STEPs exactly. Its slot opening (11.0) and snap triangle (0.6) match the official STEPs and disagree with QuackWorks SCAD (11.65 / 0.4). I found no fork-wrong items in this scope. The fork has no Jr./Mini profiles, round-end rails, receivers, backers or double-sided parts (coverage gap).

## Proposed fix issues

- Filed `opengrid-build123#y4pk` — Double-sided Multiconnect connectors: mirror across the stem face (Y = profile depth), not the head face, so that the outer faces carry the wide head (discrepancy 1).
- Filed `opengrid-build123#bc2f` — Multiconnect dimples: flip the cone so r = dimple_size·scale at the head face, tapering to 0 at depth dimple_size. Add the dimple to both rounded end caps to match `roundedEnd` (discrepancies 2, 3).
- Filed `opengrid-build123#mzxc` — Multiconnect receiver/backer slot tool: start the dimple and on-ramp patterns at the closed (top-wall) end, as SCAD does. Keep passthrough consistent with that convention (discrepancy 4).
- Not filed (cosmetic): trim the standalone delete tool's 0.02 EPS overshoot, or centre it, so the exported length equals `length` (discrepancy 5).
- Decision needed, not filed: choose the on-ramp radius source, generator 11.65 or official 11.0 (discrepancy 6).

## Resolutions

- Discrepancy 1 — resolved by `opengrid-build123#y4pk`. `_multiconnect_double_sided` now mirrors the part across the stem face (Y = profile depth). Measured result for the double-sided rail and round: X half-width 10.0 at Y=0.05 and Y=7.95, and 7.5 at Y=3.95 and Y=4.05. Both solids are valid.
- Discrepancies 2 and 3 — resolved by `opengrid-build123#bc2f`. The dimple cone base now sits on the head face. Measured pocket chord at depth 0.05 / 0.3 / 0.6 / 0.95 is 1.9 / 1.4 / 0.8 / 0.1, so r = 1 at the face and 0 at 1 mm. A Both-Sides rail and the slot tool now also have a dimple at the far cap (Z=L). The same fix corrected the pitch direction: `_multiconnect_dimple_z_offsets` produced −140…28 for L=150, which put only two dimples on the rail. It now produces 0, 28, …, 140, which matches an OpenSCAD render of `rail(150)` with apexes at 0…140 from the top.
- Discrepancy 4 — resolved by `opengrid-build123#mzxc`. Receivers and backers now place the slot tool turned 180° about Y, with its Z=0 end (= SCAD TOP) at the closed end. That end is at Z = L − w/2 − top wall for open-ended parts and at Z = L + EPS for passthrough parts. Measured open-ended bumps: L=50 at Z 9.35 and 37.35, L=150 at Z 25.35…137.35. Measured open-ended ramps at L=150: Z 53.35 plus a partial ramp at −2.65. Passthrough at L=150: bumps at Z 122.0 / 94.0 / … and ramps at 122.0 / 66.0 / 10.0. All of these match SCAD.
