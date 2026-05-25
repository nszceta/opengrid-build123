from __future__ import annotations
from dataclasses import fields as dataclass_fields
from pathlib import Path
import importlib.util
import math
import yaml
from typing import Any

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
    SnapThreadConfig,
    ConnectorSlotDeleteToolConfig,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    ThreadType,
    build_connector_slot_delete_tool,
    build_adjacent_grid_connector,
    build_multiconnect_profile,
    build_multiconnect_backer,
    build_multiconnect_delete_tool,
    build_multiconnect_rail,
    build_multiconnect_receiver,
    build_snap_threads,
    _connector_z_base,
    _connector_positions,
    build_open_grid,
    _OG_SNAP_THREADS_PROFILE,
    _scaled_snap_thread_profile,
    _snap_thread_radial_offset,
    _snap_thread_angles,
)

_EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "examples" / "config.yaml"
_EXAMPLE_MAIN_PATH = Path(__file__).resolve().parents[1] / "examples" / "main.py"

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


def test_multiconnect_receiver_contains_single_offset_slot() -> None:
    config = MulticonnectConfig(length=40.0, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    receiver = build_multiconnect_receiver(config)
    size = receiver.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((25.3, 6.15, 40.0), abs=0.05)
    assert receiver.volume < 25.3 * 6.15 * 40.0


def test_multiconnect_backer_slot_count_uses_opengrid_spacing() -> None:
    narrow = build_multiconnect_backer(
        MulticonnectConfig(width=20.0, length=30.0, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    )
    two_slots = build_multiconnect_backer(
        MulticonnectConfig(width=56.0, length=30.0, rounding=MulticonnectRounding.NONE, on_ramps_enabled=False)
    )

    assert float(narrow.bounding_box().size.X) == pytest.approx(28.0)
    assert float(two_slots.bounding_box().size.X) == pytest.approx(56.0)
    assert two_slots.volume < narrow.volume * 2.0


def test_multiconnect_dimple_and_on_ramp_toggles_change_volume_not_envelope() -> None:
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
    assert delete_tool.bounding_box().size == pytest.approx(delete_tool_without_ramps.bounding_box().size)
    assert delete_tool.volume > delete_tool_without_ramps.volume

def test_output_verification_exports_shape_svgs_into_named_subdirectories(tmp_path: Path) -> None:
    rail = build_multiconnect_rail(MulticonnectConfig(length=28.0, rounding=MulticonnectRounding.NONE))

    example_main = _example_main()
    paths = example_main._export_output_verification(
        multiconnect_rail=rail,
        snap_threads=rail,
        verification_dir=tmp_path,
    )

    assert tuple(path.relative_to(tmp_path) for path in paths) == (
        Path("multiconnect_rail/multiconnect_rail_iso.svg"),
        Path("multiconnect_rail/multiconnect_rail_back.svg"),
        Path("multiconnect_rail/multiconnect_rail_top.svg"),
        Path("multiconnect_rail/gallery.html"),
        Path("snap_threads/snap_threads_iso.svg"),
        Path("snap_threads/snap_threads_front.svg"),
        Path("snap_threads/snap_threads_top.svg"),
        Path("snap_threads/gallery.html"),
    )
    for path in paths:
        assert path.stat().st_size > 0
    gallery = (tmp_path / "multiconnect_rail" / "gallery.html").read_text(encoding="utf-8")
    assert "multiconnect_rail_back.svg" in gallery


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
