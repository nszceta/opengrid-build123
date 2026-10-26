# openConnect head and screw — dimension audit

Kata: `opengrid-build123#ykp1` (parent `#enag`).

## Scope

- `build_openconnect_head()` with default `OpenConnectHeadConfig` → `output/openconnect_head.step`
  (`src/opengrid_build123/opengrid.py:469-525`, `:947-964`, `:2646-2673`).
- `build_openconnect_screw()` with default `OpenConnectScrewConfig` and `ConnectorSlotConfig`
  → `output/openconnect_screw.step` (`opengrid.py:529-557`, `:585-598`, `:967-977`, `:2676-2691`).
- The same head is used by the openConnect snap (`opengrid.py:2702-2703`), so head findings apply there too.
- Thread profile is out of scope; see [snap-threads.md](snap-threads.md). Only thread length/placement is checked here.

## Sources

| Tag | Source |
| --- | --- |
| SCAD | `../reference_repos/opengrid-projects/lib/opengrid_base.scad:3-5,43-60` (EPS, `OCHEAD_*`, `OCSLOT_*` constants) |
| SCAD | `../reference_repos/opengrid-projects/lib/openconnect_lib.scad:13-33` (`ochead_cfg`), `:216-227` (`connector_slot_cfg`), `:251-303` (`openconnect_head`), `:304-312` (`openconnect_lock`), `:490-545` (`openconnect_screw`) |
| SCAD | `../reference_repos/opengrid-projects/opengrid_parametric_snap.scad:12,118-145,177-178,341,456-463` (UI defaults, screw thread height) |
| BOSL2 | `../reference_repos/BOSL2/shapes2d.scad:951-958` (`trapezoid` `ang`/`rounding` corner order `[X+Y+,X-Y+,X-Y-,X+Y-]`) |
| PDF | `../reference_docs/openGrid Multiconnect Thread Docs.pdf` p.1. It covers only the Multiconnect thread. The extracted text has no openConnect head or slot dimension. |
| PDF | `../reference_docs/opengrid-tile-dimensions.pdf` p.1. It shows the raw tile: thickness 6.8 and the tile opening. It has no openConnect dimension. |
| fork | `../reference_repos/opengrid-build123-makerrepo-fork/`: a grep for `openconnect`/`openConnect`/`coin_slot` returns no matches. The fork has **no openConnect**, so the fork column is n/a for every row (coverage gap). |
| QuackWorks | No openConnect implementation (a grep for `openconnect`/`coin_slot` in `*.scad` returns nothing). |

## Method

All values come from built geometry. I used throwaway scripts under `/tmp`, run with `uv run python`. Nothing was committed.

1. Built `build_openconnect_head()` and `build_openconnect_screw()`. Probed `bounding_box()`, volume, and planar XY sections. Each section is an intersection with a `Box(200,200,1e-4)` at Z ∈ {0.1, 0.3, 0.6, 0.9, 1.3, 1.7, 2.0, 2.3, 2.5, 2.7, 3.5, 5.0}. I listed the 2D vertices of each section face. I also took vertical sections at y=0 (XZ) and x=0 (YZ).
2. Imported `output/openconnect_head.step` and `output/openconnect_screw.step`. Head: bbox (-8.5,-1.7,0)–(8.5,8.9,2.59), vol 366.677, identical to a fresh build. Screw: bbox (-8.5,-7.9988,0)–(8.5,8.9,9.39), vol 1440.919. A fresh build gives 1441.785. The 0.9 mm³ difference is thread tessellation; the bbox is identical.
3. Overhang cone check: I built the SCAD cone `cyl(d1=20.8, d2=15.6, h=2.6)` at (0.32, 0.45) as `bd.Cone(10.4, 7.8, 2.6)` and intersected it with our head. It removes 0.29 mm³.
4. Board context: imported `output/opengrid_board.step` (Full, 3×5, bbox 84×140×6.8). Sectioned it at z = 0.05 / 3.4 / 6.75. Tile-hole bbox: 25.7 / 26.4 / 25.7 mm.
5. For SCAD values, I evaluated the expressions in `openconnect_lib.scad` by hand. OpenSCAD is not installed. The transform chains are traced in the notes under the table.

Head frame used throughout: large (outer) rectangle at z=0, small rectangle at z=2.6. Back of the head is +Y. The screw axis is at the origin, and the threads go +Z. The SCAD screw is built in this same frame and is then flipped with `up(threads+total) xrot(180) zrot(180)` (`openconnect_lib.scad:520`). Ours is not flipped, so the outer face lies on the bed. This is an export-orientation difference only.

## Comparison

Tolerance is 0.01 mm. EPS: ours 0.01 (`opengrid.py:68`), SCAD 0.005 (`opengrid_base.scad:3`).

| feature | ours (measured) | PDF | fork | SCAD | verdict |
| --- | --- | --- | --- | --- | --- |
| Head bottom (large rect) height | 0.6 (constant section z 0–0.6) | — | n/a | 0.6 `opengrid_base.scad:43` | match |
| Head middle (45° transition) height | 0.59→2.0 (loft starts at 0.6−EPS) | — | n/a | 0.595→1.995 hull, 1.4 `opengrid_base.scad:45`, `openconnect_lib.scad:284-286` | match |
| Head top (small rect) height | 0.6 (2.0→2.59) | — | n/a | 0.6 `opengrid_base.scad:44` | match |
| Head total height | 2.59 (bbox; top extrude starts at 2.0−EPS, length 0.6) | — | n/a | 2.6 (`openconnect_lib.scad:290` extrudes `top_height+EPS`) | match at tolerance (Δ0.01 = our EPS; head-only STEP is 0.01 short) |
| Large rect width × depth | 17.0 × 10.6 (x ±8.5, y −1.7…8.9) | — | n/a | 17 × 10.6 `opengrid_base.scad:46-47` | match |
| Large rect back chamfer | 4.0 (verts (8.5,4.9),(4.5,8.9)) | — | n/a | 4 `opengrid_base.scad:48`, `openconnect_lib.scad:32` | match |
| Small rect width × depth | 14.2 × 9.2 (x ±7.1, y −1.7…7.5) | — | n/a | 17−2·1.4=14.2, 10.6−1.4=9.2 `openconnect_lib.scad:27-28` | match |
| Small rect chamfer | 3.18 (verts (7.1,4.32),(3.92,7.5)) | — | n/a | 4−1.4+tan22.5°·1.4=3.180 `openconnect_lib.scad:29` | match |
| Back position (back edge y) | large 8.9, small 7.5 (= w/2+0.4) | — | n/a | `back(w/2+0.4)` `openconnect_lib.scad:32-33`, `opengrid_base.scad:55` | match |
| Middle-to-bottom (axis to front edge) | 1.7 (front y = −1.7) | — | n/a | 10.6−8.5−0.4=1.7 `opengrid_base.scad:57` | match |
| Lock relief position (center y) | 1.7 (y 1.1…2.3) | — | n/a | 8.5−7.2+0.4=1.7 `openconnect_lib.scad:292` | match |
| Lock relief depth | 0.6 (x 7.9…8.5) | — | n/a | 0.6 `opengrid_base.scad:51` | match |
| Lock relief tip width | 1.2, square corners | — | n/a | 1.2, tip corners r0.8 `openconnect_lib.scad:307` | ours wrong (no fillets) |
| Lock relief mouth width (at head edge) | 1.2 (rectangular) | — | n/a | 2.4 (45° flanks: 1.2+2·0.6) + flared r0.8 mouth (negative rounding) `openconnect_lib.scad:307`, BOSL2 `shapes2d.scad:956` | ours wrong |
| Lock relief Z extent | 0…2.6 straight box, both sides | — | n/a | 0…2.0 (`bottom_height` + `middle_height`) `openconnect_lib.scad:306-310` | match in effect on right; see next row |
| Lock relief left taper-in | none (z=1.3 section: no notch either side) | — | n/a | Left (−X) notch skews inward 0.8 over the middle section, angle atan(0.8/1.4)=29.7°, following the chamfer (`nub_taperin=true`) `openconnect_lib.scad:274,295,309`. At z=1.3 the notch is still 0.3 deep. | ours wrong |
| Coin slot chord width at outer face | 17 (gap spans the full head width; z=0.1 section splits the head at y −1.1…1.1) | — | n/a | 13 (`coin_slot_width`, r = 1.3+13²/20.8 = 9.425; circle top at z=2.6) `openconnect_lib.scad:217-227,530-531` | ours wrong |
| Coin slot depth | Full head height 2.59 everywhere; circle centred on the outer face (z=0) | — | n/a | 2.6 at the axis, 0 at chord ends (circle centre z = 2.6−9.425 = −6.825) `openconnect_lib.scad:530-531` | ours wrong |
| Coin slot reference face | Measured down from z=2.6 (thread junction): `_subtract_connector_slot(head, …, total_height)` `opengrid.py:972` | — | n/a | Measured up from the outer face z=0 (`up(coin_slot_height)`) `openconnect_lib.scad:530` | ours wrong |
| Coin slot orientation | Thickness along Y; slot runs along X | — | n/a | `zrot(90) xrot(90)`: thickness along X; slot runs along Y (slide direction) `openconnect_lib.scad:530` | ours wrong |
| Coin slot thickness | 2.2 (gap y −1.1…1.1) | — | n/a | 2.4 lib default `openconnect_lib.scad:219`; 2.2 UI default `opengrid_parametric_snap.scad:140` | spec ambiguous (ours = UI default) |
| Coin slot front channel | none (superseded by through-cut) | — | n/a | cuboid x ±1.2, y −13…0, z ≤ 2.6 (open channel to front edge) `openconnect_lib.scad:540-542` | ours wrong |
| Flat slot | Box 6.5 (X) × 2.2 (Y), offset to y −2.2…0, z −1.8…1.3; start/end thickness ignored | — | n/a | Prismoid 6.5 (Y) × 1.8→1.2 (X), centred, z 1.9…5.0 (cuts into threads) `openconnect_lib.scad:532-539` | ours wrong |
| Head overhang cone intersect | absent | — | n/a | Head ∩ cone d 20.8→15.6, h 2.6, offset (0.32, 0.45) `openconnect_lib.scad:527-528`. Removes 0.29 mm³ of our head (back chamfer corners). | ours wrong (minor) |
| Thread start (head/thread junction) | z 2.59 | — | n/a | z 2.595 (`up(total−EPS)`) `openconnect_lib.scad:522-523` | match |
| Thread section length | 6.8 (2.59…9.39) | 6.8 board thickness (tile PDF p.1) | n/a | 6.8 = `OG_STANDARD_THICKNESS` `opengrid_base.scad:5`, `opengrid_parametric_snap.scad:12,178` | match |
| Thread major-diameter envelope | ±7.999 (y −7.9988 bbox) | Multiconnect thread PDF p.1 | n/a | — | n/a (deferred to [snap-threads.md](snap-threads.md)) |
| Overall screw length | 9.39 | — | n/a | 2.6−0.005+6.8 = 9.395 | match |
| Folded variant | `OpenConnectScrewConfig.folded` (`opengrid.py:592`) is never read by the builder | — | n/a | `conditional_fold(fold_position=middle_to_bottom+EPS, gap 0.4×0.2)` `openconnect_lib.scad:496-519` | n/a-coverage gap (ours) |
| Fit vs Full board | Head 17×10.6 vs tile hole 25.7 (faces) / 26.4 (mid). Threads 6.8 = board 6.8 (`output/opengrid_board.step`) | 6.8 (tile PDF p.1) | n/a | — | match (context) |
| Whole feature | — | — | absent | — | fork coverage gap |

### Notes on SCAD transform tracing

- **Coin slot.** The code is `up(2.6) zrot(90) xrot(90) cyl(r, h=t, anchor=BACK)`. `anchor=BACK` puts the circle centre at local y=−r. `xrot(90)` maps that to z=−r and maps the cylinder axis to −Y. `zrot(90)` turns the axis to X. The circle top is therefore at z=2.6 and its centre at z=−6.825. At the outer face (z=0) the chord is 2·√(9.425²−6.825²) = 13.0.
- **Coin slot cuboid.** The child cuboid `[13, r, t]` uses `left(6.5)` and `attach(BACK,BACK,inside)`. After the same transforms it occupies x ±t/2, y −13…0, z −6.8…2.6.
- **Flat slot prismoid.** It uses `fwd(0.7)` and `attach(BACK,BOTTOM)`. Its base is at z 2.6−0.7 = 1.9 and its height is 5−2.6+0.7 = 3.1, so it reaches z=5.0 (= `flat_slot_height`).
- **Lock relief.** The code is `trapezoid(h=0.6, w2=1.2, ang=45, rounding=[0.8,0.8,−0.8,−0.8], anchor=BACK)`, rotated by `zrot(-90)` and moved by `right(0.6)`. The result is a 1.2 tip at depth 0.6 and a 2.4 mouth on the head edge. Rounding order is `[X+Y+,X-Y+,X-Y-,X+Y-]` (BOSL2 `shapes2d.scad:956`), so the tip corners get r0.8 and the mouth corners get flared r0.8.

## Discrepancies

**Ours wrong**

1. **Lock reliefs** (`_openconnect_lock_tools`, `opengrid.py:2663-2673`).
   - Ours cuts rectangular 1.2×0.6 notches.
   - SCAD cuts 45°-flanked trapezoids: 1.2 tip, 2.4 mouth, r0.8 tip fillets, and an r0.8 flared mouth.
   - The left (−X) notch should taper inward by 0.8 across the middle section. Ours does not.
   - Affects both the head STEP and the openConnect snap.
2. **Screw coin slot is cut from the wrong face and on the wrong axis.**
   - Ours places a cylinder of r=9.425 centred on the outer face, with thickness along Y. This cuts a 2.2 mm gap through the full 17 mm width and full height of the head. The two head pieces are joined only through the threads.
   - SCAD cuts a circular segment: 13 mm chord at the outer face, 2.6 deep at the axis, thickness along X.
3. **Missing coin-slot front channel.** SCAD adds a cuboid channel from the axis to the front edge (`openconnect_lib.scad:540-542`). Ours has nothing equivalent; its through-cut replaces it.
4. **Flat-blade slot is wrong.**
   - Ours: an off-centre uniform 2.2-thick box at z −1.8…1.3, mostly outside the part.
   - SCAD: a centred 1.8→1.2 tapered prismoid at z 1.9…5.0, cutting into the thread body.
5. **Overhang cone intersect is missing.** SCAD intersects the screw head with a cone; ours does not. The effect is small: 0.29 mm³ at the back-chamfer corners.

**Spec ambiguous**

6. **Coin slot thickness.** The SCAD lib default is 2.4; the SCAD customizer default is 2.2. Ours uses 2.2.
7. **Head-only height.** Ours is 2.59 against 2.6, a Δ of 0.01 (our EPS). This is at the tolerance limit. The cause is that the top extrude is moved down by EPS and is not lengthened by EPS, unlike SCAD `:290`.

**Coverage gaps**

8. **Folded screw.** The `folded` config flag is accepted but ignored.
9. **Fork.** The fork has no openConnect at all.
10. **PDFs.** Neither PDF gives openConnect head or slot dimensions. This doc treats SCAD as the only dimensional reference.

**Fork wrong:** none. There is nothing to compare.

## Proposed fix issues

- `opengrid-build123#r3zr`: replace the openConnect lock-relief boxes with the SCAD trapezoid notch (45° flanks, 1.2 tip / 2.4 mouth, r0.8 tip fillets, flared r0.8 mouth, Z 0…2.0), with left-side taper-in.
- `opengrid-build123#q9pm`: rewrite the openConnect screw connector slot so that:
  - the cut is referenced from the outer face;
  - the slot runs along Y;
  - the circle is placed for a 13 mm chord and 2.6 mm depth;
  - it includes the front cuboid channel and the tapered flat-slot prismoid reaching z=5.0.

  The fix must be openConnect-specific, because `_subtract_connector_slot` is shared with the Multiconnect head. The issue also asks for a decision on coin thickness, 2.2 or 2.4.
  Related: `opengrid-build123#xb1v` covers the Multiconnect side of the same `_subtract_connector_slot` bug and is linked to `q9pm`.
- `opengrid-build123#ny0h`: add the head ∩ overhang-cone intersect, and implement `folded` (conditional fold at middle_to_bottom, gap 0.4×0.2).
- No issue filed for the 0.01 head-height EPS shortfall. It is at tolerance, and the screw is unaffected. Optional cleanup: extrude the top section by `top_height + EPS`.

## Resolution

Verified against OpenSCAD renders of `openconnect_head` / `openconnect_screw` (`$fa=1`, `$fs=0.4`, coin thickness 2.2) by mesh boolean symmetric difference.

- `opengrid-build123#r3zr`: lock reliefs are now the SCAD trapezoid notch (1.2 tip with r0.8 fillets, 2.4 mouth with flared r0.8 corners, mouth 0.005 outside the edge, z 0…2.0), left notch sheared inward 0.8 over the middle section. Measured: X-line y=1.7 material −7.905…7.905 at z=0.3, −7.505…7.8 at z=1.3, −7.277…7.4 at z=1.7; Y-line x=−8.45 z=0.3 notch gap 0.461…2.939. Head vs SCAD render: ours−ref 0.001 mm³, ref−ours 0.002 mm³. Head height is now exactly 2.60 (sections stacked without the −EPS shift), closing item 7.
- `opengrid-build123#q9pm`: openConnect screw slot is openConnect-specific (`_openconnect_screw_slot_tool`): coin circle tangent at z=2.6, thickness 2.2 along X, front channel, tapered 1.8→1.2 flat prismoid z 1.9…5.0. Measured: Y-line x=0 z=0.005 material only y 6.494…8.9 (13 mm chord, open to the front edge); X-line y=3 gap ±1.1; at z=4.9 flat slot y ±3.25, x ±0.61. Coin thickness stays 2.2 (UI default, item 6 unchanged).
- `opengrid-build123#ny0h`: unfolded head is intersected with the overhang cone (d 20.8→15.6, offset 0.32/0.45). `folded=True` ports `conditional_fold` (fold at middle_to_bottom+0.005, gap 0.4×0.2, slice-off 0.2; head keeps slots, skips the cone; text shifted +2 in y). Unfolded screw vs SCAD: ours−ref 0.58, ref−ours 1.68 mm³ (thread facets). Folded: one solid, bbox (−8.5, −7.205, 0)…(8.5, 9.4, 10.605) vs SCAD (−8.5, −7.2, 0)…(8.5, 9.4, 10.605); ours−ref 0.54, ref−ours 1.64 mm³. The hinge overlaps both pieces by ≥0.005 so the layout is a single solid (SCAD only touches the front piece).
