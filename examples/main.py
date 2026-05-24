from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Protocol, cast

import build123d as bd
import yaml
from ocp_vscode import Camera, show, set_port
from ocp_vscode.comms import port_check

from opengrid_build123 import (
    AdjacentGridConnectorConfig,
    BoardKind,
    ChamferMode,
    ConnectorSlotDeleteToolConfig,
    FillSpaceMode,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    build_adjacent_grid_connector,
    build_connector_slot_delete_tool,
    build_open_grid,
)

_DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


class _DisplayShape(Protocol):
    def translate(self, vector: tuple[float, float, float]) -> object: ...


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export and optionally view configured openGrid objects")
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG_PATH,
        help=f"YAML configuration path (default: {_DEFAULT_CONFIG_PATH})",
    )
    return parser.parse_args()


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file)
    if not isinstance(loaded, dict):
        raise SystemExit(f"Config {path} must contain a YAML mapping")
    return cast(dict[str, Any], loaded)


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    if not isinstance(value, dict):
        raise SystemExit(f"Config section `{name}` must be a mapping")
    return cast(dict[str, Any], value)


def _required(section: dict[str, Any], key: str) -> Any:
    if key not in section:
        raise SystemExit(f"Missing required config key `{key}`")
    return section[key]


def _as_bool(section: dict[str, Any], key: str) -> bool:
    value = _required(section, key)
    if not isinstance(value, bool):
        raise SystemExit(f"Config key `{key}` must be true or false")
    return value


def _as_int(section: dict[str, Any], key: str) -> int:
    value = _required(section, key)
    if not isinstance(value, int):
        raise SystemExit(f"Config key `{key}` must be an integer")
    return value


def _as_float(section: dict[str, Any], key: str) -> float:
    value = _required(section, key)
    if not isinstance(value, int | float):
        raise SystemExit(f"Config key `{key}` must be numeric")
    return float(value)


def _as_str(section: dict[str, Any], key: str) -> str:
    value = _required(section, key)
    if not isinstance(value, str):
        raise SystemExit(f"Config key `{key}` must be a string")
    return value


def _as_optional_port(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if value is None:
        try:
            return int(os.environ.get("OCP_PORT", "3939"))
        except ValueError as exc:
            raise SystemExit("OCP_PORT must be an integer") from exc
    if not isinstance(value, int):
        raise SystemExit(f"Config key `{key}` must be an integer or null")
    return value


def _as_vector(section: dict[str, Any], key: str) -> tuple[float, float, float]:
    value = _required(section, key)
    if not isinstance(value, list) or len(value) != 3:
        raise SystemExit(f"Config key `{key}` must be a three-number list")
    return (_vector_item(value[0], key), _vector_item(value[1], key), _vector_item(value[2], key))


def _vector_item(value: Any, key: str) -> float:
    if not isinstance(value, int | float):
        raise SystemExit(f"Config key `{key}` must contain only numbers")
    return float(value)


def _output_dir(config: dict[str, Any]) -> Path:
    output = _section(config, "output")
    return Path(_as_str(output, "directory"))


def _slot_delete_tool_config(config: dict[str, Any]) -> ConnectorSlotDeleteToolConfig:
    slot = _section(config, "connector_slot_delete_tool")
    return ConnectorSlotDeleteToolConfig(
        radius=_as_float(slot, "radius"),
        dimple_radius=_as_float(slot, "dimple_radius"),
        separation=_as_float(slot, "separation"),
        height=_as_float(slot, "height"),
        flare_width=_as_float(slot, "flare_width"),
    )


def _adjacent_connector_config(config: dict[str, Any]) -> AdjacentGridConnectorConfig:
    connector = _section(config, "adjacent_grid_connector")
    return AdjacentGridConnectorConfig(
        slot_delete_tool=_slot_delete_tool_config(config),
        fit_clearance=_as_float(connector, "fit_clearance"),
    )


def _grid_config(config: dict[str, Any], slot_delete_tool: ConnectorSlotDeleteToolConfig) -> GridConfig:
    board = _section(config, "board")
    return GridConfig(
        kind=BoardKind(_as_str(board, "kind")),
        board_width=_as_int(board, "board_width"),
        board_height=_as_int(board, "board_height"),
        chamfers=ChamferMode(_as_str(board, "chamfers")),
        chamfer_top_left=_as_bool(board, "chamfer_top_left"),
        chamfer_top_right=_as_bool(board, "chamfer_top_right"),
        chamfer_bottom_left=_as_bool(board, "chamfer_bottom_left"),
        chamfer_bottom_right=_as_bool(board, "chamfer_bottom_right"),
        connector_holes=_as_bool(board, "connector_holes"),
        connector_holes_bottom=_as_bool(board, "connector_holes_bottom"),
        connector_holes_right=_as_bool(board, "connector_holes_right"),
        connector_holes_left=_as_bool(board, "connector_holes_left"),
        connector_holes_top=_as_bool(board, "connector_holes_top"),
        connector_slot_delete_tool=slot_delete_tool,
        screw_mounting=ScrewMounting(_as_str(board, "screw_mounting")),
        screw_every_x_rows=_as_int(board, "screw_every_x_rows"),
        screw_every_x_columns=_as_int(board, "screw_every_x_columns"),
        screw_custom_positions=_as_str(board, "screw_custom_positions"),
        screw_diameter=_as_float(board, "screw_diameter"),
        screw_head_diameter=_as_float(board, "screw_head_diameter"),
        screw_head_inset=_as_float(board, "screw_head_inset"),
        screw_head_is_countersunk=_as_bool(board, "screw_head_is_countersunk"),
        screw_head_countersunk_degree=_as_float(board, "screw_head_countersunk_degree"),
        add_adhesive_base=_as_bool(board, "add_adhesive_base"),
        adhesive_base_thickness=_as_float(board, "adhesive_base_thickness"),
        tile_size=_as_float(board, "tile_size"),
        tile_thickness=_as_float(board, "tile_thickness"),
        lite_tile_thickness=_as_float(board, "lite_tile_thickness"),
        heavy_tile_thickness=_as_float(board, "heavy_tile_thickness"),
        heavy_tile_gap=_as_float(board, "heavy_tile_gap"),
        stack_count=_as_int(board, "stack_count"),
        stacking_method=StackingMethod(_as_str(board, "stacking_method")),
        interface_thickness=_as_float(board, "interface_thickness"),
        interface_separation=_as_float(board, "interface_separation"),
        fill_space_mode=FillSpaceMode(_as_str(board, "fill_space_mode")),
        space_width=_as_float(board, "space_width"),
        space_depth=_as_float(board, "space_depth"),
        max_tile_width=_as_int(board, "max_tile_width"),
        max_tile_depth=_as_int(board, "max_tile_depth"),
        tile_spacing=_as_float(board, "tile_spacing"),
    )


def _show_objects(
    grid: object,
    slot_delete_tool: _DisplayShape,
    adjacent_connector: _DisplayShape,
    viewer: dict[str, Any],
) -> None:
    port = _as_optional_port(viewer, "port")
    if not port_check(port):
        raise SystemExit(
            f"OCP CAD Viewer is not listening on port {port}. "
            "Open the OCP CAD Viewer panel in VS Code first, or configure `viewer.port`."
        )
    set_port(port)
    show(
        grid,
        slot_delete_tool.translate(_as_vector(viewer, "slot_delete_tool_offset")),
        adjacent_connector.translate(_as_vector(viewer, "adjacent_connector_offset")),
        names=[
            "openGrid board with adjacent-grid connector slots",
            "adjacent-grid connector slot delete tool",
            "adjacent-grid connector",
        ],
        port=port,
        reset_camera=Camera.CENTER,
        axes=True,
        grid=True,
    )


def main() -> None:
    args = _parse_args()
    config = _load_config(args.config)
    output_dir = _output_dir(config)
    output_dir.mkdir(parents=True, exist_ok=True)

    adjacent_connector_config = _adjacent_connector_config(config)
    slot_delete_tool_config = adjacent_connector_config.slot_delete_tool
    board_config = _grid_config(config, slot_delete_tool_config)
    grid = build_open_grid(board_config)
    slot_delete_tool = build_connector_slot_delete_tool(slot_delete_tool_config)
    adjacent_connector = build_adjacent_grid_connector(adjacent_connector_config)

    grid_path = output_dir / "opengrid_board.step"
    slot_delete_tool_path = output_dir / "adjacent_grid_connector_slot_delete_tool.step"
    adjacent_connector_path = output_dir / "adjacent_grid_connector.step"
    bd.export_step(grid, grid_path)
    bd.export_step(slot_delete_tool, slot_delete_tool_path)
    bd.export_step(adjacent_connector, adjacent_connector_path)

    viewer = _section(config, "viewer")
    if _as_bool(viewer, "show"):
        _show_objects(grid, slot_delete_tool, adjacent_connector, viewer)

    print(
        f"{grid_path}\n{slot_delete_tool_path}\n{adjacent_connector_path}"
        f"\nboard={board_config!r}"
        f"\nadjacent_connector={adjacent_connector_config!r}"
    )


if __name__ == "__main__":
    main()
