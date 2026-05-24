from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Sequence, TypeAlias, cast

import build123d as bd

__all__ = [
    "BoardKind",
    "ChamferMode",
    "FillSpaceMode",
    "ConnectorSlotDeleteToolConfig",
    "AdjacentGridConnectorConfig",
    "GridConfig",
    "ScrewMounting",
    "StackingMethod",
    "build_fill_space",
    "build_connector_slot_delete_tool",
    "build_adjacent_grid_connector",
    "build_open_grid",
    "export_grid",
    "open_grid",
    "open_grid_heavy",
    "open_grid_lite",
]

Shape: TypeAlias = bd.Part | bd.Compound | bd.Solid
Point2D: TypeAlias = tuple[float, float]
Point3D: TypeAlias = tuple[float, float, float]

_EPSILON = 0.01
_DEFAULT_TILE_SIZE = 28.0
_DEFAULT_TILE_THICKNESS = 6.8
_DEFAULT_LITE_THICKNESS = 4.0
_DEFAULT_HEAVY_THICKNESS = 13.8
_DEFAULT_HEAVY_GAP = 0.2
_DEFAULT_INTERFACE_THICKNESS = 0.4
_DEFAULT_INTERFACE_SEPARATION = 0.1
_DEFAULT_ADHESIVE_THICKNESS = 0.6
_OUTSIDE_EXTRUSION = 0.8
_INSIDE_GRID_TOP_CHAMFER = 0.4
_INSIDE_GRID_MIDDLE_CHAMFER = 1.0
_TOP_CAPTURE_INITIAL_INSET = 2.4
_TILE_INNER_SIZE_DIFFERENCE = 3.0
_INTERSECTION_DISTANCE = 4.2
_CORNER_SQUARE_THICKNESS = 2.6
_CONNECTOR_CUTOUT_RADIUS = 2.6
_CONNECTOR_CUTOUT_DIMPLE_RADIUS = 2.7
_CONNECTOR_CUTOUT_SEPARATION = 2.5
_CONNECTOR_CUTOUT_FLARE_WIDTH = 1.0
_LITE_CONNECTOR_CUTOUT_DISTANCE_FROM_TOP = 1.0
_CONNECTOR_CUTOUT_HEIGHT = 2.4

_SCREW_CUSTOM_DEFAULT = "011110"


class BoardKind(StrEnum):
    FULL = "Full"
    LITE = "Lite"
    HEAVY = "Heavy"


class ChamferMode(StrEnum):
    EVERYWHERE = "Everywhere"
    CORNERS = "Corners"
    NONE = "None"


class ScrewMounting(StrEnum):
    EVERYWHERE = "Everywhere"
    CORNERS = "Corners"
    BY_ROW_AND_COLUMN = "By Row and Column"
    CUSTOM = "Custom"
    NONE = "None"


class StackingMethod(StrEnum):
    INTERFACE_LAYER = "Interface Layer"
    IRONING = "Ironing - BETA"


class FillSpaceMode(StrEnum):
    NONE = "None"
    COMPLETE_TILES_ONLY = "Complete Tiles Only"
    FILL_AVAILABLE_SPACE = "Fill Available Space"


@dataclass(frozen=True, slots=True)
class ConnectorSlotDeleteToolConfig:
    """Configuration for the adjacent-grid connector side slot delete tool."""

    radius: float = _CONNECTOR_CUTOUT_RADIUS
    dimple_radius: float = _CONNECTOR_CUTOUT_DIMPLE_RADIUS
    separation: float = _CONNECTOR_CUTOUT_SEPARATION
    height: float = _CONNECTOR_CUTOUT_HEIGHT
    flare_width: float = _CONNECTOR_CUTOUT_FLARE_WIDTH

    def validate(self) -> None:
        if min(
            self.radius,
            self.dimple_radius,
            self.separation,
            self.height,
            self.flare_width,
        ) <= 0.0:
            raise ValueError("connector slot delete tool dimensions must be positive")
        if self.separation * 3.0 <= self.dimple_radius:
            raise ValueError("connector slot delete tool separation is too small for the insertion flare")


@dataclass(frozen=True, slots=True)
class AdjacentGridConnectorConfig:
    """Configuration for the positive connector joining adjacent openGrid boards."""

    slot_delete_tool: ConnectorSlotDeleteToolConfig = field(default_factory=ConnectorSlotDeleteToolConfig)
    fit_clearance: float = 0.1

    def validate(self) -> None:
        self.slot_delete_tool.validate()
        min_dimension = min(
            self.slot_delete_tool.radius,
            self.slot_delete_tool.height / 2.0,
            self.slot_delete_tool.flare_width / 2.0,
        )
        if self.fit_clearance < 0.0:
            raise ValueError("adjacent-grid connector fit_clearance must be non-negative")
        if self.fit_clearance >= min_dimension:
            raise ValueError("adjacent-grid connector fit_clearance is too large")




@dataclass(frozen=True, slots=True)
class GridConfig:
    kind: BoardKind = BoardKind.LITE
    board_width: int = 2
    board_height: int = 2
    chamfers: ChamferMode = ChamferMode.CORNERS
    chamfer_top_left: bool = True
    chamfer_top_right: bool = True
    chamfer_bottom_left: bool = True
    chamfer_bottom_right: bool = True
    connector_holes: bool = True
    connector_holes_bottom: bool = True
    connector_holes_right: bool = True
    connector_holes_left: bool = True
    connector_holes_top: bool = True
    connector_slot_delete_tool: ConnectorSlotDeleteToolConfig = field(default_factory=ConnectorSlotDeleteToolConfig)
    screw_mounting: ScrewMounting = ScrewMounting.CORNERS
    screw_every_x_rows: int = 1
    screw_every_x_columns: int = 2
    screw_custom_positions: str = _SCREW_CUSTOM_DEFAULT
    screw_diameter: float = 4.1
    screw_head_diameter: float = 7.2
    screw_head_inset: float = 1.0
    screw_head_is_countersunk: bool = True
    screw_head_countersunk_degree: float = 90.0
    add_adhesive_base: bool = False
    adhesive_base_thickness: float = _DEFAULT_ADHESIVE_THICKNESS
    tile_size: float = _DEFAULT_TILE_SIZE
    tile_thickness: float = _DEFAULT_TILE_THICKNESS
    lite_tile_thickness: float = _DEFAULT_LITE_THICKNESS
    heavy_tile_thickness: float = _DEFAULT_HEAVY_THICKNESS
    heavy_tile_gap: float = _DEFAULT_HEAVY_GAP
    stack_count: int = 1
    stacking_method: StackingMethod = StackingMethod.INTERFACE_LAYER
    interface_thickness: float = _DEFAULT_INTERFACE_THICKNESS
    interface_separation: float = _DEFAULT_INTERFACE_SEPARATION
    fill_space_mode: FillSpaceMode = FillSpaceMode.NONE
    space_width: float = 330.0
    space_depth: float = 500.0
    max_tile_width: int = 8
    max_tile_depth: int = 8
    tile_spacing: float = 5.0

    def validate(self) -> None:
        if self.board_width < 1 or self.board_height < 1:
            raise ValueError("board dimensions must be positive")
        if self.tile_size <= 0:
            raise ValueError("tile_size must be positive")
        if min(self.tile_thickness, self.lite_tile_thickness, self.heavy_tile_thickness) <= 0:
            raise ValueError("tile thicknesses must be positive")
        if self.stack_count < 1:
            raise ValueError("stack_count must be at least 1")
        if self.max_tile_width < 1 or self.max_tile_depth < 1:
            raise ValueError("max tile dimensions must be positive")
        self.connector_slot_delete_tool.validate()


def open_grid(
    board_width: int,
    board_height: int,
    *,
    tile_size: float = _DEFAULT_TILE_SIZE,
    tile_thickness: float = _DEFAULT_TILE_THICKNESS,
    screw_mounting: ScrewMounting = ScrewMounting.NONE,
    chamfers: ChamferMode = ChamferMode.NONE,
    connector_holes: bool = False,
    config: GridConfig | None = None,
) -> Shape:
    base = config or GridConfig(
        kind=BoardKind.FULL,
        board_width=board_width,
        board_height=board_height,
        tile_size=tile_size,
        tile_thickness=tile_thickness,
        screw_mounting=screw_mounting,
        chamfers=chamfers,
        connector_holes=connector_holes,
    )
    cfg = _replace_grid(base, BoardKind.FULL, board_width, board_height, tile_size)
    return _single_board(cfg, BoardKind.FULL)


def open_grid_lite(
    board_width: int,
    board_height: int,
    *,
    tile_size: float = _DEFAULT_TILE_SIZE,
    screw_mounting: ScrewMounting = ScrewMounting.NONE,
    chamfers: ChamferMode = ChamferMode.NONE,
    add_adhesive_base: bool = False,
    connector_holes: bool = False,
    config: GridConfig | None = None,
) -> Shape:
    base = config or GridConfig(
        kind=BoardKind.LITE,
        board_width=board_width,
        board_height=board_height,
        tile_size=tile_size,
        screw_mounting=screw_mounting,
        chamfers=chamfers,
        add_adhesive_base=add_adhesive_base,
        connector_holes=connector_holes,
    )
    cfg = _replace_grid(base, BoardKind.LITE, board_width, board_height, tile_size)
    return _single_board(cfg, BoardKind.LITE)


def open_grid_heavy(
    board_width: int,
    board_height: int,
    *,
    tile_size: float = _DEFAULT_TILE_SIZE,
    screw_mounting: ScrewMounting = ScrewMounting.NONE,
    chamfers: ChamferMode = ChamferMode.NONE,
    connector_holes: bool = False,
    config: GridConfig | None = None,
) -> Shape:
    base = config or GridConfig(
        kind=BoardKind.HEAVY,
        board_width=board_width,
        board_height=board_height,
        tile_size=tile_size,
        screw_mounting=screw_mounting,
        chamfers=chamfers,
        connector_holes=connector_holes,
    )
    cfg = _replace_grid(base, BoardKind.HEAVY, board_width, board_height, tile_size)
    return _single_board(cfg, BoardKind.HEAVY)


def build_open_grid(config: GridConfig = GridConfig()) -> Shape:
    config.validate()
    if config.fill_space_mode is not FillSpaceMode.NONE:
        return build_fill_space(config)
    if config.add_adhesive_base:
        stack_count = 1
    else:
        stack_count = config.stack_count
    if stack_count == 1:
        return _single_board(config, config.kind)
    return _stacked_boards(config, stack_count)


def build_fill_space(config: GridConfig) -> Shape:
    config.validate()
    if config.fill_space_mode is FillSpaceMode.COMPLETE_TILES_ONLY:
        return _fill_complete_tiles(config)
    if config.fill_space_mode is FillSpaceMode.FILL_AVAILABLE_SPACE:
        return _fill_available_space(config)
    return _single_board(config, config.kind)


def build_connector_slot_delete_tool(
    config: ConnectorSlotDeleteToolConfig = ConnectorSlotDeleteToolConfig(),
) -> Shape:
    """Build the adjacent-grid connector side slot delete tool.

    The returned tool has its origin on the board edge, extends inward along
    +X, is centered on Y, and starts at Z=0. Geometry is translated from
    QuackWorks `openGrid/openGrid.scad` `connector_cutout_delete_tool`,
    licensed CC BY-NC-SA 4.0.
    """
    config.validate()
    flare_height = config.separation * 2.0 - (config.dimple_radius - config.separation)
    with bd.BuildSketch() as profile:
        with bd.Locations((-config.radius - 0.1, 0.0), (config.radius - 0.1, 0.0)):
            bd.Circle(config.radius)
        bd.make_hull()
        dimple_x = -0.1 + config.radius - config.separation
        dimple_y = config.radius + config.separation
        with bd.Locations((dimple_x, -dimple_y), (dimple_x, dimple_y)):
            bd.Circle(config.dimple_radius, mode=bd.Mode.SUBTRACT)
        bd.Rectangle(
            config.flare_width,
            flare_height,
            align=(bd.Align.MIN, bd.Align.CENTER),
        )
        bd.Rectangle(
            config.dimple_radius * 4.0,
            config.dimple_radius * 4.0,
            align=(bd.Align.MIN, bd.Align.CENTER),
            mode=bd.Mode.INTERSECT,
        )
    return cast(Shape, bd.extrude(profile.sketch, amount=config.height))
def build_adjacent_grid_connector(
    config: AdjacentGridConnectorConfig = AdjacentGridConnectorConfig(),
) -> Shape:
    """Build the positive adjacent-grid connector that mates with side slots.

    The connector is two opposed slot-mating halves sharing the board seam at
    X=0. Each half is derived from the adjacent-grid connector slot delete
    tool and inset by `fit_clearance`, so it fits into slots made with the
    same `ConnectorSlotDeleteToolConfig`.
    """
    config.validate()
    half = build_connector_slot_delete_tool(config.slot_delete_tool)
    if config.fit_clearance > 0.0:
        half = cast(Shape, bd.offset(half, amount=-config.fit_clearance))
    half_box = half.bounding_box()
    half = half.translate((-float(half_box.min.X), 0.0, -float(half_box.min.Z)))
    other_half = half.rotate(bd.Axis.Z, 180.0)
    return cast(Shape, half + other_half)





def export_grid(config: GridConfig, path: str | Path) -> None:
    bd.export_stl(build_open_grid(config), str(path))


def _replace_grid(
    config: GridConfig,
    kind: BoardKind,
    width: int,
    height: int,
    tile_size: float,
) -> GridConfig:
    return replace(config, kind=kind, board_width=width, board_height=height, tile_size=tile_size)


def _single_board(config: GridConfig, kind: BoardKind) -> Shape:
    thickness = _selected_thickness(config, kind)
    board = _board_lattice(config, kind)
    board = _apply_corner_modifications(board, config, thickness)
    if config.connector_holes:
        board = _subtract_connector_holes(board, config, thickness, kind)
    if kind is BoardKind.LITE and config.add_adhesive_base:
        board = board + _adhesive_base(config)
    return cast(Shape, board)


def _selected_thickness(config: GridConfig, kind: BoardKind) -> float:
    if kind is BoardKind.LITE:
        return config.lite_tile_thickness + (config.adhesive_base_thickness if config.add_adhesive_base else 0.0)
    if kind is BoardKind.HEAVY:
        return config.heavy_tile_thickness
    return config.tile_thickness


def _board_lattice(config: GridConfig, kind: BoardKind) -> Shape:
    tile = _tile_frame(config.tile_size, _profile_layers(config, kind))
    pieces: list[Shape] = []
    x0 = -((config.board_width - 1) * config.tile_size) / 2.0
    y0 = -((config.board_height - 1) * config.tile_size) / 2.0
    for ix in range(config.board_width):
        for iy in range(config.board_height):
            pieces.append(tile.translate((x0 + ix * config.tile_size, y0 + iy * config.tile_size, 0.0)))
    return _compound(pieces)


ProfileLayer: TypeAlias = tuple[float, float, float]


def _profile_layers(config: GridConfig, kind: BoardKind) -> tuple[ProfileLayer, ...]:
    if kind is BoardKind.LITE:
        return _lite_layers(config.lite_tile_thickness)
    if kind is BoardKind.HEAVY:
        return _heavy_layers(config)
    return _full_layers(config.tile_thickness, heavy_profile=False)


def _full_layers(thickness: float, *, heavy_profile: bool) -> tuple[ProfileLayer, ...]:
    side = _side_profile(thickness, heavy_profile=heavy_profile)
    corner = _corner_profile(thickness)
    z_values = sorted({z for z, _ in side} | {z for z, _ in corner})
    return tuple((z, _interpolated_offset(side, z), _interpolated_offset(corner, z)) for z in z_values)


def _side_profile(thickness: float, *, heavy_profile: bool) -> tuple[tuple[float, float], ...]:
    max_offset = _max_profile_offset()
    top_offset = max_offset - _INSIDE_GRID_TOP_CHAMFER
    if heavy_profile:
        return (
            (0.0, _OUTSIDE_EXTRUSION),
            (thickness - _TOP_CAPTURE_INITIAL_INSET, _OUTSIDE_EXTRUSION),
            (thickness - _TOP_CAPTURE_INITIAL_INSET + _INSIDE_GRID_MIDDLE_CHAMFER, max_offset),
            (thickness - _INSIDE_GRID_TOP_CHAMFER, max_offset),
            (thickness, top_offset),
        )
    return (
        (0.0, top_offset),
        (_INSIDE_GRID_TOP_CHAMFER, max_offset),
        (_TOP_CAPTURE_INITIAL_INSET - _INSIDE_GRID_MIDDLE_CHAMFER, max_offset),
        (_TOP_CAPTURE_INITIAL_INSET, _OUTSIDE_EXTRUSION),
        (thickness - _TOP_CAPTURE_INITIAL_INSET, _OUTSIDE_EXTRUSION),
        (thickness - _TOP_CAPTURE_INITIAL_INSET + _INSIDE_GRID_MIDDLE_CHAMFER, max_offset),
        (thickness - _INSIDE_GRID_TOP_CHAMFER, max_offset),
        (thickness, top_offset),
    )


def _corner_profile(thickness: float) -> tuple[tuple[float, float], ...]:
    corner_offset = _corner_offset()
    corner_chamfer = _TOP_CAPTURE_INITIAL_INSET - _INSIDE_GRID_MIDDLE_CHAMFER
    return (
        (0.0, corner_offset - corner_chamfer),
        (corner_chamfer, corner_offset),
        (thickness - corner_chamfer, corner_offset),
        (thickness, corner_offset - corner_chamfer),
    )


def _lite_layers(thickness: float) -> tuple[ProfileLayer, ...]:
    full = _full_layers(_DEFAULT_TILE_THICKNESS, heavy_profile=False)
    lower_cut = _DEFAULT_TILE_THICKNESS - thickness
    side_profile = tuple((z, side) for z, side, _ in full)
    corner_profile = tuple((z, corner) for z, _, corner in full)
    side_at_cut = _interpolated_offset(side_profile, lower_cut)
    corner_at_cut = _interpolated_offset(corner_profile, lower_cut)
    return (
        (0.0, side_at_cut, corner_at_cut),
        *((z - lower_cut, side, corner) for z, side, corner in full if z > lower_cut),
    )


def _interpolated_offset(layers: Sequence[tuple[float, float]], z_value: float) -> float:
    for (z0, offset0), (z1, offset1) in zip(layers, layers[1:]):
        if z0 <= z_value <= z1:
            if z1 == z0:
                return offset1
            ratio = (z_value - z0) / (z1 - z0)
            return offset0 + (offset1 - offset0) * ratio
    return layers[-1][1]


def _heavy_layers(config: GridConfig) -> tuple[ProfileLayer, ...]:
    full = _full_layers(config.tile_thickness, heavy_profile=True)
    web_end = config.tile_thickness + config.heavy_tile_gap
    top = tuple((web_end + (config.tile_thickness - z), side, corner) for z, side, corner in reversed(full))
    return (*full, *top)


def _max_profile_offset() -> float:
    inside = _TILE_INNER_SIZE_DIFFERENCE / 2.0 - _OUTSIDE_EXTRUSION
    return _OUTSIDE_EXTRUSION + inside


def _corner_offset() -> float:
    return math.sqrt(_INTERSECTION_DISTANCE * _INTERSECTION_DISTANCE / 2.0) + _CORNER_SQUARE_THICKNESS


def _tile_frame(tile_size: float, layers: Sequence[ProfileLayer]) -> Shape:
    components: list[Shape] = []
    z_values = tuple(z for z, _, _ in layers)
    for side in ("bottom", "top", "left", "right"):
        point_sets = tuple(_side_strip_points(tile_size, side_offset, side) for _, side_offset, _ in layers)
        components.append(_loft_layer_polygons(point_sets, z_values))
    for rotation in (0.0, 90.0, 180.0, 270.0):
        components.append(_loft_corner(tile_size, layers, rotation))
    return _fuse(components)


def _loft_layer_polygons(point_sets: Iterable[tuple[Point2D, ...]], z_values: Iterable[float]) -> Shape:
    sketches: list[bd.Sketch] = []
    for points, z in zip(point_sets, z_values):
        with bd.BuildSketch(bd.Plane.XY.offset(z)) as sketch:
            bd.Polygon(points, align=None)
        sketches.append(sketch.sketch)
    return cast(Shape, bd.loft(sketches, ruled=True))


def _loft_corner(tile_size: float, layers: Sequence[ProfileLayer], rotation: float) -> Shape:
    sketches: list[bd.Sketch] = []
    half = tile_size / 2.0
    for z, _, corner_offset in layers:
        with bd.BuildSketch(bd.Plane.XY.offset(z)) as sketch:
            bd.Polygon(_rotate_points(_corner_block_points(half, corner_offset), rotation), align=None)
            bd.Rectangle(tile_size, tile_size, mode=bd.Mode.INTERSECT)
        sketches.append(sketch.sketch)
    return cast(Shape, bd.loft(sketches, ruled=True))


def _side_strip_points(tile_size: float, offset: float, side: str) -> tuple[Point2D, ...]:
    half = tile_size / 2.0
    if side == "bottom":
        return ((-half, -half), (half, -half), (half, -half + offset), (-half, -half + offset))
    if side == "top":
        return ((-half, half - offset), (half, half - offset), (half, half), (-half, half))
    if side == "left":
        return ((-half, -half), (-half + offset, -half), (-half + offset, half), (-half, half))
    return ((half - offset, -half), (half, -half), (half, half), (half - offset, half))



def _corner_block_points(half: float, corner_offset: float) -> tuple[Point2D, ...]:
    raw = (
        (0.0, -corner_offset),
        (corner_offset, -corner_offset),
        (corner_offset, corner_offset),
        (0.0, corner_offset),
    )
    rotated = _rotate_points(raw, 45.0)
    return tuple((x - half, y - half) for x, y in rotated)


def _rotate_points(points: Iterable[Point2D], angle_degrees: float) -> tuple[Point2D, ...]:
    angle = math.radians(angle_degrees)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return tuple((x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in points)


def _apply_corner_modifications(board: Shape, config: GridConfig, thickness: float) -> Shape:
    board = _subtract_chamfers(board, config, thickness)
    screw_positions = _screw_positions(config)
    if not screw_positions:
        return board
    return board - _screw_tool(config, thickness, screw_positions)


def _subtract_chamfers(board: Shape, config: GridConfig, thickness: float) -> Shape:
    positions = _chamfer_positions(config)
    if not positions:
        return board
    tool_size = math.sqrt(_INTERSECTION_DISTANCE * _INTERSECTION_DISTANCE * 2.0)
    cutter = bd.Box(tool_size, tool_size, thickness + 2.0 * _EPSILON).rotate(bd.Axis.Z, 45)
    tools = [cutter.translate((x, y, thickness / 2.0)) for x, y in positions]
    return board - _fuse(tools)


def _chamfer_positions(config: GridConfig) -> tuple[Point2D, ...]:
    width = config.board_width * config.tile_size
    height = config.board_height * config.tile_size
    if config.chamfers is ChamferMode.NONE:
        return tuple()
    if config.chamfers is ChamferMode.CORNERS or config.screw_mounting in {ScrewMounting.EVERYWHERE, ScrewMounting.CORNERS}:
        return _outer_chamfer_positions(config, width, height)
    return tuple(
        (x * config.tile_size - width / 2.0, y * config.tile_size - height / 2.0)
        for x in range(config.board_width + 1)
        for y in range(config.board_height + 1)
    )


def _outer_chamfer_positions(config: GridConfig, width: float, height: float) -> tuple[Point2D, ...]:
    positions: list[Point2D] = []
    if config.chamfer_bottom_right:
        positions.append((width / 2.0, -height / 2.0))
    if config.chamfer_top_right:
        positions.append((width / 2.0, height / 2.0))
    if config.chamfer_bottom_left:
        positions.append((-width / 2.0, -height / 2.0))
    if config.chamfer_top_left:
        positions.append((-width / 2.0, height / 2.0))
    return tuple(positions)


def _screw_positions(config: GridConfig) -> tuple[Point2D, ...]:
    if config.screw_mounting is ScrewMounting.NONE:
        return tuple()
    if config.screw_mounting is ScrewMounting.CORNERS:
        return _unique(_corner_screw_positions(config))
    if config.screw_mounting is ScrewMounting.EVERYWHERE:
        return tuple(_internal_grid_positions(config))
    if config.screw_mounting is ScrewMounting.BY_ROW_AND_COLUMN:
        return tuple(_row_column_screw_positions(config))
    return tuple(_custom_screw_positions(config))


def _corner_screw_positions(config: GridConfig) -> tuple[Point2D, ...]:
    half_width = config.board_width * config.tile_size / 2.0
    half_height = config.board_height * config.tile_size / 2.0
    inset = config.tile_size
    return (
        (half_width - inset, half_height - inset),
        (-half_width + inset, half_height - inset),
        (half_width - inset, -half_height + inset),
        (-half_width + inset, -half_height + inset),
    )


def _internal_grid_positions(config: GridConfig) -> Iterable[Point2D]:
    for ix in range(1, config.board_width):
        for iy in range(1, config.board_height):
            yield (ix * config.tile_size - config.board_width * config.tile_size / 2.0, iy * config.tile_size - config.board_height * config.tile_size / 2.0)


def _row_column_screw_positions(config: GridConfig) -> Iterable[Point2D]:
    col_step = max(1, config.screw_every_x_columns)
    row_step = max(1, config.screw_every_x_rows)
    x_shift = 0.0 if ((config.board_width - 2) % col_step) % 2 == 0 else -config.tile_size / 2.0
    y_shift = 0.0 if ((config.board_height - 2) % row_step) % 2 == 0 else config.tile_size / 2.0
    for ix in range(1, config.board_width, col_step):
        for iy in range(1, config.board_height, row_step):
            x = ix * config.tile_size - config.board_width * config.tile_size / 2.0 + x_shift
            y = iy * config.tile_size - config.board_height * config.tile_size / 2.0 + y_shift
            yield (x, y)


def _custom_screw_positions(config: GridConfig) -> Iterable[Point2D]:
    start_x = -(config.board_width - 2) / 2.0 * config.tile_size
    start_y = (config.board_height - 2) / 2.0 * config.tile_size
    max_len = max(0, (config.board_width - 1) * (config.board_height - 1))
    for index, marker in enumerate(config.screw_custom_positions[:max_len]):
        if marker == "1":
            yield (
                start_x + config.tile_size * (index % max(1, config.board_width - 1)),
                start_y - config.tile_size * (index // max(1, config.board_width - 1)),
            )


def _screw_tool(config: GridConfig, thickness: float, positions: Sequence[Point2D]) -> Shape:
    through = thickness + 2.0 * _EPSILON
    bits: list[Shape] = []
    for x, y in positions:
        bits.append(bd.Cylinder(config.screw_diameter / 2.0, through).translate((x, y, thickness / 2.0)))
        bits.extend(_screw_head_tools(config, thickness, x, y))
    return _fuse(bits)


def _screw_head_tools(config: GridConfig, thickness: float, x: float, y: float) -> list[Shape]:
    inset = max(config.screw_head_inset, _EPSILON)
    tools: list[Shape] = [
        bd.Cylinder(config.screw_head_diameter / 2.0, inset).translate((x, y, thickness - inset / 2.0 + _EPSILON))
    ]
    cone_height = _countersink_height(config)
    if config.screw_head_is_countersunk and cone_height > _EPSILON:
        tools.append(
            bd.Cone(config.screw_diameter / 2.0, config.screw_head_diameter / 2.0, cone_height).translate(
                (x, y, thickness - inset - cone_height / 2.0)
            )
        )
    return tools


def _countersink_height(config: GridConfig) -> float:
    radius_delta = config.screw_head_diameter / 2.0 - config.screw_diameter / 2.0
    angle = math.radians((180.0 - config.screw_head_countersunk_degree) / 2.0)
    return math.tan(angle) * radius_delta - _EPSILON


def _subtract_connector_holes(board: Shape, config: GridConfig, thickness: float, kind: BoardKind) -> Shape:
    positions = _connector_positions(config)
    if not positions:
        return board
    tools = [_connector_tool(config, thickness, kind, position) for position in positions]
    return board - _fuse(tools)


def _connector_positions(config: GridConfig) -> tuple[tuple[str, float], ...]:
    positions: list[tuple[str, float]] = []
    if config.board_height > 1:
        for y in _edge_slot_offsets(config.board_height, config.tile_size):
            if config.connector_holes_right:
                positions.append(("right", y))
            if config.connector_holes_left:
                positions.append(("left", y))
    if config.board_width > 1:
        for x in _edge_slot_offsets(config.board_width, config.tile_size):
            if config.connector_holes_top:
                positions.append(("top", x))
            if config.connector_holes_bottom:
                positions.append(("bottom", x))
    return tuple(positions)


def _edge_slot_offsets(count: int, tile_size: float) -> tuple[float, ...]:
    return tuple((i - count / 2.0) * tile_size for i in range(1, count))


def _connector_tool(config: GridConfig, thickness: float, kind: BoardKind, position: tuple[str, float]) -> Shape:
    side, offset = position
    z_base = _connector_z_base(thickness, kind, config.connector_slot_delete_tool.height)
    width = config.board_width * config.tile_size
    height = config.board_height * config.tile_size
    if side == "right":
        return _right_connector_slot_delete_tool(config, width / 2.0, offset, z_base)
    if side == "left":
        return _left_connector_slot_delete_tool(config, width / 2.0, offset, z_base)
    if side == "top":
        return _top_connector_slot_delete_tool(config, height / 2.0, offset, z_base)
    return _bottom_connector_slot_delete_tool(config, height / 2.0, offset, z_base)


def _connector_z_base(
    thickness: float,
    kind: BoardKind,
    cutout_height: float = _CONNECTOR_CUTOUT_HEIGHT,
) -> float:
    if kind is BoardKind.LITE:
        return max(
            0.0,
            thickness - cutout_height - _LITE_CONNECTOR_CUTOUT_DISTANCE_FROM_TOP,
        )
    return max(0.0, (thickness - cutout_height) / 2.0)


def _right_connector_slot_delete_tool(
    config: GridConfig,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return _configured_connector_slot_delete_tool(config).rotate(bd.Axis.Z, 180.0).translate(
        (edge + _EPSILON, offset, z_base)
    )


def _left_connector_slot_delete_tool(
    config: GridConfig,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return _configured_connector_slot_delete_tool(config).translate(
        (-edge - _EPSILON, offset, z_base)
    )


def _top_connector_slot_delete_tool(
    config: GridConfig,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return _configured_connector_slot_delete_tool(config).rotate(bd.Axis.Z, -90.0).translate(
        (offset, edge + _EPSILON, z_base)
    )


def _bottom_connector_slot_delete_tool(
    config: GridConfig,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return _configured_connector_slot_delete_tool(config).rotate(bd.Axis.Z, 90.0).translate(
        (offset, -edge - _EPSILON, z_base)
    )


def _configured_connector_slot_delete_tool(config: GridConfig) -> Shape:
    return build_connector_slot_delete_tool(config.connector_slot_delete_tool)


def _adhesive_base(config: GridConfig) -> Shape:
    width = config.board_width * config.tile_size
    height = config.board_height * config.tile_size
    base = bd.Box(width, height, config.adhesive_base_thickness).translate((0.0, 0.0, -config.adhesive_base_thickness / 2.0))
    return _subtract_chamfers(base, config, config.adhesive_base_thickness)


def _stacked_boards(config: GridConfig, stack_count: int) -> Shape:
    thickness = _selected_thickness(config, config.kind)
    spacing = thickness + _adjusted_interface_thickness(config) + 2.0 * config.interface_separation
    boards = [_single_board(config, config.kind).translate((0.0, 0.0, i * spacing)) for i in range(stack_count)]
    if config.stacking_method is StackingMethod.INTERFACE_LAYER:
        boards.extend(_interface_layers(config, stack_count, thickness, spacing))
    return _fuse(boards)


def _adjusted_interface_thickness(config: GridConfig) -> float:
    if config.stacking_method is StackingMethod.INTERFACE_LAYER:
        return config.interface_thickness
    return 0.0


def _interface_layers(config: GridConfig, stack_count: int, thickness: float, spacing: float) -> list[Shape]:
    layer = _projection_layer(config, config.interface_thickness)
    return [layer.translate((0.0, 0.0, i * spacing + thickness + config.interface_separation)) for i in range(stack_count - 1)]


def _projection_layer(config: GridConfig, thickness: float) -> Shape:
    footprint_layers: tuple[ProfileLayer, ...] = ((0.0, _max_profile_offset(), _corner_offset()), (thickness, _max_profile_offset(), _corner_offset()))
    return _projection_lattice(config, footprint_layers)


def _projection_lattice(config: GridConfig, layers: Sequence[ProfileLayer]) -> Shape:
    tile = _tile_frame(config.tile_size, layers)
    pieces: list[Shape] = []
    x0 = -((config.board_width - 1) * config.tile_size) / 2.0
    y0 = -((config.board_height - 1) * config.tile_size) / 2.0
    for ix in range(config.board_width):
        for iy in range(config.board_height):
            pieces.append(tile.translate((x0 + ix * config.tile_size, y0 + iy * config.tile_size, 0.0)))
    return _fuse(pieces)


def _fill_complete_tiles(config: GridConfig) -> Shape:
    total_width = math.floor(config.space_width / config.tile_size)
    total_depth = math.floor(config.space_depth / config.tile_size)
    max_wide = math.floor(total_width / config.max_tile_width)
    max_deep = math.floor(total_depth / config.max_tile_depth)
    rem_width = total_width - max_wide * config.max_tile_width
    rem_depth = total_depth - max_deep * config.max_tile_depth
    return _place_complete_tiles(config, max_wide, max_deep, rem_width, rem_depth)


def _place_complete_tiles(config: GridConfig, max_wide: int, max_deep: int, rem_width: int, rem_depth: int) -> Shape:
    pieces: list[Shape] = []
    for x in range(max_wide):
        for y in range(max_deep):
            pieces.append(_placed_tile(config, x * config.max_tile_width, y * config.max_tile_depth, config.max_tile_width, config.max_tile_depth))
    _append_remainder_tiles(pieces, config, max_wide, max_deep, rem_width, rem_depth)
    return _compound(pieces)


def _append_remainder_tiles(pieces: list[Shape], config: GridConfig, max_wide: int, max_deep: int, rem_width: int, rem_depth: int) -> None:
    for y in range(max_deep):
        if rem_width > 0:
            pieces.append(_placed_tile(config, max_wide * config.max_tile_width, y * config.max_tile_depth, rem_width, config.max_tile_depth))
    for x in range(max_wide):
        if rem_depth > 0:
            pieces.append(_placed_tile(config, x * config.max_tile_width, max_deep * config.max_tile_depth, config.max_tile_width, rem_depth))
    if rem_width > 0 and rem_depth > 0:
        pieces.append(_placed_tile(config, max_wide * config.max_tile_width, max_deep * config.max_tile_depth, rem_width, rem_depth))


def _placed_tile(config: GridConfig, x_cells: int, y_cells: int, width: int, height: int) -> Shape:
    tile_config = replace(config, board_width=width, board_height=height, fill_space_mode=FillSpaceMode.NONE)
    spacing = config.tile_size + config.tile_spacing
    return _single_board(tile_config, config.kind).translate((x_cells * spacing, y_cells * spacing, 0.0))


def _fill_available_space(config: GridConfig) -> Shape:
    width_cells = math.ceil(config.space_width / config.tile_size)
    depth_cells = math.ceil(config.space_depth / config.tile_size)
    tile_widths = _tile_runs(width_cells, config.max_tile_width)
    tile_depths = _tile_runs(depth_cells, config.max_tile_depth)
    return _place_partitioned_tiles(config, tile_widths, tile_depths)


def _tile_runs(total_cells: int, max_cells: int) -> tuple[int, ...]:
    full_count, remainder = divmod(total_cells, max_cells)
    full_runs = (max_cells,) * full_count
    if remainder == 0:
        return full_runs
    return (*full_runs, remainder)


def _place_partitioned_tiles(config: GridConfig, tile_widths: Sequence[int], tile_depths: Sequence[int]) -> Shape:
    base_tiles: dict[tuple[int, int], Shape] = {}
    pieces: list[Shape] = []
    x = 0.0
    for width in tile_widths:
        y = 0.0
        for depth in tile_depths:
            pieces.append(
                _partitioned_tile(config, width, depth, base_tiles).translate(
                    (x + width * config.tile_size / 2.0, y + depth * config.tile_size / 2.0, 0.0)
                )
            )
            y += depth * config.tile_size + config.tile_spacing
        x += width * config.tile_size + config.tile_spacing
    return _compound(pieces)


def _partitioned_tile(
    config: GridConfig,
    width_cells: int,
    height_cells: int,
    base_tiles: dict[tuple[int, int], Shape],
) -> Shape:
    key = (width_cells, height_cells)
    if key not in base_tiles:
        tile_config = replace(config, board_width=width_cells, board_height=height_cells, fill_space_mode=FillSpaceMode.NONE)
        base_tiles[key] = _single_board(tile_config, config.kind)
    return base_tiles[key]


def _compound(shapes: Sequence[Shape]) -> Shape:
    if not shapes:
        return bd.Part()
    return cast(Shape, bd.Compound(children=shapes))

def _fuse(shapes: Sequence[Shape]) -> Shape:
    if not shapes:
        return bd.Part()
    result = shapes[0]
    for shape in shapes[1:]:
        result = result + shape
    return cast(Shape, result)


def _unique(points: Iterable[Point2D]) -> tuple[Point2D, ...]:
    seen: set[tuple[int, int]] = set()
    unique_points: list[Point2D] = []
    for x, y in points:
        key = (round(x * 1_000_000), round(y * 1_000_000))
        if key not in seen:
            seen.add(key)
            unique_points.append((x, y))
    return tuple(unique_points)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an openGrid board with build123d")
    parser.add_argument("--kind", choices=[kind.value for kind in BoardKind], default=BoardKind.LITE.value)
    parser.add_argument("--width", type=int, default=2)
    parser.add_argument("--height", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-connectors", action="store_true")
    parser.add_argument("--screw-mounting", choices=[mode.value for mode in ScrewMounting], default=ScrewMounting.CORNERS.value)
    parser.add_argument("--chamfers", choices=[mode.value for mode in ChamferMode], default=ChamferMode.CORNERS.value)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = GridConfig(
        kind=BoardKind(args.kind),
        board_width=args.width,
        board_height=args.height,
        connector_holes=not args.no_connectors,
        screw_mounting=ScrewMounting(args.screw_mounting),
        chamfers=ChamferMode(args.chamfers),
    )
    export_grid(config, args.output)


if __name__ == "__main__":
    main()
