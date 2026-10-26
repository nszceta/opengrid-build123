# QuackWorks update 6123129..e0c1cb7 — impact review

## Scope

Review the QuackWorks reference update from `6123129` to `e0c1cb7` (`../reference_repos/QuackWorks`, origin `https://github.com/AndyLevesque/QuackWorks`). Answer two questions:

1. Does the `openGrid/opengrid-snap.scad` change move any snap dimension that our `build_snap_body`, `build_opengrid_snap`, or `build_expanding_snap` use?
2. Did any Multiconnect reference used by the Multiconnect profile audit (`Modules/multiconnectSlotDesign.scad`, `Modules/multiconnectSlotDesignBOSL.scad`, `Modules/multiconnectGenerator.scad`) come only from the removed `MultiConnectOpenSCAD` gitlink? Where does that content live now?

## Sources

- `git -C ../reference_repos/QuackWorks log -p 6123129..e0c1cb7` and `--stat`
  - `e0c1cb7` merge PR #140 "Remove stray MultiConnectOpenSCAD gitlink" (commit `9eeaf78`)
  - `cd59620` merge PR #127 "Fix snaps rendering as disconnected bodies: click hole bridge + nub overlap" (commits `5c84f2e`, `2c24ea1`)
- QuackWorks `openGrid/opengrid-snap.scad` @ `e0c1cb7`: lines 22, 26, 37–42, 58–100, 104–119.
- opengrid-projects `lib/opengrid_snap_lib.scad`: 54–60 (cut defaults), 269–282 (bottom/side cut placement), 272 (no bottom cut on directional BACK), 358 (nub `shiftout=-EPS`), 527 (expanding snap disables side/bottom cuts).
- Ours `src/opengrid_build123/opengrid.py`: 280–295 (`SnapBodyConfig` cut defaults), 912–931 (`build_snap_body`), 933–946 (`build_expanding_snap`, line 941 `enable_cuts=False`), 1018–1037 (`build_opengrid_snap`), 1473–1482 (`_snap_body_nubs`), 1573–1613 (`_snap_body_cut_tools`, `_snap_body_bottom_cut`, `_snap_body_side_cut`).
- `../reference_docs/opengrid-tile-dimensions.pdf` page 1: tile drawing only ("Opengrid Raw Tile"). It has no snap dimensions, so the PDF column is n/a.
- Fork `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/`: it has no snap body. It only has `BaseSnapSlotCutter` (`base.py:92`), which is the tile-side slot. So the fork column is n/a.
- Official snap STEPs by David D (Shapr3D export, 2025-08-07), Printables model 1214361. ForkProvenance pointed me to them. I downloaded them anonymously via the Printables GraphQL `getDownloadLink` mutation and kept them in a local cache outside the repo:
  - `opengrid-bare-snap.step` (file id 5805721)
  - `opengrid-bare-lite-snap.step` (5805722)
  - `opengrid-bare-directional-snap-v21.step` (5828016)
  - `opengrid-bare-directional-lite-snap-v2.step` (5828017)

  These are the strongest evidence for snap geometry. They are cited below as "official STEP".

## What changed and why

| commit | file | change | stated reason |
|---|---|---|---|
| `5c84f2e` | `openGrid/opengrid-snap.scad:107` | main bottom click hole height: `2.8 + (lite ? 0 : fulldiff)` → `lite ? 1.5 : 2.8 + fulldiff` | Lite snap left a 0.2 mm bridge over the 2.8 mm hole in the 3.0 mm core. CGAL produced disconnected STL bodies. Lite only. The commit says "Standard snap is unaffected". |
| `5c84f2e` | `openGrid/opengrid-snap.scad:110` | directional rear click hole height (starts at z = 0.599): `2.2 + (lite ? 0 : fulldiff)` → `lite ? 0.9 : 2.2 + fulldiff` | Same CGAL bridge issue, lite only |
| `2c24ea1` | `openGrid/opengrid-snap.scad:22` | nub placement `move([w/2, 0, 0])` → `move([w/2 - 0.01, 0, 0])` | Nub only touched the core face, and slicers split it into a separate shell. A 0.01 mm inward shift makes the nub overlap the core volume. |
| `9eeaf78` | `MultiConnectOpenSCAD` (mode 160000) | gitlink deleted | No `.gitmodules` ever existed, so `git submodule update --init --recursive` failed. Every commit the gitlink recorded is in QuackWorks' own history. MultiConnectOpenSCAD is the repo's former name: someone committed a nested clone by accident. |

`git diff 6123129 e0c1cb7` touches only those two paths. `Modules/` has no change in the range.

## Method

- Built our snaps with the repo builders (throwaway scripts outside the repo, run with `uv run python`, not committed):
  - `build_snap_body(SnapBodyConfig(body_shape=S, thickness=t))` for S ∈ {DIRECTIONAL, SYMMETRIC} and t ∈ {6.8 standard, 3.4 lite}
  - `build_expanding_snap(ExpandingSnapConfig(snap_body=SnapBodyConfig(thickness=t)))`
  - `build_opengrid_snap(OpenGridSnapConfig(snap_body=SnapBodyConfig(thickness=t)))`
- Probes on each built shape:
  - `len(shape.solids())`
  - `shape.bounding_box()`
  - Bottom-cut height: `shape.is_inside(Vector(x, y, z))` scanned in 0.01 mm steps from z = 0.02 at the cut centre (1.0 mm in from each side face: (±11.4, 0) and (0, ±11.4)). The reported value is the first z with material.
  - Cut radial extent: x scan at y = 0, z = 1.0.
  - Cut tangential extent: y scan at x = 11.4, z = 1.0.
- QuackWorks values come from the SCAD expressions at `6123129` (old) and `e0c1cb7` (new). Snap width is `w = 24.80` and `fulldiff = 3.4` (`opengrid-snap.scad:37–38`).
- Official STEPs: `bd.import_step(...)`, translated so the bbox centre is at XY 0 and min Z = 0. Probes, using `is_inside` on every solid of the import:
  - Radial scan along each axis at z = 0.3 (0.01 steps), split into contiguous gap segments.
  - For each segment, a z scan at the segment centre gives the first z with material.
  - A tangential scan gives the half-length.
  - Caveat: on the directional files the bbox centre sits about 0.1–0.2 mm off the body centre in Y, because the nubs are asymmetric. So the ±X half-lengths read 6.0 / 6.4; the true value is 6.2.

### Probe results (built geometry)

| build | solids | bbox X / Y / Z | material starts above bottom cut (side faces with a cut) | side with no bottom cut |
|---|---|---|---|---|
| snap body DIRECTIONAL 6.8 | 1 | ±12.8 / −12.8…13.2 / 0…6.8 | z = 6.21 (±X, −Y) | +Y (back): material at z = 0.02 |
| snap body DIRECTIONAL 3.4 | 1 | ±12.8 / −12.8…13.2 / 0…3.4 | z = 2.81 (±X, −Y) | +Y (back): material at z = 0.02 |
| snap body SYMMETRIC 6.8 | 1 | ±12.8 / ±12.8 / 0…6.8 | z = 6.21 (all four) | — |
| snap body SYMMETRIC 3.4 | 1 | ±12.8 / ±12.8 / 0…3.4 | z = 2.81 (all four) | — |
| expanding snap 6.8 / 3.4 | 1 / 1 | — | none: material at z = 0.02 (cuts disabled, `opengrid.py:941`) | all |
| opengrid_snap (openConnect) 6.8 / 3.4 | 1 / 1 | — | z = 6.21 / 2.81 | — |

- Bottom cut radial extent at z = 1: x = 11.11…11.69. This is 0.6 wide and centred on 11.4 = w/2 − 1.0.
- Bottom cut tangential extent: material returns at |y| = 6.2, so the cut length is 12.4.
- The first-material z is cut top + 0.01 because of the 0.01 scan step. Cut top = thickness − 0.6 (`opengrid.py:1587`).

### Probe results (official STEPs)

| file | solids | size X × Y × Z | bottom cut: radial range, first material z, half-length |
|---|---|---|---|
| bare snap | 9 (body 3670.49 + 4 × 6.19 + 4 × 5.15 separate solids) | 25.6 × 25.6 × 6.8 | all four sides: 11.11…11.69, z 6.2, 6.2 |
| bare **lite** snap | 9 (body 1837.36 + 4 × 6.19 + 4 × 4.45) | 25.6 × 25.6 × 3.4 | all four sides: 11.11…11.69, **z 2.8**, 6.2 |
| directional v2.1 | 1 | 25.6 × 26.0 × 6.8 | ±X: 11.11…11.69, z 6.2. +Y: no full-height cut; a 12.21…12.39 segment reaches z ≈ 1.55. −Y: segments 10.58…11.17 (z ≈ 1.6) and 11.88…12.39 (z ≈ 1.43). |
| directional **lite** v2 | 1 | 25.6 × 26.0 × 3.4 | ±X: 11.11…11.69, **z 2.8**. +Y: no inner gap. −Y: 11.21…11.79 (0.1 offset from the centring), **z 2.81** |

Ours, directional lite, same probe: ±X 11.11…11.69, z 2.81. +Y: no inner gap. −Y: 11.11…11.69, z 2.81, plus a 0.03 sliver at 10.91 from the slant tool. This matches the official directional lite file.

## Comparison: snap change

| parameter | old (6123129) | new (e0c1cb7) | ours (built) | affected? |
|---|---|---|---|---|
| snap width `w` | 24.80 (`:37`) | 24.80 | 24.80 (bbox ±12.8 minus 0.4 nub) | no |
| main click hole height, standard | 2.8 + 3.4 = 6.2 (`:107`) | 6.2 | 6.2 (probe 6.21) | no |
| main click hole height, **lite** | 2.8 (`:107`) | **1.5** | **2.8** (probe 2.81) | **yes: ours = old QW** |
| main click hole width × length × inset | 0.6 × 12.4 at w/2−1 | unchanged | 0.6 × 12.4 centred at w/2−1 (probe) | no |
| rear directional click hole, standard | z 0.599…6.199 (`:110`) | unchanged | no rear bottom cut. Ours follows `opengrid_snap_lib.scad:272` and uses a slant tool instead (`opengrid.py:1580`). | no (different topology, unchanged upstream) |
| rear directional click hole, **lite** | z 0.599…2.799 | **z 0.599…1.499** | same as row above | no direct counterpart |
| nub x origin | w/2 = 12.40 (`:22`) | w/2 − 0.01 = 12.39 | nub fused to body (1 solid). Basic nub outer face at 12.80. | Δ 0.01 at the QW outer face (12.79 vs 12.80), within tolerance. Mesh-only fix. |
| nub z-overlap `+0.01` (`:26`) | present | present | n/a (B-rep fuse) | no |
| bottom wall click holes 1.4 × 12 × 0.4 at z 2.2 (+3.4) (`:116–119`) | unchanged | unchanged | side cut z 5.6…6.0 / 2.2…2.6 (`opengrid.py:1600–1613`) | not changed by this update (out of scope here, see SnapBody audit) |

### Verdict table (feature | ours | PDF | fork | SCAD | verdict)

| feature | ours | PDF | fork | SCAD | verdict |
|---|---|---|---|---|---|
| lite main bottom click-hole height | 2.8 (built, probe 2.81) | n/a (p.1 tile only) | n/a (no snap body) | official STEP bare lite and directional lite: 2.8. opengrid-projects `opengrid_snap_lib.scad:273–275`: thickness − 0.6 = 2.8. QuackWorks `opengrid-snap.scad:107`: 1.5 (new), 2.8 (old). | match (ours = official). The new QuackWorks value deviates from the official design. |
| standard main bottom click-hole height | 6.2 | n/a | n/a | 6.2 in the official bare STEP and in both SCAD sources | match |
| lite rear directional click hole | no back bottom cut (opengrid-projects topology) | n/a | n/a | Official directional lite STEP: no inner gap on the big-nub side; front cut top 2.8. QW 0.599…1.499 (new), …2.799 (old). opengrid-projects: no BACK bottom cut (`:272`). | match vs official STEP. The QW 0.9 mm hole is not in the official design. |
| nub-to-core placement | fused, outer face 12.80 | n/a | n/a | QW 12.79 (new), 12.80 (old). opengrid-projects `shiftout=-EPS` (`:358`). | match (≤ 0.01) |
| expanding snap bottom cuts | none (`opengrid.py:941`) | n/a | n/a | opengrid-projects `:527` disables them | match (QW has no expanding snap) |

## Submodule removal: Multiconnect references

- The gitlink `MultiConnectOpenSCAD` (mode 160000) pointed at `ab23fbc` (2024-10-26) at `6123129`.
- `git merge-base --is-ancestor ab23fbc 6123129` succeeds, so the target is a QuackWorks commit, not an external repo.
- `git log --all -- .gitmodules` is empty: no URL was ever declared.
- `git grep MultiConnectOpenSCAD` finds no reference in the tree at `6123129` or `e0c1cb7`.
- The local checkout has no `MultiConnectOpenSCAD/` directory.
- The three Multiconnect files are regular tracked blobs in QuackWorks' own `Modules/`. The blob IDs are the same at both commits:
  - `Modules/multiconnectSlotDesign.scad` `fdc30a7…` (added in `63c9b6f`, last changed in `10dc044`)
  - `Modules/multiconnectSlotDesignBOSL.scad` `d5e43d9…` (added `79b5a04`, last `cf394c7`)
  - `Modules/multiconnectGenerator.scad` `69db286…` (added `55ef10f`, last `18e08c2`). Our `MulticonnectConfig` docstring (`opengrid.py:646–648`) and `tests/test_opengrid.py:75` reference this file.
- The gitlink target `ab23fbc` itself contains the same `Modules/multiconnect*` files. So the gitlink was a snapshot of the same repo and never a separate source.

**Conclusion:** none of the Multiconnect references came only from MultiConnectOpenSCAD. They live, unchanged, in `../reference_repos/QuackWorks/Modules/`. Upstream, MultiConnectOpenSCAD is QuackWorks' former name (commit `9eeaf78` message). No web lookup was needed because the commit-ancestry evidence is local and conclusive. The Multiconnect profile audit is not affected.

## Discrepancies

1. **Lite snap main bottom click-hole height.** Ours is 2.8 mm and new QuackWorks is 1.5 mm. The official David D STEPs (bare lite, directional lite v2) measure 2.8, so ours is right.
   - Ours also matches opengrid-projects `opengrid_snap_lib.scad` and pre-update QuackWorks.
   - The QuackWorks change is a CGAL/STL meshing workaround. It moves QuackWorks away from the official geometry.
   - Our B-rep builds as one solid in all variants, so the defect that motivated it does not happen here. Verdict: match. QuackWorks (new) deviates.
2. **Lite directional rear click hole** (QW 0.9 mm tall, was 2.2). The official directional lite STEP has no such hole on the big-nub side, and neither do we. The QuackWorks rear hole is a divergence from the official design, both before and after this update.
3. **Nub 0.01 mm inward shift.** It moves the QW nub outer face to 12.79 vs our 12.80. This is within the 0.01 tolerance and serves mesh connectivity only. No action.
4. **Gitlink removal.** No impact on any reference we use.
5. **Flag for the SnapBody audit (outside this update's scope).** On the official *standard* directional v2.1 STEP, the front (−Y) side at z = 0.3 shows split segments that end at z ≈ 1.4–1.6, not a full-height 0.6 × 6.2 cut. Ours has a full-height cut (11.11…11.69 to z 6.21) on that side. This suggests the v2.1 standard directional front differs from opengrid-projects and ours. I did not analyse it further; it belongs to the SnapBody audit.
6. **Official bare / bare-lite STEPs ship as 9 solids** (body plus 8 small separate solids). The directional STEPs ship as 1 solid. This is informational and has no dimension impact.

## Proposed fix issues

None filed. No "ours wrong" findings. Do not adopt the QuackWorks 1.5 mm lite click-hole height: the official STEPs confirm 2.8 mm.
