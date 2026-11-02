# opengrid-build123

A build123d conversion of the parametric openGrid board generator from the reference OpenSCAD model.

## Status

Implemented:

- Full, Lite, and Heavy openGrid boards, including fill-space modes
- Parametric board width/height, tile size, stacking, chamfers, screw mounting with optional #8/M4 fastener presets, connector slots, and Lite adhesive backing
- Adjacent-grid connector slot/delete-tool and positive connector primitives
- Snap thread, snap body, and self-expanding snap primitives
- Assembled snap products with bare, basic-thread, self-expanding, openConnect, or Multiconnect attachments
- Snap-thread-backed openConnect and Multiconnect screws, openConnect heads, Multiconnect heads, and cosmetic text engraving
- Blocking-pin snap and Multiconnect blocking screw for openGrid Heavy boards: the screw shank blocks the snap's legs from collapsing, so pull-out does not depend on thread tightness
- Multiconnect profile, part-kind, rail, receiver, backer, and rail-delete-tool builders
- STEP/STL export, OCP VS Code viewer example, and SVG verification galleries

## Requirements

- Python 3.13 or 3.14
- [uv](https://docs.astral.sh/uv/)

`build123d` is sourced directly from GitHub:

```toml
dependencies = [
    "build123d @ git+https://github.com/gumyr/build123d",
]
```

## Setup

```bash
uv sync
```

## Export an STL or STEP file

```bash
uv run opengrid-build123 --kind Full --width 2 --height 2 --output opengrid_full_2x2.stl
```

The `--output` extension picks the format: `.stl` for a mesh, `.step` or `.stp` for a STEP solid. Any other extension is an error. `export_grid()` in Python follows the same rule.

Supported `--kind` values:

- `Full`
- `Lite`
- `Heavy`

Screw holes default to a 4.1 mm hole with a 7.2 mm 90° countersink. Add `--screw-preset` to use a named fastener instead:

```bash
uv run opengrid-build123 --kind Full --screw-mounting Everywhere --screw-preset "#8 Pan Head" --output full_8pan.stl
```

| Preset | Hole | Head relief |
| --- | --- | --- |
| `#8 Pan Head` | 4.5 | counterbore Ø8.3 × 3.0 deep |
| `#8 Flat Head` | 4.5 | 82° countersink to Ø8.6, 0.5 recess |
| `M4 Pan Head` | 4.5 | counterbore Ø8.4 × 3.3 deep |
| `M4 Flat Head` | 4.5 | 90° countersink to Ø8.8, 0.5 recess |

In Python, `apply_screw_preset(config, ScrewPreset.NUMBER_8_PAN_HEAD)` returns a copy of the config with only `screw_diameter` and the `screw_head_*` fields replaced. Placement, board kind, and every other field are kept, and further tweaks go through `dataclasses.replace`. In `examples/config.yaml`, set `board.screw_preset` (`null` keeps the explicit `screw_*` values).

```python
from dataclasses import replace

from opengrid_build123 import BoardKind, GridConfig, ScrewMounting, ScrewPreset, apply_screw_preset, build_open_grid

config = apply_screw_preset(
    GridConfig(kind=BoardKind.FULL, board_width=3, board_height=3, screw_mounting=ScrewMounting.EVERYWHERE),
    ScrewPreset.NUMBER_8_PAN_HEAD,
)
config = replace(config, screw_head_diameter=8.6)  # optional: looser head fit
board = build_open_grid(config)
```

Preset sizes are normal-fit clearance holes plus head reliefs taken from the maximum head sizes in ASME B18.6.3 (#8) and ISO 7045/7046 (M4). On Full boards, the board corner next to each screw reaches only r 4.22 at the top face. The `#8 Pan Head` counterbore (r 4.15) stays inside it. The flat-head countersinks (r 4.3/4.4) and any head relief wider than Ø8.44 notch the snap opening edge by up to about 0.2 mm. On 4.0 mm Lite boards, a pan-head counterbore leaves 1.0 mm (#8) or 0.7 mm (M4) under the head.

## Export STEP files and visual verification galleries

The unified example reads `examples/config.yaml` by default. Edit that file to configure boards, adjacent-grid connector objects, every Multiconnect part kind, snap primitives, assembled snap products, snap-thread-backed screws, STEP output, SVG verification, and optional OCP viewer display.

Export the configured objects as one STEP file per object and generate visual verification galleries:

```bash
uv run examples/main.py --config examples/config.yaml
```

Verification SVGs are grouped by component under `output/verification/<component>/gallery.html`, with a top-level index at `output/verification/gallery.html`. Each gallery contains multiple views for every defined variant of that component, for example:

```text
output/verification/
  opengrid_board/gallery.html
  snap_threads/gallery.html
  snap_body/gallery.html
  expanding_snap/gallery.html
  multiconnect_rail/gallery.html
  multiconnect_parts/gallery.html
  openconnect_screw/gallery.html
  blocking_pin_snap/gallery.html
  multiconnect_blocking_screw/gallery.html
  blocking_pin_assembly/gallery.html
```

Use `output/verification/<component>/gallery.html` for visual inspection after geometry-sensitive changes. To display the configured objects in OCP CAD Viewer, set `viewer.show: true` in the YAML and open the OCP CAD Viewer panel in VS Code before running the script.

## Python API

```python
from pathlib import Path

from opengrid_build123 import (
    BoardKind,
    GridConfig,
    MulticonnectConfig,
    OpenGridSnapConfig,
    OpenGridSnapKind,
    SnapBodyConfig,
    SnapThreadConfig,
    build_multiconnect_part,
    build_open_grid,
    build_opengrid_snap,
    export_grid,
)

board_config = GridConfig(kind=BoardKind.FULL, board_width=2, board_height=2)
board = build_open_grid(board_config)
export_grid(board_config, Path("opengrid_full_2x2.stl"))

snap = build_opengrid_snap(
    OpenGridSnapConfig(
        kind=OpenGridSnapKind.SELF_EXPANDING_THREADS,
        snap_body=SnapBodyConfig(),
        threads=SnapThreadConfig(),
    )
)
rail = build_multiconnect_part(MulticonnectConfig(length=56.0))
```

### Blocking-pin snap and screw (Heavy boards)

`build_blocking_pin_snap` and `build_multiconnect_blocking_screw` make a two-part lock for a 13.8 mm openGrid Heavy board. Push the snap into a cell until its top is flush with the board face: the four legs flex inward past the top lip and their ledges spring out under it. Then thread the screw into the snap hub until it stops. The screw shank fills the leg bore, so the legs cannot collapse inward under a pull. The thread only holds the screw in place and can be printed loose. Print the snap upright and the screw head-up (thread tip down).

```python
import build123d as bd

from opengrid_build123 import (
    BlockingPinSnapConfig,
    MulticonnectBlockingScrewConfig,
    build_blocking_pin_snap,
    build_multiconnect_blocking_screw,
)

snap_config = BlockingPinSnapConfig()
snap = build_blocking_pin_snap(snap_config)  # z = 0 at the deep end, top at snap_config.height
screw = build_multiconnect_blocking_screw(MulticonnectBlockingScrewConfig(snap=snap_config))  # head face at z = 0

seated_snap = snap.translate((0, 0, snap_config.board_thickness - snap_config.height))
```

`examples/main.py` writes `output/blocking_pin_snap.step`, `output/multiconnect_blocking_screw.step`, and a section view of the seated and locked assembly in a 1×1 Heavy board at `output/verification/blocking_pin_assembly/`.

## Verification

```bash
uv run pytest tests/test_opengrid.py -q
uv tool run basedpyright src tests examples
```

Current test coverage checks:

- Full/Lite/Heavy board dimensions
- Lite adhesive backing thickness
- Subtractive options removing material without changing outer dimensions
- Screw counterbore/countersink geometry, including the `#8 Pan Head` preset's flat-bottom counterbore
- Overall corner chamfers cutting through the full tile height
- Connector snap slots centered in side height
- Stacked interface layer spacing
- Complete-tile and large available-space fill placement
- Snap thread, snap body, expanding snap, assembled snap, screw, engraving, and Multiconnect behavior
- Reference-source parity checks for snap body, expanding snap, and Multiconnect source dimensions/envelopes
- Blocking-pin snap fit in a Heavy board: flush seat, ledge and pad gaps, shank-to-bore blocking clearance, and collapse blocked by the shank
- Variant SVG verification galleries and top-level verification index under `output/verification/`

## Project layout

```text
src/opengrid_build123/
  __init__.py
  opengrid.py
examples/
  main.py
tests/
  test_opengrid.py
```
