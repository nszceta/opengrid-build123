from __future__ import annotations

import pytest

from opengrid_build123.opengrid import (
    AdjacentGridConnectorConfig,
    BoardKind,
    ChamferMode,
    FillSpaceMode,
    ConnectorSlotDeleteToolConfig,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    build_connector_slot_delete_tool,
    build_adjacent_grid_connector,
    _connector_z_base,
    _connector_positions,
    build_open_grid,
)


def _bbox_size(config: GridConfig) -> tuple[float, float, float]:
    size = build_open_grid(config).bounding_box().size
    return (float(size.X), float(size.Y), float(size.Z))


def _volume(config: GridConfig) -> float:
    return float(build_open_grid(config).volume)


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
