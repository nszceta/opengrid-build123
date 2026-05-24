from __future__ import annotations

import pytest

from opengrid_build123.opengrid import (
    BoardKind,
    ChamferMode,
    FillSpaceMode,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    _connector_z_base,
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

def test_connector_slots_are_centered_on_board_side_height() -> None:
    full_base = _connector_z_base(6.8, BoardKind.FULL)
    lite_base = _connector_z_base(4.0, BoardKind.LITE)

    assert full_base == pytest.approx((6.8 - 2.4) / 2.0)
    assert full_base + 2.4 / 2.0 == pytest.approx(6.8 / 2.0)
    assert lite_base == pytest.approx((4.0 - 2.4) / 2.0)
    assert lite_base + 2.4 / 2.0 == pytest.approx(4.0 / 2.0)


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
