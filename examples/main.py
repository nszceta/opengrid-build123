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
    MulticonnectConfig,
    MulticonnectPartKind,
    MulticonnectProfile,
    MulticonnectRounding,
    SnapThreadConfig,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    ThreadType,
    build_multiconnect_profile,
    build_multiconnect_backer,
    build_multiconnect_delete_tool,
    build_multiconnect_rail,
    build_multiconnect_receiver,
    build_adjacent_grid_connector,
    build_connector_slot_delete_tool,
    build_snap_threads,
    build_open_grid,
)

_DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")
_Vector3 = tuple[float, float, float]
_VerificationView = tuple[str, _Vector3, _Vector3]

_MULTICONNECT_RAIL_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("multiconnect_rail_iso.svg", (48.0, -72.0, 56.0), (0.0, 0.0, 1.0)),
    ("multiconnect_rail_back.svg", (0.0, -96.0, 35.0), (0.0, 0.0, 1.0)),
    ("multiconnect_rail_top.svg", (0.0, 0.0, 96.0), (0.0, 1.0, 0.0)),
)

_SNAP_THREAD_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("snap_threads_iso.svg", (28.0, -36.0, 24.0), (0.0, 0.0, 1.0)),
    ("snap_threads_front.svg", (0.0, -48.0, 3.4), (0.0, 0.0, 1.0)),
    ("snap_threads_top.svg", (0.0, 0.0, 48.0), (0.0, 1.0, 0.0)),
)

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


def _verification_dir(config: dict[str, Any]) -> Path:
    return _output_dir(config) / "verification"




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


def _multiconnect_config(config: dict[str, Any]) -> MulticonnectConfig:
    multiconnect = _section(config, "multiconnect")
    return MulticonnectConfig(
        profile=MulticonnectProfile(_as_str(multiconnect, "profile")),
        part_kind=MulticonnectPartKind(_as_str(multiconnect, "part_kind")),
        length=_as_float(multiconnect, "length"),
        width=_as_float(multiconnect, "width"),
        grid_size=_as_float(multiconnect, "grid_size"),
        radius=_as_float(multiconnect, "radius"),
        capture_depth=_as_float(multiconnect, "capture_depth"),
        dovetail_depth=_as_float(multiconnect, "dovetail_depth"),
        stem_depth=_as_float(multiconnect, "stem_depth"),
        receiver_offset=_as_float(multiconnect, "receiver_offset"),
        dimple_radius=_as_float(multiconnect, "dimple_radius"),
        dimples_enabled=_as_bool(multiconnect, "dimples_enabled"),
        dimple_scale=_as_float(multiconnect, "dimple_scale"),
        rounding=MulticonnectRounding(_as_str(multiconnect, "rounding")),
        receiver_side_wall_thickness=_as_float(multiconnect, "receiver_side_wall_thickness"),
        receiver_back_thickness=_as_float(multiconnect, "receiver_back_thickness"),
        receiver_top_wall_thickness=_as_float(multiconnect, "receiver_top_wall_thickness"),
        on_ramps_enabled=_as_bool(multiconnect, "on_ramps_enabled"),
        on_ramp_every_n_holes=_as_int(multiconnect, "on_ramp_every_n_holes"),
        on_ramp_start_offset=_as_int(multiconnect, "on_ramp_start_offset"),
    )


def _snap_thread_config(config: dict[str, Any]) -> SnapThreadConfig:
    snap_threads = _section(config, "snap_threads")
    return SnapThreadConfig(
        thread_type=ThreadType(_as_str(snap_threads, "thread_type")),
        height=_as_float(snap_threads, "height"),
        diameter=_as_float(snap_threads, "diameter"),
        clearance=_as_float(snap_threads, "clearance"),
        pitch=_as_float(snap_threads, "pitch"),
        top_bevel=_as_float(snap_threads, "top_bevel"),
        bottom_bevel_standard=_as_float(snap_threads, "bottom_bevel_standard"),
        bottom_bevel_lite=_as_float(snap_threads, "bottom_bevel_lite"),
        offset_angle=_as_float(snap_threads, "offset_angle"),
        blunt_cutoff=_as_bool(snap_threads, "blunt_cutoff"),
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
    multiconnect_rail: _DisplayShape,
    multiconnect_receiver: _DisplayShape,
    multiconnect_backer: _DisplayShape,
    multiconnect_delete_tool: _DisplayShape,
    snap_threads: _DisplayShape,
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
        multiconnect_rail.translate(_as_vector(viewer, "multiconnect_rail_offset")),
        multiconnect_receiver.translate(_as_vector(viewer, "multiconnect_receiver_offset")),
        multiconnect_backer.translate(_as_vector(viewer, "multiconnect_backer_offset")),
        multiconnect_delete_tool.translate(_as_vector(viewer, "multiconnect_delete_tool_offset")),
        snap_threads.translate(_as_vector(viewer, "snap_threads_offset")),
        names=[
            "openGrid board with adjacent-grid connector slots",
            "adjacent-grid connector slot delete tool",
            "adjacent-grid connector",
            "Multiconnect rail",
            "Multiconnect receiver",
            "Multiconnect backer",
            "Multiconnect delete tool",
            "snap threads",
        ],
        port=port,
        reset_camera=Camera.CENTER,
        axes=True,
        grid=True,
    )


def _export_svg_projection(
    shape: _DisplayShape,
    path: Path,
    viewport_origin: _Vector3,
    viewport_up: _Vector3 = (0.0, 0.0, 1.0),
) -> None:
    visible, hidden = cast(Any, shape).project_to_viewport(viewport_origin, viewport_up=viewport_up)
    exporter = bd.ExportSVG(scale=8.0, margin=2.0)
    exporter.add_layer("visible", line_color=bd.Color("black"), line_weight=0.08)
    exporter.add_layer("hidden", line_color=bd.Color("lightgray"), line_weight=0.04, line_type=bd.LineType.HIDDEN)
    exporter.add_shape(hidden, layer="hidden")
    exporter.add_shape(visible, layer="visible")
    exporter.write(path)


def _export_shape_verification(
    shape: _DisplayShape,
    verification_dir: Path,
    *,
    title: str,
    gallery_filename: str,
    views: tuple[_VerificationView, ...],
) -> tuple[Path, ...]:
    verification_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, origin, up in views:
        path = verification_dir / filename
        _export_svg_projection(shape, path, origin, up)
        paths.append(path)
    gallery_path = verification_dir / gallery_filename
    _write_verification_gallery(title, paths, gallery_path)
    return (*paths, gallery_path)


def _export_output_verification(
    *,
    multiconnect_rail: _DisplayShape,
    snap_threads: _DisplayShape,
    verification_dir: Path,
) -> tuple[Path, ...]:
    return (
        *_export_shape_verification(
            multiconnect_rail,
            verification_dir / "multiconnect_rail",
            title="Multiconnect rail verification",
            gallery_filename="gallery.html",
            views=_MULTICONNECT_RAIL_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            snap_threads,
            verification_dir / "snap_threads",
            title="snap threads verification",
            gallery_filename="gallery.html",
            views=_SNAP_THREAD_VERIFICATION_VIEWS,
        ),
    )


def _write_verification_gallery(title: str, svg_paths: list[Path], gallery_path: Path) -> None:
    figures = "\n".join(
        f'<figure><figcaption>{path.name}</figcaption><img src="{path.name}" alt="{path.name}"></figure>'
        for path in svg_paths
    )
    gallery_path.write_text(
        "<!doctype html>\n"
        '<html lang="en">\n'
        f"<head><meta charset=\"utf-8\"><title>{title}</title>"
        "<style>body{font-family:sans-serif}main{display:flex;gap:1rem;flex-wrap:wrap}"
        "figure{margin:0}img{max-width:28rem;border:1px solid #ccc}</style></head>\n"
        f"<body><h1>{title}</h1><main>{figures}</main></body></html>\n",
        encoding="utf-8",
    )


def main() -> None:
    args = _parse_args()
    config = _load_config(args.config)
    output_dir = _output_dir(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    verification_dir = _verification_dir(config)

    adjacent_connector_config = _adjacent_connector_config(config)
    slot_delete_tool_config = adjacent_connector_config.slot_delete_tool
    board_config = _grid_config(config, slot_delete_tool_config)
    multiconnect_config = _multiconnect_config(config)
    snap_thread_config = _snap_thread_config(config)
    multiconnect_profile = build_multiconnect_profile(multiconnect_config)
    multiconnect_rail = build_multiconnect_rail(multiconnect_config)
    multiconnect_receiver = build_multiconnect_receiver(multiconnect_config)
    multiconnect_backer = build_multiconnect_backer(multiconnect_config)
    multiconnect_delete_tool = build_multiconnect_delete_tool(multiconnect_config)
    snap_threads = build_snap_threads(snap_thread_config)
    grid = build_open_grid(board_config)
    slot_delete_tool = build_connector_slot_delete_tool(slot_delete_tool_config)
    adjacent_connector = build_adjacent_grid_connector(adjacent_connector_config)

    grid_path = output_dir / "opengrid_board.step"
    slot_delete_tool_path = output_dir / "adjacent_grid_connector_slot_delete_tool.step"
    adjacent_connector_path = output_dir / "adjacent_grid_connector.step"
    multiconnect_rail_path = output_dir / "multiconnect_rail.step"
    multiconnect_receiver_path = output_dir / "multiconnect_receiver.step"
    multiconnect_backer_path = output_dir / "multiconnect_backer.step"
    multiconnect_delete_tool_path = output_dir / "multiconnect_delete_tool.step"
    snap_threads_path = output_dir / "snap_threads.step"
    bd.export_step(grid, grid_path)
    bd.export_step(slot_delete_tool, slot_delete_tool_path)
    bd.export_step(adjacent_connector, adjacent_connector_path)
    bd.export_step(multiconnect_rail, multiconnect_rail_path)
    bd.export_step(multiconnect_receiver, multiconnect_receiver_path)
    bd.export_step(multiconnect_backer, multiconnect_backer_path)
    bd.export_step(multiconnect_delete_tool, multiconnect_delete_tool_path)
    bd.export_step(snap_threads, snap_threads_path)
    verification_paths = _export_output_verification(
        multiconnect_rail=multiconnect_rail,
        snap_threads=snap_threads,
        verification_dir=verification_dir,
    )

    viewer = _section(config, "viewer")
    if _as_bool(viewer, "show"):
        _show_objects(
            grid,
            slot_delete_tool,
            adjacent_connector,
            multiconnect_rail,
            multiconnect_receiver,
            multiconnect_backer,
            multiconnect_delete_tool,
            snap_threads,
            viewer,
        )

    output_paths = (
        grid_path,
        slot_delete_tool_path,
        adjacent_connector_path,
        multiconnect_rail_path,
        multiconnect_receiver_path,
        multiconnect_backer_path,
        multiconnect_delete_tool_path,
        snap_threads_path,
        *verification_paths,
    )
    print(
        "\n".join(str(path) for path in output_paths)
        + f"\nboard={board_config!r}"
        + f"\nadjacent_connector={adjacent_connector_config!r}"
        + f"\nmulticonnect={multiconnect_config!r}"
        + f"\nsnap_threads={snap_thread_config!r}"
        + f"\nmulticonnect_profile={multiconnect_profile!r}"
    )


if __name__ == "__main__":
    main()
