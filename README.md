# opengrid-build123

A build123d conversion of the parametric openGrid board generator from the reference OpenSCAD model.

## Status

Implemented:

- Full, Lite, and Heavy openGrid boards, including fill-space modes
- Parametric board width/height, tile size, stacking, chamfers, screw mounting, connector slots, and Lite adhesive backing
- Adjacent-grid connector slot/delete-tool and positive connector primitives
- Snap thread, snap body, and self-expanding snap primitives
- Assembled snap products with bare, basic-thread, self-expanding, openConnect, or Multiconnect attachments
- Snap-thread-backed openConnect and Multiconnect screws, openConnect heads, Multiconnect heads, and cosmetic text engraving
- Multiconnect profile, rail, receiver, backer, and rail-delete-tool builders
- STEP/STL export, OCP VS Code viewer example, and SVG verification galleries

## Requirements

- Python 3.13 or 3.14
- [uv](https://docs.astral.sh/uv/)

`build123d` is sourced directly from GitHub:

```toml
build123d = { git = "https://github.com/gumyr/build123d" }
```

## Setup

```bash
uv sync
```

## Export an STL

```bash
uv run opengrid-build123 --kind Full --width 2 --height 2 --output opengrid_full_2x2.stl
```

Supported `--kind` values:

- `Full`
- `Lite`
- `Heavy`

## Export STEP files and visual verification galleries

The unified example reads `examples/config.yaml` by default. Edit that file to configure boards, adjacent-grid connector objects, Multiconnect rails/receivers/backers/delete tools, snap primitives, assembled snap products, snap-thread-backed screws, STEP output, SVG verification, and optional OCP viewer display.

Export the configured objects as one STEP file per object and generate visual verification galleries:

```bash
uv run examples/main.py --config examples/config.yaml
```

Verification SVGs are grouped by component under `output/verification/<component>/gallery.html`. Each gallery contains multiple views for every defined variant of that component, for example:

```text
output/verification/
  opengrid_board/gallery.html
  snap_threads/gallery.html
  snap_body/gallery.html
  expanding_snap/gallery.html
  multiconnect_rail/gallery.html
  openconnect_screw/gallery.html
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
    build_multiconnect_rail,
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
rail = build_multiconnect_rail(MulticonnectConfig(length=56.0))
```

## Verification

```bash
uv run pytest tests/test_opengrid.py -q
uv tool run basedpyright src tests examples
```

Current test coverage checks:

- Full/Lite/Heavy board dimensions
- Lite adhesive backing thickness
- Subtractive options removing material without changing outer dimensions
- Overall corner chamfers cutting through the full tile height
- Connector snap slots centered in side height
- Stacked interface layer spacing
- Complete-tile and available-space fill placement
- Snap thread, snap body, expanding snap, assembled snap, screw, engraving, and Multiconnect behavior
- Reference-source parity checks for snap body, expanding snap, and Multiconnect source dimensions/envelopes
- Variant SVG verification galleries under `output/verification/<component>/gallery.html`

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
