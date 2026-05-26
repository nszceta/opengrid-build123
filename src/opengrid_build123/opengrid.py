from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field, replace
from functools import lru_cache
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Sequence, TypeAlias, cast

import build123d as bd

__all__ = [
    "BoardKind",
    "ChamferMode",
    "FillSpaceMode",
    "ThreadType",
    "SnapBodyShape",
    "OpenGridSnapKind",
    "ConnectorSlotDeleteToolConfig",
    "AdjacentGridConnectorConfig",
    "MulticonnectProfile",
    "MulticonnectPartKind",
    "MulticonnectConfig",
    "MulticonnectRounding",
    "OpenConnectHeadConfig",
    "ConnectorSlotConfig",
    "MulticonnectHeadConfig",
    "SnapThreadConfig",
    "SnapBodyConfig",
    "ExpandingSnapConfig",
    "TextLabel",
    "TextEngravingConfig",
    "OpenConnectScrewConfig",
    "MulticonnectScrewConfig",
    "OpenGridSnapConfig",
    "GridConfig",
    "ScrewMounting",
    "StackingMethod",
    "build_fill_space",
    "build_openconnect_head",
    "build_openconnect_screw",
    "build_multiconnect_head",
    "build_multiconnect_screw",
    "build_opengrid_snap",
    "build_connector_slot_delete_tool",
    "build_adjacent_grid_connector",
    "build_multiconnect_profile",
    "build_multiconnect_part",
    "build_multiconnect_rail",
    "build_multiconnect_receiver",
    "build_multiconnect_backer",
    "build_multiconnect_delete_tool",
    "build_snap_threads",
    "build_snap_body",
    "build_expanding_snap",
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
_MULTICONNECT_STANDARD_RADIUS = 10.0
_MULTICONNECT_STANDARD_DEPTH1 = 1.0
_MULTICONNECT_STANDARD_DEPTH2 = 2.5
_MULTICONNECT_STANDARD_DEPTH3 = 0.5
_MULTICONNECT_STANDARD_OFFSET = 0.15
_MULTICONNECT_STANDARD_DIMPLE_RADIUS = 1.0

_OG_SNAP_THREADS_DIAMETER = 16.0
_OG_SNAP_THREADS_CLEARANCE = 0.5
_OG_SNAP_THREADS_COMPATIBILITY_ANGLE = 53.5
_OG_SNAP_THREADS_PITCH = 3.0
_OG_SNAP_THREADS_PROFILE: tuple[Point2D, ...] = (
    (-1.25 / 3.0, -1.0 / 3.0),
    (-0.25 / 3.0, 0.0),
    (0.25 / 3.0, 0.0),
    (1.25 / 3.0, -1.0 / 3.0),
)
_SNAP_THREAD_BASE_SEGMENTS = 144
_SNAP_THREAD_Z_SEGMENTS_PER_PITCH = 24
_SNAP_THREAD_CUT_BASE_SEGMENTS = 18
_SNAP_THREAD_CUT_Z_SEGMENTS_PER_PITCH = 3
_SNAP_THREAD_LEAD_IN_OFFSET = 1.5
_SNAP_THREAD_MIN_TURNS = 0.5
_SNAP_THREAD_BLUNT_ANGLE = 10.0
_OG_SNAP_WIDTH = 24.8
_OG_SNAP_CORNER_OUTER_DIAGONAL = 2.7 + 1.0 / math.sqrt(2.0)
_OG_SNAP_CORNER_CHAMFER = _OG_SNAP_CORNER_OUTER_DIAGONAL * math.sqrt(2.0)
_OG_SNAP_CORNER_INNER_DIAGONAL = _OG_SNAP_WIDTH * math.sqrt(2.0) / 2.0 - _OG_SNAP_CORNER_OUTER_DIAGONAL

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


class ThreadType(StrEnum):
    BASIC = "Basic"
    BLUNT = "Blunt"


class SnapBodyShape(StrEnum):
    DIRECTIONAL = "Directional"
    SYMMETRIC = "Symmetric"
class OpenGridSnapKind(StrEnum):
    BARE = "Bare"
    BASIC_THREADS = "Basic Threads"
    SELF_EXPANDING_THREADS = "Self-Expanding Threads"
    OPENCONNECT = "openConnect"
    MULTICONNECT = "multiConnect"






class MulticonnectProfile(StrEnum):
    STANDARD = "Standard"
    JR = "Jr."
    MINI = "Mini"
    MULTIPOINT_BETA = "Multipoint Beta"
    CUSTOM = "Custom"


class MulticonnectPartKind(StrEnum):
    CONNECTOR_ROUND = "Connector Round"
    CONNECTOR_RAIL = "Connector Rail"
    CONNECTOR_DOUBLE_SIDED_ROUND = "Connector Double sided Round"
    CONNECTOR_DOUBLE_SIDED_RAIL = "Connector Double-Sided Rail"
    CONNECTOR_RAIL_DELETE_TOOL = "Connector Rail Delete Tool"
    RECEIVER_OPEN_ENDED = "Receiver Open-Ended"
    RECEIVER_PASSTHROUGH = "Receiver Passthrough"
    BACKER_OPEN_ENDED = "Backer Open-Ended"
    BACKER_PASSTHROUGH = "Backer Passthrough"


class MulticonnectRounding(StrEnum):
    NONE = "None"
    ONE_SIDE = "One Side"
    BOTH_SIDES = "Both Sides"


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
class SnapThreadConfig:
    """Configuration for the openGrid snap thread primitive.

    Returned thread solids are centered on X/Y with their Z range anchored at
    ``[0, height]`` so snap bodies and screw variants can compose them directly.
    """

    thread_type: ThreadType = ThreadType.BLUNT
    height: float = _DEFAULT_TILE_THICKNESS
    diameter: float = _OG_SNAP_THREADS_DIAMETER
    clearance: float = _OG_SNAP_THREADS_CLEARANCE
    pitch: float = _OG_SNAP_THREADS_PITCH
    top_bevel: float = 0.5
    bottom_bevel_standard: float = 2.0
    bottom_bevel_lite: float = 1.2
    offset_angle: float = 0.0
    blunt_cutoff: bool = True

    def validate(self) -> None:
        if min(self.height, self.diameter, self.pitch) <= 0.0:
            raise ValueError("snap thread height, diameter, and pitch must be positive")
        if min(self.clearance, self.top_bevel, self.bottom_bevel_standard, self.bottom_bevel_lite) < 0.0:
            raise ValueError("snap thread clearance and bevels must be non-negative")

    @property
    def effective_diameter(self) -> float:
        return self.diameter + self.clearance

@dataclass(frozen=True, slots=True)
class SnapBodyConfig:
    """Configuration for the openGrid snap body primitive.

    Defaults mirror `opengrid-projects/lib/opengrid_snap_lib.scad`.
    Returned snap bodies are centered on X/Y with their Z range anchored at
    ``[0, thickness]`` for direct composition with snap threads and connector
    heads.
    """

    body_shape: SnapBodyShape = SnapBodyShape.DIRECTIONAL
    width: float = _OG_SNAP_WIDTH
    height: float = _OG_SNAP_WIDTH
    thickness: float = _DEFAULT_TILE_THICKNESS
    corner_chamfer: float = _OG_SNAP_CORNER_CHAMFER
    directional_corner_fillet_radius: float = 1.5
    corner_edge_height: float = 1.5
    top_corner_extrude: float = 1.1
    bottom_corner_extrude: float = 0.6
    cut_width_inset: float = 6.2
    bottom_cut_thickness: float = 0.6
    bottom_cut_offset_to_top: float = 0.6
    bottom_cut_offset_to_edge: float = 0.7
    side_cut_thickness: float = 0.4
    side_cut_depth: float = 0.8
    side_cut_offset_to_top: float = 0.8
    directional_slant_height_standard: float = 3.4
    directional_slant_height_lite: float = 1.2
    directional_slant_depth_standard: float = 0.8
    directional_slant_depth_lite: float = 0.2
    basic_nub_width_inset: float = 7.0
    basic_nub_depth: float = 0.4
    basic_nub_width_tip_taper: float = 4.0
    basic_nub_top_angle: float = 35.0
    basic_nub_bottom_angle: float = 35.0
    basic_nub_fillet_radius: float = 15.0
    basic_nub_height_standard: float = 2.0
    basic_nub_height_lite: float = 1.8
    directional_nub_width_inset: float = 5.0
    directional_nub_depth: float = 0.8
    directional_nub_width_tip_taper: float = 1.6
    directional_nub_top_angle: float = 35.0
    directional_nub_height_standard: float = 4.0
    directional_nub_height_lite: float = 2.4
    directional_nub_bottom_angle_standard: float = 35.0
    directional_nub_bottom_angle_lite: float = 45.0
    directional_nub_fillet_radius: float = 2.8
    antidirect_nub_height_standard: float = 2.0
    antidirect_nub_height_lite: float = 1.4
    nub_offset_to_top: float = 1.4
    notch_width: float = 5.0
    notch_surface_inset: float = 1.0
    notch_gap_inset: float = 1.8
    notch_surface_height_standard: float = 1.2
    notch_surface_height_lite: float = 0.8
    notch_gap_height_standard: float = 1.0
    notch_gap_height_lite: float = 0.6
    enable_corners: bool = True
    enable_nubs: bool = True
    enable_cuts: bool = True
    enable_uninstall_notch: bool = True
    enable_directional_slants: bool = True

    def validate(self) -> None:
        if min(self.width, self.height, self.thickness) <= 0.0:
            raise ValueError("snap body width, height, and thickness must be positive")
        non_negative = (
            self.corner_chamfer,
            self.directional_corner_fillet_radius,
            self.corner_edge_height,
            self.top_corner_extrude,
            self.bottom_corner_extrude,
            self.cut_width_inset,
            self.bottom_cut_thickness,
            self.bottom_cut_offset_to_top,
            self.bottom_cut_offset_to_edge,
            self.side_cut_thickness,
            self.side_cut_depth,
            self.side_cut_offset_to_top,
            self.directional_slant_height_standard,
            self.directional_slant_height_lite,
            self.directional_slant_depth_standard,
            self.directional_slant_depth_lite,
            self.basic_nub_width_inset,
            self.basic_nub_depth,
            self.basic_nub_width_tip_taper,
            self.basic_nub_top_angle,
            self.basic_nub_bottom_angle,
            self.basic_nub_fillet_radius,
            self.basic_nub_height_standard,
            self.basic_nub_height_lite,
            self.directional_nub_width_inset,
            self.directional_nub_depth,
            self.directional_nub_width_tip_taper,
            self.directional_nub_top_angle,
            self.directional_nub_height_standard,
            self.directional_nub_height_lite,
            self.directional_nub_bottom_angle_standard,
            self.directional_nub_bottom_angle_lite,
            self.directional_nub_fillet_radius,
            self.antidirect_nub_height_standard,
            self.antidirect_nub_height_lite,
            self.nub_offset_to_top,
            self.notch_width,
            self.notch_surface_inset,
            self.notch_gap_inset,
            self.notch_surface_height_standard,
            self.notch_surface_height_lite,
            self.notch_gap_height_standard,
            self.notch_gap_height_lite,
        )
        if min(non_negative) < 0.0:
            raise ValueError("snap body feature dimensions must be non-negative")
        if self.corner_chamfer * 2.0 >= min(self.width, self.height):
            raise ValueError("snap body corner_chamfer is too large")
        if self.cut_width_inset * 2.0 >= min(self.width, self.height):
            raise ValueError("snap body cut_width_inset is too large")
        if max(self.basic_nub_width_inset, self.directional_nub_width_inset) * 2.0 >= min(self.width, self.height):
            raise ValueError("snap body nub width inset is too large")


@dataclass(frozen=True, slots=True)
class ExpandingSnapConfig:
    """Configuration for a self-expanding openGrid snap.

    The defaults are sourced from `opengrid_expanding_snap.scad` and the
    support libraries it imports. The result is a snap body with snap-thread and
    spring relief geometry removed from the center so the printed snap can flex.
    """

    snap_body: SnapBodyConfig = field(default_factory=SnapBodyConfig)
    threads: SnapThreadConfig = field(default_factory=SnapThreadConfig)
    expand_distance_standard: float = 1.0
    expand_distance_lite: float = 1.2
    expand_entry_height_standard: float = 0.4
    expand_entry_height_lite: float = 0.4
    expand_entry_height_blunt: float = 1.0
    expand_end_height_standard: float = 2.0
    expand_end_height_lite: float = 1.2
    expand_split_angle: float = 45.0
    spring_thickness: float = 1.26
    spring_to_center_thickness: float = 0.84
    spring_gap: float = 0.42
    spring_face_chamfer: float = 0.2
    center_offset: Point2D = (0.0, 0.0)

    def validate(self) -> None:
        self.snap_body.validate()
        self.threads.validate()
        non_negative = (
            self.expand_distance_standard,
            self.expand_distance_lite,
            self.expand_entry_height_standard,
            self.expand_entry_height_lite,
            self.expand_entry_height_blunt,
            self.expand_end_height_standard,
            self.expand_end_height_lite,
            self.spring_thickness,
            self.spring_to_center_thickness,
            self.spring_gap,
            self.spring_face_chamfer,
        )
        if min(non_negative) < 0.0:
            raise ValueError("expanding snap distances and spring dimensions must be non-negative")
        if self.spring_gap <= 0.0:
            raise ValueError("expanding snap spring_gap must be positive")
        if self.threads.effective_diameter >= min(self.snap_body.width, self.snap_body.height):
            raise ValueError("expanding snap thread diameter is too large for the snap body")

@dataclass(frozen=True, slots=True)
class TextLabel:
    """Single top-face engraving label for snap and screw products."""

    text: str
    size: float = 4.0
    position: Point2D = (0.0, 0.0)
    depth: float = 0.4
    font: str = "Arial"
    top: bool = True

    def validate(self) -> None:
        if not self.text:
            raise ValueError("text label must not be empty")
        if min(self.size, self.depth) <= 0.0:
            raise ValueError("text label size and depth must be positive")


@dataclass(frozen=True, slots=True)
class TextEngravingConfig:
    """Cosmetic text or emoji engraving applied by product-level builders."""

    labels: tuple[TextLabel, ...] = ()

    def validate(self) -> None:
        for label in self.labels:
            label.validate()


@dataclass(frozen=True, slots=True)
class OpenConnectHeadConfig:
    """Configuration for the openConnect snap/screw rectangular head."""

    bottom_height: float = 0.6
    top_height: float = 0.6
    middle_height: float = 1.4
    large_rect_width: float = 17.0
    large_rect_height: float = 10.6
    large_rect_chamfer: float = 4.0
    nub_to_top_distance: float = 7.2
    nub_depth: float = 0.6
    nub_tip_height: float = 1.2
    nub_fillet: float = 0.8
    back_pos_offset: float = 0.4
    add_nubs: bool = True

    def validate(self) -> None:
        if min(
            self.bottom_height,
            self.top_height,
            self.middle_height,
            self.large_rect_width,
            self.large_rect_height,
            self.large_rect_chamfer,
            self.nub_to_top_distance,
            self.nub_depth,
            self.nub_tip_height,
            self.nub_fillet,
        ) <= 0.0:
            raise ValueError("openConnect head dimensions must be positive")
        if self.small_rect_width <= 0.0 or self.small_rect_height <= 0.0:
            raise ValueError("openConnect middle height is too large for the head")
        if self.small_rect_chamfer <= 0.0:
            raise ValueError("openConnect small-rect chamfer must be positive")
        if self.large_rect_chamfer * 2.0 >= min(self.large_rect_width, self.large_rect_height):
            raise ValueError("openConnect large-rect chamfer is too large")

    @property
    def total_height(self) -> float:
        return self.bottom_height + self.middle_height + self.top_height

    @property
    def middle_to_bottom(self) -> float:
        return self.large_rect_height - self.large_rect_width / 2.0 - self.back_pos_offset

    @property
    def small_rect_width(self) -> float:
        return self.large_rect_width - self.middle_height * 2.0

    @property
    def small_rect_height(self) -> float:
        return self.large_rect_height - self.middle_height

    @property
    def small_rect_chamfer(self) -> float:
        angle_adjust = math.tan(math.radians(45.0 / 2.0)) * self.middle_height
        return self.large_rect_chamfer - self.middle_height + angle_adjust


@dataclass(frozen=True, slots=True)
class ConnectorSlotConfig:
    """Coin/flat screwdriver slot used in openConnect and Multiconnect screws."""

    coin_slot_height: float = 2.6
    coin_slot_width: float = 13.0
    coin_slot_thickness: float = 2.2
    flat_slot_height: float = 5.0
    flat_slot_width: float = 6.5
    flat_slot_height_offset: float = 0.7
    flat_slot_start_thickness: float = 1.8
    flat_slot_end_thickness: float = 1.2

    def validate(self) -> None:
        if min(
            self.coin_slot_height,
            self.coin_slot_width,
            self.coin_slot_thickness,
            self.flat_slot_height,
            self.flat_slot_width,
            self.flat_slot_start_thickness,
            self.flat_slot_end_thickness,
        ) <= 0.0:
            raise ValueError("connector slot dimensions must be positive")
        if self.flat_slot_height <= self.coin_slot_height:
            raise ValueError("connector flat slot must extend below the coin slot")

    @property
    def coin_slot_radius(self) -> float:
        return self.coin_slot_height / 2.0 + self.coin_slot_width * self.coin_slot_width / (8.0 * self.coin_slot_height)


@dataclass(frozen=True, slots=True)
class MulticonnectHeadConfig:
    """Configuration for the round Multiconnect screw/snap head."""

    large_diameter: float = 20.0
    small_diameter: float = 15.0
    top_height: float = 0.5
    middle_height: float = 2.5
    bottom_height: float = 1.0
    top_pattern: str = "coin_slot"

    def validate(self) -> None:
        if min(self.large_diameter, self.small_diameter, self.top_height, self.middle_height, self.bottom_height) <= 0.0:
            raise ValueError("Multiconnect head dimensions must be positive")
        if self.small_diameter > self.large_diameter:
            raise ValueError("Multiconnect small diameter must not exceed large diameter")
        if self.top_pattern not in {"coin_slot", "dimple", "none"}:
            raise ValueError("Multiconnect top_pattern must be coin_slot, dimple, or none")

    @property
    def total_height(self) -> float:
        return self.top_height + self.middle_height + self.bottom_height


@dataclass(frozen=True, slots=True)
class OpenConnectScrewConfig:
    """Snap-thread-backed openConnect screw product."""

    threads: SnapThreadConfig = field(default_factory=lambda: SnapThreadConfig(clearance=0.0))
    head: OpenConnectHeadConfig = field(default_factory=OpenConnectHeadConfig)
    connector_slot: ConnectorSlotConfig = field(default_factory=ConnectorSlotConfig)
    text: TextEngravingConfig = field(default_factory=TextEngravingConfig)
    folded: bool = False

    def validate(self) -> None:
        self.threads.validate()
        self.head.validate()
        self.connector_slot.validate()
        self.text.validate()


@dataclass(frozen=True, slots=True)
class MulticonnectScrewConfig:
    """Snap-thread-backed Multiconnect screw product."""

    threads: SnapThreadConfig = field(default_factory=lambda: SnapThreadConfig(clearance=0.0))
    head: MulticonnectHeadConfig = field(default_factory=MulticonnectHeadConfig)
    connector_slot: ConnectorSlotConfig = field(default_factory=ConnectorSlotConfig)
    text: TextEngravingConfig = field(default_factory=TextEngravingConfig)

    def validate(self) -> None:
        self.threads.validate()
        self.head.validate()
        self.connector_slot.validate()
        self.text.validate()


@dataclass(frozen=True, slots=True)
class OpenGridSnapConfig:
    """Configuration for source-equivalent assembled openGrid snap products."""

    kind: OpenGridSnapKind = OpenGridSnapKind.OPENCONNECT
    snap_body: SnapBodyConfig = field(default_factory=SnapBodyConfig)
    threads: SnapThreadConfig = field(default_factory=SnapThreadConfig)
    expanding_snap: ExpandingSnapConfig = field(default_factory=ExpandingSnapConfig)
    openconnect_head: OpenConnectHeadConfig = field(default_factory=OpenConnectHeadConfig)
    multiconnect_head: MulticonnectHeadConfig = field(default_factory=MulticonnectHeadConfig)
    text: TextEngravingConfig = field(default_factory=TextEngravingConfig)
    center_offset: Point2D = (0.0, 0.0)
    reverse_threads_entryside: bool = False
    disable_threads: bool = False

    def validate(self) -> None:
        self.snap_body.validate()
        self.threads.validate()
        self.expanding_snap.validate()
        self.openconnect_head.validate()
        self.multiconnect_head.validate()
        self.text.validate()



@dataclass(frozen=True, slots=True)
class MulticonnectConfig:
    """Configuration for Multiconnect profile and core solid generation.

    `capture_depth`, `dovetail_depth`, and `stem_depth` map to the source
    `Depth1`, `Depth2`, and `Depth3` parameters in QuackWorks
    `Modules/multiconnectGenerator.scad`, licensed CC BY-NC-SA 4.0.
    """

    profile: MulticonnectProfile = MulticonnectProfile.STANDARD
    part_kind: MulticonnectPartKind = MulticonnectPartKind.CONNECTOR_RAIL
    length: float = 50.0
    width: float = 75.0
    grid_size: float = _DEFAULT_TILE_SIZE
    radius: float = _MULTICONNECT_STANDARD_RADIUS
    capture_depth: float = _MULTICONNECT_STANDARD_DEPTH1
    dovetail_depth: float = _MULTICONNECT_STANDARD_DEPTH2
    stem_depth: float = _MULTICONNECT_STANDARD_DEPTH3
    receiver_offset: float = _MULTICONNECT_STANDARD_OFFSET
    dimple_radius: float = _MULTICONNECT_STANDARD_DIMPLE_RADIUS
    dimples_enabled: bool = True
    dimple_scale: float = 1.0
    rounding: MulticonnectRounding = MulticonnectRounding.BOTH_SIDES
    receiver_side_wall_thickness: float = 2.5
    receiver_back_thickness: float = 2.0
    receiver_top_wall_thickness: float = 2.5
    on_ramps_enabled: bool = True
    on_ramp_every_n_holes: int = 2
    on_ramp_start_offset: int = 1

    def validate(self) -> None:
        if min(
            self.length,
            self.width,
            self.grid_size,
            self.radius,
            self.capture_depth,
            self.dovetail_depth,
            self.stem_depth,
            self.dimple_radius,
            self.dimple_scale,
            self.receiver_side_wall_thickness,
            self.receiver_back_thickness,
            self.receiver_top_wall_thickness,
        ) <= 0.0:
            raise ValueError("multiconnect dimensions must be positive")
        if self.receiver_offset < 0.0:
            raise ValueError("multiconnect receiver_offset must be non-negative")
        if self.on_ramp_every_n_holes < 1:
            raise ValueError("multiconnect on_ramp_every_n_holes must be positive")
        if self.on_ramp_start_offset < 0:
            raise ValueError("multiconnect on_ramp_start_offset must be non-negative")


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
    return _copy_shape(_connector_slot_delete_tool_base(config))


@lru_cache(maxsize=128)
def _connector_slot_delete_tool_base(config: ConnectorSlotDeleteToolConfig) -> Shape:
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


def _copy_shape(shape: Shape) -> Shape:
    return shape.translate((0.0, 0.0, 0.0))


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


def build_snap_body(config: SnapBodyConfig = SnapBodyConfig()) -> Shape:
    """Build the openGrid snap body without threaded or openConnect inserts.

    Geometry follows `opengrid-projects/lib/opengrid_snap_lib.scad`
    `base_snap`: an octagonal chamfered core, source-configured corner pads,
    side nubs, side/bottom relief cuts, directional slants, and the front
    uninstall notch. Text engraving is intentionally not part of this primitive.
    """
    config.validate()
    body = _snap_body_core(config)
    if config.enable_corners:
        body = cast(Shape, body + _snap_body_corner_features(config))
    if config.enable_nubs:
        body = cast(Shape, body + _snap_body_nubs(config))
    if config.enable_cuts:
        body = cast(Shape, body - _snap_body_cut_tools(config))
    if config.enable_uninstall_notch and config.notch_width > _EPSILON:
        body = cast(Shape, body - _snap_body_uninstall_notch_tool(config))
    return body


def build_expanding_snap(config: ExpandingSnapConfig = ExpandingSnapConfig()) -> Shape:
    """Build a self-expanding openGrid snap body with snap-thread reliefs.

    This ports the mechanical intent of `expanding_snap(...)`: standard side
    relief cuts are omitted, directional lead-in slants remain, and the center
    receives snap-thread, expansion, and spring-gap subtraction tools.
    """
    config.validate()
    body_config = replace(config.snap_body, enable_cuts=False)
    body = build_snap_body(body_config)
    if body_config.body_shape is SnapBodyShape.DIRECTIONAL and body_config.enable_directional_slants:
        body = cast(Shape, body - _snap_body_directional_slant_tool(body_config))
    tool = _expanding_snap_removal_tool(config).translate((config.center_offset[0], config.center_offset[1], 0.0))
    return cast(Shape, body - tool)
def build_openconnect_head(config: OpenConnectHeadConfig = OpenConnectHeadConfig()) -> Shape:
    """Build the source openConnect rectangular head with lock reliefs."""

    config.validate()
    bottom_profile = _openconnect_head_profile(config, top=False)
    top_profile = _openconnect_head_profile(config, top=True)
    bottom = _extrude_xy_polygon(bottom_profile, config.bottom_height)
    transition = _loft_layer_polygons(
        (bottom_profile, top_profile),
        (config.bottom_height - _EPSILON, config.bottom_height + config.middle_height),
    )
    top = _extrude_xy_polygon(top_profile, config.top_height).translate(
        (0.0, 0.0, config.bottom_height + config.middle_height - _EPSILON)
    )
    head = _fuse((bottom, transition, top))
    if config.add_nubs:
        head = cast(Shape, head - _openconnect_lock_tools(config))
    return head


def build_openconnect_screw(config: OpenConnectScrewConfig = OpenConnectScrewConfig()) -> Shape:
    """Build a snap-thread-backed openConnect screw with screwdriver slot."""

    config.validate()
    head = build_openconnect_head(config.head)
    head = _subtract_connector_slot(head, config.connector_slot, config.head.total_height)
    threads = build_snap_threads(replace(config.threads, clearance=0.0)).translate(
        (0.0, 0.0, config.head.total_height - _EPSILON)
    )
    screw = cast(Shape, head + threads)
    return _engrave_text(screw, config.text, config.head.total_height + config.threads.height)


def build_multiconnect_head(
    config: MulticonnectHeadConfig = MulticonnectHeadConfig(),
    connector_slot: ConnectorSlotConfig = ConnectorSlotConfig(),
) -> Shape:
    """Build the round Multiconnect head used by snap adapters and screws."""

    config.validate()
    connector_slot.validate()
    bottom = bd.Cylinder(config.large_diameter / 2.0, config.bottom_height).translate(
        (0.0, 0.0, config.bottom_height / 2.0)
    )
    middle_top_radius = max(_EPSILON, config.large_diameter / 2.0 - config.middle_height)
    middle = bd.Cone(config.large_diameter / 2.0, middle_top_radius, config.middle_height).translate(
        (0.0, 0.0, config.bottom_height + config.middle_height / 2.0 - _EPSILON)
    )
    top = bd.Cylinder(config.small_diameter / 2.0, config.top_height).translate(
        (0.0, 0.0, config.bottom_height + config.middle_height + config.top_height / 2.0 - _EPSILON)
    )
    head = _fuse((cast(Shape, bottom), cast(Shape, middle), cast(Shape, top)))
    if config.top_pattern == "coin_slot":
        head = _subtract_connector_slot(head, connector_slot, config.total_height)
    elif config.top_pattern == "dimple":
        head = cast(Shape, head - bd.Cone(1.0, _EPSILON, 1.0).translate((0.0, 0.0, config.total_height - 0.5)))
    return head


def build_multiconnect_screw(config: MulticonnectScrewConfig = MulticonnectScrewConfig()) -> Shape:
    """Build a snap-thread-backed Multiconnect screw."""

    config.validate()
    head = build_multiconnect_head(config.head, config.connector_slot)
    threads = build_snap_threads(replace(config.threads, clearance=0.0)).translate(
        (0.0, 0.0, config.head.total_height - _EPSILON)
    )
    screw = cast(Shape, head + threads)
    return _engrave_text(screw, config.text, config.head.total_height + config.threads.height)


def build_opengrid_snap(config: OpenGridSnapConfig = OpenGridSnapConfig()) -> Shape:
    """Build assembled snap products from the parametric source generator."""

    config.validate()
    if config.kind is OpenGridSnapKind.SELF_EXPANDING_THREADS:
        expanding = replace(
            config.expanding_snap,
            snap_body=config.snap_body,
            threads=config.threads,
            center_offset=config.center_offset,
        )
        return _engrave_text(build_expanding_snap(expanding), config.text, config.snap_body.thickness)

    body = _engrave_text(build_snap_body(config.snap_body), config.text, config.snap_body.thickness)
    if config.kind is OpenGridSnapKind.BARE:
        return body
    attachment = _opengrid_snap_attachment(config)
    if attachment is None:
        return body
    return cast(Shape, body + attachment.translate((config.center_offset[0], config.center_offset[1], config.snap_body.thickness - _EPSILON)))




def build_multiconnect_profile(config: MulticonnectConfig = MulticonnectConfig()) -> tuple[Point2D, ...]:
    """Return the right-half Multiconnect dovetail profile coordinates.

    Male connector profiles use no offset. Receiver, backer, and rail delete
    tool profiles apply the source receiver/delete-tool offset.
    """
    config.validate()
    spec = _multiconnect_dimensions(config)
    offset = spec.receiver_offset if _multiconnect_part_uses_receiver_offset(config.part_kind) else 0.0
    return _dimensions_to_multiconnect_coords(
        spec.radius,
        spec.capture_depth,
        spec.dovetail_depth,
        spec.stem_depth,
        offset,
    )


def build_multiconnect_part(config: MulticonnectConfig = MulticonnectConfig()) -> Shape:
    """Build the Multiconnect solid selected by ``config.part_kind``."""

    config.validate()
    if config.part_kind is MulticonnectPartKind.CONNECTOR_ROUND:
        return _multiconnect_round_connector(config, double_sided=False)
    if config.part_kind is MulticonnectPartKind.CONNECTOR_RAIL:
        return build_multiconnect_rail(config)
    if config.part_kind is MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_ROUND:
        return _multiconnect_round_connector(config, double_sided=True)
    if config.part_kind is MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_RAIL:
        return _multiconnect_double_sided(build_multiconnect_rail(config))
    if config.part_kind is MulticonnectPartKind.CONNECTOR_RAIL_DELETE_TOOL:
        return build_multiconnect_delete_tool(config)
    if config.part_kind in {
        MulticonnectPartKind.RECEIVER_OPEN_ENDED,
        MulticonnectPartKind.RECEIVER_PASSTHROUGH,
    }:
        return build_multiconnect_receiver(config)
    return build_multiconnect_backer(config)


def build_multiconnect_rail(config: MulticonnectConfig = MulticonnectConfig()) -> Shape:
    """Build a male Multiconnect rail from the mirrored dovetail profile.

    The rail is centered on X, extends from Y=0 to the profile depth, and runs
    along +Z. `length` is the straight rail length; rounded end caps extend
    beyond it by the profile radius, matching the source customizer semantics.
    """
    config.validate()
    rail_config = replace(config, part_kind=MulticonnectPartKind.CONNECTOR_RAIL)
    profile = build_multiconnect_profile(rail_config)
    spec = _multiconnect_dimensions(config)
    rail = _multiconnect_linear_tool(profile, config.length)
    if config.rounding is not MulticonnectRounding.NONE:
        rail = cast(Shape, rail + _multiconnect_end_cap(profile, at_end=False))
    if config.rounding is MulticonnectRounding.BOTH_SIDES:
        rail = cast(Shape, rail + _multiconnect_end_cap(profile, at_end=True).translate((0.0, 0.0, config.length)))
    if config.dimples_enabled:
        rail = rail - _multiconnect_dimples(config, spec.dimple_radius, config.length)
    return cast(Shape, rail)


def build_multiconnect_delete_tool(config: MulticonnectConfig = MulticonnectConfig()) -> Shape:
    """Build the receiver/backer negative tool for a Multiconnect rail slot."""

    config.validate()
    return _multiconnect_slot_tool(replace(config, part_kind=MulticonnectPartKind.CONNECTOR_RAIL_DELETE_TOOL))


def build_multiconnect_receiver(config: MulticonnectConfig = MulticonnectConfig()) -> Shape:
    """Build a single Multiconnect receiver block with one rail slot."""

    config.validate()
    part_kind = _multiconnect_receiver_part_kind(config)
    slot_config = replace(config, part_kind=part_kind)
    profile = build_multiconnect_profile(slot_config)
    slot_width = _multiconnect_profile_width(profile)
    slot_depth = _multiconnect_profile_depth(profile)
    body = bd.Box(
        slot_width + 2.0 * config.receiver_side_wall_thickness,
        slot_depth + config.receiver_back_thickness,
        config.length,
    ).translate((0.0, (slot_depth + config.receiver_back_thickness) / 2.0, config.length / 2.0))
    tool = _multiconnect_slot_tool(slot_config).translate(
        (0.0, config.receiver_back_thickness, _multiconnect_slot_z_offset(slot_config, profile))
    )
    return cast(Shape, body - tool)


def build_multiconnect_backer(config: MulticonnectConfig = MulticonnectConfig()) -> Shape:
    """Build a Multiconnect slotted backer with openGrid-spaced slot columns."""

    config.validate()
    part_kind = _multiconnect_backer_part_kind(config)
    backer_config = replace(config, part_kind=part_kind)
    profile = build_multiconnect_profile(backer_config)
    slot_depth = _multiconnect_profile_depth(profile)
    slot_count = max(1, math.floor(config.width / config.grid_size))
    effective_width = max(config.width, config.grid_size)
    body = bd.Box(effective_width, slot_depth + config.receiver_back_thickness, config.length).translate(
        (0.0, (slot_depth + config.receiver_back_thickness) / 2.0, config.length / 2.0)
    )
    slot_tool = _multiconnect_slot_tool(backer_config)
    slots = [
        slot_tool.translate(
            (x_offset, config.receiver_back_thickness, _multiconnect_slot_z_offset(backer_config, profile))
        )
        for x_offset in _multiconnect_slot_x_offsets(slot_count, config.grid_size)
    ]
    return cast(Shape, body - _fuse(slots))


def _multiconnect_receiver_part_kind(config: MulticonnectConfig) -> MulticonnectPartKind:
    if config.part_kind is MulticonnectPartKind.RECEIVER_PASSTHROUGH:
        return MulticonnectPartKind.RECEIVER_PASSTHROUGH
    return MulticonnectPartKind.RECEIVER_OPEN_ENDED


def _multiconnect_backer_part_kind(config: MulticonnectConfig) -> MulticonnectPartKind:
    if config.part_kind is MulticonnectPartKind.BACKER_PASSTHROUGH:
        return MulticonnectPartKind.BACKER_PASSTHROUGH
    return MulticonnectPartKind.BACKER_OPEN_ENDED


def _multiconnect_is_open_ended_receiver(part_kind: MulticonnectPartKind) -> bool:
    return part_kind in {
        MulticonnectPartKind.RECEIVER_OPEN_ENDED,
        MulticonnectPartKind.BACKER_OPEN_ENDED,
    }


def _multiconnect_slot_z_offset(config: MulticonnectConfig, profile: Sequence[Point2D]) -> float:
    if not _multiconnect_is_open_ended_receiver(config.part_kind):
        return -_EPSILON
    return -(_multiconnect_profile_width(profile) / 2.0 + config.receiver_top_wall_thickness)




@dataclass(frozen=True, slots=True)
class _MulticonnectDimensions:
    radius: float
    capture_depth: float
    dovetail_depth: float
    stem_depth: float
    receiver_offset: float
    dimple_radius: float


_MULTICONNECT_PRESETS: dict[MulticonnectProfile, _MulticonnectDimensions] = {
    MulticonnectProfile.STANDARD: _MulticonnectDimensions(
        radius=_MULTICONNECT_STANDARD_RADIUS,
        capture_depth=_MULTICONNECT_STANDARD_DEPTH1,
        dovetail_depth=_MULTICONNECT_STANDARD_DEPTH2,
        stem_depth=_MULTICONNECT_STANDARD_DEPTH3,
        receiver_offset=_MULTICONNECT_STANDARD_OFFSET,
        dimple_radius=_MULTICONNECT_STANDARD_DIMPLE_RADIUS,
    ),
    MulticonnectProfile.JR: _MulticonnectDimensions(
        radius=5.0,
        capture_depth=0.6,
        dovetail_depth=1.2,
        stem_depth=0.4,
        receiver_offset=0.16,
        dimple_radius=0.8,
    ),
    MulticonnectProfile.MINI: _MulticonnectDimensions(
        radius=3.2,
        capture_depth=1.0,
        dovetail_depth=1.2,
        stem_depth=0.4,
        receiver_offset=0.16,
        dimple_radius=0.8,
    ),
    MulticonnectProfile.MULTIPOINT_BETA: _MulticonnectDimensions(
        radius=7.9,
        capture_depth=0.4,
        dovetail_depth=2.2,
        stem_depth=0.4,
        receiver_offset=0.15,
        dimple_radius=0.8,
    ),
}


def _multiconnect_dimensions(config: MulticonnectConfig) -> _MulticonnectDimensions:
    if config.profile is MulticonnectProfile.CUSTOM:
        return _MulticonnectDimensions(
            radius=config.radius,
            capture_depth=config.capture_depth,
            dovetail_depth=config.dovetail_depth,
            stem_depth=config.stem_depth,
            receiver_offset=config.receiver_offset,
            dimple_radius=config.dimple_radius,
        )
    return _MULTICONNECT_PRESETS[config.profile]


def _multiconnect_part_uses_receiver_offset(part_kind: MulticonnectPartKind) -> bool:
    return part_kind in {
        MulticonnectPartKind.CONNECTOR_RAIL_DELETE_TOOL,
        MulticonnectPartKind.RECEIVER_OPEN_ENDED,
        MulticonnectPartKind.RECEIVER_PASSTHROUGH,
        MulticonnectPartKind.BACKER_OPEN_ENDED,
        MulticonnectPartKind.BACKER_PASSTHROUGH,
    }


def _dimensions_to_multiconnect_coords(
    radius: float,
    capture_depth: float,
    dovetail_depth: float,
    stem_depth: float,
    offset: float,
) -> tuple[Point2D, ...]:
    offset_bevel = math.sin(math.radians(45.0)) * offset * 2.0 if offset != 0.0 else 0.0
    return (
        (0.0, 0.0),
        (radius + offset, 0.0),
        (radius + offset, capture_depth + offset_bevel),
        (radius - dovetail_depth + offset, dovetail_depth + capture_depth + offset_bevel),
        (radius - dovetail_depth + offset, dovetail_depth + capture_depth + stem_depth + offset),
        (0.0, dovetail_depth + capture_depth + stem_depth + offset),
    )


def _multiconnect_full_profile(profile: Sequence[Point2D]) -> tuple[Point2D, ...]:
    return (*profile, *((-x, y) for x, y in reversed(profile[1:-1])))


def _multiconnect_profile_width(profile: Sequence[Point2D]) -> float:
    return max(x for x, _ in profile) * 2.0


def _multiconnect_profile_depth(profile: Sequence[Point2D]) -> float:
    return max(y for _, y in profile)


def _multiconnect_linear_tool(profile: Sequence[Point2D], length: float) -> Shape:
    with bd.BuildSketch() as sketch:
        bd.Polygon(_multiconnect_full_profile(profile), align=None)
    return cast(Shape, bd.extrude(sketch.sketch, amount=length))


def _multiconnect_end_cap(profile: Sequence[Point2D], *, at_end: bool) -> Shape:
    radius = _multiconnect_profile_width(profile) / 2.0
    depth = _multiconnect_profile_depth(profile)
    face = bd.Face(bd.Wire.make_polygon((*profile, profile[0])))
    revolved = bd.Solid.revolve(face, 360.0, bd.Axis.Y)
    z_center = radius / 2.0 if at_end else -radius / 2.0
    half_space = bd.Box(
        2.0 * radius + 2.0 * _EPSILON,
        depth + 2.0 * _EPSILON,
        radius + 2.0 * _EPSILON,
    ).translate((0.0, depth / 2.0, z_center))
    return cast(Shape, revolved & half_space)


def _multiconnect_round_connector(config: MulticonnectConfig, *, double_sided: bool) -> Shape:
    round_config = replace(config, part_kind=MulticonnectPartKind.CONNECTOR_ROUND)
    profile = build_multiconnect_profile(round_config)
    round_connector = cast(
        Shape,
        _multiconnect_end_cap(profile, at_end=False)
        + _multiconnect_end_cap(profile, at_end=True),
    )
    if config.dimples_enabled:
        spec = _multiconnect_dimensions(config)
        round_connector = cast(
            Shape,
            round_connector - _multiconnect_dimples(config, spec.dimple_radius, 0.0),
        )
    if not double_sided:
        return round_connector
    return _multiconnect_double_sided(round_connector)


def _multiconnect_double_sided(shape: Shape) -> Shape:
    return cast(Shape, shape + shape.rotate(bd.Axis.Z, 180.0))


def _multiconnect_slot_tool(config: MulticonnectConfig) -> Shape:
    profile = build_multiconnect_profile(config)
    spec = _multiconnect_dimensions(config)
    tool = _multiconnect_linear_tool(profile, config.length + 2.0 * _EPSILON)
    if config.rounding is not MulticonnectRounding.NONE:
        tool = cast(Shape, tool + _multiconnect_end_cap(profile, at_end=False))
    if config.rounding is MulticonnectRounding.BOTH_SIDES:
        tool = cast(
            Shape,
            tool + _multiconnect_end_cap(profile, at_end=True).translate((0.0, 0.0, config.length)),
        )
    if config.dimples_enabled:
        tool = cast(Shape, tool - _multiconnect_dimples(config, spec.dimple_radius, config.length))
    if config.on_ramps_enabled:
        tool = cast(Shape, tool + _multiconnect_on_ramps(config, profile))
    return tool




def _multiconnect_dimples(config: MulticonnectConfig, dimple_radius: float, length: float) -> Shape:
    dimple_size = dimple_radius * config.dimple_scale
    dimples = [
        bd.Cone(dimple_size, 0.0, dimple_size + _EPSILON, rotation=(90.0, 0.0, 0.0)).translate(
            (0.0, -_EPSILON, z_offset)
        )
        for z_offset in _multiconnect_dimple_z_offsets(length, config.grid_size)
    ]
    return _fuse(dimples)


def _multiconnect_dimple_z_offsets(length: float, spacing: float) -> tuple[float, ...]:
    if length <= _EPSILON:
        return (0.0,)
    count = math.ceil(length / spacing) + 1
    start = -length + length % spacing
    return tuple(start + index * spacing for index in range(count))


def _multiconnect_on_ramps(config: MulticonnectConfig, profile: Sequence[Point2D]) -> Shape:
    radius = _multiconnect_profile_width(profile) / 2.0
    depth = _multiconnect_profile_depth(profile)
    ramps = [
        bd.Cone(radius + 1.5, radius, depth + 2.0 * _EPSILON, rotation=(90.0, 0.0, 0.0)).translate(
            (0.0, depth / 2.0, z_offset)
        )
        for z_offset in _multiconnect_on_ramp_z_offsets(config)
    ]
    if not ramps:
        return bd.Part()
    bounds = bd.Box(
        2.0 * (radius + 1.5),
        depth,
        config.length + _multiconnect_profile_width(profile) + 2.0 * _EPSILON,
    ).translate((0.0, depth / 2.0, config.length / 2.0))
    return cast(Shape, _fuse(ramps) & bounds)


def _multiconnect_on_ramp_z_offsets(config: MulticonnectConfig) -> tuple[float, ...]:
    spacing = config.grid_size * config.on_ramp_every_n_holes
    start = config.grid_size * config.on_ramp_start_offset
    if _multiconnect_is_open_ended_receiver(config.part_kind):
        start += spacing
    count = math.floor(config.length / spacing) + 1
    return tuple(
        z_offset
        for index in range(count)
        if (z_offset := start + index * spacing) <= config.length + _EPSILON
    )


def _multiconnect_slot_x_offsets(slot_count: int, grid_size: float) -> tuple[float, ...]:
    center = (slot_count - 1) / 2.0
    return tuple((index - center) * grid_size for index in range(slot_count))


def _snap_body_core(config: SnapBodyConfig) -> Shape:
    return _extrude_xy_polygon(_chamfered_rectangle_points(config.width, config.height, config.corner_chamfer), config.thickness)


def _chamfered_rectangle_points(width: float, height: float, chamfer: float) -> tuple[Point2D, ...]:
    half_width = width / 2.0
    half_height = height / 2.0
    if chamfer <= _EPSILON:
        return (
            (-half_width, -half_height),
            (half_width, -half_height),
            (half_width, half_height),
            (-half_width, half_height),
        )
    return (
        (-half_width + chamfer, -half_height),
        (half_width - chamfer, -half_height),
        (half_width, -half_height + chamfer),
        (half_width, half_height - chamfer),
        (half_width - chamfer, half_height),
        (-half_width + chamfer, half_height),
        (-half_width, half_height - chamfer),
        (-half_width, -half_height + chamfer),
    )


def _extrude_xy_polygon(points: Sequence[Point2D], height: float) -> Shape:
    with bd.BuildSketch() as sketch:
        bd.Polygon(*points, align=None)
    return cast(Shape, bd.extrude(sketch.sketch, amount=height))


def _snap_body_corner_features(config: SnapBodyConfig) -> Shape:
    features: list[Shape] = []
    top_height = min(config.corner_edge_height, config.thickness)
    if top_height <= _EPSILON:
        return bd.Part()
    top_z = config.thickness - top_height
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            features.append(_snap_body_corner_patch(config, sx, sy, config.top_corner_extrude, top_height, top_z))
    if config.body_shape is SnapBodyShape.DIRECTIONAL and config.thickness >= _DEFAULT_TILE_THICKNESS:
        for sx in (-1.0, 1.0):
            features.append(_snap_body_corner_patch(config, sx, 1.0, config.bottom_corner_extrude, top_height, 0.0))
    return _fuse(features)


def _snap_body_corner_patch(
    config: SnapBodyConfig,
    sx: float,
    sy: float,
    extrude: float,
    height: float,
    z_base: float,
) -> Shape:
    if extrude <= _EPSILON or config.corner_chamfer <= _EPSILON:
        return bd.Part()
    half_width = config.width / 2.0
    half_height = config.height / 2.0
    fill = min(config.corner_chamfer, extrude * math.sqrt(2.0))
    raw_points = (
        (sx * (half_width - config.corner_chamfer), sy * half_height),
        (sx * (half_width - config.corner_chamfer + fill), sy * half_height),
        (sx * half_width, sy * (half_height - config.corner_chamfer + fill)),
        (sx * half_width, sy * (half_height - config.corner_chamfer)),
    )
    return _extrude_xy_polygon(_ordered_points(raw_points), height).translate((0.0, 0.0, z_base))


def _ordered_points(points: Sequence[Point2D]) -> tuple[Point2D, ...]:
    center_x = sum(x for x, _ in points) / len(points)
    center_y = sum(y for _, y in points) / len(points)
    return tuple(sorted(points, key=lambda point: math.atan2(point[1] - center_y, point[0] - center_x)))


def _snap_body_nubs(config: SnapBodyConfig) -> Shape:
    nubs: list[Shape] = []
    for side in ("front", "left", "right", "back"):
        spec = _snap_body_nub_spec(config, side)
        tangent_length = _snap_body_side_tangent_length(config, side) - spec.inset * 2.0
        upper_z = config.thickness - config.nub_offset_to_top
        lower_z = max(0.0, upper_z - spec.height)
        if tangent_length > _EPSILON and spec.depth > _EPSILON and upper_z - lower_z > _EPSILON:
            nubs.append(_snap_body_nub(config, side, tangent_length, lower_z, upper_z, spec))
    return _fuse(nubs)


def _snap_body_nub_spec(config: SnapBodyConfig, side: str) -> _SnapBodyNubSpec:
    basic_height = _snap_body_standard_or_lite(config, config.basic_nub_height_standard, config.basic_nub_height_lite)
    if config.body_shape is SnapBodyShape.DIRECTIONAL and side == "back":
        return _SnapBodyNubSpec(
            inset=config.directional_nub_width_inset,
            depth=config.directional_nub_depth,
            width_tip_taper=config.directional_nub_width_tip_taper,
            top_angle=config.directional_nub_top_angle,
            bottom_angle=_snap_body_standard_or_lite(
                config,
                config.directional_nub_bottom_angle_standard,
                config.directional_nub_bottom_angle_lite,
            ),
            height=_snap_body_standard_or_lite(
                config,
                config.directional_nub_height_standard,
                config.directional_nub_height_lite,
            ),
        )
    if config.body_shape is SnapBodyShape.DIRECTIONAL and side == "front":
        return _SnapBodyNubSpec(
            inset=config.basic_nub_width_inset,
            depth=config.basic_nub_depth,
            width_tip_taper=config.basic_nub_width_tip_taper,
            top_angle=config.basic_nub_top_angle,
            bottom_angle=config.basic_nub_bottom_angle,
            height=_snap_body_standard_or_lite(
                config,
                config.antidirect_nub_height_standard,
                config.antidirect_nub_height_lite,
            ),
        )
    return _SnapBodyNubSpec(
        inset=config.basic_nub_width_inset,
        depth=config.basic_nub_depth,
        width_tip_taper=config.basic_nub_width_tip_taper,
        top_angle=config.basic_nub_top_angle,
        bottom_angle=config.basic_nub_bottom_angle,
        height=basic_height,
    )


@dataclass(frozen=True, slots=True)
class _SnapBodyNubSpec:
    inset: float
    depth: float
    width_tip_taper: float
    top_angle: float
    bottom_angle: float
    height: float


def _snap_body_nub(
    config: SnapBodyConfig,
    side: str,
    tangent_length: float,
    lower_z: float,
    upper_z: float,
    spec: _SnapBodyNubSpec,
) -> Shape:
    outer_length = max(_EPSILON, tangent_length - spec.width_tip_taper)
    top_drop = _snap_body_angle_shift(spec.depth, spec.top_angle)
    bottom_rise = _snap_body_angle_shift(spec.depth, spec.bottom_angle)
    outer_lower_z = min(upper_z - _EPSILON, lower_z + bottom_rise)
    outer_upper_z = max(outer_lower_z + _EPSILON, upper_z - top_drop)
    inner = _snap_body_side_rectangle(config, side, tangent_length, lower_z, upper_z, spec.depth, outside=True, outer=False)
    outer = _snap_body_side_rectangle(config, side, outer_length, outer_lower_z, outer_upper_z, spec.depth, outside=True, outer=True)
    return cast(Shape, bd.ConvexPolyhedron((*inner, *outer), align=bd.Align.NONE))


def _snap_body_angle_shift(depth: float, angle_degrees: float) -> float:
    if angle_degrees <= _EPSILON:
        return 0.0
    return depth / math.tan(math.radians(angle_degrees))


def _snap_body_standard_or_lite(config: SnapBodyConfig, standard: float, lite: float) -> float:
    if config.thickness >= _DEFAULT_TILE_THICKNESS:
        return standard
    return lite


def _snap_body_side_tangent_length(config: SnapBodyConfig, side: str) -> float:
    if side in {"front", "back"}:
        return config.width
    return config.height


def _snap_body_cut_tools(config: SnapBodyConfig) -> Shape:
    tools: list[Shape] = []
    for side in ("front", "left", "right", "back"):
        if not (config.body_shape is SnapBodyShape.DIRECTIONAL and side == "back"):
            tools.append(_snap_body_bottom_cut(config, side))
        if side != "front" or config.enable_uninstall_notch:
            tools.append(_snap_body_side_cut(config, side))
    if config.body_shape is SnapBodyShape.DIRECTIONAL and config.enable_directional_slants:
        tools.append(_snap_body_directional_slant_tool(config))
    return _fuse(tools)


def _snap_body_bottom_cut(config: SnapBodyConfig, side: str) -> Shape:
    length = _snap_body_side_tangent_length(config, side) - config.cut_width_inset * 2.0
    cut_height = max(0.0, config.thickness - config.bottom_cut_offset_to_top + _EPSILON)
    return _snap_side_box(
        config,
        side,
        length,
        config.bottom_cut_thickness,
        cut_height,
        cut_height / 2.0 - _EPSILON / 2.0,
        outside=False,
        offset=config.bottom_cut_offset_to_edge,
    )


def _snap_body_side_cut(config: SnapBodyConfig, side: str) -> Shape:
    length = _snap_body_side_tangent_length(config, side) - config.cut_width_inset * 2.0
    upper_z = config.thickness - config.side_cut_offset_to_top
    lower_z = max(0.0, upper_z - config.side_cut_thickness)
    cut_height = upper_z - lower_z
    return _snap_side_box(
        config,
        side,
        length,
        config.side_cut_depth,
        cut_height,
        (lower_z + upper_z) / 2.0,
        outside=False,
    )


def _snap_body_directional_slant_tool(config: SnapBodyConfig) -> Shape:
    depth = _snap_body_standard_or_lite(
        config,
        config.directional_slant_depth_standard,
        config.directional_slant_depth_lite,
    )
    height = _snap_body_standard_or_lite(
        config,
        config.directional_slant_height_standard,
        config.directional_slant_height_lite,
    )
    length = config.width - config.cut_width_inset * 2.0
    slant_height = min(height, config.thickness)
    lower = _snap_body_side_rectangle(
        config,
        "front",
        length,
        0.0,
        slant_height,
        depth,
        outside=False,
        outer=True,
        offset=config.bottom_cut_offset_to_edge + config.bottom_cut_thickness,
    )
    upper = _snap_body_side_rectangle(
        config,
        "front",
        length,
        slant_height,
        slant_height + _EPSILON,
        _EPSILON,
        outside=False,
        outer=False,
        offset=config.bottom_cut_offset_to_edge + config.bottom_cut_thickness,
    )
    return cast(Shape, bd.ConvexPolyhedron((*lower, *upper), align=bd.Align.NONE))


def _snap_body_uninstall_notch_tool(config: SnapBodyConfig) -> Shape:
    surface_height = _snap_body_standard_or_lite(
        config,
        config.notch_surface_height_standard,
        config.notch_surface_height_lite,
    )
    gap_height = _snap_body_standard_or_lite(
        config,
        config.notch_gap_height_standard,
        config.notch_gap_height_lite,
    )
    surface = _snap_side_box(
        config,
        "front",
        config.notch_width,
        config.notch_surface_inset,
        surface_height,
        config.thickness - surface_height / 2.0,
        outside=False,
    )
    gap = _snap_side_box(
        config,
        "front",
        config.notch_width,
        config.notch_gap_inset,
        gap_height,
        config.thickness - surface_height - gap_height / 2.0,
        outside=False,
        offset=config.notch_surface_inset,
    )
    return _fuse((surface, gap))


def _snap_body_side_rectangle(
    config: SnapBodyConfig,
    side: str,
    length: float,
    lower_z: float,
    upper_z: float,
    depth: float,
    *,
    outside: bool,
    outer: bool,
    offset: float = 0.0,
) -> tuple[Point3D, ...]:
    half_length = length / 2.0
    if side in {"front", "back"}:
        sign = 1.0 if side == "back" else -1.0
        y_inner = sign * config.height / 2.0
        y_outer = sign * (config.height / 2.0 + depth)
        if not outside:
            y_inner = sign * (config.height / 2.0 - offset)
            y_outer = sign * (config.height / 2.0 - offset - depth)
        y = y_outer if outer else y_inner
        return (
            (-half_length, y, lower_z),
            (half_length, y, lower_z),
            (half_length, y, upper_z),
            (-half_length, y, upper_z),
        )
    sign = 1.0 if side == "right" else -1.0
    x_inner = sign * config.width / 2.0
    x_outer = sign * (config.width / 2.0 + depth)
    if not outside:
        x_inner = sign * (config.width / 2.0 - offset)
        x_outer = sign * (config.width / 2.0 - offset - depth)
    x = x_outer if outer else x_inner
    return (
        (x, -half_length, lower_z),
        (x, half_length, lower_z),
        (x, half_length, upper_z),
        (x, -half_length, upper_z),
    )


def _snap_side_box(
    config: SnapBodyConfig,
    side: str,
    length: float,
    depth: float,
    height: float,
    z_center: float,
    *,
    outside: bool,
    offset: float = 0.0,
) -> Shape:
    if min(length, depth, height) <= _EPSILON:
        return bd.Part()
    if side in {"front", "back"}:
        sign = 1.0 if side == "back" else -1.0
        y_abs = config.height / 2.0 + depth / 2.0 if outside else config.height / 2.0 - offset - depth / 2.0
        return cast(Shape, bd.Box(length, depth, height).translate((0.0, sign * y_abs, z_center)))
    sign = 1.0 if side == "right" else -1.0
    x_abs = config.width / 2.0 + depth / 2.0 if outside else config.width / 2.0 - offset - depth / 2.0
    return cast(Shape, bd.Box(depth, length, height).translate((sign * x_abs, 0.0, z_center)))


def _expanding_snap_removal_tool(config: ExpandingSnapConfig) -> Shape:
    return _compound(
        (
            _expanding_thread_tool(config),
            _expanding_spring_gap_tools(config),
        )
    )


def _expanding_thread_tool(config: ExpandingSnapConfig) -> Shape:
    height = config.snap_body.thickness
    entry_height = min(_expanding_snap_entry_height(config), height)
    end_height = min(_expanding_snap_end_height(config), max(0.0, height - entry_height))
    transition_height = max(0.0, height - entry_height - end_height)
    tools: list[Shape] = []
    if entry_height > _EPSILON:
        tools.append(_snap_thread_cut_tool(config, entry_height + _EPSILON).translate((0.0, 0.0, -_EPSILON / 2.0)))

    distance = _expanding_snap_distance(config)
    transition_offset = distance / 2.0
    if transition_height > _EPSILON:
        tools.extend(
            _expanded_thread_pair(
                config,
                transition_height + _EPSILON,
                entry_height - _EPSILON / 2.0,
                transition_offset,
            )
        )
    if end_height > _EPSILON:
        tools.extend(
            _expanded_thread_pair(
                config,
                end_height + _EPSILON,
                entry_height + transition_height - _EPSILON / 2.0,
                distance,
            )
        )
    return _compound(tools)


def _expanded_thread_pair(
    config: ExpandingSnapConfig,
    height: float,
    z_base: float,
    distance: float,
) -> tuple[Shape, Shape]:
    thread = _snap_thread_cut_tool(config, height)
    return (
        thread.translate((*_polar_offset(config.expand_split_angle, distance), z_base)),
        thread.translate((*_polar_offset(config.expand_split_angle + 180.0, distance), z_base)),
    )


def _snap_thread_cut_tool(config: ExpandingSnapConfig, height: float) -> Shape:
    return _snap_thread_loft(
        replace(config.threads, height=height),
        base_segments=_SNAP_THREAD_CUT_BASE_SEGMENTS,
        z_segments_per_pitch=_SNAP_THREAD_CUT_Z_SEGMENTS_PER_PITCH,
    )




def _expanding_spring_gap_tools(config: ExpandingSnapConfig) -> Shape:
    body = config.snap_body
    thread_radius = config.threads.effective_diameter / 2.0
    reach = thread_radius + config.spring_to_center_thickness + config.spring_thickness
    gap_length = max(body.width, body.height)
    gap_height = body.thickness + 2.0 * _EPSILON
    radial_gaps = (
        _radial_gap_tool(config.expand_split_angle, reach, gap_length, config.spring_gap, gap_height),
        _radial_gap_tool(config.expand_split_angle + 180.0, reach, gap_length, config.spring_gap, gap_height),
    )
    center_split = _rotated_box(
        max(body.width, body.height) + 2.0,
        config.spring_gap,
        gap_height,
        config.expand_split_angle + 90.0,
        (0.0, 0.0, body.thickness / 2.0),
    )
    return _compound((*radial_gaps, center_split))


def _radial_gap_tool(angle_degrees: float, start: float, length: float, width: float, height: float) -> Shape:
    center_distance = start + length / 2.0
    x, y = _polar_offset(angle_degrees, center_distance)
    return _rotated_box(length, width, height, angle_degrees, (x, y, height / 2.0 - _EPSILON))


def _rotated_box(width: float, depth: float, height: float, angle_degrees: float, center: Point3D) -> Shape:
    return cast(Shape, bd.Box(width, depth, height).rotate(bd.Axis.Z, angle_degrees).translate(center))


def _polar_offset(angle_degrees: float, distance: float) -> Point2D:
    angle = math.radians(angle_degrees)
    return (math.cos(angle) * distance, math.sin(angle) * distance)


def _expanding_snap_distance(config: ExpandingSnapConfig) -> float:
    if config.snap_body.thickness >= _DEFAULT_TILE_THICKNESS:
        return config.expand_distance_standard
    return config.expand_distance_lite


def _expanding_snap_entry_height(config: ExpandingSnapConfig) -> float:
    if config.threads.thread_type is ThreadType.BLUNT:
        return config.expand_entry_height_blunt
    if config.snap_body.thickness >= _DEFAULT_TILE_THICKNESS:
        return config.expand_entry_height_standard
    return config.expand_entry_height_lite


def _expanding_snap_end_height(config: ExpandingSnapConfig) -> float:
    if config.snap_body.thickness >= _DEFAULT_TILE_THICKNESS:
        return config.expand_end_height_standard
    return config.expand_end_height_lite


def build_snap_threads(config: SnapThreadConfig = SnapThreadConfig()) -> Shape:
    config.validate()
    return _snap_thread_loft(config)


def _snap_thread_loft(
    config: SnapThreadConfig,
    *,
    base_segments: int = _SNAP_THREAD_BASE_SEGMENTS,
    z_segments_per_pitch: int = _SNAP_THREAD_Z_SEGMENTS_PER_PITCH,
) -> Shape:
    diameter = config.effective_diameter
    rotation = config.offset_angle + _OG_SNAP_THREADS_COMPATIBILITY_ANGLE
    bottom_bevel = _snap_thread_bottom_bevel(config)
    angles = _snap_thread_angles(rotation, base_segments=base_segments)
    profile = _scaled_snap_thread_profile(config.pitch)
    sketches: list[bd.Sketch] = []
    for z in _snap_thread_z_values(config, rotation, z_segments_per_pitch=z_segments_per_pitch):
        points = tuple(
            _snap_thread_point(config, profile, angle, z, diameter, bottom_bevel, rotation)
            for angle in angles
        )
        with bd.BuildSketch(bd.Plane.XY.offset(z)) as sketch:
            bd.Polygon(points, align=None)
        sketches.append(sketch.sketch)
    return cast(Shape, bd.loft(sketches, ruled=True, clean=False))


def _snap_thread_point(
    config: SnapThreadConfig,
    profile: Sequence[Point2D],
    angle_degrees: float,
    z: float,
    diameter: float,
    bottom_bevel: float,
    rotation: float,
) -> Point2D:
    offset = _snap_thread_radial_offset(config, profile, angle_degrees, z)
    radius = diameter / 2.0 + offset
    radius = min(radius, _snap_thread_bevel_radius(config, z, diameter, bottom_bevel))

    angle = math.radians(angle_degrees + rotation)
    return (radius * math.cos(angle), radius * math.sin(angle))


def _snap_thread_radial_offset(config: SnapThreadConfig, profile: Sequence[Point2D], angle_degrees: float, z: float) -> float:
    pitch = config.pitch
    local_z = z
    if config.thread_type is ThreadType.BLUNT:
        local_z = _snap_thread_blunt_local_z(config, z)
    local = ((local_z - angle_degrees * pitch / 360.0 + pitch / 2.0) % pitch) - pitch / 2.0
    root_offset = profile[0][1]
    if local < profile[0][0] or local > profile[-1][0]:
        return root_offset
    for (x0, y0), (x1, y1) in zip(profile, profile[1:]):
        if x0 <= local <= x1:
            if x0 == x1:
                return y1
            ratio = (local - x0) / (x1 - x0)
            return y0 + (y1 - y0) * ratio
    return root_offset


def _snap_thread_blunt_local_z(config: SnapThreadConfig, z: float) -> float:
    return z + _snap_thread_blunt_z_shift(config)


def _snap_thread_blunt_z_shift(config: SnapThreadConfig) -> float:
    bottom_bevel = _snap_thread_bottom_bevel(config)
    offset_height = min(config.height - _SNAP_THREAD_LEAD_IN_OFFSET - bottom_bevel, 0.0)
    return _SNAP_THREAD_MIN_TURNS * config.pitch - offset_height - 0.25


def _snap_thread_bevel_radius(
    config: SnapThreadConfig,
    z: float,
    diameter: float,
    bottom_bevel: float,
    *,
    clamp_to_root: bool = True,
) -> float:
    radius = diameter / 2.0
    if bottom_bevel > 0.0 and z < bottom_bevel:
        radius = min(radius, diameter / 2.0 - bottom_bevel + z)
    if config.top_bevel > 0.0 and z > config.height - config.top_bevel:
        radius = min(radius, diameter / 2.0 - z + config.height - config.top_bevel)
    if config.thread_type is ThreadType.BLUNT and config.blunt_cutoff and z > config.height - _EPSILON:
        radius = min(radius, diameter / 2.0 - config.pitch / 3.0)
    if clamp_to_root:
        return max(radius, diameter / 2.0 - config.pitch / 3.0)
    return radius


def _snap_thread_bottom_bevel(config: SnapThreadConfig) -> float:
    if config.height >= _DEFAULT_TILE_THICKNESS:
        return config.bottom_bevel_standard
    if config.height >= 3.4:
        return config.bottom_bevel_lite
    return 0.0


def _scaled_snap_thread_profile(pitch: float) -> tuple[Point2D, ...]:
    return tuple((x * pitch, y * pitch) for x, y in _OG_SNAP_THREADS_PROFILE)


def _snap_thread_angles(rotation: float, *, base_segments: int = _SNAP_THREAD_BASE_SEGMENTS) -> tuple[float, ...]:
    del rotation
    return tuple(360.0 * index / base_segments for index in range(base_segments))


def _snap_thread_z_values(
    config: SnapThreadConfig,
    rotation: float,
    *,
    z_segments_per_pitch: int = _SNAP_THREAD_Z_SEGMENTS_PER_PITCH,
) -> tuple[float, ...]:
    segment_count = max(2, math.ceil(config.height / config.pitch * z_segments_per_pitch))
    z_values = {_snap_thread_z_key(config.height * index / segment_count): config.height * index / segment_count for index in range(segment_count + 1)}
    profile = _scaled_snap_thread_profile(config.pitch)
    for axis in (0.0, 90.0, 180.0, 270.0):
        angle = (axis - rotation) % 360.0
        local_base = angle * config.pitch / 360.0
        for profile_z, _ in profile:
            local_z = local_base + profile_z
            while local_z <= config.height + config.pitch:
                z = _snap_thread_z_from_local_z(config, local_z)
                if 0.0 <= z <= config.height:
                    z_values[_snap_thread_z_key(z)] = z
                local_z += config.pitch
    return tuple(value for _, value in sorted(z_values.items()))


def _snap_thread_z_key(z: float) -> int:
    return round(z * 1_000_000_000)


def _snap_thread_z_from_local_z(config: SnapThreadConfig, local_z: float) -> float:
    if config.thread_type is ThreadType.BLUNT:
        return local_z - _snap_thread_blunt_z_shift(config)
    return local_z

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
    base_tool = _connector_slot_delete_tool_base(config.connector_slot_delete_tool)
    if side == "right":
        return _right_connector_slot_delete_tool(
            base_tool,
            edge=width / 2.0,
            offset=offset,
            z_base=z_base,
        )
    if side == "left":
        return _left_connector_slot_delete_tool(
            base_tool,
            edge=width / 2.0,
            offset=offset,
            z_base=z_base,
        )
    if side == "top":
        return _top_connector_slot_delete_tool(
            base_tool,
            edge=height / 2.0,
            offset=offset,
            z_base=z_base,
        )
    return _bottom_connector_slot_delete_tool(
        base_tool,
        edge=height / 2.0,
        offset=offset,
        z_base=z_base,
    )


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
    base_tool: Shape,
    *,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return base_tool.rotate(bd.Axis.Z, 180.0).translate((edge + _EPSILON, offset, z_base))


def _left_connector_slot_delete_tool(
    base_tool: Shape,
    *,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return base_tool.translate((-edge - _EPSILON, offset, z_base))


def _top_connector_slot_delete_tool(
    base_tool: Shape,
    *,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return base_tool.rotate(bd.Axis.Z, -90.0).translate((offset, edge + _EPSILON, z_base))


def _bottom_connector_slot_delete_tool(
    base_tool: Shape,
    *,
    edge: float,
    offset: float,
    z_base: float,
) -> Shape:
    return base_tool.rotate(bd.Axis.Z, 90.0).translate((offset, -edge - _EPSILON, z_base))


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
    base_tiles: dict[tuple[int, int], Shape] = {}
    pieces: list[Shape] = []
    for x in range(max_wide):
        for y in range(max_deep):
            pieces.append(
                _placed_tile(
                    config,
                    x * config.max_tile_width,
                    y * config.max_tile_depth,
                    config.max_tile_width,
                    config.max_tile_depth,
                    base_tiles,
                )
            )
    _append_remainder_tiles(pieces, config, max_wide, max_deep, rem_width, rem_depth, base_tiles)
    return _compound(pieces)


def _append_remainder_tiles(
    pieces: list[Shape],
    config: GridConfig,
    max_wide: int,
    max_deep: int,
    rem_width: int,
    rem_depth: int,
    base_tiles: dict[tuple[int, int], Shape],
) -> None:
    for y in range(max_deep):
        if rem_width > 0:
            pieces.append(
                _placed_tile(
                    config,
                    max_wide * config.max_tile_width,
                    y * config.max_tile_depth,
                    rem_width,
                    config.max_tile_depth,
                    base_tiles,
                )
            )
    for x in range(max_wide):
        if rem_depth > 0:
            pieces.append(
                _placed_tile(
                    config,
                    x * config.max_tile_width,
                    max_deep * config.max_tile_depth,
                    config.max_tile_width,
                    rem_depth,
                    base_tiles,
                )
            )
    if rem_width > 0 and rem_depth > 0:
        pieces.append(
            _placed_tile(
                config,
                max_wide * config.max_tile_width,
                max_deep * config.max_tile_depth,
                rem_width,
                rem_depth,
                base_tiles,
            )
        )


def _placed_tile(
    config: GridConfig,
    x_cells: int,
    y_cells: int,
    width: int,
    height: int,
    base_tiles: dict[tuple[int, int], Shape],
) -> Shape:
    spacing = config.tile_size + config.tile_spacing
    return _base_tile(config, width, height, base_tiles).translate((x_cells * spacing, y_cells * spacing, 0.0))


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
                _base_tile(config, width, depth, base_tiles).translate(
                    (x + width * config.tile_size / 2.0, y + depth * config.tile_size / 2.0, 0.0)
                )
            )
            y += depth * config.tile_size + config.tile_spacing
        x += width * config.tile_size + config.tile_spacing
    return _compound(pieces)


def _base_tile(
    config: GridConfig,
    width_cells: int,
    height_cells: int,
    base_tiles: dict[tuple[int, int], Shape],
) -> Shape:
    key = (width_cells, height_cells)
    if key not in base_tiles:
        tile_config = replace(
            config,
            board_width=width_cells,
            board_height=height_cells,
            fill_space_mode=FillSpaceMode.NONE,
        )
        base_tiles[key] = _single_board(tile_config, config.kind)
    return base_tiles[key]


def _compound(shapes: Sequence[Shape]) -> Shape:
    if not shapes:
        return bd.Part()
    return cast(Shape, bd.Compound(children=shapes))

def _fuse(shapes: Sequence[Shape]) -> Shape:
    if not shapes:
        return bd.Part()
    if len(shapes) == 1:
        return shapes[0]
    return cast(Shape, shapes[0].fuse(*shapes[1:]))

def _openconnect_head_profile(config: OpenConnectHeadConfig, *, top: bool) -> tuple[Point2D, ...]:
    width = config.small_rect_width if top else config.large_rect_width
    height = config.small_rect_height if top else config.large_rect_height
    chamfer = config.small_rect_chamfer if top else config.large_rect_chamfer
    back_offset = width / 2.0 + config.back_pos_offset
    y_front = back_offset - height
    y_back = back_offset
    return (
        (-width / 2.0, y_front),
        (width / 2.0, y_front),
        (width / 2.0, y_back - chamfer),
        (width / 2.0 - chamfer, y_back),
        (-width / 2.0 + chamfer, y_back),
        (-width / 2.0, y_back - chamfer),
    )


def _openconnect_lock_tools(config: OpenConnectHeadConfig) -> Shape:
    y = config.large_rect_width / 2.0 - config.nub_to_top_distance + config.back_pos_offset
    tools = (
        bd.Box(config.nub_depth * 2.0, config.nub_tip_height, config.total_height + 2.0 * _EPSILON).translate(
            (-config.large_rect_width / 2.0, y, config.total_height / 2.0)
        ),
        bd.Box(config.nub_depth * 2.0, config.nub_tip_height, config.total_height + 2.0 * _EPSILON).translate(
            (config.large_rect_width / 2.0, y, config.total_height / 2.0)
        ),
    )
    return _fuse(tuple(cast(Shape, tool) for tool in tools))


def _subtract_connector_slot(shape: Shape, config: ConnectorSlotConfig, top_z: float) -> Shape:
    coin = bd.Cylinder(config.coin_slot_radius, config.coin_slot_thickness).rotate(bd.Axis.X, 90.0).translate(
        (0.0, 0.0, top_z - config.coin_slot_height)
    )
    flat = bd.Box(
        config.flat_slot_width,
        config.coin_slot_thickness,
        config.flat_slot_height - config.coin_slot_height + config.flat_slot_height_offset,
    ).translate(
        (
            0.0,
            -config.coin_slot_thickness / 2.0,
            top_z - config.flat_slot_height / 2.0 - config.flat_slot_height_offset / 2.0,
        )
    )
    return cast(Shape, shape - _fuse((cast(Shape, coin), cast(Shape, flat))))


def _opengrid_snap_attachment(config: OpenGridSnapConfig) -> Shape | None:
    if config.kind is OpenGridSnapKind.BASIC_THREADS:
        if config.disable_threads:
            return None
        threads = build_snap_threads(config.threads)
        if config.reverse_threads_entryside:
            return cast(Shape, threads.rotate(bd.Axis.X, 180.0).translate((0.0, 0.0, config.threads.height)))
        return threads
    if config.kind is OpenGridSnapKind.OPENCONNECT:
        return build_openconnect_head(config.openconnect_head)
    if config.kind is OpenGridSnapKind.MULTICONNECT:
        return build_multiconnect_head(config.multiconnect_head)
    return None


def _engrave_text(shape: Shape, config: TextEngravingConfig, top_z: float) -> Shape:
    if not config.labels:
        return shape
    config.validate()
    tools: list[Shape] = []
    for label in config.labels:
        text = bd.Text(label.text, label.size, font=label.font).translate((label.position[0], label.position[1], 0.0))
        z = top_z - label.depth + _EPSILON if label.top else -_EPSILON
        tools.append(cast(Shape, bd.extrude(text, amount=label.depth + _EPSILON).translate((0.0, 0.0, z))))
    return cast(Shape, shape - _fuse(tools))


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
