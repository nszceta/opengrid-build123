from __future__ import annotations

import argparse
import os

from ocp_vscode import Camera, show, set_port
from ocp_vscode.comms import port_check

from opengrid_build123 import BoardKind, ChamferMode, GridConfig, ScrewMounting, build_open_grid


def _default_port() -> int:
    try:
        return int(os.environ.get("OCP_PORT", "3939"))
    except ValueError as exc:
        raise SystemExit("OCP_PORT must be an integer") from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show the converted openGrid model in OCP CAD Viewer")
    parser.add_argument("--port", type=int, default=_default_port())
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not port_check(args.port):
        raise SystemExit(
            f"OCP CAD Viewer is not listening on port {args.port}. "
            "Open the OCP CAD Viewer panel in VS Code first, or pass --port/ set OCP_PORT to the viewer port."
        )

    set_port(args.port)
    grid = build_open_grid(
        GridConfig(
            kind=BoardKind.FULL,
            board_width=6,
            board_height=5,
            chamfers=ChamferMode.CORNERS,
            connector_holes=True,
            screw_mounting=ScrewMounting.CORNERS,
        )
    )
    show(grid, names=["openGrid Full 6x5"], port=args.port, reset_camera=Camera.CENTER, axes=True, grid=True)


if __name__ == "__main__":
    main()
