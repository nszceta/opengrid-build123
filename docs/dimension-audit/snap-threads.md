# Snap threads dimension audit

## Scope

- `build_snap_threads()` with `SnapThreadConfig` and `ThreadType.BLUNT` / `ThreadType.BASIC` (`src/opengrid_build123/opengrid.py:241-268`, `:1870-2009`, constants `:97-113`).
- The export `output/snap_threads.step` (default config: Blunt, h 6.8, Ø16 + 0.5 clearance).
- Where the primitive is used, as far as the thread geometry is concerned:
  - Multiconnect screw (`opengrid.py:1011-1013`) and openConnect screw (`:973-975`), both with clearance 0.
  - The Basic Threads snap attachment (`:1037`, `:2694-2701`).
- Not in scope: head, body and expanding-spring geometry. Other audits cover these.

## Sources

| Id | Source |
|---|---|
| PDF | `../reference_docs/openGrid Multiconnect Thread Docs.pdf`, page 1 (only page). Title "openGrid Multiconnect T…", scale 6:1, dated 08/01/25. Text extraction gives only bare numbers, so the dimensions were read from a 300 dpi rasterization (`pdftoppm -r 300`). The page has two views. "Negative" is the cut tool: Ø14.5, groove 1 deep, 0.5 flats, bottom lip 0.8×45° + 0.2 land to Ø12.9. "Positive" is the screw: Ø14 core, thread 1 deep, 0.5 crest, 0.5 root, 1 axial per flank, tip chamfer 1×1. No lengths, turns, handedness or phase are given. |
| SCAD | `../reference_repos/opengrid-projects/lib/opengrid_threads_lib.scad` (`threads_cfg` :12-44, `blunt_threads` :77-111, `snap_threads` :113-145), `lib/opengrid_base.scad:18-28` (profile, Ø16, clearance 0.5, compat angle 53.5, pitch 3) |
| SCAD use | `opengrid_parametric_snap.scad:418-421` (snap hole: `attach(TOP,BOTTOM,inside=true)`), `:358-362` (Multiconnect screw), `:448-455` (screw seated in snap: `up(h+head) yrot(180)`), `lib/openconnect_lib.scad:520-523` (openConnect screw) |
| BOSL2 | `../reference_repos/BOSL2/threading.scad:1835-2093` (`generic_threaded_rod`: phase, bevel cone :2036-2051), `:2382+` (`thread_helix`), `attachments.scad:765` (`inside=true` ⇒ default tag `"remove"`) |
| fork | `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/*.py`. It has no thread code at all (grep "thread" finds nothing). |
| QuackWorks | `../reference_repos/QuackWorks/openGrid/*`, `Modules/*`: no thread code. The Underware files use Multiboard small threads instead (`Underware/Underware_Connectors.scad:58-64`: Ø6.747, pitch 3, 60° flank, 0.5 depth). These are not openGrid snap threads. |

## Method

1. Built with `uv run python` (throwaway scripts outside the repo):
   - `build_snap_threads()` for Blunt and Basic, at clearance 0.5 and 0.
   - Lite heights 4.0 and 3.4.
   - `build_multiconnect_screw()`.
   - `build_opengrid_snap(kind=BASIC_THREADS)`.
   - Imported `output/snap_threads.step`.
   - Exported each shape to STL (tolerance 0.002 mm, angular 0.05).
2. Reference renders: OpenSCAD 2021.01 (official AppImage) rendered with the in-tree BOSL2 (`BOSL_VERSION 2.0.742`) and `$fa=1; $fs=0.4` (the same values as `opengrid_parametric_snap.scad:169-170`):
   - `snap_threads(threads_height=6.8, text_cfg=["text_depth",0], …)` for Blunt/Basic × clearance 0.5/0.
   - `opengrid_parametric_snap.scad -D generate_screw="multiConnect" -D generate_snap="None"`.
   - A minimal hole composition matching `:418-421`: `diff() cuboid([24,24,6.8]) attach(TOP,BOTTOM,inside=true,shiftout=EPS/2) snap_threads(6.8+EPS, …)`.
   - The full parametric Basic Threads snap STL came out broken (sections had no hole loops), so it was not used. The minimal composition replaces it.
3. Probes, all done the same way on ours and SCAD:
   - **Z sections** (`trimesh.section`), giving min/max radius per z: major/minor diameter and bevels.
   - **Radial rays** at 0/90/180/270° (actual angle about +X, CCW), 6801 z samples per ray, inward for external threads and outward via section polygons for holes. They give crest-flat centres (pitch, phase, handedness) and the z range where the thread is present (thread start/end).
   - **Ideal-profile deviation**: rays at 50 angles × 400 z, compared with the analytic profile. The profile is right-handed, crest centre at z = θ·3/360 + c, 45° flanks, 0.5 crest, 0.5 root, depth 1, measured in the region free of bevels.
   - Half-plane sections of the build123d solid at 0/53.5/90° to check the flank angle.
4. Tolerance is 0.01 mm. "Phase c" means the crest-centre z at actual angle 0°, mod 3.

## Comparison

| feature | ours | PDF | fork | SCAD | verdict |
|---|---|---|---|---|---|
| Major Ø, external (clearance 0) | 16.00 (section rmax 8.000, bbox ±7.999) | 16 (14 + 2×1), p1 Positive | — | 16.00 (rmax 7.999–8.000), `opengrid_base.scad:24` | match |
| Minor Ø, external | 14.00 (rmin 6.998–7.000) | 14, p1 Positive | — | 14.00 (rmin 7.002) | match |
| Major Ø, cut tool (clearance 0.5) | 16.50 (rmax 8.25; STEP bbox ±8.249) | 16.5 (14.5 + 2×1), p1 Negative | — | 16.50 (rmax 8.25) | match |
| Minor Ø, cut tool | 14.50 (rmin 7.248–7.25) | 14.5, p1 Negative | — | 14.50 (rmin 7.252; `blunt_threads` core `d-2`, :91) | match |
| Clearance (on Ø) | 0.5, `opengrid.py:98`, `effective_diameter` :266-268 | 0.5 (14.5 − 14) | — | 0.5, `opengrid_base.scad:25`; screws use 0 (`:362`, `openconnect_lib.scad:518`) | match |
| Thread depth (radial) | 1.000 | 1, p1 | — | 1.000 (profile y −1/3·p) | match |
| Pitch | 3.000 (crest centres 2.554→5.556 at 0°; 1.054→4.055 at 180°) | 3 (0.5+1+0.5+1), p1 | — | 3.000 (0.304→3.304, 1.804→4.804) | match |
| Crest flat / root flat | 0.5 / 0.5 (profile `opengrid.py:101-106`) | 0.5 / 0.5, p1 | — | 0.5 / 0.5 (`opengrid_base.scad:18-23`) | match |
| Flank angle | 45° (half-plane 53.5°: Δr 0.8655 = Δz 0.8655) | 45° (1 axial : 1 radial), p1 | — | 45° | match |
| Profile accuracy vs ideal (bevel-free region) | max \|err\| 0.0315–0.0325, p99 0.023 (STEP and fresh builds) | — | — | max \|err\| 0.0026 | ours wrong. Corners are chorded between the 0/90/180/270° breakpoints (`opengrid.py:1989-1998`). |
| Handedness | right (crest z rises with CCW angle) | not stated | — | right (BOSL2 default `left_handed=false`) | match |
| Starts | 1 | not stated | — | 1 | match |
| Phase c, Basic, standalone frame | 2.554 | not stated | — | 2.554 (`generic_threaded_rod` centred + `zrot(53.5)`, :132-136) | match |
| Phase c, Blunt, standalone frame (STEP, screws) | **1.305** (crest 4.305 at 0°) | not stated | — | 2.554 (same as Basic; zrot+up at :93-95 leaves the helix unchanged) | ours wrong. `_snap_thread_blunt_z_shift` (`opengrid.py:1933-1940`) shifts z without rotating: −1.25 mm = 150° of seat rotation. |
| Thread height / Z anchoring (standalone) | z 0…6.8, centred XY (bbox) | not stated | — | z 0…6.8 (anchor BOTTOM) | match |
| Blunt: thread at thread-frame z=0 | absent below z≈1.05 (2.0 bevel clamp); rmax 7.25 at z 0.01–0.5 | — | — | full profile to z=0 (rmax 8.25 at z 0.01). `snap_threads` passes no bevels to `blunt_threads` (:134, defaults :77) | ours wrong. |
| Blunt: helix end (blunt start) | none; thread to z≈6.79 at every angle; `blunt_cutoff` only clamps the z=h slice to root (`opengrid.py:1956-1957`) | — | — | helix starts at z −1.25, turns (h−1.5)/3+0.5, 10° lead-in taper (`:83-99`). Thread ends at z 6.727/4.501/5.251/6.001 at 0/90/180/270° | ours wrong. |
| Blunt: top bevel 0.5 at z=h | applied (rmax 7.75 at z 6.8) | — | — | not applied | ours wrong. |
| `blunt_cutoff` semantics | clamp at z=h | — | — | removes helix overhang below z=0 (:102-103) | ours wrong (different end and meaning). |
| Basic: bevel at thread-frame z=0 | 2.0 (r = 6.25+z, clamped to 7.25) | — | — | 0.5 (`bevel1=top_bevel`, :136): r 7.76 at z 0.01 | ours wrong (ends swapped). |
| Basic: bevel at thread-frame z=h | 0.5 (r 7.76 at 6.79) | — | — | 2.0 (`bevel2`), cone through core: rmin 6.25 (cl 0.5) / 6.00 (cl 0) at the face | ours wrong. |
| Basic: core chamfer | none (`clamp_to_root`, `opengrid.py:1958-1959`) | Positive: tip core chamfer 1×1 (Ø14→Ø12). Negative: lip 0.8×45° + 0.2 land to Ø12.9 | — | Positive tip Ø12.00 (matches PDF). Negative lip 1.0×45° to Ø12.5 at the face, no land | ours wrong (no chamfer or lip). SCAD vs PDF on the negative lip: spec ambiguous (Ø12.5 vs Ø12.9). |
| Bevel selection by height | 2.0 if h≥6.8, 1.2 if h≥3.4, else 0 (`opengrid.py:1963-1968`) | — | — | same (:125-128) | match |
| Lite h=4.0 / 3.4 | bbox z 0…4.0 / 0…3.4, Ø16.5 | — | — | same anchoring | match (bevel and blunt issues above still apply) |
| Blunt offset_height | uses bottom bevel (2.0/1.2) in `min(h−1.5−bb,0)` (`opengrid.py:1939`) | — | — | `bottom_bevel` = 0 here (:86, the call at :134 passes none) | match for h≥2.7 (both 0). Diverges only for custom h<2.7 |
| Multiconnect screw thread (head frame) | z 4.0…10.8, phase 1.304, no thread for the first 1.05 mm next to the head, full thread at the tip, tip core Ø14 | Positive: thread up to the head side, tip chamfer to Ø12 | — | z 4.0…10.8, phase 2.554, full thread from the head, blunt helix end at the tip, tip core Ø14 (Blunt) | ours wrong (phase, bevel ends, blunt end). Default Blunt SCAD also lacks the PDF tip chamfer (PDF vs SCAD: spec ambiguous). |
| Basic Threads snap: thread as hole vs stud | **stud unioned on top**: bbox z 0…13.59, centre solid (`opengrid.py:1037`, `:2698-2701`) | Negative = cut tool | — | threaded hole through the 6.8 body (`inside=true` ⇒ `remove`, BOSL2 `attachments.scad:765`). Thread frame turned 180° about Y: hole phase 2.748 (predicted 6.8−1.5−2.554 = 2.746) | ours wrong. |
| Screw seated in snap | — | — | — | `up(h+head) yrot(180)` (`:448-455`) maps the screw thread onto the hole exactly (phase 2.746 = 2.748) | n/a for ours until the Basic Threads hole and Blunt thread fixes land |
| `output/snap_threads.step` vs builder | bbox ±8.249 × 0…6.8, vol 1249.31, phase 1.305, same ray profile as `build_snap_threads()` | — | — | — | export matches the builder; inherits the Blunt issues |
| fork coverage | — | — | no thread code | — | n/a-coverage gap |
| QuackWorks coverage | — | — | — | no openGrid snap threads (only Multiboard Ø6.747 threads) | n/a-coverage gap |

## Discrepancies

1. **Basic Threads snap is a stud, not a hole.** Ours unions the thread solid on top of the body (z 0…13.59). SCAD subtracts it, flipped about Y, as a through hole. This is the biggest functional error: a "Basic Threads" snap cannot take a screw.
2. **Blunt phase is off by 1.25 mm (150°).** The z-only shift in `_snap_thread_blunt_z_shift` changes the helix phase. SCAD's paired `zrot`/`up` only moves the helix ends. This affects `output/snap_threads.step` and both screws (the default thread type is Blunt). Ours Blunt and ours Basic also disagree with each other.
3. **Blunt is modelled as a bevelled full thread.** SCAD Blunt has:
   - no bevels;
   - a full profile at thread-frame z=0;
   - a helix that ends inside the part with a 10° taper (the "blunt start"), which sits at the screw tip or the snap bottom.

   Ours applies the 2.0/0.5 bevels, runs the thread to the top, and gives `blunt_cutoff` a different meaning.
4. **Basic bevel ends are swapped, and the core is never chamfered.** SCAD has 0.5 at z=0 and 2.0 at z=h, and the 2.0 cone cuts through the core (screw tip Ø12, hole lip Ø12.5). Ours has 2.0 at z=0 and 0.5 at z=h, clamped to the root. On the screws, ours puts the large bevel next to the head.
5. **Faceting.** The ruled loft chords the profile corners, which gives errors up to 0.032 mm. The tolerance is 0.01 mm.
6. **PDF vs SCAD (spec ambiguous).**
   - Negative end lip: the PDF has 0.8×45° + 0.2 land to Ø12.9. SCAD Basic has a 1.0×45° cone to Ø12.5.
   - SCAD Blunt (the default) has no tip chamfer or lip at all, but the PDF Positive shows a 1×1 tip chamfer.
   - The PDF does not distinguish Blunt from Basic and gives no lengths, turns, handedness or phase.
7. **Fork and QuackWorks have no openGrid snap-thread geometry.** This is a coverage gap. The fork's claim to be "official" cannot be tested for threads.

All core thread dimensions match the PDF and SCAD within 0.01 mm: Ø16/Ø14 external, Ø16.5/Ø14.5 cut tool, pitch 3, 45° flanks, 0.5 flats, depth 1, right-hand, 1 start, Z anchoring 0…h.

## Proposed fix issues

- Basic Threads snap. Subtract the thread tool instead of unioning it. Turn it 180° about Y with thread-frame z=0 at the snap top, using h+EPS and shiftout as in SCAD. `reverse_threads_entryside` then removes that flip.
- Blunt thread rework.
  - Make the z shift phase-preserving, or drop it and model only the helix start and end.
  - Apply no bevels.
  - Give the helix a finite length: start at z −1.25 (clipped at 0), turns (h−1.5)/p+0.5, 10° lead-in taper at the thread-frame top.
  - Make `blunt_cutoff` remove the below-zero overhang.
- Basic bevels.
  - Swap the ends: `top_bevel` at thread-frame z=0, `bottom_bevel` at z=h.
  - Let the bevel cone cut through the core (no root clamp).
  - Decide whether to follow SCAD (Ø12.5 lip, 1.0 cone) or the PDF negative (0.8 chamfer + 0.2 land, Ø12.9) for the cut tool.
- Priority 3: improve the loft so the profile corners are exact at every angular segment, or use a true helical sweep.

## Resolution

`build_snap_threads()` now lofts the thread profile along its helix (one radial section every 2.5°, exact profile corners in each section) and fuses it to a root-diameter core. It is compared with fresh OpenSCAD renders of `snap_threads` (in-tree BOSL2, `$fa=1; $fs=0.4`) by mesh boolean and by the same ray probes as above.

- Blunt follows `blunt_threads`. It has the Basic helix phase: at +X the crest spans z 2.204–2.904 at r 7.9, so the crest centre is at 2.554. It has no bevels, and the full profile runs down to z=0 (r 8.053 at 0°, z 0.0005; SCAD 8.053). The helix starts at crest z min(h−1.5,0)−1.25 and ends at crest z h−1.25, followed by the BOSL2 sqrt lead-in over 10°. Thread top at 0/90/180/270° (r>7.26 ray, same method on both): 6.758/4.542/5.292/6.042. The SCAD render gives 6.770/4.544/5.294/6.044. `blunt_cutoff` now removes the helix below z=0; `False` keeps it (bbox z −2.5). Mesh difference vs SCAD at 6.8 / cl 0.5: ours−SCAD 0.004 mm³, SCAD−ours 0.49 mm³ (the SCAD core is +EPS). At 4.0 and 3.4 the differences are ≤0.33 mm³; at 1.005 with no cutoff, ≤0.34 mm³. Screws therefore get the full thread at the head and the blunt end at the tip.
- Basic has `top_bevel` at z=0 (r 7.75 at z 0.0005; SCAD 7.749) and the bottom bevel at z=h. Both cones cut through the core: rmin at the z=h face is 6.25 at cl 0.5 (SCAD 6.249), and the screw tip at cl 0 is Ø12.00. The cut tool follows SCAD (1.0×45° cone to Ø12.5, no land) per source precedence; the PDF Ø12.9 lip is not used. Mesh difference vs SCAD at 6.8 / cl 0.5: 0.17/0.08 mm³. At 4.0 and 3.4 it is ≤0.11 mm³.
- The ideal-profile deviation (50 angles × 400 z, bevel-free region) is now max 0.0020 mm for both Basic and Blunt. The SCAD render gives 0.0024. Build time is 3.0 s for Blunt and 4.3 s for Basic; the old loft took 4.6 s and 4.4 s.
- `build_opengrid_snap(BASIC_THREADS)` subtracts `build_snap_threads(height=t+EPS)`, turned 180° about Y with its frame z=0 at t+EPS/2. With `reverse_threads_entryside` it is unflipped from −EPS/2. Bbox z 0…6.8, and the axis is open. Against the SCAD composition `diff() cuboid attach(TOP,BOTTOM,inside=true,shiftout=EPS/2) snap_threads(6.8+EPS)`, the mesh difference is 0.22/0.48 mm³ (Basic) and 0.62/0.19 mm³ (Blunt). A clearance-0 screw thread seated as in `:448-455` interferes 0.000 mm³. Unflipped it interferes 14.7 mm³; with the old X-axis flip, 61.7 mm³.
