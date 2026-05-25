from __future__ import annotations

import argparse
from dataclasses import replace
import os
import shutil
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
    ConnectorSlotConfig,
    FillSpaceMode,
    MulticonnectConfig,
    MulticonnectPartKind,
    MulticonnectProfile,
    MulticonnectRounding,
    MulticonnectHeadConfig,
    SnapThreadConfig,
    ExpandingSnapConfig,
    SnapBodyConfig,
    SnapBodyShape,
    OpenConnectHeadConfig,
    OpenConnectScrewConfig,
    OpenGridSnapConfig,
    OpenGridSnapKind,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    ThreadType,
    MulticonnectScrewConfig,
    TextEngravingConfig,
    TextLabel,
    build_multiconnect_profile,
    build_openconnect_head,
    build_openconnect_screw,
    build_multiconnect_head,
    build_multiconnect_screw,
    build_opengrid_snap,
    build_multiconnect_backer,
    build_multiconnect_delete_tool,
    build_multiconnect_rail,
    build_multiconnect_receiver,
    build_adjacent_grid_connector,
    build_connector_slot_delete_tool,
    build_snap_threads,
    build_snap_body,
    build_expanding_snap,
    build_open_grid,
)

_DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")
_Vector3 = tuple[float, float, float]
_VerificationView = tuple[str, _Vector3, _Vector3]
_VISIBLE_SVG_STROKE_WIDTH = "0.08"


_BOARD_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("opengrid_board_iso.svg", (72.0, -96.0, 64.0), (0.0, 0.0, 1.0)),
    ("opengrid_board_front.svg", (0.0, -128.0, 4.0), (0.0, 0.0, 1.0)),
    ("opengrid_board_top.svg", (0.0, 0.0, 128.0), (0.0, 1.0, 0.0)),
)

_ADJACENT_SLOT_DELETE_TOOL_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("adjacent_grid_connector_slot_delete_tool_iso.svg", (18.0, -24.0, 18.0), (0.0, 0.0, 1.0)),
    ("adjacent_grid_connector_slot_delete_tool_front.svg", (0.0, -36.0, 2.0), (0.0, 0.0, 1.0)),
    ("adjacent_grid_connector_slot_delete_tool_top.svg", (0.0, 0.0, 36.0), (0.0, 1.0, 0.0)),
)

_ADJACENT_CONNECTOR_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("adjacent_grid_connector_iso.svg", (28.0, -36.0, 18.0), (0.0, 0.0, 1.0)),
    ("adjacent_grid_connector_front.svg", (0.0, -48.0, 2.0), (0.0, 0.0, 1.0)),
    ("adjacent_grid_connector_top.svg", (0.0, 0.0, 48.0), (0.0, 1.0, 0.0)),
)

_MULTICONNECT_RAIL_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("multiconnect_rail_iso.svg", (48.0, -72.0, 56.0), (0.0, 0.0, 1.0)),
    ("multiconnect_rail_back.svg", (0.0, -96.0, 35.0), (0.0, 0.0, 1.0)),
    ("multiconnect_rail_top.svg", (0.0, 0.0, 96.0), (0.0, 1.0, 0.0)),
)
_MULTICONNECT_RECEIVER_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("multiconnect_receiver_iso.svg", (48.0, -72.0, 56.0), (0.0, 0.0, 1.0)),
    ("multiconnect_receiver_back.svg", (0.0, -96.0, 35.0), (0.0, 0.0, 1.0)),
    ("multiconnect_receiver_top.svg", (0.0, 0.0, 96.0), (0.0, 1.0, 0.0)),
)

_MULTICONNECT_BACKER_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("multiconnect_backer_iso.svg", (72.0, -96.0, 64.0), (0.0, 0.0, 1.0)),
    ("multiconnect_backer_back.svg", (0.0, -128.0, 35.0), (0.0, 0.0, 1.0)),
    ("multiconnect_backer_top.svg", (0.0, 0.0, 128.0), (0.0, 1.0, 0.0)),
)

_MULTICONNECT_DELETE_TOOL_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("multiconnect_delete_tool_iso.svg", (48.0, -72.0, 56.0), (0.0, 0.0, 1.0)),
    ("multiconnect_delete_tool_back.svg", (0.0, -96.0, 35.0), (0.0, 0.0, 1.0)),
    ("multiconnect_delete_tool_top.svg", (0.0, 0.0, 96.0), (0.0, 1.0, 0.0)),
)


_SNAP_THREAD_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("snap_threads_iso.svg", (28.0, -36.0, 24.0), (0.0, 0.0, 1.0)),
    ("snap_threads_front.svg", (0.0, -48.0, 3.4), (0.0, 0.0, 1.0)),
    ("snap_threads_top.svg", (0.0, 0.0, 48.0), (0.0, 1.0, 0.0)),
)

_SNAP_BODY_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("snap_body_iso.svg", (36.0, -48.0, 28.0), (0.0, 0.0, 1.0)),
    ("snap_body_front.svg", (0.0, -64.0, 3.4), (0.0, 0.0, 1.0)),
    ("snap_body_top.svg", (0.0, 0.0, 64.0), (0.0, 1.0, 0.0)),
)

_EXPANDING_SNAP_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("expanding_snap_iso.svg", (36.0, -48.0, 28.0), (0.0, 0.0, 1.0)),
    ("expanding_snap_front.svg", (0.0, -64.0, 3.4), (0.0, 0.0, 1.0)),
    ("expanding_snap_top.svg", (0.0, 0.0, 64.0), (0.0, 1.0, 0.0)),
)

_OPENGRID_SNAP_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("opengrid_snap_iso.svg", (42.0, -56.0, 36.0), (0.0, 0.0, 1.0)),
    ("opengrid_snap_front.svg", (0.0, -72.0, 8.0), (0.0, 0.0, 1.0)),
    ("opengrid_snap_top.svg", (0.0, 0.0, 72.0), (0.0, 1.0, 0.0)),
)

_OPENCONNECT_SCREW_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("openconnect_screw_iso.svg", (32.0, -48.0, 28.0), (0.0, 0.0, 1.0)),
    ("openconnect_screw_front.svg", (0.0, -64.0, 8.0), (0.0, 0.0, 1.0)),
    ("openconnect_screw_top.svg", (0.0, 0.0, 64.0), (0.0, 1.0, 0.0)),
)
_OPENCONNECT_HEAD_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("openconnect_head_iso.svg", (28.0, -40.0, 20.0), (0.0, 0.0, 1.0)),
    ("openconnect_head_front.svg", (0.0, -56.0, 3.0), (0.0, 0.0, 1.0)),
    ("openconnect_head_top.svg", (0.0, 0.0, 56.0), (0.0, 1.0, 0.0)),
)

_MULTICONNECT_HEAD_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("multiconnect_head_iso.svg", (28.0, -40.0, 20.0), (0.0, 0.0, 1.0)),
    ("multiconnect_head_front.svg", (0.0, -56.0, 3.0), (0.0, 0.0, 1.0)),
    ("multiconnect_head_top.svg", (0.0, 0.0, 56.0), (0.0, 1.0, 0.0)),
)

_MULTICONNECT_SCREW_VERIFICATION_VIEWS: tuple[_VerificationView, ...] = (
    ("multiconnect_screw_iso.svg", (32.0, -48.0, 28.0), (0.0, 0.0, 1.0)),
    ("multiconnect_screw_front.svg", (0.0, -64.0, 8.0), (0.0, 0.0, 1.0)),
    ("multiconnect_screw_top.svg", (0.0, 0.0, 64.0), (0.0, 1.0, 0.0)),
)

class _DisplayShape(Protocol):
    def translate(self, vector: tuple[float, float, float]) -> object: ...
_VerificationVariant = tuple[str, _DisplayShape, tuple[_VerificationView, ...]]


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


def _as_vector2(section: dict[str, Any], key: str) -> tuple[float, float]:
    value = _required(section, key)
    if not isinstance(value, list) or len(value) != 2:
        raise SystemExit(f"Config key `{key}` must be a two-number list")
    return (_vector_item(value[0], key), _vector_item(value[1], key))


def _vector_item(value: Any, key: str) -> float:
    if not isinstance(value, int | float):
        raise SystemExit(f"Config key `{key}` must contain only numbers")
    return float(value)


def _output_dir(config: dict[str, Any]) -> Path:
    output = _section(config, "output")
    directory = _as_str(output, "directory").strip()
    if not directory:
        raise SystemExit("Config key `directory` must not be blank")
    return Path(directory)


def _verification_dir(config: dict[str, Any]) -> Path:
    return _output_dir(config) / "verification"


def _prepare_output_dir(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise SystemExit(f"Output path {path} exists but is not a directory")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


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


def _snap_body_config(config: dict[str, Any]) -> SnapBodyConfig:
    snap_body = _section(config, "snap_body")
    return SnapBodyConfig(
        body_shape=SnapBodyShape(_as_str(snap_body, "body_shape")),
        width=_as_float(snap_body, "width"),
        height=_as_float(snap_body, "height"),
        thickness=_as_float(snap_body, "thickness"),
        corner_chamfer=_as_float(snap_body, "corner_chamfer"),
        directional_corner_fillet_radius=_as_float(snap_body, "directional_corner_fillet_radius"),
        corner_edge_height=_as_float(snap_body, "corner_edge_height"),
        top_corner_extrude=_as_float(snap_body, "top_corner_extrude"),
        bottom_corner_extrude=_as_float(snap_body, "bottom_corner_extrude"),
        cut_width_inset=_as_float(snap_body, "cut_width_inset"),
        bottom_cut_thickness=_as_float(snap_body, "bottom_cut_thickness"),
        bottom_cut_offset_to_top=_as_float(snap_body, "bottom_cut_offset_to_top"),
        bottom_cut_offset_to_edge=_as_float(snap_body, "bottom_cut_offset_to_edge"),
        side_cut_thickness=_as_float(snap_body, "side_cut_thickness"),
        side_cut_depth=_as_float(snap_body, "side_cut_depth"),
        side_cut_offset_to_top=_as_float(snap_body, "side_cut_offset_to_top"),
        directional_slant_height_standard=_as_float(snap_body, "directional_slant_height_standard"),
        directional_slant_height_lite=_as_float(snap_body, "directional_slant_height_lite"),
        directional_slant_depth_standard=_as_float(snap_body, "directional_slant_depth_standard"),
        directional_slant_depth_lite=_as_float(snap_body, "directional_slant_depth_lite"),
        basic_nub_width_inset=_as_float(snap_body, "basic_nub_width_inset"),
        basic_nub_depth=_as_float(snap_body, "basic_nub_depth"),
        basic_nub_width_tip_taper=_as_float(snap_body, "basic_nub_width_tip_taper"),
        basic_nub_top_angle=_as_float(snap_body, "basic_nub_top_angle"),
        basic_nub_bottom_angle=_as_float(snap_body, "basic_nub_bottom_angle"),
        basic_nub_fillet_radius=_as_float(snap_body, "basic_nub_fillet_radius"),
        basic_nub_height_standard=_as_float(snap_body, "basic_nub_height_standard"),
        basic_nub_height_lite=_as_float(snap_body, "basic_nub_height_lite"),
        directional_nub_width_inset=_as_float(snap_body, "directional_nub_width_inset"),
        directional_nub_depth=_as_float(snap_body, "directional_nub_depth"),
        directional_nub_width_tip_taper=_as_float(snap_body, "directional_nub_width_tip_taper"),
        directional_nub_top_angle=_as_float(snap_body, "directional_nub_top_angle"),
        directional_nub_height_standard=_as_float(snap_body, "directional_nub_height_standard"),
        directional_nub_height_lite=_as_float(snap_body, "directional_nub_height_lite"),
        directional_nub_bottom_angle_standard=_as_float(snap_body, "directional_nub_bottom_angle_standard"),
        directional_nub_bottom_angle_lite=_as_float(snap_body, "directional_nub_bottom_angle_lite"),
        directional_nub_fillet_radius=_as_float(snap_body, "directional_nub_fillet_radius"),
        antidirect_nub_height_standard=_as_float(snap_body, "antidirect_nub_height_standard"),
        antidirect_nub_height_lite=_as_float(snap_body, "antidirect_nub_height_lite"),
        nub_offset_to_top=_as_float(snap_body, "nub_offset_to_top"),
        notch_width=_as_float(snap_body, "notch_width"),
        notch_surface_inset=_as_float(snap_body, "notch_surface_inset"),
        notch_gap_inset=_as_float(snap_body, "notch_gap_inset"),
        notch_surface_height_standard=_as_float(snap_body, "notch_surface_height_standard"),
        notch_surface_height_lite=_as_float(snap_body, "notch_surface_height_lite"),
        notch_gap_height_standard=_as_float(snap_body, "notch_gap_height_standard"),
        notch_gap_height_lite=_as_float(snap_body, "notch_gap_height_lite"),
        enable_corners=_as_bool(snap_body, "enable_corners"),
        enable_nubs=_as_bool(snap_body, "enable_nubs"),
        enable_cuts=_as_bool(snap_body, "enable_cuts"),
        enable_uninstall_notch=_as_bool(snap_body, "enable_uninstall_notch"),
        enable_directional_slants=_as_bool(snap_body, "enable_directional_slants"),
    )


def _expanding_snap_config(snap_body: SnapBodyConfig, threads: SnapThreadConfig, config: dict[str, Any]) -> ExpandingSnapConfig:
    expanding_snap = _section(config, "expanding_snap")
    return ExpandingSnapConfig(
        snap_body=snap_body,
        threads=threads,
        expand_distance_standard=_as_float(expanding_snap, "expand_distance_standard"),
        expand_distance_lite=_as_float(expanding_snap, "expand_distance_lite"),
        expand_entry_height_standard=_as_float(expanding_snap, "expand_entry_height_standard"),
        expand_entry_height_lite=_as_float(expanding_snap, "expand_entry_height_lite"),
        expand_entry_height_blunt=_as_float(expanding_snap, "expand_entry_height_blunt"),
        expand_end_height_standard=_as_float(expanding_snap, "expand_end_height_standard"),
        expand_end_height_lite=_as_float(expanding_snap, "expand_end_height_lite"),
        expand_split_angle=_as_float(expanding_snap, "expand_split_angle"),
        spring_thickness=_as_float(expanding_snap, "spring_thickness"),
        spring_to_center_thickness=_as_float(expanding_snap, "spring_to_center_thickness"),
        spring_gap=_as_float(expanding_snap, "spring_gap"),
        spring_face_chamfer=_as_float(expanding_snap, "spring_face_chamfer"),
        center_offset=_as_vector2(expanding_snap, "center_offset"),
    )


def _text_engraving_config(config: dict[str, Any]) -> TextEngravingConfig:
    text_section = _section(config, "text_engraving")
    labels_value = _required(text_section, "labels")
    if not isinstance(labels_value, list):
        raise SystemExit("Config key `labels` must be a list")
    labels: list[TextLabel] = []
    for item in labels_value:
        if not isinstance(item, dict):
            raise SystemExit("Text label entries must be mappings")
        labels.append(
            TextLabel(
                text=_as_str(item, "text"),
                size=_as_float(item, "size"),
                position=_as_vector2(item, "position"),
                depth=_as_float(item, "depth"),
                font=_as_str(item, "font"),
                top=_as_bool(item, "top"),
            )
        )
    return TextEngravingConfig(labels=tuple(labels))


def _openconnect_head_config(config: dict[str, Any]) -> OpenConnectHeadConfig:
    head = _section(config, "openconnect_head")
    return OpenConnectHeadConfig(
        bottom_height=_as_float(head, "bottom_height"),
        top_height=_as_float(head, "top_height"),
        middle_height=_as_float(head, "middle_height"),
        large_rect_width=_as_float(head, "large_rect_width"),
        large_rect_height=_as_float(head, "large_rect_height"),
        large_rect_chamfer=_as_float(head, "large_rect_chamfer"),
        nub_to_top_distance=_as_float(head, "nub_to_top_distance"),
        nub_depth=_as_float(head, "nub_depth"),
        nub_tip_height=_as_float(head, "nub_tip_height"),
        nub_fillet=_as_float(head, "nub_fillet"),
        back_pos_offset=_as_float(head, "back_pos_offset"),
        add_nubs=_as_bool(head, "add_nubs"),
    )


def _connector_slot_config(config: dict[str, Any]) -> ConnectorSlotConfig:
    slot = _section(config, "connector_slot")
    return ConnectorSlotConfig(
        coin_slot_height=_as_float(slot, "coin_slot_height"),
        coin_slot_width=_as_float(slot, "coin_slot_width"),
        coin_slot_thickness=_as_float(slot, "coin_slot_thickness"),
        flat_slot_height=_as_float(slot, "flat_slot_height"),
        flat_slot_width=_as_float(slot, "flat_slot_width"),
        flat_slot_height_offset=_as_float(slot, "flat_slot_height_offset"),
        flat_slot_start_thickness=_as_float(slot, "flat_slot_start_thickness"),
        flat_slot_end_thickness=_as_float(slot, "flat_slot_end_thickness"),
    )


def _multiconnect_head_config(config: dict[str, Any]) -> MulticonnectHeadConfig:
    head = _section(config, "multiconnect_head")
    return MulticonnectHeadConfig(
        large_diameter=_as_float(head, "large_diameter"),
        small_diameter=_as_float(head, "small_diameter"),
        top_height=_as_float(head, "top_height"),
        middle_height=_as_float(head, "middle_height"),
        bottom_height=_as_float(head, "bottom_height"),
        top_pattern=_as_str(head, "top_pattern"),
    )


def _openconnect_screw_config(
    threads: SnapThreadConfig,
    head: OpenConnectHeadConfig,
    connector_slot: ConnectorSlotConfig,
    text: TextEngravingConfig,
    config: dict[str, Any],
) -> OpenConnectScrewConfig:
    screw = _section(config, "openconnect_screw")
    return OpenConnectScrewConfig(
        threads=threads,
        head=head,
        connector_slot=connector_slot,
        text=text,
        folded=_as_bool(screw, "folded"),
    )


def _multiconnect_screw_config(
    threads: SnapThreadConfig,
    head: MulticonnectHeadConfig,
    connector_slot: ConnectorSlotConfig,
    text: TextEngravingConfig,
) -> MulticonnectScrewConfig:
    return MulticonnectScrewConfig(threads=threads, head=head, connector_slot=connector_slot, text=text)


def _opengrid_snap_config(
    snap_body: SnapBodyConfig,
    threads: SnapThreadConfig,
    expanding_snap: ExpandingSnapConfig,
    openconnect_head: OpenConnectHeadConfig,
    multiconnect_head: MulticonnectHeadConfig,
    text: TextEngravingConfig,
    config: dict[str, Any],
) -> OpenGridSnapConfig:
    snap = _section(config, "opengrid_snap")
    return OpenGridSnapConfig(
        kind=OpenGridSnapKind(_as_str(snap, "kind")),
        snap_body=snap_body,
        threads=threads,
        expanding_snap=expanding_snap,
        openconnect_head=openconnect_head,
        multiconnect_head=multiconnect_head,
        text=text,
        center_offset=_as_vector2(snap, "center_offset"),
        reverse_threads_entryside=_as_bool(snap, "reverse_threads_entryside"),
        disable_threads=_as_bool(snap, "disable_threads"),
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
    snap_body: _DisplayShape,
    expanding_snap: _DisplayShape,
    opengrid_snap: _DisplayShape,
    openconnect_screw: _DisplayShape,
    multiconnect_screw: _DisplayShape,
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
        snap_body.translate(_as_vector(viewer, "snap_body_offset")),
        expanding_snap.translate(_as_vector(viewer, "expanding_snap_offset")),
        opengrid_snap.translate(_as_vector(viewer, "opengrid_snap_offset")),
        openconnect_screw.translate(_as_vector(viewer, "openconnect_screw_offset")),
        multiconnect_screw.translate(_as_vector(viewer, "multiconnect_screw_offset")),
        names=[
            "openGrid board with adjacent-grid connector slots",
            "adjacent-grid connector slot delete tool",
            "adjacent-grid connector",
            "Multiconnect rail",
            "Multiconnect receiver",
            "Multiconnect backer",
            "Multiconnect delete tool",
            "snap threads",
            "snap body",
            "expanding snap",
            "assembled openGrid snap",
            "openConnect screw",
            "Multiconnect screw",
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
    visible, _hidden = cast(Any, shape).project_to_viewport(viewport_origin, viewport_up=viewport_up)
    exporter = bd.ExportSVG(scale=8.0, margin=2.0)
    exporter.add_layer("visible", line_color=bd.Color("black"), line_weight=0.08)
    exporter.add_shape(visible, layer="visible")
    exporter.write(path)
    _make_svg_projection_legible(path)


def _make_svg_projection_legible(path: Path) -> None:
    svg = path.read_text(encoding="utf-8")
    svg = svg.replace('stroke-width="0.01"', f'stroke-width="{_VISIBLE_SVG_STROKE_WIDTH}"')
    svg = svg.replace('stroke="rgb(0,0,0)"', f'stroke="rgb(0,0,0)" stroke-width="{_VISIBLE_SVG_STROKE_WIDTH}"', 1) if "stroke-width" not in svg else svg
    path.write_text(svg, encoding="utf-8")


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
def _slug(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_").replace(".", "").replace("(", "").replace(")", "")


def _variant_views(component: str, variant: str, views: tuple[_VerificationView, ...]) -> tuple[_VerificationView, ...]:
    prefix = f"{component}_"
    return tuple(
        (
            f"{component}_{variant}_{filename.removeprefix(prefix)}",
            origin,
            up,
        )
        for filename, origin, up in views
    )


def _export_component_variant_verification(
    variants: tuple[_VerificationVariant, ...],
    component_dir: Path,
    title: str,
) -> tuple[Path, ...]:
    component = component_dir.name
    svg_paths: list[Path] = []
    component_dir.mkdir(parents=True, exist_ok=True)
    for variant, shape, views in variants:
        for filename, origin, up in _variant_views(component, variant, views):
            path = component_dir / filename
            _export_svg_projection(shape, path, origin, up)
            svg_paths.append(path)
    gallery_path = component_dir / "gallery.html"
    _write_verification_gallery(title, svg_paths, gallery_path)
    return (*svg_paths, gallery_path)


def _multiconnect_profile_variants() -> tuple[MulticonnectProfile, ...]:
    return tuple(MulticonnectProfile)



def _export_output_verification(
    *,
    grid: _DisplayShape,
    slot_delete_tool: _DisplayShape,
    adjacent_connector: _DisplayShape,
    multiconnect_rail: _DisplayShape,
    multiconnect_receiver: _DisplayShape,
    multiconnect_backer: _DisplayShape,
    multiconnect_delete_tool: _DisplayShape,
    snap_threads: _DisplayShape,
    snap_body: _DisplayShape,
    expanding_snap: _DisplayShape,
    openconnect_head: _DisplayShape,
    multiconnect_head: _DisplayShape,
    opengrid_snap: _DisplayShape,
    openconnect_screw: _DisplayShape,
    multiconnect_screw: _DisplayShape,
    verification_dir: Path,
) -> tuple[Path, ...]:
    return (
        *_export_shape_verification(
            grid,
            verification_dir / "opengrid_board",
            title="openGrid board verification",
            gallery_filename="gallery.html",
            views=_BOARD_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            slot_delete_tool,
            verification_dir / "adjacent_grid_connector_slot_delete_tool",
            title="adjacent-grid connector slot delete tool verification",
            gallery_filename="gallery.html",
            views=_ADJACENT_SLOT_DELETE_TOOL_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            adjacent_connector,
            verification_dir / "adjacent_grid_connector",
            title="adjacent-grid connector verification",
            gallery_filename="gallery.html",
            views=_ADJACENT_CONNECTOR_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            multiconnect_rail,
            verification_dir / "multiconnect_rail",
            title="Multiconnect rail verification",
            gallery_filename="gallery.html",
            views=_MULTICONNECT_RAIL_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            multiconnect_receiver,
            verification_dir / "multiconnect_receiver",
            title="Multiconnect receiver verification",
            gallery_filename="gallery.html",
            views=_MULTICONNECT_RECEIVER_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            multiconnect_backer,
            verification_dir / "multiconnect_backer",
            title="Multiconnect backer verification",
            gallery_filename="gallery.html",
            views=_MULTICONNECT_BACKER_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            multiconnect_delete_tool,
            verification_dir / "multiconnect_delete_tool",
            title="Multiconnect delete tool verification",
            gallery_filename="gallery.html",
            views=_MULTICONNECT_DELETE_TOOL_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            snap_threads,
            verification_dir / "snap_threads",
            title="snap threads verification",
            gallery_filename="gallery.html",
            views=_SNAP_THREAD_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            snap_body,
            verification_dir / "snap_body",
            title="snap body verification",
            gallery_filename="gallery.html",
            views=_SNAP_BODY_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            expanding_snap,
            verification_dir / "expanding_snap",
            title="expanding snap verification",
            gallery_filename="gallery.html",
            views=_EXPANDING_SNAP_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            openconnect_head,
            verification_dir / "openconnect_head",
            title="openConnect head verification",
            gallery_filename="gallery.html",
            views=_OPENCONNECT_HEAD_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            multiconnect_head,
            verification_dir / "multiconnect_head",
            title="Multiconnect head verification",
            gallery_filename="gallery.html",
            views=_MULTICONNECT_HEAD_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            opengrid_snap,
            verification_dir / "opengrid_snap",
            title="assembled openGrid snap verification",
            gallery_filename="gallery.html",
            views=_OPENGRID_SNAP_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            openconnect_screw,
            verification_dir / "openconnect_screw",
            title="openConnect screw verification",
            gallery_filename="gallery.html",
            views=_OPENCONNECT_SCREW_VERIFICATION_VIEWS,
        ),
        *_export_shape_verification(
            multiconnect_screw,
            verification_dir / "multiconnect_screw",
            title="Multiconnect screw verification",
            gallery_filename="gallery.html",
            views=_MULTICONNECT_SCREW_VERIFICATION_VIEWS,
        ),
    )


def _export_variant_output_verification(
    *,
    board_config: GridConfig,
    slot_delete_tool_config: ConnectorSlotDeleteToolConfig,
    adjacent_connector_config: AdjacentGridConnectorConfig,
    multiconnect_config: MulticonnectConfig,
    snap_thread_config: SnapThreadConfig,
    snap_body_config: SnapBodyConfig,
    expanding_snap_config: ExpandingSnapConfig,
    openconnect_head_config: OpenConnectHeadConfig,
    connector_slot_config: ConnectorSlotConfig,
    multiconnect_head_config: MulticonnectHeadConfig,
    opengrid_snap_config: OpenGridSnapConfig,
    openconnect_screw_config: OpenConnectScrewConfig,
    multiconnect_screw_config: MulticonnectScrewConfig,
    verification_dir: Path,
) -> tuple[Path, ...]:
    return (
        *_export_component_variant_verification(_board_verification_variants(board_config), verification_dir / "opengrid_board", "openGrid board variant verification"),
        *_export_component_variant_verification(
            _slot_delete_tool_verification_variants(slot_delete_tool_config),
            verification_dir / "adjacent_grid_connector_slot_delete_tool",
            "adjacent-grid connector slot delete tool variant verification",
        ),
        *_export_component_variant_verification(
            _adjacent_connector_verification_variants(adjacent_connector_config),
            verification_dir / "adjacent_grid_connector",
            "adjacent-grid connector variant verification",
        ),
        *_export_component_variant_verification(
            _multiconnect_rail_verification_variants(multiconnect_config),
            verification_dir / "multiconnect_rail",
            "Multiconnect rail variant verification",
        ),
        *_export_component_variant_verification(
            _multiconnect_receiver_verification_variants(multiconnect_config),
            verification_dir / "multiconnect_receiver",
            "Multiconnect receiver variant verification",
        ),
        *_export_component_variant_verification(
            _multiconnect_backer_verification_variants(multiconnect_config),
            verification_dir / "multiconnect_backer",
            "Multiconnect backer variant verification",
        ),
        *_export_component_variant_verification(
            _multiconnect_delete_tool_verification_variants(multiconnect_config),
            verification_dir / "multiconnect_delete_tool",
            "Multiconnect delete tool variant verification",
        ),
        *_export_component_variant_verification(_snap_thread_verification_variants(snap_thread_config), verification_dir / "snap_threads", "snap thread variant verification"),
        *_export_component_variant_verification(_snap_body_verification_variants(snap_body_config), verification_dir / "snap_body", "snap body variant verification"),
        *_export_component_variant_verification(
            _expanding_snap_verification_variants(expanding_snap_config),
            verification_dir / "expanding_snap",
            "expanding snap variant verification",
        ),
        *_export_component_variant_verification(
            _openconnect_head_verification_variants(openconnect_head_config),
            verification_dir / "openconnect_head",
            "openConnect head variant verification",
        ),
        *_export_component_variant_verification(
            _multiconnect_head_verification_variants(multiconnect_head_config, connector_slot_config),
            verification_dir / "multiconnect_head",
            "Multiconnect head variant verification",
        ),
        *_export_component_variant_verification(
            _opengrid_snap_verification_variants(opengrid_snap_config),
            verification_dir / "opengrid_snap",
            "assembled openGrid snap variant verification",
        ),
        *_export_component_variant_verification(
            _openconnect_screw_verification_variants(openconnect_screw_config),
            verification_dir / "openconnect_screw",
            "openConnect screw variant verification",
        ),
        *_export_component_variant_verification(
            _multiconnect_screw_verification_variants(multiconnect_screw_config),
            verification_dir / "multiconnect_screw",
            "Multiconnect screw variant verification",
        ),
    )


def _board_verification_variants(config: GridConfig) -> tuple[_VerificationVariant, ...]:
    kind_variants = tuple(
        (_slug(kind.value), build_open_grid(replace(config, kind=kind, fill_space_mode=FillSpaceMode.NONE)), _BOARD_VERIFICATION_VIEWS)
        for kind in BoardKind
    )
    fill_variants = tuple(
        (
            f"fill_{_slug(mode.value)}",
            build_open_grid(replace(config, fill_space_mode=mode)),
            _BOARD_VERIFICATION_VIEWS,
        )
        for mode in FillSpaceMode
    )
    return (*kind_variants, *fill_variants)


def _slot_delete_tool_verification_variants(config: ConnectorSlotDeleteToolConfig) -> tuple[_VerificationVariant, ...]:
    return (("default", build_connector_slot_delete_tool(config), _ADJACENT_SLOT_DELETE_TOOL_VERIFICATION_VIEWS),)


def _adjacent_connector_verification_variants(config: AdjacentGridConnectorConfig) -> tuple[_VerificationVariant, ...]:
    return (
        ("configured", build_adjacent_grid_connector(config), _ADJACENT_CONNECTOR_VERIFICATION_VIEWS),
        ("tight_fit", build_adjacent_grid_connector(replace(config, fit_clearance=0.0)), _ADJACENT_CONNECTOR_VERIFICATION_VIEWS),
        ("loose_fit", build_adjacent_grid_connector(replace(config, fit_clearance=0.2)), _ADJACENT_CONNECTOR_VERIFICATION_VIEWS),
    )


def _multiconnect_rail_verification_variants(config: MulticonnectConfig) -> tuple[_VerificationVariant, ...]:
    profile_variants = tuple(
        (f"profile_{_slug(profile.value)}", build_multiconnect_rail(replace(config, profile=profile)), _MULTICONNECT_RAIL_VERIFICATION_VIEWS)
        for profile in _multiconnect_profile_variants()
    )
    rounding_variants = tuple(
        (f"rounding_{_slug(rounding.value)}", build_multiconnect_rail(replace(config, rounding=rounding)), _MULTICONNECT_RAIL_VERIFICATION_VIEWS)
        for rounding in MulticonnectRounding
    )
    return (*profile_variants, *rounding_variants)


def _multiconnect_receiver_verification_variants(config: MulticonnectConfig) -> tuple[_VerificationVariant, ...]:
    return tuple(
        (
            f"profile_{_slug(profile.value)}",
            build_multiconnect_receiver(replace(config, profile=profile)),
            _MULTICONNECT_RECEIVER_VERIFICATION_VIEWS,
        )
        for profile in _multiconnect_profile_variants()
    )


def _multiconnect_backer_verification_variants(config: MulticonnectConfig) -> tuple[_VerificationVariant, ...]:
    return tuple(
        (
            f"profile_{_slug(profile.value)}",
            build_multiconnect_backer(replace(config, profile=profile)),
            _MULTICONNECT_BACKER_VERIFICATION_VIEWS,
        )
        for profile in _multiconnect_profile_variants()
    )


def _multiconnect_delete_tool_verification_variants(config: MulticonnectConfig) -> tuple[_VerificationVariant, ...]:
    return tuple(
        (
            f"profile_{_slug(profile.value)}",
            build_multiconnect_delete_tool(replace(config, profile=profile)),
            _MULTICONNECT_DELETE_TOOL_VERIFICATION_VIEWS,
        )
        for profile in _multiconnect_profile_variants()
    )


def _snap_thread_verification_variants(config: SnapThreadConfig) -> tuple[_VerificationVariant, ...]:
    type_variants = tuple(
        (f"type_{_slug(thread_type.value)}", build_snap_threads(replace(config, thread_type=thread_type)), _SNAP_THREAD_VERIFICATION_VIEWS)
        for thread_type in ThreadType
    )
    height_variants = tuple(
        (name, build_snap_threads(replace(config, height=height)), _SNAP_THREAD_VERIFICATION_VIEWS)
        for name, height in (("height_standard", 6.8), ("height_lite", 4.0), ("height_lite_basic", 3.4))
    )
    return (*type_variants, *height_variants)


def _snap_body_verification_variants(config: SnapBodyConfig) -> tuple[_VerificationVariant, ...]:
    shape_variants = tuple(
        (f"shape_{_slug(shape.value)}", build_snap_body(replace(config, body_shape=shape)), _SNAP_BODY_VERIFICATION_VIEWS)
        for shape in SnapBodyShape
    )
    thickness_variants = tuple(
        (name, build_snap_body(replace(config, thickness=thickness)), _SNAP_BODY_VERIFICATION_VIEWS)
        for name, thickness in (("thickness_standard", 6.8), ("thickness_lite", 4.0), ("thickness_lite_basic", 3.4))
    )
    return (*shape_variants, *thickness_variants)


def _expanding_snap_verification_variants(config: ExpandingSnapConfig) -> tuple[_VerificationVariant, ...]:
    type_variants = tuple(
        (
            f"threads_{_slug(thread_type.value)}",
            build_expanding_snap(replace(config, threads=replace(config.threads, thread_type=thread_type))),
            _EXPANDING_SNAP_VERIFICATION_VIEWS,
        )
        for thread_type in ThreadType
    )
    shape_variants = tuple(
        (
            f"shape_{_slug(shape.value)}",
            build_expanding_snap(replace(config, snap_body=replace(config.snap_body, body_shape=shape))),
            _EXPANDING_SNAP_VERIFICATION_VIEWS,
        )
        for shape in SnapBodyShape
    )
    thickness_variants = tuple(
        (
            name,
            build_expanding_snap(replace(config, snap_body=replace(config.snap_body, thickness=thickness))),
            _EXPANDING_SNAP_VERIFICATION_VIEWS,
        )
        for name, thickness in (("thickness_standard", 6.8), ("thickness_lite", 4.0))
    )
    return (*type_variants, *shape_variants, *thickness_variants)


def _openconnect_head_verification_variants(config: OpenConnectHeadConfig) -> tuple[_VerificationVariant, ...]:
    return (
        ("nubs_enabled", build_openconnect_head(replace(config, add_nubs=True)), _OPENCONNECT_HEAD_VERIFICATION_VIEWS),
        ("nubs_disabled", build_openconnect_head(replace(config, add_nubs=False)), _OPENCONNECT_HEAD_VERIFICATION_VIEWS),
    )


def _multiconnect_head_verification_variants(
    config: MulticonnectHeadConfig,
    connector_slot: ConnectorSlotConfig,
) -> tuple[_VerificationVariant, ...]:
    return tuple(
        (
            f"top_{_slug(top_pattern)}",
            build_multiconnect_head(replace(config, top_pattern=top_pattern), connector_slot),
            _MULTICONNECT_HEAD_VERIFICATION_VIEWS,
        )
        for top_pattern in ("coin_slot", "dimple", "none")
    )


def _opengrid_snap_verification_variants(config: OpenGridSnapConfig) -> tuple[_VerificationVariant, ...]:
    return tuple(
        (
            f"kind_{_slug(kind.value)}",
            build_opengrid_snap(replace(config, kind=kind)),
            _OPENGRID_SNAP_VERIFICATION_VIEWS,
        )
        for kind in OpenGridSnapKind
    )


def _openconnect_screw_verification_variants(config: OpenConnectScrewConfig) -> tuple[_VerificationVariant, ...]:
    folded_variants = tuple(
        (f"folded_{_slug(str(folded))}", build_openconnect_screw(replace(config, folded=folded)), _OPENCONNECT_SCREW_VERIFICATION_VIEWS)
        for folded in (False, True)
    )
    thread_variants = tuple(
        (
            f"threads_{_slug(thread_type.value)}",
            build_openconnect_screw(replace(config, threads=replace(config.threads, thread_type=thread_type))),
            _OPENCONNECT_SCREW_VERIFICATION_VIEWS,
        )
        for thread_type in ThreadType
    )
    return (*folded_variants, *thread_variants)


def _multiconnect_screw_verification_variants(config: MulticonnectScrewConfig) -> tuple[_VerificationVariant, ...]:
    top_variants = tuple(
        (
            f"top_{_slug(top_pattern)}",
            build_multiconnect_screw(replace(config, head=replace(config.head, top_pattern=top_pattern))),
            _MULTICONNECT_SCREW_VERIFICATION_VIEWS,
        )
        for top_pattern in ("coin_slot", "dimple", "none")
    )
    thread_variants = tuple(
        (
            f"threads_{_slug(thread_type.value)}",
            build_multiconnect_screw(replace(config, threads=replace(config.threads, thread_type=thread_type))),
            _MULTICONNECT_SCREW_VERIFICATION_VIEWS,
        )
        for thread_type in ThreadType
    )
    return (*top_variants, *thread_variants)

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
    _prepare_output_dir(output_dir)
    verification_dir = output_dir / "verification"

    adjacent_connector_config = _adjacent_connector_config(config)
    slot_delete_tool_config = adjacent_connector_config.slot_delete_tool
    board_config = _grid_config(config, slot_delete_tool_config)
    multiconnect_config = _multiconnect_config(config)
    snap_thread_config = _snap_thread_config(config)
    snap_body_config = _snap_body_config(config)
    expanding_snap_config = _expanding_snap_config(snap_body_config, snap_thread_config, config)
    text_config = _text_engraving_config(config)
    openconnect_head_config = _openconnect_head_config(config)
    connector_slot_config = _connector_slot_config(config)
    multiconnect_head_config = _multiconnect_head_config(config)
    opengrid_snap_config = _opengrid_snap_config(
        snap_body_config,
        snap_thread_config,
        expanding_snap_config,
        openconnect_head_config,
        multiconnect_head_config,
        text_config,
        config,
    )
    openconnect_screw_config = _openconnect_screw_config(
        replace(snap_thread_config, clearance=0.0),
        openconnect_head_config,
        connector_slot_config,
        text_config,
        config,
    )
    multiconnect_screw_config = _multiconnect_screw_config(
        replace(snap_thread_config, clearance=0.0),
        multiconnect_head_config,
        connector_slot_config,
        text_config,
    )
    multiconnect_profile = build_multiconnect_profile(multiconnect_config)
    multiconnect_rail = build_multiconnect_rail(multiconnect_config)
    multiconnect_receiver = build_multiconnect_receiver(multiconnect_config)
    multiconnect_backer = build_multiconnect_backer(multiconnect_config)
    multiconnect_delete_tool = build_multiconnect_delete_tool(multiconnect_config)
    snap_threads = build_snap_threads(snap_thread_config)
    snap_body = build_snap_body(snap_body_config)
    expanding_snap = build_expanding_snap(expanding_snap_config)
    grid = build_open_grid(board_config)
    slot_delete_tool = build_connector_slot_delete_tool(slot_delete_tool_config)
    adjacent_connector = build_adjacent_grid_connector(adjacent_connector_config)
    openconnect_head = build_openconnect_head(openconnect_head_config)
    multiconnect_head = build_multiconnect_head(multiconnect_head_config, connector_slot_config)
    opengrid_snap = build_opengrid_snap(opengrid_snap_config)
    openconnect_screw = build_openconnect_screw(openconnect_screw_config)
    multiconnect_screw = build_multiconnect_screw(multiconnect_screw_config)

    grid_path = output_dir / "opengrid_board.step"
    slot_delete_tool_path = output_dir / "adjacent_grid_connector_slot_delete_tool.step"
    adjacent_connector_path = output_dir / "adjacent_grid_connector.step"
    multiconnect_rail_path = output_dir / "multiconnect_rail.step"
    multiconnect_receiver_path = output_dir / "multiconnect_receiver.step"
    multiconnect_backer_path = output_dir / "multiconnect_backer.step"
    multiconnect_delete_tool_path = output_dir / "multiconnect_delete_tool.step"
    snap_threads_path = output_dir / "snap_threads.step"
    snap_body_path = output_dir / "snap_body.step"
    expanding_snap_path = output_dir / "expanding_snap.step"
    openconnect_head_path = output_dir / "openconnect_head.step"
    multiconnect_head_path = output_dir / "multiconnect_head.step"
    opengrid_snap_path = output_dir / "opengrid_snap.step"
    openconnect_screw_path = output_dir / "openconnect_screw.step"
    multiconnect_screw_path = output_dir / "multiconnect_screw.step"
    bd.export_step(grid, grid_path)
    bd.export_step(slot_delete_tool, slot_delete_tool_path)
    bd.export_step(adjacent_connector, adjacent_connector_path)
    bd.export_step(multiconnect_rail, multiconnect_rail_path)
    bd.export_step(multiconnect_receiver, multiconnect_receiver_path)
    bd.export_step(multiconnect_backer, multiconnect_backer_path)
    bd.export_step(multiconnect_delete_tool, multiconnect_delete_tool_path)
    bd.export_step(snap_threads, snap_threads_path)
    bd.export_step(snap_body, snap_body_path)
    bd.export_step(expanding_snap, expanding_snap_path)
    bd.export_step(openconnect_head, openconnect_head_path)
    bd.export_step(multiconnect_head, multiconnect_head_path)
    bd.export_step(opengrid_snap, opengrid_snap_path)
    bd.export_step(openconnect_screw, openconnect_screw_path)
    bd.export_step(multiconnect_screw, multiconnect_screw_path)
    verification_paths = _export_variant_output_verification(
        board_config=board_config,
        slot_delete_tool_config=slot_delete_tool_config,
        adjacent_connector_config=adjacent_connector_config,
        multiconnect_config=multiconnect_config,
        snap_thread_config=snap_thread_config,
        snap_body_config=snap_body_config,
        expanding_snap_config=expanding_snap_config,
        openconnect_head_config=openconnect_head_config,
        connector_slot_config=connector_slot_config,
        multiconnect_head_config=multiconnect_head_config,
        opengrid_snap_config=opengrid_snap_config,
        openconnect_screw_config=openconnect_screw_config,
        multiconnect_screw_config=multiconnect_screw_config,
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
            snap_body,
            expanding_snap,
            opengrid_snap,
            openconnect_screw,
            multiconnect_screw,
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
        snap_body_path,
        expanding_snap_path,
        openconnect_head_path,
        multiconnect_head_path,
        opengrid_snap_path,
        openconnect_screw_path,
        multiconnect_screw_path,
        *verification_paths,
    )
    print(
        "\n".join(str(path) for path in output_paths)
        + f"\nboard={board_config!r}"
        + f"\nadjacent_connector={adjacent_connector_config!r}"
        + f"\nmulticonnect={multiconnect_config!r}"
        + f"\nsnap_threads={snap_thread_config!r}"
        + f"\nsnap_body={snap_body_config!r}"
        + f"\nexpanding_snap={expanding_snap_config!r}"
        + f"\nopengrid_snap={opengrid_snap_config!r}"
        + f"\nopenconnect_screw={openconnect_screw_config!r}"
        + f"\nmulticonnect_screw={multiconnect_screw_config!r}"
        + f"\nmulticonnect_profile={multiconnect_profile!r}"
    )


if __name__ == "__main__":
    main()
