# Blocking-pin snap: FEA simulation report
> **STATUS: results below are from the earlier campaign (leg_width 8, mesh 1.4, several frictionless cases) and are superseded.**
> The final consistent run (`--case all --jobs 2 --threads 24`, leg_width 10, mu 0.3 gated cases at mesh <= 1.0) was
> still running when this note was written. When it finishes, `output/simulation/blocking_pin/summary.md` is authoritative
> and this report must be regenerated from it.


Reproduce: `uv run --group sim examples/simulate_blocking_pin.py --case all`
(single cases: `--case INS|INSR|SVC-A|SVC-C|OVL|UNB|SENS|PLA|MESH|FRIC|VALIDATE`).
All output goes to `output/simulation/blocking_pin/` (per-case folders with PNG
field maps, `result.json`, plus `summary.json`, `summary.md`, `index.html`).
This report is the committed summary; the figures live only in `output/`.

## Method

Pipeline: build123d builders (`_blocking_pin_snap_shape`,
`_multiconnect_blocking_screw_shape` with `thread_proxy=True`, Heavy board 3x3
cells) -> STEP -> gmsh (single-threaded, deterministic) 10-node tetrahedra ->
CalculiX 2.23 (`*STATIC`, `NLGEOM`, spooles) -> own `.frd`/`.dat` parsing ->
matplotlib. Material: bilinear elastic-plastic (hardening modulus E/50),
isotropic. Contact on `*CONTACT PAIR` surface-to-surface with a linear
penalty (K = 10 E / h, scaled per case), Coulomb friction with a penalty stick slope.

| Material | E [MPa] | nu | yield [MPa] | interlayer [MPa] |
|---|---|---|---|---|
| PETG | 2100 | 0.38 | 45 | 25 |
| PLA | 3500 | 0.36 | 55 | 20 |

* **Symmetry.** Quarter model (pull, insertion) or half model (shear). The board
  is rigidly clamped at the boundary of the 3x3 patch (stiffer than a real board).
* **Thread proxy.** Smooth bore and smooth cylinder of the same radius (7.5 mm) joined
  by `*TIE`; about 10 rim nodes of the cylinder stay untied. No thread form is resolved.
* **Contacts.** Ledge against board lip, shank against bore, stop annulus
  against sleeve. Friction mu = 0.3 (headline) with stick slope 0.002 K;
  the elastic slip is mu p / lambda. The overload family was run frictionless (conservative, see below).
* **Loads.** Pull is an area-weighted nodal load on the underside of the
  head cone (ramped in one `*STEP` per output frame); shear is -y on the +y half of the cone.
  A weak grounded spring (2 N/mm at the head axis node) removes rigid-body modes.
* **Pre-lift.** Snap and screw start lifted by the first-contact lift (0.035 mm for the shipped
  defaults) so contacts start closed. The seat play is added back to every reported lift
  ("total lift" = FEA lift + seat play).
* **Meshes.** Leg size 0.4 mm x scale, roots 0.32, board refined near the lip.
  Scale 1.0 is about 55-60k nodes, scale 1.4 about 26k (half model 50k).
  **Most cases were run at scale 1.4** (see Limitations); the refined check and INS-R use 1.0.

## Load derivation (5 kg shelf)

Weight W = 5 x 9.81 = 49 N acting 100 mm from the wall. Two snaps (rows 14 mm and 42 mm
above the bottom pivot). Moment balance about the bottom pivot:
W x 100 = 4905 N mm = k (42^2 + 14^2), k = 2.5 N/mm.
Top snap pull = k x 42 = 105 N, bottom 35 N. Shear = 49 N / 2 = 24.5 N per snap.
Service cases: SVC-A = 100 N pull (rounded 105 N), SVC-C = 100 N pull + 2 x 24.5 N shear.
Acceptance for service: von Mises <= sigma_y/2 = 22.5 MPa (PETG), sigma_zz <= 12.5 MPa,
total lift <= 0.3 mm. Peaks exclude nodes within 0.5 mm of sharp edges (dihedral > 30 degrees,
symmetry-plane edges excepted); raw and 99.5th-percentile values are in `result.json`.

## Validation (`output/simulation/blocking_pin/validation/`)

| Check | Result | Limit |
|---|---|---|
| Cantilever (L 10, b 2, t 0.8, 2 elements through thickness) | tip 0.910 vs Euler-Bernoulli 0.930 mm, 2.1 %; reaction balance 0 % | 5 % / 1 % |
| Penalty contact + friction (stick) | Fz 100.0 N, Fx -15.0 N exact | 1 % |
| `*TIE` plug in sleeve | 50 N reaction, 0 % error | 1 % |

Equilibrium (reaction vs applied) of every service case is within 1e-4 %.

## Results (shipped defaults: blocking_clearance 0.05, seat_clearance 0.02, ledge_reach 12.95)

| Case | Setup | Result | Verdict |
|---|---|---|---|
| INS | contact insertion, mu 0.3, PETG | leg strain 0.90 % (<= 1.2), sigma_zz 19.2 MPa (<= 25), peak force 26.7 N (<= 40) | PASS |
| INS-R | snap alone, ledges displaced 0.5 mm radially, mesh 1.0 (upper bound, not gated) | strain 0.99 %, sigma_zz 21.8 MPa | cross-check OK |
| SVC-A | 100 N pull, mu 0.3 | snap vm 12.0, sigma_zz 4.5 MPa; screw vm 6.3; board vm 9.1; total lift 0.293 mm (0.202 relative to lip) | PASS |
| SVC-C | 100 N + 2x24.5 N shear, **mu 0** | snap vm 25.4 (> 22.5), lift 0.363 mm | FAIL (frictionless bound) |
| SVC-C~mu03 | same, mu 0.3 | snap vm 16.7, sigma_zz 5.6, screw 4.8, board 11.4 MPa; lift 0.313 mm (0.218 relative to lip) | **FAIL on lift by 0.013 mm**; all stresses pass |
| OVL | pull to collapse, mu 0 | capacity 320 N (lift > 1.0 mm); snap first yield 200 N, board 253 N; no interlayer exceedance; thread-proxy shear 4.9 MPa at capacity (limit 26) | PASS (>= 300 N) |
| UNB | shank removed, mu 0 | capacity 11 N | PASS (3.5 % of OVL) |
| SENS | blocking_clearance 0.05 / 0.10 / 0.20, mu 0 | capacity 320 / 294 / 244 N; lift at 100 N 0.344 / 0.420 / 0.573 mm | trend |
| PLA-SVC-A | PLA, 100 N, mu 0.3 | snap vm 12.0, sigma_zz 6.8 MPa (limit 10 = 20/2); lift 0.219 mm | PASS |
| PLA-INS | PLA insertion | strain 0.90 %, **sigma_zz 31.8 MPa (> 20)**, force 44.1 N, solver stopped at 75 % stroke | not for PLA |
| SVC-A-mu0 vs SVC-A-fine | frictionless, mesh 1.4 vs 1.0 | lift 0.344 vs 0.347 mm; snap sigma_zz 4.72 vs 4.78 MPa (1.2 %); snap vm 17.7 vs 15.3 MPa (15.5 %); screw vm 7.6 vs 12.6 MPa | **FAIL (< 10 % not met for contact-driven vm)** |

Capacity of the frictional configuration is higher: at mesh 1.4 an earlier
exploration run with friction (reach 13.05, otherwise the shipped values) collapsed at about 440 N versus
339 N frictionless. Blocked versus unblocked: 320 N versus 11 N, a factor of about 28.

Board compliance dominates lift: the 1.6 mm bars bend, so at 100 N the board lip itself lifts about
0.09 mm and moves out about 0.06 mm. Lift scales as 1.43 x radial slip (ramp slope 0.7).

## Defaults tuning

At the PLAN defaults (blocking_clearance 0.10, seat_clearance 0.05) FEA gave 100 N service lift
0.42-0.47 mm (limit 0.3) and frictionless capacity about 280 N (< 300). Applied (confirmed by
SnapGeometry): `blocking_clearance` 0.05 and `seat_clearance` 0.02. `ledge_reach` stays
12.95 (13.05 added insertion strain, 1.03 % / 22.6 MPa in INS-R, for no real gain).

## Deviations from PLAN and limitations

* **SVC-C total lift 0.313 mm (> 0.3) with mu 0.3** under the conservative total-lift definition. Relative
  to the board lip (excluding board bending) it is 0.218 mm. A further reduction needs a smaller blocking
  clearance (below 0.05 mm, tolerance-limited) or a stiffer board; not applied.
* **Mesh convergence not met** for contact-driven von Mises peaks (15.5 % snap, 40 % screw; the screw peak is at the
  grounded-spring node and at contact patch edges). Lift and sigma_zz converge (< 2 %). The refined values still lie below
  the 22.5 MPa limit, so the SVC-A verdict does not change. Most cases used scale 1.4 (about 1.4 elements across the legs, not 2)
  because friction cases at scale 1.0 take hours; INS-R at scale 1.0 resolves the leg strain.
* Overload (OVL, UNB, SENS) and SVC-C (first row) are frictionless (conservative: the ramp friction resists leg slip).
* Insertion INS at mesh 1.4, not 1.0 (a 1.0 run was abandoned for runtime, over 4 h projected).
* The stop annulus radius is 9.0 mm (SnapGeometry design), not 10.6.
* Isotropic material; interlayer strength is only checked post hoc on sigma_zz. Thread form is replaced by
  the tie. Board clamped rigidly at the 3x3 patch edge. Penalty contact has finite stick slip. Robust peak
  excludes nodes within 0.5 mm of sharp edges. Peak edge-contact stress at the ledge reaches 58-170 MPa (raw, mesh dependent).
* PLA is not suitable for the snap: insertion sigma_zz exceeds its interlayer strength and force exceeds 40 N.
