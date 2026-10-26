# Snap body, expanding snap, assembled openGrid snap — dimension audit

## Scope

- `build_snap_body()` (`SnapBodyConfig`, `SnapBodyShape` Directional / Symmetric) at thickness 6.8 (standard), 4.0 and 3.4 (lite). Export: `output/snap_body.step`.
- `build_expanding_snap()` (`ExpandingSnapConfig`) for Directional/Symmetric, 6.8/3.4, Blunt/Basic threads. Export: `output/expanding_snap.step`.
- `build_opengrid_snap()` (`OpenGridSnapKind`): Bare (= snap body), Basic Threads (thread composition only), Self-Expanding Threads (= expanding snap), openConnect and multiConnect (head placement only). Export: `output/opengrid_snap.step` (openConnect).
- Fit of the snap in the Full board slot (fork `BaseSnapSlotCutter`, our built Full board, and the official board).
- The QuackWorks `openGrid/opengrid-snap.scad` change `6123129..e0c1cb7`.
- Out of scope: the thread form (snap-threads audit), the openConnect / Multiconnect head shapes themselves (`openconnect.md`, `multiconnect-head.md`), and the text engraving.

## Sources

| tag | source |
|---|---|
| ours | `src/opengrid_build123/opengrid.py`. Constants :68-70, :114-117. `SnapBodyConfig` :270-388. `ExpandingSnapConfig` :391-437. `OpenGridSnapConfig` :617-638. `build_snap_body` :912-930. `build_expanding_snap` :933-946. `build_opengrid_snap` :1018-1037. Core/corners :1398-1464. Nubs :1473-1552. Cuts :1573-1613. Directional slant :1616-1651. Notch :1654-1684. Side-rectangle/box helpers :1687-1748. Expanding tools :1751-1867. Snap attachment :2694-2706 |
| SCAD lib | `../reference_repos/opengrid-projects/lib/opengrid_snap_lib.scad` @ `b133d5a`. Cfg defaults :15-217. `snap_corner` :219-243. `snap_cut` :244-309. `snap_nub` :310-366. `snap_uninstall_notch` :367-392. `expanding_spring` :393-484. `base_snap` :486-510. `expanding_snap` :512-568. Plus `lib/opengrid_base.scad:3-12` (EPS, 6.8, OG_SNAP_WIDTH 24.8, corner constants) and `lib/opengrid_threads_lib.scad:46-75` (`snap_expand_cfg`), :146-205 (`expanding_threads`) |
| SCAD products | `../reference_repos/opengrid-projects/opengrid_parametric_snap.scad` :12-58 (UI defaults), :396-431 (assembly; heads at :423-427). `opengrid_expanding_snap.scad` :12-24 (expand distance 1.0 / 1.2), :44 (split angle 45) |
| QW | `../reference_repos/QuackWorks/openGrid/opengrid-snap.scad` @ `e0c1cb7`, :20-126 (w 24.8 :37, h 6.8 / 3.4 :38-39, top corner wedges :52-56, nubs :58-100, click holes :104-113, wall click holes :116-119). Old version @ `6123129` from `git show` |
| fork | `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/base.py:92-211` (`BaseSnapSlotCutter`: profile :128-165, diagonal :167-197). `constants.py:4-5`. The fork has **no snap body**, so the fork column is n/a except for the fit rows |
| PDF | `../reference_docs/opengrid-tile-dimensions.pdf` page 1 ("Opengrid Raw Tile"). Text extraction gives only loose numbers. I read the values from a 110 dpi raster: Section A-A (face wall 1.1, lip 1.5, chamfer 0.4, groove wall 0.8, thickness 6.8) and Section B-B (corner 1.4 x 1.4). It has no snap dimensions. `openGrid Multiconnect Thread Docs.pdf` page 1 covers threads only (n/a here) |
| official | David D's official snap STEPs (Printables 1214361), downloaded by the QuackWorks update review (`quackworks-update-e0c1cb7.md`) to a local cache outside the repo: `bare.step` (opengrid-bare-snap), `lite.step` (bare lite), `dir.step` (directional v2.1), `dirlite.step` (directional lite v2). Official boards from ForkProvenance: `~/.cache/fork-provenance/official/opengrid-2x2.step`. These are in the same frame as ours: centred, z 0..t, directional nub on +Y |

## Method

All probes ran outside the repo, in `~/.cache/snapaudit/`. Nothing was committed.

1. **Reference renders.** OpenSCAD 2026.10.24 (snapshot AppImage, `--backend=manifold`, `OPENSCADPATH=../reference_repos`). I wrote small driver files that call the library modules directly, with text disabled:
   - `base_snap(snap_body_cfg(snap_thickness=t, snap_body_shape=S), disable_features=["snap_text"])` for S ∈ {Directional, Symmetric} and t ∈ {6.8, 4, 3.4}
   - `expanding_snap(...)` with `snap_expand_cfg(1.0, 1.2)` (the product defaults) for S × {6.8, 3.4} × {Blunt, Basic}
   - `base_snap` with `attach(TOP,TOP) openconnect_head(add_nubs="Both")`, and the same with the `multiconnect_head` body copied from `opengrid_parametric_snap.scad:370-374`
   - `openGridSnap(lite, directional, anchor=BOTTOM)` from QW at `e0c1cb7` and at `6123129`
2. **Our shapes.** I exported `build_snap_body`, `build_expanding_snap` and `build_opengrid_snap` (openConnect, multiConnect) for the same variants to STL with `bd.export_stl(tolerance=0.002, angular_tolerance=0.05)`. I also imported `output/{snap_body,expanding_snap,opengrid_snap}.step`. Their volumes equal the freshly built defaults: 3782.23 / 2524.76 mm³. `opengrid_snap.step` is 4146.41 mm³ vs 4147.28 mm³ built, and the 0.87 mm³ difference is the config's "OG" engraving.
3. **Comparisons** (trimesh + manifold3d + shapely):
   - Boolean differences `ours − ref` and `ref − ours`. Each residual piece is listed with its volume and bbox.
   - Planar sections at listed Z.
   - Line probes: intersect the section with a line, e.g. x=0 from y=12 to 14 for the nub reach, or the diagonal x=y for the corners.
   - Chords of the central void at 0°/45°/90°/135° for the expanding thread hole.
4. **Fit.** I placed each snap (z 0..t) at a cell centre of the official 2x2 board and of our `build_open_grid(GridConfig(FULL, 2x2, no connectors/screws/chamfers))`, then took the boolean intersection volume. Our board equals the official board in the slot region: the interference results are identical in both, and `official − ours` = 0. The fork `Base` equals the official board (ForkProvenance), so the fork result is the same. I ran the snap both with its top at the board face and flipped.

Tolerance is 0.01 mm. Radial/diagonal values are distances from the snap axis.

## Comparison table

Frame: z=0 is the snap bottom and z=t is the top (notch face). Front = −Y and back = +Y (the directional nub). "lib" = opengrid_snap_lib.

| feature | ours | PDF | fork | SCAD | verdict |
|---|---|---|---|---|---|
| Body width × height | 24.80 × 24.80 (core x/y ±12.40 at all z) | n/a | n/a | lib 24.8 (`opengrid_base.scad:9`); QW 24.80 (:37); official ±12.40 | match |
| Thickness std / lite | 6.80 / 4.00 / 3.40 (bbox z) | 6.8 board (A-A) | 6.8 (`constants.py:5`) | lib 6.8 / 4 / 3.4 (`opengrid_base.scad:5-7`, parametric :12); QW 6.8 / 3.4 (:38-39); official 6.8 / 3.4 | match |
| Core corner chamfer | leg 4.818 (inner diagonal 14.129) | n/a | n/a | lib `OG_SNAP_CORNER_CHAMFER` = (2.7+1/√2)·√2 = 4.818 (`opengrid_base.scad:10-12`); QW rounding 4.81837 with `$fn=2` (:50); official diagonal 14.13 | match |
| Top corner pad, radial reach | 15.23 over the full z 5.3–6.8 (prism) | B-B 1.4×1.4 board chamfer | diagonal bump 1.4 (`base.py:104`) | lib prismoid `yang=[45,90]` (:232): 15.23 only at z ≥ 6.4, then 45° down to 14.13 at z 5.3. Probe along x=y (x coordinate of the outer edge) at z 5.5: lib 10.129, official 10.132, QW 10.133, ours 10.769. At z 6.45: all 10.765–10.769 | **ours wrong** |
| Directional back-bottom corner pad | radial 14.73 over z 0–1.5, no fillet | n/a | n/a | lib `yang=[90,45]`, r 1.5 rounding (:235-241). official: 14.73 up to z 0.9, then slope (x=y probe: 10.20 @1.2, 10.03 @1.45). ours − official 1.18 mm³ per corner | **ours wrong** |
| Basic nub (std): z range, depth, base/tip | z 3.4–5.4, reach 12.80, base 10.8, tip 6.8, 35°/35° | n/a | n/a | lib inset 7, depth 0.4, taper 4, 35/35, offset 1.4, `shiftout=-EPS` → reach 12.795 (:105-125, :358), plus r 15 fillet (:360-361): width ±4.276 @x12.6. official reach 12.80, width ±4.396 @x12.6. QW (:60-71) reach 12.79 | match (ours = official ≤0.004; lib fillet narrower, n/a) |
| Basic nub lite height | 1.8 (z 0.2–2.0 at t 3.4) | n/a | n/a | lib 1.8 (:113); official lite: no residual vs ours | match |
| Directional back nub (std) | z 1.4–5.4, reach 13.20, flat 2.6–4.0, base 14.8 → tip 13.2 | n/a | n/a | lib inset 5, depth 0.8, taper 1.6, h 4 (:114-122): reach 13.195. official reach 13.20 with identical radial profile; width ±7.359 @y12.6 and ±6.714 @y13.1 (ours ±7.20 / ±6.70, lib ±7.162 / ±6.151) | radial: match. Base width: spec ambiguous (official ≈15.2 at base vs lib/ours 14.8) |
| Directional back nub (lite): flank profile | reach at x=0: 12.45@z0.05, 12.70@0.3, 13.00@0.6, 13.20@0.8, 13.10@1.0, 12.96@1.2 | n/a | n/a | lib: 12.71 / 12.89 / 13.10 / 13.195 / 13.195 / 13.19. official: 12.70 / 13.10 / 13.20 / 13.20 / 13.10 / 12.96 | **ours wrong**, lower flank. Upper flank: ours = official, lib differs |
| Antidirectional (front) nub | std h 2, lite 1.4, basic profile | n/a | n/a | lib (:123-124, :350); official dir: no front-nub residual | match |
| Bottom cuts (relief slots) | 0.6 wide at r 11.1–11.7, length 12.4, z −0.005…6.205 (std) / 2.805 (3.4), square ends; none on directional back | n/a | n/a | lib inset 6.2, thickness 0.6, offset-to-edge 0.7, top at t−0.6 (:54-57, :269-276), r 0.3 ends except directional front (:271), none on directional back (:272). official same, with rounded ends (ref−ours 0.63 mm³ per side) | match (dims). Square ends: **ours wrong**, minor |
| Side cuts | depth 0.8, z t−1.2…t−0.8, length 12.4, on all 4 sides including front with notch | n/a | n/a | lib (:58-60, :277-281); front disabled when the notch is on (`base_snap` :500). official: present on front (no notch); **absent on directional back** (x=0 at z 5.8: official 12.40, lib/ours 11.60) | Front + notch: **ours wrong** vs lib. Directional back: spec ambiguous (lib vs official) |
| Directional front lead-in slant | **absent**. Front face at y −12.40 at z 0.05; front bottom cut vertical at −11.7…−11.1. Slant tool removes only a ~0.012 sliver | n/a | n/a | lib (:283-308): face slant 0.8 over 3.4 std, 0.2 over 1.2 lite, corner slants 0.8/√2, front bottom cut shifted with the slant. official = lib exactly: x=0, z=0.05: face −11.612, cut −10.912…−10.312; corner diagonal 13.565 at z 0 | **ours wrong** |
| Uninstall notch | surface 5 × 1.0 × 1.2 at top front. Gap 5 × 1.8 × 1.0 offset 1.0 inward (y −11.4…−9.6). Nub not trimmed | n/a | n/a | lib (:172-198, :367-392, :502-503): gap aligned to the front face (y −12.4…−10.6, z 4.6–5.6), nub in front trimmed. official: no notch | **ours wrong** vs lib. Notch itself: lib-only feature |
| QW change: nub `w/2 → w/2−0.01` (`2c24ea1`, QW :22) | nub reach 12.80 | n/a | n/a | QW new 12.79, old 12.80; lib 12.795; official 12.80. QW new − old: ≤0.82 mm³, nub faces only | match (Δ 0.01 within tol, QW-only mesh fix) |
| QW change: lite click hole height 2.8 → 1.5 (`5c84f2e`, QW :107) | lite bottom cut top z 2.805 (t 3.4) | n/a | n/a | QW new 1.5 (old 2.8); lib t−0.6 = 2.8 (:273-275); official lite 2.8. QW new − old: +9.57 mm³ per hole (z 1.5–2.8 filled) | match (ours = lib = official = old QW). New QW is a CGAL bridge workaround, not a spec change |
| QW change: directional rear click hole 2.2 → 0.9 lite (QW :110) | ours has no bottom cut on the directional back (lib :272) | n/a | n/a | QW-only feature, z 0.599 + 0.9 (old 2.2) | n/a (no counterpart in our builders) |
| Fit: snap width vs board lip | 24.80 vs lip opening 25.00 → 0.10 per side | A-A: face wall 1.1 → 25.8, lip 1.5 → 25.0, groove 0.8 → 26.4 | `snap_cut_bottom_width` 1.1 + chamfer 0.4 → 25.0 (`base.py:97-98`, :128-162) | lib/official snap 24.8 | match |
| Fit: nubs in groove | basic 12.80 / directional 13.20 vs groove half-width 13.20; interference 0 | groove 0.8 → 13.2 | 13.2 (`base.py:150-157`) | lib/official 0 interference | match (directional nub flush, 0.00 radial clearance, same as official) |
| Fit: corner diagonal | body 14.129 vs board block 14.229 at mid-depth (0.10). Pads: see next row | B-B 1.4 × 1.4 | 5.57 offset, 1.4 bump (`base.py:167-194`) | lib/official pads follow the 45° board chamfer with 0 clearance | match (body) |
| Fit: total interference, snap in official / our / fork Full board | 12.81 mm³ (Sym 6.8), 14.91 mm³ (Dir 6.8; also flipped), 14.33 mm³ (expanding Dir 6.8): 3.20 mm³ per top corner z 5.3–6.4, plus 1.05 mm³ per directional back-bottom corner z 0.9–1.5 | — | same (board identical) | lib base 0.000, lib expanding 0.000, QW 0.01 (nub EPS) | **ours wrong** |
| Expanding: body orientation | not flipped: notch/top at z 6.8, nubs z 3.4–5.4; thread entry at z 0 = wall side | n/a | n/a | lib `up(t) yrot(180) base_snap` (:551): top face at z 0 with the entry, nubs z 1.4–3.4 | **ours wrong** |
| Expanding: side/bottom cuts disabled | yes (`enable_cuts=False`, :941), slant kept | n/a | n/a | lib `disable_all_side_cut/bottom_cut` (:527). The slant goes too (it needs `!disable_all_bottom_cut`, :283); only the corner/face slant of :299-308 remains | match (cuts). The slant is the same broken tool |
| Expanding: distances / heights | expand 1.0 / 1.2, entry 0.4 / 0.4 / blunt 1.0, end 2.0 / 1.2, split 45° | n/a | n/a | product 1.0 / 1.2 (`opengrid_expanding_snap.scad:22,24`; lib default 0.6 / 0.4 at `threads_lib:47-48`), entry/end (`threads_lib:49-54`) | match (constants) |
| Expanding: thread relief direction | hole chord along 45° grows 15.03 (z 0.2) → 17.27 (z 5.5); along 0° 15.29 → 16.66 | n/a | n/a | lib partition `spread=-d` (`threads_lib:182-185, 193-196`): along 45° 15.50 → 14.49 (−1.0 = d); along 0° 15.50 → 14.77 | **ours wrong**, expansion inverted |
| Expanding: spring slots | one 0.42 slit along 135° through the centre (±13.4), plus slots along 45° from r 10.35 out through the NE/SW corners | n/a | n/a | lib gap 0.42, spring 1.26, to-centre 0.84 (:200-217): middle gap r 3.78–12.87 along 135°/315°, plus two flanking slots offset 1.68 from r 9.09 out through the corner (:429-481). No 45° slots | **ours wrong**. Constants match |
| Expanding: total | vol 2524.7 (Blunt Dir 6.8) | n/a | n/a | lib 2622.7. Sym-diff 177 / 275 mm³ | **ours wrong** |
| Assembled openConnect: head orientation | large 17 × 10.6 profile on the snap (z 6.85 x ±8.50), small at the top (z 9.35 x ±7.10) | n/a | n/a | `attach(TOP,TOP)` flips the head (parametric :423-424): z 6.85 x ±7.10, z 9.35 x ±8.50 | **ours wrong** |
| Assembled openConnect: height | 9.38 | n/a | n/a | 9.40 (6.8 + 2.6) | **ours wrong**, 0.02 |
| Assembled multiConnect: head orientation / height | R10 on the snap (z 6.85 x ±10.00), R7.5 at the top; top 10.78 | n/a | n/a | R7.5 on the snap, R10 outermost (parametric :425-427); top 10.80 | **ours wrong**  |
| Assembled multiConnect: top pattern | coin slot (z 10.5 area 143.8 mm²) | n/a | n/a | `top_pattern="dimple"` (parametric :427) | **ours wrong** |
| Assembled Bare | snap body only | n/a | n/a | parametric :405-416 | match (body findings above apply) |
| Assembled Basic Threads | threads **unioned as a stud on top** (z 6.79–13.59, bbox z 0–13.59). Axis is solid at z 3.4 and at z 10 | n/a | n/a | `attach(TOP, BOTTOM, inside=true)` inside `diff()` (parametric :418-421) has the default "remove" tag, so it makes a **threaded hole** through the 6.8 body (height t+EPS) | **ours wrong** |

## Discrepancies

### Ours wrong

1. **Corner pads have no 45° underside and no directional fillet.** All variants are affected. In the official board, our board and the fork board, each top pad overlaps the board's 1.4 × 1.4 corner chamfer by 3.20 mm³ (up to 1.0 mm radially at z 5.4). Each directional back-bottom pad overlaps by 1.05 mm³. The SCAD lib, QW and the official STEPs all slope these pads. `directional_corner_fillet_radius` is never used.
   - Resolution: pads are prismoid hulls with the 45° slope; directional bottom pads have the r 1.5 plan fillet. Interference in the official / our Full board: 14.907 → 0.001 mm³ (Dir 6.8), 12.808 → 0.000 mm³ (Sym 6.8). Residual vs SCAD: 0.051 mm³ per pad.
2. **The directional front lead-in slant is missing.** The slant tool degenerates into a sheet about 0.01 mm thick. Ours is 33.5 mm³ fuller at the front than lib and official. The front bottom cut does not follow the slant. This affects snap_body, expanding_snap and opengrid_snap.
   - Resolution: face wedge, two corner wedges, and the front bottom cut sheared with the slant. At x=0, z=0.05: face −11.612, cut −10.912…−10.312. At z=1.7: −12.0 and −11.3…−10.7. Front corner diagonal at z 0: 13.565. These values equal the official v2.1 and SCAD. Dir 6.8 vs SCAD: 71.3 / 40.6 → 2.2 / 0.19 mm³. The remainder is the lib r 15 nub fillets.
3. **The notch and the front cuts deviate from the lib.**
   - The notch gap sits 1.0 mm inward instead of flush with the front face.
   - The nub in front of the notch is not trimmed.
   - The front side cut is added when the notch is enabled; the lib disables it in that case.
   - Bottom-cut ends are square, but lib and official round them (r 0.3).
   - Resolution: gap y −12.4…−10.6, z 4.6–5.6, and the nub in front is trimmed (y −14.2…−12.4). The front side cut is omitted when the notch is on. Bottom cuts have r 0.3 stadium ends, except the directional front. Sym 6.8 vs SCAD: 18.8 / 9.16 → 1.35 / 0.23 mm³. With no notch, Sym 6.8 vs official: 0.13 / 0.64 mm³.
4. **Lite directional back nub: the lower flank starts at z=0.** It should start from the unclipped base at z=−0.4. At z 0.3 our reach is 12.70, against 13.10 official and 12.89 lib.
   - Resolution: the nub is built from the unclamped base and then clipped at z 0. Reach at z 0.3 / 0.6 / 0.8–1.6 now equals the official. At z 0.05 ours is 12.85 and official is 12.70: the official lower flank is curved below z 0.3.
5. **Expanding snap.**
   - The body is not flipped, so the screw entry is on the wall face.
   - The thread relief widens by about 2d instead of narrowing by d, so the snap cannot expand.
   - The spring geometry differs: the flanking spring slots are missing, and extra slots cut through the NE/SW corners.
   - The thread cut tool is coarse (18 segments, one step).
   - Resolution: the body is flipped (`up(t) yrot(180)`), so the nubs are at z 1.4–3.4. The entry band has no squeeze. Each transition band is 0.05 mm of squeeze (ceil(d/0.05) bands), and the end band has the full d. In every band the thread negative is split along the 45° plane, the |p·u| < d/2 strip is dropped, and the two halves are joined (`partition(spread=−d)`). The `expanding_spring` middle gap (profile with pads and slant, face flares) and the four flanking slots are ported. The middle gap has square edges: the source `os_smooth` bullnose is not ported, which leaves 0.28 mm³ per slot end. Basic Dir 6.8 chords along 0° / 45° / 90°: z 0.2 15.49 / 15.49 / 15.49; z 6.3 14.76 / 14.48 / 14.77. SCAD gives 15.50 / 15.50 / 15.50 and 14.77 / 14.49 / 14.77. Basic vs SCAD sym-diff (all 4 variants): ≤ 1.7 / 0.7 mm³ plus the lib nub fillets. Volumes are 2589.4 vs 2586.3 (Dir 6.8) and 1322.0 vs 1320.4 (Dir 3.4). The flanking slots and the middle-gap profile agree within 0.005 mm in ray probes. Board interference is 0.001 mm³. The thread negative uses 72 segments per turn (chord sag 0.008 mm) to keep the build at about 35 s and 2–3 GB.
   - Blunt deviation: we slice one continuous thread negative. SCAD instead stacks separate Blunt `snap_threads` segments. Each of those segments ends its helix 1.25 below its own top, so the ridge in each band comes from the overhang of later, more-squeezed segments. Because of that, SCAD's 1.0 mm "unsqueezed" entry is in fact narrowed: at z 0.2 the 0° chord is 15.37 in SCAD and 15.49 in ours. Blunt vs SCAD: Dir 6.8 2612.0 vs 2622.7 mm³ (SCAD − ours 13.9 mm³), Dir 3.4 1343.4 vs 1355.0. The flip, the 45° narrowing, the springs and the end-band chords (z 6.3: 14.17 / 13.49 / 13.77 vs 14.15 / 13.50 / 13.78) match.
6. **Assembled openConnect / multiConnect heads are mounted upside down.** Both are also 0.02 mm short. The multiConnect head uses a coin slot where the SCAD snap uses a dimple.
   - Resolution: `_flip_snap_head` rotates the head 180° about Y (small face on the snap) and seats it without height loss. The assembled openConnect snap is one solid, z 0–9.40. Sections: z 6.85 x ±7.10, z 9.35 x ±8.50, y −1.70…8.90. Section sym-diff vs the SCAD `asm_oc` render is ≤ 0.003 mm² at z 6.82–9.40.
   - Resolution: the same flip for multiConnect. Now R7.5 sits on the snap (z 6.85 r 7.50) and R10 is outermost (z 9.82–10.80 r 10.00). Top is at 10.80. Taper sections are within 0.07 mm² of `asm_mc`.
   - Resolution: the `OpenGridSnapConfig.multiconnect_head` default is now `top_pattern="dimple"`. The pocket on the outer face is r 1.045 at 0.005 deep, r 0.55 at 0.5 and r 0.06 at 0.99 (official `round.step` profile). There is no coin slot.
7. **Assembled Basic Threads adds a thread stud instead of cutting a threaded hole.** It is not a snap with an internal thread. This was confirmed on built geometry: bbox z 0–13.59, solid on the axis at z 3.4.

### Fork wrong

None. The fork models no snap. Its `BaseSnapSlotCutter` equals the official board and our Full board slot (zero interference difference). Every snap-fit dimension it carries (lip 1.1 + 0.4, groove 0.8, corner 5.57 / 1.4) matches PDF A-A / B-B.

### Spec ambiguous

8. **Directional back side cut.** The lib cuts it on all four sides (`snap_cut` :277-281). The official directional v2.1 (std and lite) has no back side cut. Ours follows the lib.
9. **Directional back nub base width.** Lib and ours use 14.8 (inset 5). Official is ≈15.2 at the base, with the tip at 13.2. The radial profile matches.
10. **Lite directional back nub upper flank.** Ours and official use 35°. The lib applies the 45° `directional_nub_bottom_angle_lite` to the upper face, because BOSL2 `yang[1]` is the back (+Z after attach).
11. **Notch versus official.** The uninstall notch is a lib/product option (`notch_width` 5). The official snaps have none.
12. **QW `5c84f2e` lite click hole height (1.5 vs 2.8).** Ours, the lib, the official STEP and old QW all use 2.8. New QW changed it only to work around CGAL mesh connectivity, so it is not followed.

### QuackWorks change impact (6123129..e0c1cb7)

- `:22` nub shift of −0.01: QW nub reach 12.80 → 12.79. Ours is 12.80, lib 12.795, official 12.80. This is within tolerance and only a mesh-connectivity fix. **No effect on our builders.**
- `:107` lite main click hole 2.8 → 1.5 and `:110` lite directional rear hole 2.2 → 0.9. These are lite-only; the standard snap is unchanged (new − old ≤ 0.82 mm³). Our lite bottom cut (2.8) follows the lib and official; our builders have no rear-hole counterpart. **No dimension our builders use changes.** New QW is the outlier versus the official lite STEP.

## Proposed fix issues

- Snap corner pads: add the 45° underside slope and the directional bottom-corner fillet (removes the board interference).
- Directional snap: implement the front lead-in slant (face, corners, slanted front bottom cut) per `snap_cut` :283-308.
- Uninstall notch: flush the gap to the front, trim the nub in front of it, disable the front side cut when the notch is on, round the bottom-cut ends r 0.3.
- Lite directional back nub: apply the flank slope from the unclamped base (z −0.4), then clip at z 0.
- Expanding snap: flip the body; narrow the thread relief by d (partition-style, ≈0.05 steps); port the `expanding_spring` slots; drop the 45° corner slots; use a finer thread cut tool.
- openConnect snap: flip the head (small profile on the snap) and fix the 0.02 height loss.
- multiConnect snap head: use the dimple top pattern, as in the SCAD snap.
- The multiConnect snap head flip (not re-filed).
- Basic Threads (found by the snap threads audit): cut a threaded hole instead of adding a stud.
  - Resolution: the threaded hole is now cut through the body with the source flip. Bbox z 0–6.8, and the axis is open. The mesh difference against the SCAD hole composition is ≤0.62 mm³. A seated clearance-0 screw thread interferes 0.000 mm³. Details: `snap-threads.md` § Resolution.
