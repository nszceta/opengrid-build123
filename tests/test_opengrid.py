from __future__ import annotations
from dataclasses import fields as dataclass_fields, replace
import re
from pathlib import Path
import importlib.util
import math
import yaml
from typing import Any, cast

import pytest


from opengrid_build123.opengrid import (
    AdjacentGridConnectorConfig,
    BoardKind,
    ChamferMode,
    FillSpaceMode,
    MulticonnectConfig,
    MulticonnectPartKind,
    MulticonnectProfile,
    MulticonnectRounding,
    MulticonnectHeadConfig,
    SnapThreadConfig,
    SnapBodyConfig,
    ExpandingSnapConfig,
    SnapBodyShape,
    ConnectorSlotConfig,
    OpenConnectHeadConfig,
    OpenConnectScrewConfig,
    OpenGridSnapConfig,
    OpenGridSnapKind,
    ConnectorSlotDeleteToolConfig,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    ThreadType,
    MulticonnectScrewConfig,
    TextEngravingConfig,
    TextLabel,
    build_connector_slot_delete_tool,
    build_adjacent_grid_connector,
    build_openconnect_head,
    build_openconnect_screw,
    build_multiconnect_profile,
    build_multiconnect_part,
    build_multiconnect_backer,
    build_multiconnect_delete_tool,
    build_multiconnect_rail,
    build_multiconnect_receiver,
    build_multiconnect_head,
    build_multiconnect_screw,
    build_snap_threads,
    build_snap_body,
    build_expanding_snap,
    build_opengrid_snap,
    _connector_z_base,
    _connector_positions,
    build_open_grid,
    _OG_SNAP_THREADS_PROFILE,
    _scaled_snap_thread_profile,
    _snap_thread_radial_offset,
    _snap_thread_angles,
    _snap_thread_cut_tool,
    _multiconnect_dimple_z_offsets,
    _multiconnect_on_ramp_z_offsets,
)

_EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "examples" / "config.yaml"
_EXAMPLE_MAIN_PATH = Path(__file__).resolve().parents[1] / "examples" / "main.py"
_REFERENCE_ROOT = Path(__file__).resolve().parents[2] / "reference_repos"
_OPENGRID_BASE_PATH = _REFERENCE_ROOT / "opengrid-projects" / "lib" / "opengrid_base.scad"
_SNAP_LIB_PATH = _REFERENCE_ROOT / "opengrid-projects" / "lib" / "opengrid_snap_lib.scad"
_EXPANDING_SNAP_PATH = _REFERENCE_ROOT / "opengrid-projects" / "opengrid_expanding_snap.scad"
_MULTICONNECT_GENERATOR_PATH = _REFERENCE_ROOT / "QuackWorks" / "Modules" / "multiconnectGenerator.scad"

def _bbox_size(config: GridConfig) -> tuple[float, float, float]:
    size = build_open_grid(config).bounding_box().size
    return (float(size.X), float(size.Y), float(size.Z))


def _volume(config: GridConfig) -> float:
    return float(build_open_grid(config).volume)


def _snap_thread_bbox_size(config: SnapThreadConfig) -> tuple[float, float, float]:
    size = build_snap_threads(config).bounding_box().size
    return (float(size.X), float(size.Y), float(size.Z))


def _snap_thread_volume(config: SnapThreadConfig) -> float:
    return float(build_snap_threads(config).volume)


def _snap_body_bbox_size(config: SnapBodyConfig) -> tuple[float, float, float]:
    size = build_snap_body(config).bounding_box().size
    return (float(size.X), float(size.Y), float(size.Z))


def _snap_body_volume(config: SnapBodyConfig) -> float:
    return float(build_snap_body(config).volume)


def _expanding_snap_bbox_size(config: ExpandingSnapConfig) -> tuple[float, float, float]:
    size = build_expanding_snap(config).bounding_box().size
    return (float(size.X), float(size.Y), float(size.Z))


def _expanding_snap_volume(config: ExpandingSnapConfig) -> float:
    return float(build_expanding_snap(config).volume)


def _example_main() -> Any:
    spec = importlib.util.spec_from_file_location("opengrid_example_main", _EXAMPLE_MAIN_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _example_config() -> dict[str, object]:
    with _EXAMPLE_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file)
    assert isinstance(loaded, dict)
    return loaded


def _mapping_section(config: dict[str, object], name: str) -> dict[str, object]:
    section = config[name]
    assert isinstance(section, dict)
    return section
def _reference_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _reference_number(source: str, name: str) -> float:
    match = re.search(rf"\b{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)\b", source)
    assert match is not None, f"Missing numeric reference `{name}`"
    return float(match.group(1))


def _reference_multiconnect_specs(source: str, name: str) -> tuple[float, float, float, float, float, float]:
    match = re.search(rf"\b{re.escape(name)}\s*=\s*\[([^\]]+)\];", source)
    assert match is not None, f"Missing Multiconnect reference spec `{name}`"
    parts = tuple(float(value.strip()) for value in match.group(1).split(","))
    assert len(parts) == 6
    return parts


def _front_side_cut_probe(config: SnapBodyConfig) -> tuple[float, float, float]:
    return (
        0.0,
        -config.height / 2.0 + config.side_cut_depth / 2.0,
        config.thickness - config.side_cut_offset_to_top - config.side_cut_thickness / 2.0,
    )


def _front_bottom_cut_probe(config: SnapBodyConfig) -> tuple[float, float, float]:
    return (
        0.0,
        -config.height / 2.0 + config.bottom_cut_offset_to_edge + config.bottom_cut_thickness / 2.0,
        config.thickness / 2.0,
    )


def _back_bottom_cut_probe(config: SnapBodyConfig) -> tuple[float, float, float]:
    return (
        0.0,
        config.height / 2.0 - config.bottom_cut_offset_to_edge - config.bottom_cut_thickness / 2.0,
        config.thickness / 2.0,
    )



def _assert_points_close(actual: tuple[tuple[float, float], ...], expected: tuple[tuple[float, float], ...]) -> None:
    assert len(actual) == len(expected)
    for actual_point, expected_point in zip(actual, expected):
        assert actual_point == pytest.approx(expected_point)


def _expected_multiconnect_coords(
    radius: float,
    capture_depth: float,
    dovetail_depth: float,
    stem_depth: float,
    offset: float,
) -> tuple[tuple[float, float], ...]:
    offset_bevel = math.sin(math.radians(45.0)) * offset * 2.0 if offset else 0.0
    return (
        (0.0, 0.0),
        (radius + offset, 0.0),
        (radius + offset, capture_depth + offset_bevel),
        (radius - dovetail_depth + offset, dovetail_depth + capture_depth + offset_bevel),
        (radius - dovetail_depth + offset, dovetail_depth + capture_depth + stem_depth + offset),
        (0.0, dovetail_depth + capture_depth + stem_depth + offset),
    )


def _svg_viewbox_size(path: Path) -> tuple[float, float]:
    svg = path.read_text(encoding="utf-8")
    match = re.search(r'viewBox="[-0-9.]+ [-0-9.]+ ([-0-9.]+) ([-0-9.]+)"', svg)
    assert match is not None
    return (float(match.group(1)), float(match.group(2)))


def test_package_root_reexports_public_api() -> None:
    import opengrid_build123
    import opengrid_build123.opengrid as opengrid_module

    assert set(opengrid_build123.__all__) == set(opengrid_module.__all__)
    assert opengrid_build123.build_multiconnect_part is opengrid_module.build_multiconnect_part


def test_example_config_exhaustively_lists_config_dataclass_fields() -> None:
    config = _example_config()

    assert set(_mapping_section(config, "output")) == {"directory"}
    assert set(_mapping_section(config, "viewer")) == {
        "show",
        "port",
        "slot_delete_tool_offset",
        "adjacent_connector_offset",
        "multiconnect_rail_offset",
        "multiconnect_receiver_offset",
        "multiconnect_backer_offset",
        "multiconnect_delete_tool_offset",
        "snap_threads_offset",
        "snap_body_offset",
        "expanding_snap_offset",
        "opengrid_snap_offset",
        "openconnect_screw_offset",
        "multiconnect_screw_offset",
    }

    expected_board_fields = {field.name for field in dataclass_fields(GridConfig)} - {"connector_slot_delete_tool"}
    assert set(_mapping_section(config, "board")) == expected_board_fields
    assert set(_mapping_section(config, "connector_slot_delete_tool")) == {
        field.name for field in dataclass_fields(ConnectorSlotDeleteToolConfig)
    }
    assert set(_mapping_section(config, "adjacent_grid_connector")) == {
        field.name for field in dataclass_fields(AdjacentGridConnectorConfig)
    } - {"slot_delete_tool"}
    assert set(_mapping_section(config, "multiconnect")) == {
        field.name for field in dataclass_fields(MulticonnectConfig)
    }
    assert set(_mapping_section(config, "snap_threads")) == {
        field.name for field in dataclass_fields(SnapThreadConfig)
    }
    assert set(_mapping_section(config, "snap_body")) == {
        field.name for field in dataclass_fields(SnapBodyConfig)
    }
    assert set(_mapping_section(config, "expanding_snap")) == {
        field.name for field in dataclass_fields(ExpandingSnapConfig)
    } - {"snap_body", "threads"}
    assert set(_mapping_section(config, "text_engraving")) == {
        field.name for field in dataclass_fields(TextEngravingConfig)
    }
    assert set(_mapping_section(config, "openconnect_head")) == {
        field.name for field in dataclass_fields(OpenConnectHeadConfig)
    }
    assert set(_mapping_section(config, "connector_slot")) == {
        field.name for field in dataclass_fields(ConnectorSlotConfig)
    }
    assert set(_mapping_section(config, "multiconnect_head")) == {
        field.name for field in dataclass_fields(MulticonnectHeadConfig)
    }
    assert set(_mapping_section(config, "opengrid_snap")) == {
        field.name for field in dataclass_fields(OpenGridSnapConfig)
    } - {"snap_body", "threads", "expanding_snap", "openconnect_head", "multiconnect_head", "text"}
    assert set(_mapping_section(config, "openconnect_screw")) == {
        field.name for field in dataclass_fields(OpenConnectScrewConfig)
    } - {"threads", "head", "connector_slot", "text"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"height": 0.0},
        {"diameter": 0.0},
        {"pitch": 0.0},
        {"clearance": -0.1},
        {"top_bevel": -0.1},
        {"bottom_bevel_standard": -0.1},
        {"bottom_bevel_lite": -0.1},
    ],
)
def test_snap_thread_config_validation_rejects_invalid_dimensions(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        SnapThreadConfig(**kwargs).validate()


def test_snap_thread_source_profile_and_effective_diameter_match_reference() -> None:
    config = SnapThreadConfig(diameter=16.0, clearance=0.5)

    _assert_points_close(
        _OG_SNAP_THREADS_PROFILE,
        (
            (-1.25 / 3.0, -1.0 / 3.0),
            (-0.25 / 3.0, 0.0),
            (0.25 / 3.0, 0.0),
            (1.25 / 3.0, -1.0 / 3.0),
        ),
    )
    assert config.effective_diameter == pytest.approx(16.5)


@pytest.mark.parametrize(
    ("height", "expected_xy"),
    [
        (6.8, (16.5, 16.5)),
        (4.0, (16.5, 16.5)),
        (3.4, (16.5, 16.2714285714)),
    ],
)
def test_snap_thread_envelopes_match_source_heights(height: float, expected_xy: tuple[float, float]) -> None:
    assert _snap_thread_bbox_size(SnapThreadConfig(height=height)) == pytest.approx(
        (*expected_xy, height),
        abs=0.02,
    )


def test_snap_thread_variants_share_envelope_but_not_volume() -> None:
    basic = SnapThreadConfig(thread_type=ThreadType.BASIC)
    blunt = SnapThreadConfig(thread_type=ThreadType.BLUNT)

    assert _snap_thread_bbox_size(basic) == pytest.approx(_snap_thread_bbox_size(blunt), abs=0.02)
    assert _snap_thread_volume(basic) != pytest.approx(_snap_thread_volume(blunt))


def test_snap_thread_clearance_changes_diameter_and_volume() -> None:
    tight = SnapThreadConfig(clearance=0.0)
    loose = SnapThreadConfig(clearance=0.5)

    assert _snap_thread_bbox_size(tight)[:2] == pytest.approx((16.0, 16.0), abs=0.02)
    assert _snap_thread_bbox_size(loose)[:2] == pytest.approx((16.5, 16.5), abs=0.02)
    assert _snap_thread_volume(loose) > _snap_thread_volume(tight)


def test_snap_thread_pitch_changes_geometry_without_changing_nominal_envelope() -> None:
    fine = SnapThreadConfig(pitch=2.0)
    coarse = SnapThreadConfig(pitch=3.0)

    assert _snap_thread_bbox_size(fine) == pytest.approx(_snap_thread_bbox_size(coarse), abs=0.02)
    assert _snap_thread_volume(fine) != pytest.approx(_snap_thread_volume(coarse))


def test_snap_thread_profile_has_no_cardinal_axis_spikes() -> None:
    config = SnapThreadConfig()
    profile = _scaled_snap_thread_profile(config.pitch)
    z = config.height / 2.0
    for angle in (0.0, 90.0, 180.0, 270.0):
        before = _snap_thread_radial_offset(config, profile, angle - 0.1, z)
        at_axis = _snap_thread_radial_offset(config, profile, angle, z)
        after = _snap_thread_radial_offset(config, profile, angle + 0.1, z)
        assert at_axis == pytest.approx((before + after) / 2.0, abs=0.01)


def test_snap_thread_faceting_uses_uniform_angles_without_cardinal_spikes() -> None:
    angles = _snap_thread_angles(53.5)
    deltas = [right - left for left, right in zip(angles, angles[1:])]

    assert len(angles) == 144
    assert deltas == pytest.approx([360.0 / 144.0] * 143)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 0.0},
        {"height": 0.0},
        {"thickness": 0.0},
        {"corner_chamfer": -0.1},
        {"cut_width_inset": -0.1},
        {"basic_nub_depth": -0.1},
        {"notch_width": -0.1},
        {"corner_chamfer": 12.4},
        {"cut_width_inset": 12.4},
        {"basic_nub_width_inset": 12.4},
    ],
)
def test_snap_body_config_validation_rejects_invalid_dimensions(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        SnapBodyConfig(**kwargs).validate()


def test_snap_body_source_defaults_match_reference_constants() -> None:
    config = SnapBodyConfig()
    base_source = _reference_source(_OPENGRID_BASE_PATH)
    snap_source = _reference_source(_SNAP_LIB_PATH)
    corner_outer_diagonal = 2.7 + 1.0 / math.sqrt(2.0)

    assert config.width == pytest.approx(_reference_number(base_source, "OG_SNAP_WIDTH"))
    assert config.height == pytest.approx(_reference_number(base_source, "OG_SNAP_WIDTH"))
    assert config.thickness == pytest.approx(_reference_number(base_source, "OG_STANDARD_THICKNESS"))
    assert config.corner_chamfer == pytest.approx(corner_outer_diagonal * math.sqrt(2.0))
    assert config.cut_width_inset == pytest.approx(_reference_number(snap_source, "cut_width_inset"))
    assert config.directional_nub_depth == pytest.approx(_reference_number(snap_source, "directional_nub_depth"))
    assert config.notch_gap_inset == pytest.approx(_reference_number(snap_source, "notch_gap_inset"))
def test_snap_body_cut_rules_match_reference_source_behavior() -> None:

    without_notch_config = SnapBodyConfig(enable_uninstall_notch=False)
    with_notch = build_snap_body(SnapBodyConfig(enable_uninstall_notch=True))
    without_notch = build_snap_body(without_notch_config)

    assert not with_notch.is_inside(_front_side_cut_probe(without_notch_config))
    assert without_notch.is_inside(_front_side_cut_probe(without_notch_config))


def test_snap_body_directional_back_bottom_cut_matches_reference_source_behavior() -> None:

    directional_config = SnapBodyConfig(body_shape=SnapBodyShape.DIRECTIONAL)
    symmetric_config = SnapBodyConfig(body_shape=SnapBodyShape.SYMMETRIC)
    directional = build_snap_body(directional_config)
    symmetric = build_snap_body(symmetric_config)

    assert directional.is_inside(_back_bottom_cut_probe(directional_config))
    assert not symmetric.is_inside(_back_bottom_cut_probe(symmetric_config))



@pytest.mark.parametrize(
    ("thickness", "expected_z"),
    [
        (6.8, 6.8),
        (4.0, 4.0),
        (3.4, 3.4),
    ],
)
def test_snap_body_envelope_preserves_source_width_and_thickness(thickness: float, expected_z: float) -> None:
    size = _snap_body_bbox_size(SnapBodyConfig(thickness=thickness))

    assert size[0] == pytest.approx(25.6, abs=0.02)
    assert size[1] == pytest.approx(26.0, abs=0.02)
    assert size[2] == pytest.approx(expected_z, abs=0.02)


def test_snap_body_directional_and_symmetric_variants_share_thickness_but_differ() -> None:
    directional = SnapBodyConfig(body_shape=SnapBodyShape.DIRECTIONAL)
    symmetric = SnapBodyConfig(body_shape=SnapBodyShape.SYMMETRIC)

    assert _snap_body_bbox_size(directional)[2] == pytest.approx(_snap_body_bbox_size(symmetric)[2])
    assert _snap_body_volume(directional) != pytest.approx(_snap_body_volume(symmetric))


def test_snap_body_feature_toggles_change_volume_without_moving_anchor() -> None:
    full = SnapBodyConfig()
    no_nubs = SnapBodyConfig(enable_nubs=False)
    no_cuts = SnapBodyConfig(enable_cuts=False)
    no_notch = SnapBodyConfig(enable_uninstall_notch=False)

    assert _snap_body_volume(no_nubs) < _snap_body_volume(full)
    assert _snap_body_volume(no_cuts) > _snap_body_volume(full)
    assert _snap_body_volume(no_notch) > _snap_body_volume(full)
    assert _snap_body_bbox_size(no_cuts)[2] == pytest.approx(full.thickness)


def test_snap_body_bottom_cut_offset_leaves_top_skin() -> None:
    flush_cut = SnapBodyConfig(
        enable_corners=False,
        enable_nubs=False,
        enable_uninstall_notch=False,
        enable_directional_slants=False,
        bottom_cut_offset_to_top=0.0,
    )
    recessed_cut = SnapBodyConfig(
        enable_corners=False,
        enable_nubs=False,
        enable_uninstall_notch=False,
        enable_directional_slants=False,
        bottom_cut_offset_to_top=1.0,
    )

    assert _snap_body_bbox_size(recessed_cut) == pytest.approx(_snap_body_bbox_size(flush_cut))
    assert _snap_body_volume(recessed_cut) > _snap_body_volume(flush_cut)


def test_expanding_thread_cut_tool_uses_coarse_helical_thread_profile() -> None:
    config = ExpandingSnapConfig()
    tool = _snap_thread_cut_tool(config, config.snap_body.thickness)
    root_volume = math.pi * (config.threads.effective_diameter / 2.0 - config.threads.pitch / 3.0) ** 2 * config.snap_body.thickness

    assert tool.children == ()
    assert tool.bounding_box().size.X == pytest.approx(config.threads.effective_diameter, abs=0.2)
    assert tool.volume > root_volume


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expand_distance_standard": -0.1},
        {"expand_distance_lite": -0.1},
        {"expand_entry_height_blunt": -0.1},
        {"spring_thickness": -0.1},
        {"spring_gap": 0.0},
        {"threads": SnapThreadConfig(diameter=24.8, clearance=0.1)},
    ],
)
def test_expanding_snap_config_validation_rejects_invalid_dimensions(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        ExpandingSnapConfig(**kwargs).validate()


def test_expanding_snap_source_defaults_match_reference_constants() -> None:
    config = ExpandingSnapConfig()
    expanding_source = _reference_source(_EXPANDING_SNAP_PATH)
    snap_source = _reference_source(_SNAP_LIB_PATH)

    assert config.expand_distance_standard == pytest.approx(_reference_number(expanding_source, "expand_distance_standard"))
    assert config.expand_distance_lite == pytest.approx(_reference_number(expanding_source, "expand_distance_lite"))
    assert config.expand_entry_height_blunt == pytest.approx(1.0)
    assert config.expand_end_height_standard == pytest.approx(2.0)
    assert config.expand_split_angle == pytest.approx(_reference_number(expanding_source, "expand_split_angle"))
    assert config.spring_thickness == pytest.approx(_reference_number(snap_source, "spring_thickness"))
    assert config.spring_gap == pytest.approx(_reference_number(snap_source, "spring_gap"))
def test_expanding_snap_omits_source_side_and_bottom_cuts() -> None:

    snap_body = SnapBodyConfig(enable_uninstall_notch=False)
    expanding = build_expanding_snap(ExpandingSnapConfig(snap_body=snap_body))

    assert expanding.is_inside(_front_side_cut_probe(snap_body))
    assert expanding.is_inside(_front_bottom_cut_probe(snap_body))



def test_expanding_snap_preserves_body_envelope_and_removes_threaded_core() -> None:
    snap_body = SnapBodyConfig()
    expanding = ExpandingSnapConfig(snap_body=snap_body)

    assert _expanding_snap_bbox_size(expanding) == pytest.approx(_snap_body_bbox_size(snap_body), abs=0.02)
    assert _expanding_snap_volume(expanding) < _snap_body_volume(snap_body)


def test_expanding_snap_distance_and_spring_gap_change_geometry() -> None:
    collapsed = ExpandingSnapConfig(expand_distance_standard=0.0)
    expanded = ExpandingSnapConfig(expand_distance_standard=1.0)
    wide_gap = ExpandingSnapConfig(spring_gap=0.8)

    assert _expanding_snap_volume(expanded) < _expanding_snap_volume(collapsed)
    assert _expanding_snap_volume(wide_gap) < _expanding_snap_volume(expanded)


@pytest.mark.parametrize(
    ("kind", "expected_z"),
    [
        (BoardKind.FULL, 6.8),
        (BoardKind.LITE, 4.0),
        (BoardKind.HEAVY, 13.8),
    ],
)
def test_single_board_dimensions_match_openscad_parameters(kind: BoardKind, expected_z: float) -> None:
    config = GridConfig(
        kind=kind,
        board_width=2,
        board_height=3,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
    )

    assert _bbox_size(config) == pytest.approx((56.0, 84.0, expected_z))


def test_lite_adhesive_base_adds_configured_backing_thickness() -> None:
    no_base = GridConfig(kind=BoardKind.LITE, chamfers=ChamferMode.NONE, connector_holes=False, screw_mounting=ScrewMounting.NONE)
    with_base = GridConfig(
        kind=BoardKind.LITE,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
        add_adhesive_base=True,
        adhesive_base_thickness=0.6,
    )

    assert _bbox_size(with_base)[2] == pytest.approx(_bbox_size(no_base)[2] + 0.6)
    assert _volume(with_base) > _volume(no_base)


def test_subtractive_options_remove_material_without_changing_outer_size() -> None:
    base = GridConfig(kind=BoardKind.FULL, board_width=3, board_height=3, chamfers=ChamferMode.NONE, connector_holes=False, screw_mounting=ScrewMounting.NONE)
    detailed = GridConfig(kind=BoardKind.FULL, board_width=3, board_height=3, chamfers=ChamferMode.CORNERS, connector_holes=True, screw_mounting=ScrewMounting.CORNERS)

    assert _bbox_size(detailed) == pytest.approx(_bbox_size(base))
    assert _volume(detailed) < _volume(base)

def test_corner_chamfers_cut_through_full_tile_height() -> None:
    plain = build_open_grid(
        GridConfig(
            kind=BoardKind.FULL,
            board_width=1,
            board_height=1,
            chamfers=ChamferMode.NONE,
            connector_holes=False,
            screw_mounting=ScrewMounting.NONE,
        )
    )
    chamfered = build_open_grid(
        GridConfig(
            kind=BoardKind.FULL,
            board_width=1,
            board_height=1,
            chamfers=ChamferMode.CORNERS,
            connector_holes=False,
            screw_mounting=ScrewMounting.NONE,
        )
    )

    for z in (0.4, 3.4, 6.4):
        assert plain.is_inside((-13.0, -13.0, z))
        assert not chamfered.is_inside((-13.0, -13.0, z))
        assert chamfered.is_inside((-9.5, -13.0, z))

def test_connector_slot_delete_tool_matches_reference_envelope() -> None:
    tool = build_connector_slot_delete_tool()
    size = tool.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((5.1, 5.2, 2.4))
    assert tool.volume < 5.1 * 5.2 * 2.4
    assert tool.is_inside((0.5, 0.0, 1.2))
    assert not tool.is_inside((0.1, 2.55, 1.2))


def test_adjacent_grid_connector_is_double_sided_and_fits_slot_tool() -> None:
    slot_config = ConnectorSlotDeleteToolConfig()
    connector_config = AdjacentGridConnectorConfig(slot_delete_tool=slot_config, fit_clearance=0.1)
    slot_size = build_connector_slot_delete_tool(slot_config).bounding_box().size
    connector = build_adjacent_grid_connector(connector_config)
    connector_size = connector.bounding_box().size

    assert connector_size.X == pytest.approx((float(slot_size.X) - 0.2) * 2.0)
    assert connector_size.Y < slot_size.Y
    assert connector_size.Z < slot_size.Z
    assert connector.volume > build_connector_slot_delete_tool(slot_config).volume


def test_adjacent_grid_connector_fit_clearance_changes_envelope() -> None:
    tight = build_adjacent_grid_connector(AdjacentGridConnectorConfig(fit_clearance=0.0))
    loose = build_adjacent_grid_connector(AdjacentGridConnectorConfig(fit_clearance=0.2))

    assert loose.bounding_box().size.X < tight.bounding_box().size.X
    assert loose.bounding_box().size.Y < tight.bounding_box().size.Y
    assert loose.bounding_box().size.Z < tight.bounding_box().size.Z
    assert loose.volume < tight.volume


@pytest.mark.parametrize(
    ("profile", "radius", "capture_depth", "dovetail_depth", "stem_depth", "receiver_offset"),
    [
        (MulticonnectProfile.STANDARD, 10.0, 1.0, 2.5, 0.5, 0.15),
        (MulticonnectProfile.JR, 5.0, 0.6, 1.2, 0.4, 0.16),
        (MulticonnectProfile.MINI, 3.2, 1.0, 1.2, 0.4, 0.16),
        (MulticonnectProfile.MULTIPOINT_BETA, 7.9, 0.4, 2.2, 0.4, 0.15),
    ],
)
def test_multiconnect_profile_presets_match_source_dimensions(
    profile: MulticonnectProfile,
    radius: float,
    capture_depth: float,
    dovetail_depth: float,
    stem_depth: float,
    receiver_offset: float,
) -> None:
    male = build_multiconnect_profile(
        MulticonnectConfig(profile=profile, part_kind=MulticonnectPartKind.CONNECTOR_RAIL)
    )
    receiver = build_multiconnect_profile(
        MulticonnectConfig(profile=profile, part_kind=MulticonnectPartKind.RECEIVER_OPEN_ENDED)
    )

    _assert_points_close(male, _expected_multiconnect_coords(radius, capture_depth, dovetail_depth, stem_depth, 0.0))
    _assert_points_close(
        receiver,
        _expected_multiconnect_coords(radius, capture_depth, dovetail_depth, stem_depth, receiver_offset),
    )
def test_multiconnect_profiles_match_reference_generator_specs() -> None:
    source = _reference_source(_MULTICONNECT_GENERATOR_PATH)
    references = (
        (MulticonnectProfile.STANDARD, "standardSpecs"),
        (MulticonnectProfile.JR, "jrSpecs"),
        (MulticonnectProfile.MINI, "miniSpecs"),
        (MulticonnectProfile.MULTIPOINT_BETA, "multipointBeta"),
    )

    for profile, source_name in references:
        radius, capture_depth, dovetail_depth, stem_depth, receiver_offset, _dimple_radius = (
            _reference_multiconnect_specs(source, source_name)
        )
        male = build_multiconnect_profile(
            MulticonnectConfig(profile=profile, part_kind=MulticonnectPartKind.CONNECTOR_RAIL)
        )
        receiver = build_multiconnect_profile(
            MulticonnectConfig(profile=profile, part_kind=MulticonnectPartKind.RECEIVER_OPEN_ENDED)
        )

        _assert_points_close(male, _expected_multiconnect_coords(radius, capture_depth, dovetail_depth, stem_depth, 0.0))
        _assert_points_close(
            receiver,
            _expected_multiconnect_coords(radius, capture_depth, dovetail_depth, stem_depth, receiver_offset),
        )




@pytest.mark.parametrize(
    "part_kind",
    [
        MulticonnectPartKind.CONNECTOR_ROUND,
        MulticonnectPartKind.CONNECTOR_RAIL,
        MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_ROUND,
        MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_RAIL,
    ],
)
def test_multiconnect_male_part_profiles_do_not_apply_receiver_offset(part_kind: MulticonnectPartKind) -> None:
    assert build_multiconnect_profile(MulticonnectConfig(part_kind=part_kind)) == build_multiconnect_profile(
        MulticonnectConfig(part_kind=MulticonnectPartKind.CONNECTOR_RAIL)
    )


@pytest.mark.parametrize(
    "part_kind",
    [
        MulticonnectPartKind.CONNECTOR_RAIL_DELETE_TOOL,
        MulticonnectPartKind.RECEIVER_OPEN_ENDED,
        MulticonnectPartKind.RECEIVER_PASSTHROUGH,
        MulticonnectPartKind.BACKER_OPEN_ENDED,
        MulticonnectPartKind.BACKER_PASSTHROUGH,
    ],
)
def test_multiconnect_receiver_delete_and_backer_profiles_apply_offset(part_kind: MulticonnectPartKind) -> None:
    expected = _expected_multiconnect_coords(10.0, 1.0, 2.5, 0.5, 0.15)
    _assert_points_close(build_multiconnect_profile(MulticonnectConfig(part_kind=part_kind)), expected)


def test_multiconnect_custom_profile_uses_custom_dimensions() -> None:
    config = MulticonnectConfig(
        profile=MulticonnectProfile.CUSTOM,
        part_kind=MulticonnectPartKind.RECEIVER_PASSTHROUGH,
        radius=6.0,
        capture_depth=0.7,
        dovetail_depth=1.4,
        stem_depth=0.3,
        receiver_offset=0.2,
    )

    _assert_points_close(build_multiconnect_profile(config), _expected_multiconnect_coords(6.0, 0.7, 1.4, 0.3, 0.2))


def test_multiconnect_rail_uses_profile_width_depth_and_rounded_length() -> None:
    config = MulticonnectConfig(length=50.0, rounding=MulticonnectRounding.BOTH_SIDES)
    rail = build_multiconnect_rail(config)
    size = rail.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((20.0, 4.0, 70.0), abs=0.05)


@pytest.mark.parametrize("part_kind", tuple(MulticonnectPartKind))
def test_build_multiconnect_part_dispatches_every_public_part_kind(part_kind: MulticonnectPartKind) -> None:
    config = MulticonnectConfig(part_kind=part_kind, length=28.0, width=56.0, rounding=MulticonnectRounding.NONE)
    part = build_multiconnect_part(config)
    size = part.bounding_box().size

    assert min(float(size.X), float(size.Y), float(size.Z)) > 0.0
    assert part.volume > 0.0


def test_multiconnect_round_and_double_sided_parts_follow_source_composition() -> None:
    round_part = build_multiconnect_part(
        MulticonnectConfig(part_kind=MulticonnectPartKind.CONNECTOR_ROUND, dimples_enabled=False)
    )
    double_round = build_multiconnect_part(
        MulticonnectConfig(part_kind=MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_ROUND, dimples_enabled=False)
    )
    rail = build_multiconnect_part(
        MulticonnectConfig(part_kind=MulticonnectPartKind.CONNECTOR_RAIL, length=28.0, dimples_enabled=False)
    )
    double_rail = build_multiconnect_part(
        MulticonnectConfig(part_kind=MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_RAIL, length=28.0, dimples_enabled=False)
    )

    assert double_round.bounding_box().size.Y > round_part.bounding_box().size.Y
    assert double_round.volume > round_part.volume
    assert double_rail.bounding_box().size.Y > rail.bounding_box().size.Y
    assert double_rail.volume > rail.volume


def test_multiconnect_receiver_contains_single_offset_slot() -> None:
    config = MulticonnectConfig(length=40.0, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    receiver = build_multiconnect_receiver(config)
    size = receiver.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((25.3, 6.15, 40.0), abs=0.05)
    assert receiver.volume < 25.3 * 6.15 * 40.0
def test_multiconnect_receiver_and_backer_envelopes_match_reference_generator_blocks() -> None:
    source = _reference_source(_MULTICONNECT_GENERATOR_PATH)

    radius, capture_depth, dovetail_depth, stem_depth, receiver_offset, _dimple_radius = (
        _reference_multiconnect_specs(source, "standardSpecs")
    )
    receiver_profile = _expected_multiconnect_coords(
        radius,
        capture_depth,
        dovetail_depth,
        stem_depth,
        receiver_offset,
    )
    slot_width = max(x for x, _ in receiver_profile) * 2.0
    slot_depth = max(y for _, y in receiver_profile)
    side_wall = _reference_number(source, "Receiver_Side_Wall_Thickness")
    back_thickness = _reference_number(source, "Receiver_Back_Thickness")
    length = 40.0
    width = 75.0

    receiver = build_multiconnect_receiver(
        MulticonnectConfig(length=length, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    )
    backer = build_multiconnect_backer(
        MulticonnectConfig(width=width, length=length, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    )

    receiver_size = receiver.bounding_box().size
    backer_size = backer.bounding_box().size
    assert (float(receiver_size.X), float(receiver_size.Y), float(receiver_size.Z)) == pytest.approx(
        (slot_width + side_wall * 2.0, slot_depth + back_thickness, length),
        abs=0.05,
    )
    assert (float(backer_size.X), float(backer_size.Y), float(backer_size.Z)) == pytest.approx(
        (width, slot_depth + back_thickness, length),
        abs=0.05,
    )



def test_multiconnect_backer_slot_count_uses_opengrid_spacing() -> None:
    narrow = build_multiconnect_backer(
        MulticonnectConfig(width=20.0, length=30.0, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    )
    two_slots = build_multiconnect_backer(
        MulticonnectConfig(width=56.0, length=30.0, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    )

    assert float(narrow.bounding_box().size.X) == pytest.approx(28.0)
    assert float(two_slots.bounding_box().size.X) == pytest.approx(56.0)
    assert two_slots.volume == pytest.approx(narrow.volume * 2.0)


def test_multiconnect_dimple_and_on_ramp_toggles_match_source_envelopes() -> None:
    with_features = MulticonnectConfig(length=56.0)
    no_dimples = MulticonnectConfig(length=56.0, dimples_enabled=False)
    no_ramps = MulticonnectConfig(length=56.0, on_ramps_enabled=False)

    rail = build_multiconnect_rail(with_features)
    rail_without_dimples = build_multiconnect_rail(no_dimples)
    delete_tool = build_multiconnect_delete_tool(with_features)
    delete_tool_without_dimples = build_multiconnect_delete_tool(no_dimples)
    delete_tool_without_ramps = build_multiconnect_delete_tool(no_ramps)

    assert rail.bounding_box().size == pytest.approx(rail_without_dimples.bounding_box().size)
    assert rail.volume < rail_without_dimples.volume
    assert delete_tool.bounding_box().size == pytest.approx(delete_tool_without_dimples.bounding_box().size)
    assert delete_tool.volume < delete_tool_without_dimples.volume
    assert float(delete_tool.bounding_box().size.X) > float(delete_tool_without_ramps.bounding_box().size.X)
    assert delete_tool.volume > delete_tool_without_ramps.volume


def test_multiconnect_dimple_and_on_ramp_positions_follow_reference_formulas() -> None:
    rail_config = MulticonnectConfig(length=50.0, grid_size=28.0)
    delete_tool_config = replace(rail_config, part_kind=MulticonnectPartKind.CONNECTOR_RAIL_DELETE_TOOL)
    passthrough_config = replace(rail_config, part_kind=MulticonnectPartKind.RECEIVER_PASSTHROUGH)
    open_ended_config = replace(rail_config, part_kind=MulticonnectPartKind.RECEIVER_OPEN_ENDED)

    assert _multiconnect_dimple_z_offsets(rail_config.length, rail_config.grid_size) == pytest.approx((-28.0, 0.0, 28.0))
    assert _multiconnect_on_ramp_z_offsets(delete_tool_config) == pytest.approx((28.0,))
    assert _multiconnect_on_ramp_z_offsets(passthrough_config) == pytest.approx((28.0,))
    assert _multiconnect_on_ramp_z_offsets(open_ended_config) == ()


def test_multiconnect_delete_tool_on_ramp_envelope_matches_reference_render() -> None:
    delete_tool = build_multiconnect_delete_tool(MulticonnectConfig(length=50.0, grid_size=28.0))
    size = delete_tool.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((23.3, 4.15, 70.3), abs=0.06)

def test_output_dir_rejects_blank_directory() -> None:
    example_main = _example_main()

    with pytest.raises(SystemExit):
        example_main._output_dir({"output": {"directory": "   "}})


def test_variant_verification_defines_every_public_enum_variant() -> None:
    example_main = _example_main()
    board_config = GridConfig(
        board_width=1,
        board_height=1,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
    )
    multiconnect_config = MulticonnectConfig(length=12.0, width=28.0, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    snap_threads = SnapThreadConfig(height=4.0)
    snap_body = SnapBodyConfig(thickness=4.0)
    expanding = ExpandingSnapConfig(snap_body=snap_body, threads=snap_threads)

    board_variants = {variant for variant, _shape, _views in example_main._board_verification_variants(board_config)}
    assert board_variants >= {
        example_main._slug(kind.value) for kind in BoardKind
    } | {f"fill_{example_main._slug(mode.value)}" for mode in FillSpaceMode} | {
        "connector_side_right",
        "connector_side_left",
        "connector_side_top",
        "connector_side_bottom",
        "stacking_interface_layer",
        "stacking_ironing",
    }
    assert {variant for variant, _shape, _views in example_main._multiconnect_rail_verification_variants(multiconnect_config)} >= {
        f"profile_{example_main._slug(profile.value)}" for profile in MulticonnectProfile
    } | {f"rounding_{example_main._slug(rounding.value)}" for rounding in MulticonnectRounding}
    assert {variant for variant, _shape, _views in example_main._multiconnect_part_verification_variants(multiconnect_config)} == {
        f"part_{example_main._slug(part_kind.value)}" for part_kind in MulticonnectPartKind
    }
    assert {variant for variant, _shape, _views in example_main._snap_thread_verification_variants(snap_threads)} >= {
        f"type_{example_main._slug(thread_type.value)}" for thread_type in ThreadType
    }
    assert {variant for variant, _shape, _views in example_main._snap_body_verification_variants(snap_body)} >= {
        f"shape_{example_main._slug(shape.value)}" for shape in SnapBodyShape
    }
    assert {variant for variant, _shape, _views in example_main._expanding_snap_verification_variants(expanding)} >= {
        f"threads_{example_main._slug(thread_type.value)}" for thread_type in ThreadType
    } | {f"shape_{example_main._slug(shape.value)}" for shape in SnapBodyShape}
    assert {variant for variant, _shape, _views in example_main._opengrid_snap_verification_variants(OpenGridSnapConfig(snap_body=snap_body, threads=snap_threads, expanding_snap=expanding))} == {
        f"kind_{example_main._slug(kind.value)}" for kind in OpenGridSnapKind
    }
    assert {variant for variant, _shape, _views in example_main._multiconnect_head_verification_variants(MulticonnectHeadConfig(), ConnectorSlotConfig())} == {
        "top_coin_slot",
        "top_dimple",
        "top_none",
    }

def test_prepare_output_dir_removes_stale_output_tree(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    stale_file = output_dir / "stale.txt"
    output_dir.mkdir()
    stale_file.write_text("stale", encoding="utf-8")

    example_main = _example_main()
    example_main._prepare_output_dir(output_dir)

    assert output_dir.is_dir()
    assert not stale_file.exists()


def test_output_verification_exports_shape_svgs_into_named_subdirectories(tmp_path: Path) -> None:
    rail = build_multiconnect_rail(MulticonnectConfig(length=28.0, rounding=MulticonnectRounding.NONE))
    multiconnect_config = MulticonnectConfig(length=28.0, width=56.0, rounding=MulticonnectRounding.NONE)

    example_main = _example_main()
    paths = example_main._export_output_verification(
        grid=rail,
        slot_delete_tool=rail,
        adjacent_connector=rail,
        multiconnect_rail=rail,
        multiconnect_receiver=build_multiconnect_receiver(multiconnect_config),
        multiconnect_backer=build_multiconnect_backer(multiconnect_config),
        multiconnect_delete_tool=build_multiconnect_delete_tool(multiconnect_config),
        snap_threads=rail,
        snap_body=rail,
        expanding_snap=rail,
        openconnect_head=rail,
        multiconnect_head=build_multiconnect_head(MulticonnectHeadConfig()),
        opengrid_snap=rail,
        openconnect_screw=rail,
        multiconnect_screw=build_multiconnect_screw(MulticonnectScrewConfig(threads=SnapThreadConfig(height=4.0))),
        verification_dir=tmp_path,
    )

    expected_components = (
        "opengrid_board",
        "adjacent_grid_connector_slot_delete_tool",
        "adjacent_grid_connector",
        "multiconnect_rail",
        "multiconnect_receiver",
        "multiconnect_backer",
        "multiconnect_delete_tool",
        "snap_threads",
        "snap_body",
        "expanding_snap",
        "openconnect_head",
        "multiconnect_head",
        "opengrid_snap",
        "openconnect_screw",
        "multiconnect_screw",
    )
    relative_paths = tuple(path.relative_to(tmp_path) for path in paths)

    assert {path.parts[0] for path in relative_paths} == set(expected_components)
    for component in expected_components:
        component_paths = [path for path in relative_paths if path.parts[0] == component]
        svg_paths = [path for path in component_paths if path.suffix == ".svg"]
        assert len(svg_paths) >= 3
        assert Path(component, "gallery.html") in component_paths
        assert all(path.name.startswith(component) for path in svg_paths)
    for path in paths:
        assert path.stat().st_size > 0
        if path.suffix == ".svg":
            svg = path.read_text(encoding="utf-8")
            assert 'stroke-width="0.01"' not in svg
            assert 'stroke-width="0.08"' in svg
    assert 'id="hidden"' not in (tmp_path / "snap_body" / "snap_body_top.svg").read_text(encoding="utf-8")
    gallery = (tmp_path / "multiconnect_rail" / "gallery.html").read_text(encoding="utf-8")
    assert "multiconnect_rail_back.svg" in gallery

    index_path = example_main._write_verification_index("verification", paths, tmp_path / "index.html")
    index = index_path.read_text(encoding="utf-8")
    assert "multiconnect_rail/gallery.html" in index
    assert "snap_body/gallery.html" in index


def test_svg_projection_viewbox_matches_projected_shape_extents(tmp_path: Path) -> None:
    example_main = _example_main()
    rail = build_multiconnect_rail(MulticonnectConfig(length=28.0, rounding=MulticonnectRounding.NONE))
    paths = example_main._export_shape_verification(
        rail,
        tmp_path / "multiconnect_rail",
        title="rail",
        gallery_filename="gallery.html",
        views=example_main._MULTICONNECT_RAIL_VERIFICATION_VIEWS,
    )
    size = rail.bounding_box().size
    viewboxes = {path.name: _svg_viewbox_size(path) for path in paths if path.suffix == ".svg"}

    top_width, top_height = viewboxes["multiconnect_rail_top.svg"]
    back_width, back_height = viewboxes["multiconnect_rail_back.svg"]
    assert top_width == pytest.approx(float(size.X), abs=1.0)
    assert top_height == pytest.approx(float(size.Y), abs=2.0)
    assert back_width == pytest.approx(float(size.X), abs=1.0)
    assert back_height == pytest.approx(float(size.Z), abs=2.0)


def test_connector_slots_are_at_source_z_centers() -> None:
    centers = {
        BoardKind.FULL: _connector_z_base(6.8, BoardKind.FULL) + 2.4 / 2.0,
        BoardKind.LITE: _connector_z_base(4.0, BoardKind.LITE) + 2.4 / 2.0,
        BoardKind.HEAVY: _connector_z_base(13.8, BoardKind.HEAVY) + 2.4 / 2.0,
    }

    assert centers[BoardKind.FULL] == pytest.approx(6.8 / 2.0)
    assert centers[BoardKind.LITE] == pytest.approx(4.0 - 2.4 / 2.0 - 1.0)
    assert centers[BoardKind.HEAVY] == pytest.approx(13.8 / 2.0)


def test_connector_holes_remove_material_without_changing_board_envelope() -> None:
    base = GridConfig(
        kind=BoardKind.FULL,
        board_width=2,
        board_height=2,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
    )
    cut = GridConfig(
        kind=BoardKind.FULL,
        board_width=2,
        board_height=2,
        chamfers=ChamferMode.NONE,
        connector_holes=True,
        screw_mounting=ScrewMounting.NONE,
    )

    assert _bbox_size(cut) == pytest.approx(_bbox_size(base))
    assert _volume(cut) < _volume(base)


@pytest.mark.parametrize(
    ("kind", "z"),
    [
        (BoardKind.FULL, 3.4),
        (BoardKind.LITE, 1.8),
        (BoardKind.HEAVY, 6.9),
    ],
)
def test_connector_cutouts_match_slot_delete_tool_depth(kind: BoardKind, z: float) -> None:
    config = GridConfig(
        kind=kind,
        board_width=2,
        board_height=2,
        chamfers=ChamferMode.NONE,
        connector_holes=True,
        screw_mounting=ScrewMounting.NONE,
    )
    board = build_open_grid(config)
    edge = config.board_width * config.tile_size / 2.0
    slot_depth = float(
        build_connector_slot_delete_tool(config.connector_slot_delete_tool).bounding_box().size.X
    )
    removed_offset = edge - slot_depth + 0.2
    retained_offset = edge - slot_depth - 0.2

    assert not board.is_inside((removed_offset, 0.0, z))
    assert board.is_inside((retained_offset, 0.0, z))
    assert not board.is_inside((-removed_offset, 0.0, z))
    assert board.is_inside((-retained_offset, 0.0, z))
    assert not board.is_inside((0.0, removed_offset, z))
    assert board.is_inside((0.0, retained_offset, z))
    assert not board.is_inside((0.0, -removed_offset, z))
    assert board.is_inside((0.0, -retained_offset, z))


def test_connector_slot_delete_tool_height_config_changes_removed_material() -> None:
    default_cut = GridConfig(
        kind=BoardKind.FULL,
        board_width=2,
        board_height=2,
        chamfers=ChamferMode.NONE,
        connector_holes=True,
        screw_mounting=ScrewMounting.NONE,
    )
    shallow_cut = GridConfig(
        kind=BoardKind.FULL,
        board_width=2,
        board_height=2,
        chamfers=ChamferMode.NONE,
        connector_holes=True,
        connector_slot_delete_tool=ConnectorSlotDeleteToolConfig(height=1.2),
        screw_mounting=ScrewMounting.NONE,
    )

    assert _bbox_size(shallow_cut) == pytest.approx(_bbox_size(default_cut))
    assert _volume(shallow_cut) > _volume(default_cut)
    assert _connector_z_base(6.8, BoardKind.FULL, 1.2) + 1.2 / 2.0 == pytest.approx(6.8 / 2.0)


def test_connector_side_flags_only_cut_requested_side() -> None:
    config = GridConfig(
        kind=BoardKind.FULL,
        board_width=2,
        board_height=2,
        chamfers=ChamferMode.NONE,
        connector_holes=True,
        connector_holes_right=True,
        connector_holes_left=False,
        connector_holes_top=False,
        connector_holes_bottom=False,
        screw_mounting=ScrewMounting.NONE,
    )
    board = build_open_grid(config)

    assert not board.is_inside((27.5, 0.0, 3.4))
    assert board.is_inside((-27.5, 0.0, 3.4))
    assert board.is_inside((0.0, 27.5, 3.4))
    assert board.is_inside((0.0, -27.5, 3.4))


def test_connector_positions_skip_short_board_axes() -> None:
    one_by_three = GridConfig(board_width=1, board_height=3)
    three_by_one = GridConfig(board_width=3, board_height=1)

    assert {side for side, _ in _connector_positions(one_by_three)} == {"right", "left"}
    assert {side for side, _ in _connector_positions(three_by_one)} == {"top", "bottom"}


def test_stacked_interface_layers_follow_spacing_formula() -> None:
    config = GridConfig(
        kind=BoardKind.LITE,
        stack_count=3,
        stacking_method=StackingMethod.INTERFACE_LAYER,
        interface_thickness=0.4,
        interface_separation=0.1,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
    )
    expected_height = 4.0 + 2.0 * (4.0 + 0.4 + 2.0 * 0.1)

    assert _bbox_size(config)[2] == pytest.approx(expected_height)


def test_complete_tile_fill_places_remainder_tiles() -> None:
    config = GridConfig(
        kind=BoardKind.FULL,
        fill_space_mode=FillSpaceMode.COMPLETE_TILES_ONLY,
        space_width=168.0,
        space_depth=140.0,
        max_tile_width=4,
        max_tile_depth=3,
        tile_spacing=5.0,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
    )

    size = _bbox_size(config)
    assert size[0] > 4 * 28.0
    assert size[1] > 3 * 28.0
    assert size[2] == pytest.approx(6.8)


def test_available_space_fill_uses_best_whole_grid_fit() -> None:
    config = GridConfig(
        kind=BoardKind.FULL,
        fill_space_mode=FillSpaceMode.FILL_AVAILABLE_SPACE,
        space_width=70.0,
        space_depth=45.0,
        max_tile_width=2,
        max_tile_depth=2,
        tile_spacing=5.0,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
    )

    size = _bbox_size(config)

    assert size == pytest.approx((89.0, 56.0, 6.8))


def test_large_available_space_fill_stays_partitioned_and_bounded() -> None:
    config = GridConfig(
        kind=BoardKind.FULL,
        fill_space_mode=FillSpaceMode.FILL_AVAILABLE_SPACE,
        space_width=560.0,
        space_depth=420.0,
        max_tile_width=8,
        max_tile_depth=8,
        tile_spacing=5.0,
        chamfers=ChamferMode.NONE,
        connector_holes=False,
        screw_mounting=ScrewMounting.NONE,
    )
    board = build_open_grid(config)
    size = board.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((570.0, 425.0, 6.8))
    assert len(cast(Any, board).children) == 6


def test_openconnect_head_matches_source_envelope_and_lock_reliefs() -> None:
    plain = build_openconnect_head(OpenConnectHeadConfig(add_nubs=False))
    locked = build_openconnect_head(OpenConnectHeadConfig(add_nubs=True))
    size = locked.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((17.0, 10.6, 2.6), abs=0.02)
    assert locked.volume < plain.volume
    assert OpenConnectHeadConfig().small_rect_width == pytest.approx(14.2)
    assert OpenConnectHeadConfig().small_rect_height == pytest.approx(9.2)


def test_snap_thread_backed_screws_add_heads_and_remove_slots() -> None:
    threads = SnapThreadConfig(clearance=0.0)
    openconnect = build_openconnect_screw(OpenConnectScrewConfig(threads=threads))
    multiconnect = build_multiconnect_screw(MulticonnectScrewConfig(threads=threads))
    bare_threads = build_snap_threads(threads)

    assert openconnect.bounding_box().size.Z > bare_threads.bounding_box().size.Z
    assert multiconnect.bounding_box().size.Z > bare_threads.bounding_box().size.Z
    assert openconnect.volume > bare_threads.volume
    assert multiconnect.volume > bare_threads.volume


def test_opengrid_snap_product_variants_compose_expected_attachments() -> None:
    bare = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.BARE))
    threaded = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.BASIC_THREADS))
    openconnect = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.OPENCONNECT))
    multiconnect = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.MULTICONNECT))

    assert threaded.bounding_box().size.Z > bare.bounding_box().size.Z
    assert openconnect.bounding_box().size.Z > bare.bounding_box().size.Z
    assert multiconnect.bounding_box().size.Z > bare.bounding_box().size.Z
    assert threaded.volume > bare.volume
    assert openconnect.volume > bare.volume
    assert multiconnect.volume > bare.volume


def test_text_engraving_removes_material_from_product_builders() -> None:
    label = TextLabel(text="OG", size=3.0, depth=0.2)
    text = TextEngravingConfig(labels=(label,))
    plain = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.BARE))
    engraved = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.BARE, text=text))

    assert engraved.bounding_box().size == pytest.approx(plain.bounding_box().size)
    assert engraved.volume < plain.volume
