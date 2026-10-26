# Multiconnect head and screw: dimension audit

## Scope

- `build_multiconnect_head()` with `MulticonnectHeadConfig` and `ConnectorSlotConfig`:
  `src/opengrid_build123/opengrid.py:980-1003`, configs at `:529-557` and `:561-581`.
- `build_multiconnect_screw()` with `MulticonnectScrewConfig`: `opengrid.py:1006-1015` and `:602-614`.
- Shared coin/flat slot cutter `_subtract_connector_slot()`: `opengrid.py:2676-2691`.
- The head as mounted on the Multiconnect snap. `build_opengrid_snap(kind=MULTICONNECT)` is at `opengrid.py:1037` and `:2704-2705`. Only the head placement is in scope here. The snap body is not.
- Exports: `output/multiconnect_head.step` and `output/multiconnect_screw.step`.

The thread form is out of scope. The SnapThreads audit owns it. This doc checks only the screw thread diameter and length.

## Sources

| id | source | what it gives |
| --- | --- | --- |
| PDF-T | `../reference_docs/openGrid Multiconnect Thread Docs.pdf`, page 1 (only page) | Thread profile only. Positive core width 14, thread depth 1, flats 0.5, bevel 1. Negative core 14.5 / 12.9, with 0.8 / 0.2 / 0.5 dims. **It has no head, coin slot, or screw-length dimensions.** The text layer gives only loose numbers, so I rasterized the page with `pdftoppm` to read the drawing. |
| PDF-B | `../reference_docs/opengrid-tile-dimensions.pdf` (1 page) | `pdftotext` returns no text containing "multi", "screw", "head" or "coin". It has no head data. |
| FORK | `../reference_repos/opengrid-build123-makerrepo-fork/opengrid/constants.py:11-15`; `multiconnect.py:62-108` (`RoundHead`); `:188-221` (`RoundHeadCutter`) | Head radii and heights, and cutter clearances. The fork has no screw, coin slot or dimple. |
| SCAD-P | `../reference_repos/opengrid-projects/opengrid_parametric_snap.scad`: `:12` (snap_thickness 6.8), `:130-135` (mchead dims), `:138-143` (connector slot dims), `:178-179` (screw thread height, head total), `:358-364` (`multiconnect_screw`), `:366-383` (`multiconnect_head`), `:425-427` (snap mount) | The source our port claims to follow. |
| SCAD-L | `../reference_repos/opengrid-projects/lib/openconnect_lib.scad:216-227` (`connector_slot_cfg`, coin radius formula) | Coin slot radius formula. |
| QW | `../reference_repos/QuackWorks/Modules/multiconnectGenerator.scad`: `:57-68` (custom params), `:115` (`standardSpecs = [10, 1, 2.5, 0.5, 0.15, 1]`), `:250-265` (`roundedEnd`, dimple at `:262`), `:296-303` (`dimensionsToCoords`, offset rule) | The original Multiconnect profile and receiver offset. |
| QW-S | `../reference_repos/QuackWorks/Modules/multiconnectSlotDesign.scad:52` (receiver slot profile `[[0,0],[10.15,0],[10.15,1.2121],[7.65,3.712],[7.65,5],[0,5]]`), `:98-102` (v1 slot dimple r 1.5) | The receiver the head must fit. |
| OFF | David D's official STEPs, Printables model 1214361. ForkProvenance downloaded them to `~/.cache/fork-provenance/official/`. I probed `round.step` and `round-negative.step` | The official round head and its negative. They contain no screw or coin slot. In the table, OFF values appear in the fork column, labelled "OFF". |

QuackWorks commit `9eeaf78` removed the `MultiConnectOpenSCAD` gitlink. The commit message says the gitlink pointed only at commits in QuackWorks' own history, because that was the repo's former name. All the content this audit needs is in this repo under `Modules/`, so the removed gitlink was not needed.

## Method

All values come from built geometry using `uv run python /tmp/mc_head_probe.py` and `/tmp/mc_scad_equiv.py`. Both are throwaway scripts and are not committed.

1. **Head radii and heights.** I built `build_multiconnect_head(MulticonnectHeadConfig(top_pattern="none"))`. For each Z I took a planar section: the shape intersected with `bd.Box(100, 100, 1e-4)` at that Z. Max radius = max `hypot(x, y)` over the section's vertices and over edge samples at t = 0, 0.25, 0.5, 0.75, 1. I also recorded `bounding_box()` and volume.
2. **Coin slot and dimple.** I built the default head (`coin_slot`) and `top_pattern="dimple"`. A line probe intersects the shape with a thin bar, `bd.Box(100, 1e-3, 1e-3)` along X or `bd.Box(1e-3, 100, 1e-3)` along Y, at a given Z. The probe lists the intervals that contain material. Removed volume = plain-head volume − patterned-head volume.
3. **SCAD reference rebuild.** I copied SCAD-P `:377` into build123d: plain head − `Cylinder(r=coin_slot_radius, 2.2)` rotated X 90°, with the centre at z = `coin_slot_height − r`. In the head frame the R10 face is at z = 0. I measured this rebuild with the same probes. I also built the SCAD dimple (`Cone(1, ~0, 1)` with its base on the z = 0 face) and measured its volume.
4. **Screw.** I built `build_multiconnect_screw()` (defaults), measured its bbox, used line probes and max radius at z = 4.5, 6, 8 and 10, and measured the bbox of `build_snap_threads(SnapThreadConfig(clearance=0))`.
5. **Snap mount.** I built `build_opengrid_snap(OpenGridSnapConfig(kind=MULTICONNECT))` and measured max radius at Z from 6.9 to 10.75.
6. **STEP.** I imported `output/multiconnect_head.step` and `output/multiconnect_screw.step` with `bd.import_step` and measured bbox, volume, sections and line probes.
7. **Official STEP.** I imported `round.step` and `round-negative.step` and ran the same section max-radius and X-line probes, measuring Z from each part's bbox min and centring on its bbox centre. Scratch script: `~/.cache/mc-head-audit/probe_official.py`. It is not committed.

How I read the SCAD frame (SCAD-P `:370-379`): the attachable is centred, `up(total/2)` moves the origin to the top (R7.5) face, and `anchor=BOTTOM` puts the R10 face at z = 0. In BOSL2, `xrot(90) cyl(..., anchor=BACK)` moves the cylinder centre from y = −r to z = −r. That puts the coin circle centre at z = 2.6 − 9.425 = −6.825, with the arc tangent at z = 2.6. The dimple `down(total) cyl(d1=2, h=1, anchor=BOTTOM)` opens on the z = 0 (R10) face.

Tolerance: 0.01 mm.

## Comparison

Notation: z = 0 is the R10 face. In ours, the R7.5 face is the thread side and threads start at the head top.

| feature | ours | PDF | fork | SCAD | verdict |
| --- | --- | --- | --- | --- | --- |
| Bottom (capture) radius | 10.000. Section r at z = 0.01, 0.5, 0.99. `large_diameter=20` (`opengrid.py:564`) | — (PDF-T p1 has no head) | 10 (`constants.py:11`). OFF `round.step`: r 10.0 at dz 0.005–0.99 | 10. `mchead_large_diameter=20` (SCAD-P `:131`). QW `Radius=10` (`:58`, `:115`) | match |
| Bottom height | 1.00 nominal (`:568`). The cylinder spans z 0–1.00, but the taper starts at 0.99 (EPS overlap) | — | 1 (`constants.py:12`) | 1 (SCAD-P `:135`). QW Depth1 = 1 (`:60`, `:115`) | match (Δ ≤ 0.01) |
| Taper height / angle | 2.5 nominal (`:567`). Measured span z 0.99–3.49: r 9.98 at 1.01, 8.74 at 2.25, 7.50 at 3.49. 45° | — | 2.5 (`constants.py:14`), loft from R10 to `top_radius`. OFF: span 1.0–3.5, r 9.99 at 1.01, 8.75 at 2.25, 7.51 at 3.49 | 2.5 (SCAD-P `:134`). Cone r1 = 10, r2 = large/2 − middle_height = 7.5 (`:373`). QW Depth2 = 2.5, top r = R − Depth2 (`:300`) | match (taper is 0.01 low vs OFF, at tolerance) |
| Taper top radius parametrization | `large/2 − middle_height` (`opengrid.py:991`). Independent of `small_diameter` | — | Independent `top_radius` (`multiconnect.py:73`, `:97-98`) | `large/2 − middle_height` (SCAD-P `:373`). QW uses the same rule (`:300`) | match (ours follows SCAD/QW. The fork uses a different parametrization, which only matters for non-default values) |
| Top (neck) radius | 7.500. Section r at z = 3.51, 3.75, 3.99. `small_diameter=15` (`:565`) | — | 7.5 (`constants.py:13`). OFF: 7.5 at dz 3.51–3.99 | 7.5 (SCAD-P `:132`, `:372`). QW 10 − 2.5 (`:300`) | match |
| Top height | 0.5 nominal (`:566`). Measured span z 3.49–3.99 | — | 0.5 (`constants.py:15`) | 0.5 (SCAD-P `:133`). QW Depth3 = 0.5 (`:64`) | match |
| Head total height | **3.99**. bbox z max, built and STEP. `total_height` property = 4.0 (`:581`). Each stacked solid is shifted down by `_EPSILON=0.01` (`:68`, `:993`, `:996`) | — | 4.0 (1 + 2.5 + 0.5). OFF `round.step` bbox height 4.000 | 4.0 (SCAD-P `:179`) | match (Δ = 0.01, at tolerance limit) |
| Head solid volume (no pattern) | 1004.789 mm³ | — | 1007.928 analytic. OFF 1006.716 with its dimple (1007.928 − 1.212 frustum = 1006.716) | 1007.928 analytic | match (the −3.1 mm³ is from the 0.01 EPS stacking) |
| Coin-slot face | Both faces. Circle centre at z = 1.4 (`opengrid.py:2677-2678`, `top_z − h`) | — | n/a (fork has no slot) | R10 outer face only. Centre z = h − r = −6.825 (SCAD-P `:377`) | ours wrong |
| Coin-slot radius | 9.425 (`ConnectorSlotConfig.coin_slot_radius`, `:557`) | — | n/a | 9.425 = h/2 + w²/8h (SCAD-L `:227`) | match |
| Coin-slot width at outer face | **18.644**. X-line at z = 0.01 has material only at \|x\| > 9.322 | — | n/a | 13.0. SCAD rebuild X-line at z = 0.001 has material at \|x\| ≥ 6.498. `coin_slot_width=13` (SCAD-P `:139`) | ours wrong |
| Coin-slot depth | **Through the full height**. X-line is empty from z = 2.0 to 3.99, so the neck is severed. The halves are joined only by the R10 ring at \|x\| > 9.32, z < 1.4 | — | n/a | 2.6 on axis (SCAD rebuild: X-line gap ±0.423 at z = 2.59). SCAD-P `:138` | ours wrong |
| Coin-slot thickness | 2.2 for the coin alone (Y gap ±1.1 at z ≥ 3.0). **3.3, off-centre** (y −2.2 … +1.1) at z −0.4 … 2.7, because of the flat box (`:2680-2690`) | — | n/a | 2.2, centred (SCAD-P `:140`, `:377`). The lib default is 2.4 (SCAD-L `:219`), but the screw passes 2.2 | ours wrong |
| Flat (screwdriver) slot | 6.5 × 2.2 box, y −2.2…0, z −0.4…2.7 (`:2680-2690`) | — | n/a | **None.** `multiconnect_head` subtracts only the coin cylinder (SCAD-P `:376-377`). The prismoid flat slot exists only in `openconnect_screw` (SCAD-L `:530-543`) | ours wrong |
| Coin-slot removed volume | 171.904 mm³ (built = STEP, 832.885 mm³ remaining) | — | n/a | 51.125 mm³ (SCAD rebuild) | ours wrong |
| Dimple face | R7.5 top face (`:1001-1002`) | — | n/a | R10 outer face (SCAD-P `:379`). QW `roundedEnd` dimple at the R10 face (`:262`) | ours wrong |
| Dimple size / shape | Cone, base r = 1 at z = 3.0, apex at z = 4.0. This is an internal void: X-line gap ±0.505 at z = 3.5, ±0.02 at z = 3.99, so it opens only as a ~0.04 mm pinhole. Volume 1.058 mm³ | — | Fork: none. OFF `round.step`: truncated cone on the R10 face, r 1.05 at the face down to r 0.05 at 1.0 deep (X-line gap ±1.044 at dz 0.005, ±0.549 at 0.5, ±0.059 at 0.99). Volume 1.212 | Opening r = 1.0 at the face, depth 1.0, apex inward. Volume 1.047 mm³ (SCAD-P `:379`: d1 = 2, h = 1). QW r = 1, h = 1 (`:68`, `:262`) | ours wrong. OFF and SCAD/QW differ by 0.05 in radius (r 1.05 truncated vs r 1.0 pointed), so the exact dimple size is ambiguous. Ours is wrong under both |
| Receiver fit clearance (RoundHeadCutter) | No head cutter. The receiver offset lives in `MulticonnectConfig.receiver_offset = 0.15` (`opengrid.py:660`), which the Multiconnect profile audit covers | — | Radial +0.15; bottom height +0.2121 (= 0.15·√2); top height −0.0621. Top face goes 4.0 → 4.15 (`multiconnect.py:191-194`). OFF `round-negative.step`: r 10.15 up to dz 1.2121 (10.15 at 1.2, 9.862 at 1.5), 45° to r 7.65 at dz 3.712, height 4.150, vol 1099.02 | QW offset 0.15: R + 0.15, Depth1 + 2·sin45·0.15, top + 0.15 (`:115`, `:296-303`). QW-S slot `[10.15, 1.2121] → [7.65, 3.712]` (`:52`) | n/a-coverage gap (fork = QW = OFF) |
| Head clearance (male part) | 0 (head is nominal) | — | 0 (`RoundHead`) | 0 | match |
| Screw thread length | 6.80 (thread bbox z 0–6.8; `SnapThreadConfig.height = _DEFAULT_TILE_THICKNESS = 6.8`, `:250`, `:70`) | — | — | 6.8 (`_screw_threads_height = snap_thickness`, SCAD-P `:12`, `:178`, `:455`) | match |
| Screw overall length | **10.79** (bbox z 0–10.79; threads start at `total_height − EPS`, `:1011-1012`) | — | n/a | 10.8 (4.0 + 6.8; SCAD-P `:360-362`) | match (Δ = 0.01, at tolerance limit) |
| Screw thread clearance | 0 (forced, `:1011`) | Positive part is the nominal profile (PDF-T p1) | n/a | 0 (`struct_set(threads_cfg, ["threads_clearance", 0])`, SCAD-P `:362`) | match |
| Screw thread major / minor dia | Major 16.0 (rmax 8.0 at z = 8, 10). Root ≈ 14.0 (X-line −7.046 at z = 8) | Positive core 14, depth 1 → 16 (PDF-T p1) | n/a | 16 (SCAD-P `:72-73`) | match. Profile detail is deferred to the SnapThreads audit |
| Screw orientation | R10 at z = 0 (outer/coin end), threads on the R7.5 face | — | n/a | Same: head `anchor=BOTTOM`, threads `attach(TOP, BOTTOM)` (SCAD-P `:360-362`) | match |
| Head orientation on snap | **R10 on the snap** (r = 10.0 at z = 6.9–7.5), R7.5 outermost (r = 7.5 at z = 10.5–10.75). Head added un-flipped (`opengrid.py:1037`, `:2705`) | — | n/a | `attach(TOP, TOP)` flips the head (SCAD-P `:426-427`): R7.5 face on the snap, R10 + dimple outermost | ours wrong |
| STEP vs builder | Head: bbox (±10, ±10, 0–3.99), vol 832.885, same sections. Screw: bbox (±10, ±10, 0–10.79), vol 2001.086 | — | — | — | match (STEP = current builder output) |

## Discrepancies

1. **Coin slot cuts through the whole head (ours wrong).** `_subtract_connector_slot` puts the coin circle centre at `top_z − coin_slot_height` (z = 1.4). SCAD puts it at `coin_slot_height − r` (z = −6.825). Because of this, ours:
   - cuts both faces;
   - is 18.64 wide instead of 13 at the outer face;
   - severs the neck over the full height.

   The head stays in one piece only through the thin R10 flange ring. It removes 171.9 mm³; SCAD removes 51.1 mm³. The helper is shared with the openConnect screw, which has the same defect (see `openconnect.md`).
2. **Extra flat slot on the Multiconnect head (ours wrong).** SCAD `multiconnect_head` has only the coin cylinder. Ours also unions a 6.5 × 2.2 box. The box is not centred (y −2.2…0), so the slot band is 3.3 wide and asymmetric for z < 2.7.
3. **Dimple is on the wrong face and is enclosed (ours wrong).** The SCAD/QW dimple opens on the R10 face: r = 1, depth 1, apex inward. The official `round.step` also puts it on the R10 face, as a truncated cone: r 1.05 at the face, r 0.05 at 1.0 deep. Ours is an inverted cone void under the R7.5 face, open only through a ~0.04 mm pinhole. It is useless as a detent. Whether the correct size is r 1.0 (SCAD) or r 1.05 truncated (official) is ambiguous. The difference is 0.05.
4. **Head is upside down on the Multiconnect snap (ours wrong).** SCAD flips the head with `attach(TOP, TOP)`. Ours stacks it with the R10 flange on the snap and the R7.5 neck outermost. A Multiconnect slot (R10.15 capture behind an R7.65 opening) cannot retain it.
   - Resolution: `_flip_snap_head` rotates the head 180° about Y. The default snap now has R7.5 on the snap (z 6.85 r 7.50) and R10 outermost (z 9.82–10.80 r 10.00). It is one solid with its top at 10.80. The outer face carries the dimple (r 1.045 at the face), not a coin slot.
5. **EPS stacking makes the head 3.99 instead of 4.00 (at tolerance).** This also shifts the taper 0.01 down and makes the screw 10.79 instead of 10.8. The error equals the 0.01 tolerance, so I did not file it separately. The coin-slot or snap-head fix can drop the −EPS offsets. `total_height` already reports 4.0.
6. **Fork vs docs.** The fork `RoundHead` matches SCAD/QW for every head dimension, and so does the official `round.step` (R10 to 1.0, 45° taper to R7.5 at 3.5, height 4.0). `RoundHeadCutter` clearances match QW `dimensionsToCoords` with offset 0.15, and match the official `round-negative.step` (R10.15 to 1.2121, R7.65 from 3.712, height 4.15). The fork's independent `top_radius` parameter differs from SCAD/QW, which derive the taper top as `R − taper_height`. Defaults agree, so the fork is not wrong here. It is a different parametrization. The fork has no screw, coin slot or dimple, so it cannot serve as a reference for those. The official round head does have a dimple.
7. **PDF coverage gap (spec ambiguous / n/a).** Neither PDF dimensions the head, coin slot, dimple or screw length. For head shape and dimple, the references are the SCAD and the official STEP. For the coin slot and screw length, the only reference is the SCAD.

## Proposed fix issues

- Multiconnect head coin slot through-cuts head; adds flat slot absent from SCAD. Required geometry: slot only on the R10 face, depth 2.6 on axis, width 13 at the face, thickness 2.2 centred, no flat slot. The same shared helper affects openConnect.
- Multiconnect head dimple on wrong face and enclosed. Required geometry: cone opening on the R10 face, depth 1, apex inward. Size is r 1.0 per SCAD/QW, or r 1.05 truncated to r 0.05 per the official `round.step`.
- Multiconnect snap mounts round head upside down. Required geometry: R7.5 face on the snap top, R10 face with the dimple outermost.
- Not filed. Optional cleanup: remove the `−_EPSILON` stacking offsets in `build_multiconnect_head` / `build_multiconnect_screw` so the head is 4.00 and the screw 10.80. Fold this into the coin-slot or snap-head fix.

## Resolution

- The Multiconnect head subtracts only the coin cylinder (`_coin_slot_tool`, thickness along Y) with its arc tangent at z=2.6 above the R10 face; no flat slot. Measured: removed 51.125 mm³ (SCAD rebuild 51.125); X-line z=0.005 material |x| ≥ 6.494; X-line z=2.65 continuous ±8.35 (neck intact); Y-line z=1.0 gap ±1.1. The −EPS stacking is removed: plain head bbox z 0…4.00, volume 1007.928 (= analytic).
- Dimple follows the official `round.step` (precedence over SCAD/QW): cone r1.05 at the R10 face to r0.05 at 1.0 deep. Measured: removed 1.212 mm³; X-line gap ±1.044 at z=0.005, ±0.549 at 0.5, ±0.059 at 0.99 (identical to the official probe).
