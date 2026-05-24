# opengrid-build123

A build123d conversion of the parametric openGrid board generator from the reference OpenSCAD model.

## Status

Implemented:

- Full, Lite, and Heavy openGrid boards
- Parametric board width/height and tile size
- OpenSCAD-style I-beam tile profile and corner transitions
- Overall corner chamfers
- Screw mounting modes
- Side connector snap slots centered in the board side height
- Lite adhesive base
- Stacked tiles with interface layers
- Fill-space generation modes
- STL export CLI
- OCP VS Code viewer example

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

## View in OCP VS Code

Open the OCP CAD Viewer panel in VS Code, then run:

```bash
uv run python examples/view_opengrid.py
```

If your viewer is on a non-default port:

```bash
uv run python examples/view_opengrid.py --port 3939
```

or:

```bash
OCP_PORT=3939 uv run python examples/view_opengrid.py
```

## Python API

```python
from opengrid_build123 import BoardKind, ChamferMode, GridConfig, ScrewMounting, build_open_grid, export_grid

config = GridConfig(
    kind=BoardKind.FULL,
    board_width=2,
    board_height=2,
    chamfers=ChamferMode.CORNERS,
    connector_holes=True,
    screw_mounting=ScrewMounting.CORNERS,
)

part = build_open_grid(config)
export_grid(config, "opengrid_full_2x2.stl")
```

## Verification

```bash
uv run pytest tests
uv run basedpyright src tests examples
```

Current test coverage checks:

- Full/Lite/Heavy board dimensions
- Lite adhesive backing thickness
- Subtractive options removing material without changing outer dimensions
- Overall corner chamfers cutting through the full tile height
- Connector snap slots centered in side height
- Stacked interface layer spacing
- Complete-tile fill-space placement

## Project layout

```text
src/opengrid_build123/
  __init__.py
  opengrid.py
examples/
  view_opengrid.py
tests/
  test_opengrid.py
```
