from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field, replace
from functools import lru_cache
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Iterator, Sequence, TypeAlias, cast

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
    "ScrewPreset",
    "apply_screw_preset",
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
_CONNECTOR_CUTOUT_DEPTH = 5.1
_CONNECTOR_CUTOUT_RADIUS = 2.6
_CONNECTOR_CUTOUT_FILLET_RADIUS = 0.5
_CONNECTOR_CUTOUT_NECK_RADIUS = 5.0 * math.sqrt(5.0) / 4.0
_CONNECTOR_CUTOUT_NECK_OFFSET = 5.1
_CONNECTOR_CUTOUT_FLARE_RADIUS = 0.25
_CONNECTOR_MOUTH_OVERHANG = 0.1
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
_SNAP_THREAD_TAPER_SAMPLES = 16
# Source `blunt_threads` lifts the helix by `up(0.25)`, independent of pitch.
_SNAP_THREAD_HELIX_LIFT = 0.25
# Ridge sections dip this far inside the core; larger than the 144-segment chord sag of the core.
_SNAP_THREAD_ROOT_OVERLAP = 0.005
# Keeps blunt ridge end vertices off the core edges at z=0 and z=height so booleans stay generic.
_SNAP_THREAD_END_GAP = 0.002
# Ridge extension beyond the clipping faces where the helix end is cut off anyway.
_SNAP_THREAD_CLIP_MARGIN = 0.05
_SNAP_THREAD_LEAD_IN_OFFSET = 1.5
_SNAP_THREAD_MIN_TURNS = 0.5
_SNAP_THREAD_BLUNT_ANGLE = 10.0
_OG_SNAP_WIDTH = 24.8
_OG_SNAP_CORNER_OUTER_DIAGONAL = 2.7 + 1.0 / math.sqrt(2.0)
_OG_SNAP_CORNER_CHAMFER = _OG_SNAP_CORNER_OUTER_DIAGONAL * math.sqrt(2.0)
_OG_SNAP_CORNER_INNER_DIAGONAL = _OG_SNAP_WIDTH * math.sqrt(2.0) / 2.0 - _OG_SNAP_CORNER_OUTER_DIAGONAL

_SCREW_CUSTOM_DEFAULT = "011110"
# opengrid_base.scad EPS. openConnect lock-relief mouths and the screw fold plane sit this far
# outside the nominal head edge / middle_to_bottom, like the SCAD source.
_SCAD_EPSILON = 0.005
_OPENCONNECT_SCREW_OVERHANG_DIAMETER = 15.6
_OPENCONNECT_SCREW_OVERHANG_OFFSET: Point2D = (0.32, 0.45)
_OPENCONNECT_FOLD_GAP_WIDTH = 0.4
_OPENCONNECT_FOLD_GAP_HEIGHT = 0.2
_OPENCONNECT_FOLDED_TEXT_SHIFT = 2.0
# Official David D round.step dimple: r1.05 at the R10 face, r0.05 at 1.0 deep.
_MULTICONNECT_HEAD_DIMPLE_RADIUS = 1.05
_MULTICONNECT_HEAD_DIMPLE_TIP_RADIUS = 0.05
_MULTICONNECT_HEAD_DIMPLE_DEPTH = 1.0


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


class ScrewPreset(StrEnum):
    """Named fastener geometries; apply with `apply_screw_preset`.

    Pan heads have flat undersides and get a cylindrical counterbore; flat heads get a countersink.
    """

    NUMBER_8_PAN_HEAD = "#8 Pan Head"
    NUMBER_8_FLAT_HEAD = "#8 Flat Head"
    M4_PAN_HEAD = "M4 Pan Head"
    M4_FLAT_HEAD = "M4 Flat Head"



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
    """Adjacent-grid connector pocket, per David D's official 'openGrid Edge Connector Negative'.

    The pocket is `depth` deep from the board edge, ends in a `radius` round,
    narrows through a neck formed by two `neck_radius` arcs centred on the board
    edge at +-`neck_offset`, with `fillet_radius` shoulder rounds and
    `flare_radius` mouth rounds.
    """

    depth: float = _CONNECTOR_CUTOUT_DEPTH
    radius: float = _CONNECTOR_CUTOUT_RADIUS
    fillet_radius: float = _CONNECTOR_CUTOUT_FILLET_RADIUS
    neck_radius: float = _CONNECTOR_CUTOUT_NECK_RADIUS
    neck_offset: float = _CONNECTOR_CUTOUT_NECK_OFFSET
    flare_radius: float = _CONNECTOR_CUTOUT_FLARE_RADIUS
    height: float = _CONNECTOR_CUTOUT_HEIGHT

    def validate(self) -> None:
        if min(self.depth, self.radius, self.fillet_radius, self.neck_radius, self.neck_offset, self.flare_radius, self.height) <= 0.0:
            raise ValueError("connector slot delete tool dimensions must be positive")
        if not self.radius < self.depth:
            raise ValueError("connector slot delete tool radius must be smaller than its depth")
        if not self.fillet_radius < self.radius < self.neck_offset:
            raise ValueError("connector slot delete tool needs fillet_radius < radius < neck_offset")
        if not self.flare_radius < self.neck_radius:
            raise ValueError("connector slot delete tool flare_radius must be smaller than neck_radius")
        if self.depth - self.radius <= 0.0:
            raise ValueError("connector slot delete tool depth is too small")
        fillet_gap = self.neck_offset - (self.radius - self.fillet_radius)
        if not 0.0 < fillet_gap < self.neck_radius + self.fillet_radius:
            raise ValueError("connector slot delete tool neck arcs do not reach the shoulder fillets")
        fillet_center = math.sqrt((self.neck_radius + self.fillet_radius) ** 2 - fillet_gap**2)
        if fillet_center >= self.depth - self.radius:
            raise ValueError("connector slot delete tool neck arcs leave no straight pocket side")
        if self.flare_radius * 2.0 >= self.neck_radius:
            raise ValueError("connector slot delete tool flare_radius is too large for the neck")


@dataclass(frozen=True, slots=True)
class AdjacentGridConnectorConfig:
    """Positive adjacent-grid connector, per David D's official 'openGrid Edge Connector'.

    Two `lobe_radius` lobes centred `lobe_offset` either side of the seam on
    straight `lobe_radius` sides, waisted by `relief_radius` arcs centred on the
    seam at +-`relief_offset` with `fillet_radius` rounds. One lobe tip carries a
    `notch_depth` V notch of `notch_angle` included angle (0 depth disables it).
    """

    lobe_radius: float = 2.5
    lobe_offset: float = 2.5
    relief_radius: float = 3.25
    relief_offset: float = 5.5
    fillet_radius: float = 0.5
    thickness: float = 2.2
    notch_depth: float = 0.6
    notch_angle: float = 45.0

    def validate(self) -> None:
        if min(self.lobe_radius, self.lobe_offset, self.relief_radius, self.relief_offset, self.fillet_radius, self.thickness) <= 0.0:
            raise ValueError("adjacent-grid connector dimensions must be positive")
        if not self.relief_offset - self.relief_radius < self.lobe_radius:
            raise ValueError("adjacent-grid connector relief arcs must cut into the connector sides")
        if self.relief_offset - self.relief_radius <= 0.0:
            raise ValueError("adjacent-grid connector relief arcs must leave a neck at the seam")
        if not 0.0 <= self.notch_depth < self.lobe_radius:
            raise ValueError("adjacent-grid connector notch_depth must be in [0, lobe_radius)")
        if not 0.0 < self.notch_angle < 180.0:
            raise ValueError("adjacent-grid connector notch_angle must be in (0, 180)")


@dataclass(frozen=True, slots=True)
class SnapThreadConfig:
    """Configuration for the openGrid snap thread primitive (source `snap_threads`).

    Returned thread solids are centered on X/Y with their Z range anchored at
    ``[0, height]`` so snap bodies and screw variants can compose them directly.
    Bevels apply to Basic threads only: ``top_bevel`` at z=0 and the
    height-selected bottom bevel at z=height. Blunt threads have no bevels; their
    helix ends inside the part below z=height, and ``blunt_cutoff`` removes the
    helix start that hangs below z=0.
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
    multiconnect_head: MulticonnectHeadConfig = field(default_factory=lambda: MulticonnectHeadConfig(top_pattern="dimple"))
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


@dataclass(frozen=True, slots=True)
class _ScrewGeometry:
    diameter: float
    head_diameter: float
    head_inset: float
    is_countersunk: bool
    countersunk_degree: float = 90.0


# Through hole = normal-fit clearance (#8: 0.177 in; M4: ISO 273 medium 4.5).
# Pan heads: counterbore = max head diameter + ~0.4, depth = max head height rounded up
# (#8 ASME B18.6.3: 7.90 x 2.87; M4 ISO 7045: 8.0 x 3.1).
# Flat heads: countersink to max head diameter + clearance at the standard angle
# (#8 ASME B18.6.3 82 deg, 8.43; M4 ISO 7046 90 deg, 8.4), recessed 0.5 below the face.
_SCREW_PRESETS: dict[ScrewPreset, _ScrewGeometry] = {
    ScrewPreset.NUMBER_8_PAN_HEAD: _ScrewGeometry(4.5, 8.3, 3.0, is_countersunk=False),
    ScrewPreset.NUMBER_8_FLAT_HEAD: _ScrewGeometry(4.5, 8.6, 0.5, is_countersunk=True, countersunk_degree=82.0),
    ScrewPreset.M4_PAN_HEAD: _ScrewGeometry(4.5, 8.4, 3.3, is_countersunk=False),
    ScrewPreset.M4_FLAT_HEAD: _ScrewGeometry(4.5, 8.8, 0.5, is_countersunk=True, countersunk_degree=90.0),
}


def apply_screw_preset(config: GridConfig, preset: ScrewPreset) -> GridConfig:
    """Return `config` with its screw hole geometry replaced by `preset`.

    Only `screw_diameter`, `screw_head_*` change; placement and every other field are kept.
    Fine-tune afterwards with `dataclasses.replace`.
    """

    geometry = _SCREW_PRESETS[preset]
    return replace(
        config,
        screw_diameter=geometry.diameter,
        screw_head_diameter=geometry.head_diameter,
        screw_head_inset=geometry.head_inset,
        screw_head_is_countersunk=geometry.is_countersunk,
        screw_head_countersunk_degree=geometry.countersunk_degree,
    )


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
    """Build the adjacent-grid connector pocket (side slot delete tool).

    The returned tool has its origin on the board edge, extends inward along
    +X, is centered on Y, and starts at Z=0. With default settings it matches
    David D's official 'openGrid Edge Connector Negative.step' (and the pocket
    in the official openGrid board STEPs) exactly.
    """
    config.validate()
    return _copy_shape(_connector_slot_delete_tool_base(config))


@lru_cache(maxsize=128)
def _connector_slot_delete_tool_base(config: ConnectorSlotDeleteToolConfig, overhang: float = 0.0) -> Shape:
    """Pocket solid; `overhang` extends the mouth outward past the board edge for clean boolean cuts."""
    config.validate()
    # Sketch frame: X lateral, Y depth from the board edge (Y=0); rotated to +X inward at the end.
    main_y = config.depth - config.radius
    fillet_x = config.radius - config.fillet_radius
    fillet_y = math.sqrt((config.neck_radius + config.fillet_radius) ** 2 - (config.neck_offset - fillet_x) ** 2)
    flare_x = config.neck_offset - math.sqrt((config.neck_radius - config.flare_radius) ** 2 - config.flare_radius**2)
    flare_y = config.flare_radius
    neck_center = (config.neck_offset, 0.0)
    fillet_to_neck = _point_toward(neck_center, config.neck_radius, (fillet_x, fillet_y))
    neck_to_flare = _point_toward(neck_center, config.neck_radius, (flare_x, flare_y))
    neck_start = _angle_degrees(neck_center, fillet_to_neck)
    flare_start = _angle_degrees((flare_x, flare_y), neck_to_flare)
    with bd.BuildSketch() as profile:
        with bd.BuildLine():
            bd.CenterArc((0.0, main_y), config.radius, start_angle=90.0, arc_size=-90.0)
            bd.Line((config.radius, main_y), (config.radius, fillet_y))
            bd.TangentArc((config.radius, fillet_y), fillet_to_neck, tangent=(0.0, -1.0))
            bd.CenterArc(neck_center, config.neck_radius, neck_start, _angle_degrees(neck_center, neck_to_flare) - neck_start)
            bd.CenterArc((flare_x, flare_y), config.flare_radius, flare_start, 270.0 - flare_start)
            bd.Line((flare_x, 0.0), (0.0, 0.0))
            bd.mirror(about=bd.Plane.YZ)
        bd.make_face()
        if overhang > 0.0:
            bd.Rectangle(2.0 * flare_x, overhang, align=(bd.Align.CENTER, bd.Align.MAX))
    pocket = cast(Shape, bd.extrude(profile.sketch, amount=config.height))
    return pocket.rotate(bd.Axis.Z, -90.0)


def _point_toward(center: Point2D, radius: float, target: Point2D) -> Point2D:
    dx, dy = target[0] - center[0], target[1] - center[1]
    scale = radius / math.hypot(dx, dy)
    return (center[0] + dx * scale, center[1] + dy * scale)


def _angle_degrees(center: Point2D, point: Point2D) -> float:
    return math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))


def _copy_shape(shape: Shape) -> Shape:
    return shape.translate((0.0, 0.0, 0.0))


def build_adjacent_grid_connector(
    config: AdjacentGridConnectorConfig = AdjacentGridConnectorConfig(),
) -> Shape:
    """Build the positive adjacent-grid connector that mates with the edge pockets.

    Matches David D's official 'openGrid Edge Connector.step'. The seam is at
    X=0, the long axis is X, Z runs from 0 to `thickness`, and the optional
    orientation notch is in the +X lobe tip.
    """
    config.validate()
    lobe_x = config.lobe_offset
    radius = config.lobe_radius
    tol = 1e-6
    with bd.BuildSketch() as profile:
        bd.Rectangle(2.0 * lobe_x, 2.0 * radius)
        with bd.Locations((-lobe_x, 0.0), (lobe_x, 0.0)):
            bd.Circle(radius)
        with bd.Locations((0.0, -config.relief_offset), (0.0, config.relief_offset)):
            bd.Circle(config.relief_radius, mode=bd.Mode.SUBTRACT)
        bd.fillet(profile.vertices().filter_by(lambda v: abs(v.X) < lobe_x - tol), config.fillet_radius)
        if config.notch_depth > 0.0:
            apex_x = lobe_x + radius - config.notch_depth
            half_angle = math.radians(config.notch_angle / 2.0)
            reach = 2.0 * radius
            dx, dy = reach * math.cos(half_angle), reach * math.sin(half_angle)
            bd.Polygon((apex_x, 0.0), (apex_x + dx, dy), (apex_x + dx, -dy), align=None, mode=bd.Mode.SUBTRACT)
            bd.fillet(
                profile.vertices().filter_by(lambda v: v.X > lobe_x + tol and abs(v.Y) > tol),
                config.fillet_radius,
            )
    return cast(Shape, bd.extrude(profile.sketch, amount=config.thickness))


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

    Ports `expanding_snap(...)`: the base snap (no side/bottom cuts, lead-in
    slants kept) is flipped so its notch face is at z=0 with the thread entry,
    the thread negative narrows by the expand distance across the split plane
    (so a screw spreads the halves), and `expanding_spring` cuts the middle
    gap plus the flanking spring slots along the split diagonal.
    """
    config.validate()
    body_config = replace(config.snap_body, enable_cuts=False)
    body = build_snap_body(body_config)
    if body_config.body_shape is SnapBodyShape.DIRECTIONAL and body_config.enable_directional_slants:
        body = cast(Shape, body - _snap_body_directional_slant_tool(body_config))
    body = body.rotate(bd.Axis.Y, 180.0).translate((0.0, 0.0, body_config.thickness))
    # Source: `left(center_position_offset[0]) back(center_position_offset[1])`.
    offset = (-config.center_offset[0], config.center_offset[1], 0.0)
    # The spring slots go first, while the body is still simple. The thread
    # negative follows band by band: one boolean against all helical bands is
    # far slower and needs gigabytes of memory in OCC.
    body = cast(Shape, body - _expanding_spring_tool(config).translate(offset))
    for tool in _expanding_thread_tools(config):
        body = cast(Shape, body - tool.translate(offset))
    return body


def build_openconnect_head(config: OpenConnectHeadConfig = OpenConnectHeadConfig()) -> Shape:
    """Build the source openConnect rectangular head with lock reliefs."""

    config.validate()
    bottom_profile = _openconnect_head_profile(config, top=False)
    top_profile = _openconnect_head_profile(config, top=True)
    bottom = _extrude_xy_polygon(bottom_profile, config.bottom_height)
    transition = _loft_layer_polygons(
        (bottom_profile, top_profile),
        (config.bottom_height, config.bottom_height + config.middle_height),
    )
    top = _extrude_xy_polygon(top_profile, config.top_height).translate(
        (0.0, 0.0, config.bottom_height + config.middle_height)
    )
    head = _fuse((bottom, transition, top))
    if config.add_nubs:
        head = cast(Shape, head - _openconnect_lock_tools(config))
    return head


def build_openconnect_screw(config: OpenConnectScrewConfig = OpenConnectScrewConfig()) -> Shape:
    """Build a snap-thread-backed openConnect screw with coin and flat-blade slots.

    Unfolded, the screw is in the head frame (outer face on z=0, threads +Z). With
    `folded`, it is laid out flat for print-in-place folding like SCAD
    `conditional_fold`; the folded head skips the overhang-cone intersect.
    """

    config.validate()
    head = build_openconnect_head(config.head)
    threads = build_snap_threads(replace(config.threads, clearance=0.0)).translate(
        (0.0, 0.0, config.head.total_height - _EPSILON)
    )
    if not config.folded:
        head = cast(Shape, head & _openconnect_overhang_cone(config.head))
    screw = cast(Shape, (head + threads) - _openconnect_screw_slot_tool(config.connector_slot))
    tip_z = config.head.total_height - _EPSILON + config.threads.height
    if not config.folded:
        return _engrave_text(screw, config.text, tip_z)
    text = replace(
        config.text,
        labels=tuple(
            replace(label, position=(label.position[0], label.position[1] + _OPENCONNECT_FOLDED_TEXT_SHIFT))
            for label in config.text.labels
        ),
    )
    screw = _engrave_text(screw, text, tip_z)
    body_length = config.head.total_height + config.threads.height
    return _openconnect_fold(screw, config.head.middle_to_bottom + _SCAD_EPSILON, body_length, tip_z)


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
        (0.0, 0.0, config.bottom_height + config.middle_height / 2.0)
    )
    top = bd.Cylinder(config.small_diameter / 2.0, config.top_height).translate(
        (0.0, 0.0, config.bottom_height + config.middle_height + config.top_height / 2.0)
    )
    head = _fuse((cast(Shape, bottom), cast(Shape, middle), cast(Shape, top)))
    if config.top_pattern == "coin_slot":
        head = cast(Shape, head - _coin_slot_tool(connector_slot, thickness_axis=bd.Axis.Y))
    elif config.top_pattern == "dimple":
        head = cast(Shape, head - _multiconnect_head_dimple())
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
    if config.kind is OpenGridSnapKind.BASIC_THREADS:
        if config.disable_threads:
            return body
        return cast(Shape, body - _opengrid_snap_thread_hole(config))
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
        return _multiconnect_double_sided(build_multiconnect_rail(config), config)
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
        rail = rail - _multiconnect_dimples(config, spec.dimple_radius, _multiconnect_rail_dimple_z_offsets(config))
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
    tool = _multiconnect_slot_tool(slot_config).rotate(bd.Axis.Y, 180.0).translate(
        (0.0, config.receiver_back_thickness, _multiconnect_slot_top_z(slot_config, profile))
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
    slot_tool = _multiconnect_slot_tool(backer_config).rotate(bd.Axis.Y, 180.0)
    slots = [
        slot_tool.translate(
            (x_offset, config.receiver_back_thickness, _multiconnect_slot_top_z(backer_config, profile))
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


def _multiconnect_slot_top_z(config: MulticonnectConfig, profile: Sequence[Point2D]) -> float:
    """Z of the slot's closed (top) end, where the flipped slot tool's Z=0 end is placed.

    The source measures dimples and on-ramps from the rail TOP, which is the
    closed end of an open-ended slot and the +Z face of a passthrough slot.
    """
    if not _multiconnect_is_open_ended_receiver(config.part_kind):
        return config.length + _EPSILON
    return config.length - (_multiconnect_profile_width(profile) / 2.0 + config.receiver_top_wall_thickness)




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
            round_connector - _multiconnect_dimples(config, spec.dimple_radius, (0.0,)),
        )
    if not double_sided:
        return round_connector
    return _multiconnect_double_sided(round_connector, config)


def _multiconnect_double_sided(shape: Shape, config: MulticonnectConfig) -> Shape:
    """Join a mirrored copy stem-to-stem (source ``attach(FRONT, FRONT)``), so both outer faces carry the head.

    The parts are X-symmetric, so mirroring across the stem face equals the source's 180-degree turn.
    """
    depth = _multiconnect_profile_depth(
        build_multiconnect_profile(replace(config, part_kind=MulticonnectPartKind.CONNECTOR_RAIL))
    )
    return cast(Shape, shape + shape.mirror(bd.Plane(origin=(0.0, depth, 0.0), z_dir=(0.0, 1.0, 0.0))))


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
        tool = cast(
            Shape,
            tool - _multiconnect_dimples(config, spec.dimple_radius, _multiconnect_rail_dimple_z_offsets(config)),
        )
    if config.on_ramps_enabled:
        tool = cast(Shape, tool + _multiconnect_on_ramps(config, profile))
    return tool




def _multiconnect_dimples(config: MulticonnectConfig, dimple_radius: float, z_offsets: Sequence[float]) -> Shape:
    """Cone pockets on the head face (Y=0): radius ``dimple_size`` at the face, tapering to 0 at depth ``dimple_size``.

    Matches the source ``cylinder(h=size, r1=size, r2=0)`` with its base on the face.
    """
    dimple_size = dimple_radius * config.dimple_scale
    height = dimple_size + _EPSILON
    dimples = [
        bd.Cone(height, 0.0, height, rotation=(-90.0, 0.0, 0.0)).translate(
            (0.0, height / 2.0 - _EPSILON, z_offset)
        )
        for z_offset in z_offsets
    ]
    return _fuse(dimples)


def _multiconnect_rail_dimple_z_offsets(config: MulticonnectConfig) -> tuple[float, ...]:
    """Rail dimples every grid pitch from the Z=0 end, plus the far rounded end cap's own dimple."""
    z_offsets = _multiconnect_dimple_z_offsets(config.length, config.grid_size)
    if config.rounding is MulticonnectRounding.BOTH_SIDES and not any(
        math.isclose(z_offset, config.length, abs_tol=_EPSILON) for z_offset in z_offsets
    ):
        z_offsets = (*z_offsets, config.length)
    return z_offsets


def _multiconnect_dimple_z_offsets(length: float, spacing: float) -> tuple[float, ...]:
    """Source ``zcopies(sp=-L+L%G)`` runs from the rail TOP into the rail; our Z=0 is TOP and +Z is into the rail."""
    if length <= _EPSILON:
        return (0.0,)
    count = math.ceil(length / spacing) + 1
    start = -length + length % spacing
    return tuple(-(start + index * spacing) for index in reversed(range(count)))


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
            features.append(_snap_body_corner_patch(config, sx, sy, config.top_corner_extrude, top_height, top_z, slope_bottom=True))
    if config.body_shape is SnapBodyShape.DIRECTIONAL and config.thickness >= _DEFAULT_TILE_THICKNESS:
        for sx in (-1.0, 1.0):
            features.append(
                _snap_body_corner_patch(
                    config,
                    sx,
                    1.0,
                    config.bottom_corner_extrude,
                    top_height,
                    0.0,
                    slope_bottom=False,
                    fillet_radius=config.directional_corner_fillet_radius,
                )
            )
    return _fuse(features)


def _snap_body_corner_patch(
    config: SnapBodyConfig,
    sx: float,
    sy: float,
    extrude: float,
    height: float,
    z_base: float,
    *,
    slope_bottom: bool,
    fillet_radius: float = 0.0,
) -> Shape:
    """Corner pad on the chamfer face: source `prismoid(xang=45, yang=...)`.

    The pad reaches ``extrude`` outward from the chamfer face, flush with the
    body sides. Its face away from the body face (bottom for top pads, top for
    the directional bottom pads) slopes at 45 degrees, so the full reach only
    spans ``height - extrude`` at the body face, matching the board chamfer.
    """
    if extrude <= _EPSILON or config.corner_chamfer <= _EPSILON:
        return bd.Part()
    half_width = config.width / 2.0
    half_height = config.height / 2.0
    fill = min(config.corner_chamfer, extrude * math.sqrt(2.0))
    inner = (
        (sx * (half_width - config.corner_chamfer), sy * half_height),
        (sx * half_width, sy * (half_height - config.corner_chamfer)),
    )
    outer = (
        (sx * (half_width - config.corner_chamfer + fill), sy * half_height),
        (sx * half_width, sy * (half_height - config.corner_chamfer + fill)),
    )
    top_z = z_base + height
    rise = min(fill / math.sqrt(2.0), height - _EPSILON)
    outer_low, outer_high = (z_base + rise, top_z) if slope_bottom else (z_base, top_z - rise)
    points = (
        *((x, y, z) for x, y in inner for z in (z_base, top_z)),
        *((x, y, z) for x, y in outer for z in (outer_low, outer_high)),
    )
    pad = cast(Shape, bd.ConvexPolyhedron(points, align=bd.Align.NONE))
    if fillet_radius <= _EPSILON:
        return pad
    masks = (
        _plan_corner_fillet_mask(outer[0], inner[0], outer[1], fillet_radius, z_base, top_z),
        _plan_corner_fillet_mask(outer[1], inner[1], outer[0], fillet_radius, z_base, top_z),
    )
    return cast(Shape, pad - _fuse(masks))


def _plan_corner_fillet_mask(
    vertex: Point2D,
    toward_a: Point2D,
    toward_b: Point2D,
    radius: float,
    lower_z: float,
    upper_z: float,
) -> Shape:
    """Vertical rounding mask for the convex plan corner at ``vertex``."""
    ua = _unit2(toward_a[0] - vertex[0], toward_a[1] - vertex[1])
    ub = _unit2(toward_b[0] - vertex[0], toward_b[1] - vertex[1])
    half_angle = math.acos(max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1]))) / 2.0
    tangent = radius / math.tan(half_angle)
    bisector = _unit2(ua[0] + ub[0], ua[1] + ub[1])
    center_distance = radius / math.sin(half_angle)
    center = (vertex[0] + bisector[0] * center_distance, vertex[1] + bisector[1] * center_distance)
    kite = (
        vertex,
        (vertex[0] + ua[0] * tangent, vertex[1] + ua[1] * tangent),
        center,
        (vertex[0] + ub[0] * tangent, vertex[1] + ub[1] * tangent),
    )
    height = upper_z - lower_z + 2.0
    prism = _extrude_xy_polygon(_ordered_points(kite), height).translate((0.0, 0.0, lower_z - 1.0))
    disc = bd.Cylinder(radius, height + 2.0).translate((center[0], center[1], (lower_z + upper_z) / 2.0))
    return cast(Shape, prism - disc)


def _unit2(x: float, y: float) -> Point2D:
    length = math.hypot(x, y)
    return (x / length, y / length)


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
        lower_z = upper_z - spec.height
        if tangent_length > _EPSILON and spec.depth > _EPSILON and upper_z > _EPSILON:
            nub = _snap_body_nub(config, side, tangent_length, lower_z, upper_z, spec)
            if lower_z < 0.0:
                # Source: the nub keeps its flank slope from the unclipped base,
                # then the body bottom plane clips it (`snap_nub` nub_remove).
                clip = bd.Box(config.width * 2.0, config.height * 2.0, upper_z).translate((0.0, 0.0, upper_z / 2.0))
                nub = cast(Shape, nub & clip)
            nubs.append(nub)
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
        if side != "front" or not config.enable_uninstall_notch:
            # Source `base_snap` disables the front side cut when the notch is on.
            tools.append(_snap_body_side_cut(config, side))
    if config.body_shape is SnapBodyShape.DIRECTIONAL and config.enable_directional_slants:
        tools.append(_snap_body_directional_slant_tool(config))
    return _fuse(tools)


def _snap_body_bottom_cut(config: SnapBodyConfig, side: str) -> Shape:
    """Relief slot `snap_cut` bottom cut: r=thickness/2 ends, square on the directional front."""
    length = _snap_body_side_tangent_length(config, side) - config.cut_width_inset * 2.0
    cut_height = max(0.0, config.thickness - config.bottom_cut_offset_to_top + _EPSILON)
    thickness = config.bottom_cut_thickness
    if min(length, thickness, cut_height) <= _EPSILON:
        return bd.Part()
    z_base = -_EPSILON / 2.0
    if config.body_shape is SnapBodyShape.DIRECTIONAL and side == "front":
        if config.enable_directional_slants:
            return _snap_body_slanted_front_bottom_cut(config, length, z_base, z_base + cut_height)
        return _snap_side_box(
            config,
            side,
            length,
            thickness,
            cut_height,
            z_base + cut_height / 2.0,
            outside=False,
            offset=config.bottom_cut_offset_to_edge,
        )
    with bd.BuildSketch() as sketch:
        if length > thickness + _EPSILON:
            bd.SlotOverall(length, thickness)
        else:
            bd.Circle(thickness / 2.0)
    cut = cast(Shape, bd.extrude(sketch.sketch, amount=cut_height))
    center = config.height / 2.0 if side in {"front", "back"} else config.width / 2.0
    distance = center - config.bottom_cut_offset_to_edge - thickness / 2.0
    if side in {"front", "back"}:
        sign = 1.0 if side == "back" else -1.0
        return cut.translate((0.0, sign * distance, z_base))
    sign = 1.0 if side == "right" else -1.0
    return cut.rotate(bd.Axis.Z, 90.0).translate((sign * distance, 0.0, z_base))


def _snap_body_directional_slant(config: SnapBodyConfig) -> tuple[float, float]:
    """Return the directional lead-in (depth at z=0, height where it reaches zero)."""
    depth = _snap_body_standard_or_lite(config, config.directional_slant_depth_standard, config.directional_slant_depth_lite)
    height = _snap_body_standard_or_lite(config, config.directional_slant_height_standard, config.directional_slant_height_lite)
    return depth, height


def _snap_body_slanted_front_bottom_cut(config: SnapBodyConfig, length: float, lower_z: float, upper_z: float) -> Shape:
    """Directional front bottom cut shifted inward with the lead-in slant.

    Source `snap_cut` (`tag_diff` remove/keep pair): below the slant height
    the 0.6 slot moves inward by the local slant depth, so the front wall
    keeps its thickness behind the slanted face.
    """
    depth, slant_height = _snap_body_directional_slant(config)
    inner_y = -(config.height / 2.0 - config.bottom_cut_offset_to_edge)
    half = length / 2.0

    def section(z: float) -> tuple[Point3D, ...]:
        shift = depth * max(0.0, slant_height - z) / slant_height if slant_height > _EPSILON else 0.0
        y0 = inner_y + shift
        y1 = y0 + config.bottom_cut_thickness
        return ((-half, y0, z), (half, y0, z), (half, y1, z), (-half, y1, z))

    split_z = min(max(slant_height, lower_z), upper_z)
    parts: list[Shape] = []
    if split_z - lower_z > _EPSILON:
        parts.append(cast(Shape, bd.ConvexPolyhedron((*section(lower_z), *section(split_z)), align=bd.Align.NONE)))
    if upper_z - split_z > _EPSILON:
        parts.append(cast(Shape, bd.ConvexPolyhedron((*section(split_z), *section(upper_z)), align=bd.Align.NONE)))
    return _fuse(parts)


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
    """Directional front lead-in: source `snap_cut` face and corner slants.

    The front face recedes by the slant depth at z=0 and returns to the body
    face at the slant height; both front chamfer faces recede by depth/sqrt(2).
    """
    depth, slant_height = _snap_body_directional_slant(config)
    if depth <= _EPSILON or slant_height <= _EPSILON:
        return bd.Part()
    half_width = config.width / 2.0
    half_height = config.height / 2.0
    wedges = [
        _inward_slant_wedge((-half_width, -half_height), (half_width, -half_height), (0.0, 1.0), depth, slant_height),
    ]
    if config.corner_chamfer > _EPSILON:
        corner_depth = depth / math.sqrt(2.0)
        for sx in (-1.0, 1.0):
            start = (sx * (half_width - config.corner_chamfer), -half_height)
            end = (sx * half_width, -half_height + config.corner_chamfer)
            center = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
            along = _unit2(end[0] - start[0], end[1] - start[1])
            # Source attaches a snap-width-long prismoid centered on the chamfer face.
            a = (center[0] - along[0] * half_width, center[1] - along[1] * half_width)
            b = (center[0] + along[0] * half_width, center[1] + along[1] * half_width)
            wedges.append(_inward_slant_wedge(a, b, _unit2(-sx, 1.0), corner_depth, slant_height))
    return _fuse(wedges)


def _inward_slant_wedge(a: Point2D, b: Point2D, normal: Point2D, depth: float, height: float) -> Shape:
    """Wedge removing ``depth`` inward of face line ``a``-``b`` at z=0, tapering to 0 at ``height``.

    Like the source prismoid it starts at the face plane, so material outside
    the face (the front nub) is kept.
    """
    below = 0.1
    bottom_depth = depth * (1.0 + below / height)
    points: list[Point3D] = []
    for x, y in (a, b):
        points.extend(
            (
                (x, y, height),
                (x, y, -below),
                (x + normal[0] * bottom_depth, y + normal[1] * bottom_depth, -below),
            )
        )
    return cast(Shape, bd.ConvexPolyhedron(points, align=bd.Align.NONE))


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
    # Source `snap_uninstall_notch`: surface pocket at the top front, the gap
    # below it flush with the front face, and a trim of the nub in front of it.
    surface = _snap_side_box(
        config,
        "front",
        config.notch_width,
        config.notch_surface_inset,
        surface_height + _EPSILON,
        config.thickness - surface_height / 2.0 + _EPSILON / 2.0,
        outside=False,
    )
    gap_z = config.thickness - surface_height - gap_height / 2.0
    gap = _snap_side_box(config, "front", config.notch_width, config.notch_gap_inset, gap_height, gap_z, outside=False)
    trim = _snap_side_box(config, "front", config.notch_width, config.notch_gap_inset, gap_height, gap_z, outside=True)
    return _fuse((surface, gap, trim))


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


def _expanding_thread_tools(config: ExpandingSnapConfig) -> Iterator[Shape]:
    """Source `expanding_threads`: entry, 0.05-step transition, and end bands.

    Each transition/end band is a slice of the thread negative whose halves
    across the split plane are moved together (`partition(spread=-d)` with
    `$slop=d/2`), so the hole narrows by the local expand distance.

    The source stacks separate `snap_threads` segments rotated to stay in
    phase (`up(z) zrot(z * 360 / pitch)`); this slices one continuous thread
    instead. For Basic threads that is identical. For Blunt threads the
    source segments each end their helix 1.25 below their own top, so their
    ridges overhang lower bands; slicing keeps one continuous blunt helix.
    Bands abut without overlap so the per-band subtractions stay robust.
    """
    height = config.snap_body.thickness
    entry_height = _expanding_snap_entry_height(config)
    end_height = _expanding_snap_end_height(config)
    transition_height = height - entry_height - end_height
    distance = max(0.0, _expanding_snap_distance(config))
    step = 0.05
    segment_count = math.ceil(round(distance / step, 9)) if distance > 0.0 else 0
    # Source: only the end segment keeps its bottom bevel, chosen from its own height.
    end_segment_height = end_height + _EPSILON
    end_bevel = (
        config.threads.bottom_bevel_standard
        if end_segment_height >= _DEFAULT_TILE_THICKNESS
        else config.threads.bottom_bevel_lite
        if end_segment_height >= 3.4
        else 0.0
    )
    threads = replace(
        config.threads,
        height=height + _EPSILON,
        top_bevel=0.0,
        bottom_bevel_standard=end_bevel,
        bottom_bevel_lite=end_bevel,
        blunt_cutoff=False,
    )
    # Half the thread resolution (chord sag 0.008 mm at d=16.5): every band adds
    # its helical faces to the body, and 144 segments need ~5 GB to subtract.
    negative = _snap_thread_loft(threads, base_segments=_SNAP_THREAD_BASE_SEGMENTS // 2).translate((0.0, 0.0, -_EPSILON / 2.0))
    margin = 4.0
    bands: list[tuple[float, float, float]] = []
    if entry_height > 0.0:
        bands.append((-margin, entry_height, 0.0))
    if segment_count > 0:
        height_step = transition_height / segment_count
        for index in range(segment_count):
            z0 = entry_height + height_step * index
            bands.append((z0, z0 + height_step, min(distance, step * (index + 1))))
    elif transition_height > 0.0:
        bands.append((entry_height, entry_height + transition_height, 0.0))
    if end_height > 0.0:
        bands.append((entry_height + transition_height, height + margin, distance))
    size = 4.0 * max(config.snap_body.width, config.snap_body.height)
    for lower, upper, band_distance in bands:
        slab = bd.Box(size, size, upper - lower).translate((0.0, 0.0, (lower + upper) / 2.0))
        piece = cast(Shape, negative & slab)
        yield _expanding_partition_squeeze(config, piece, band_distance) if band_distance > 0.0 else piece


def _expanding_partition_squeeze(config: ExpandingSnapConfig, tool: Shape, distance: float) -> Shape:
    """Drop the |p.u| < distance/2 band of ``tool`` and close the gap (BOSL2 `partition`).

    The two halves are fused into one solid: subtracting them separately
    leaves coplanar split faces in the body that later cuts can silently miss.
    """
    angle = math.radians(config.expand_split_angle)
    # `zrot(-a) partition()` moves the halves along the rotated BACK axis.
    ux, uy = math.sin(angle), math.cos(angle)
    size = 4.0 * max(config.snap_body.width, config.snap_body.height, config.snap_body.thickness)
    shift = (distance + _EPSILON) / 2.0
    halves: list[Shape] = []
    for sign in (1.0, -1.0):
        reach = distance / 2.0 + size / 2.0
        mask = bd.Box(size, size, size).rotate(bd.Axis.Z, math.degrees(math.atan2(uy, ux))).translate((sign * ux * reach, sign * uy * reach, 0.0))
        halves.append(cast(Shape, tool & mask).translate((-sign * ux * shift, -sign * uy * shift, 0.0)))
    return _fuse(halves)


def _expanding_spring_tool(config: ExpandingSnapConfig) -> Shape:
    """Source `expanding_spring`, in the flipped snap frame, rotated by the split angle.

    Per diagonal end: a middle gap from inside the thread hole to one spring
    thickness short of the corner face (following the corner pad / slant
    profile), face chamfers on it, and two flanking slots offset by
    spring thickness + gap that run from the spring out through the corner.
    """
    body = config.snap_body
    thickness = body.thickness
    gap = config.spring_gap
    chamfer = config.spring_face_chamfer
    thread_radius = config.threads.effective_diameter / 2.0
    gap_length = thread_radius + config.spring_to_center_thickness
    inner_diagonal = (body.width + body.height) / 2.0 / math.sqrt(2.0) - body.corner_chamfer / math.sqrt(2.0)
    start = inner_diagonal - gap_length - config.spring_thickness
    edge = body.corner_edge_height
    top_extrude = body.top_corner_extrude
    bottom_extrude = body.bottom_corner_extrude
    slant_depth, slant_height = _snap_body_directional_slant(body)
    directional = body.body_shape is SnapBodyShape.DIRECTIONAL
    end_types = (
        "corners" if directional and thickness >= _DEFAULT_TILE_THICKNESS else "none",
        "slant" if directional and body.enable_directional_slants else "none",
    )
    tools: list[Shape] = []
    for index, end_type in enumerate(end_types):
        top_corner = ((gap_length, edge), (gap_length + top_extrude, edge - top_extrude), (gap_length + top_extrude, 0.0))
        if end_type == "slant":
            outer = ((gap_length - slant_depth, thickness), (gap_length, thickness - slant_height))
            bottom_to_side = -slant_depth
        elif end_type == "corners":
            outer = (
                (gap_length + bottom_extrude, thickness),
                (gap_length + bottom_extrude, thickness - (edge - bottom_extrude)),
                (gap_length, thickness - edge),
            )
            bottom_to_side = bottom_extrude
        else:
            outer = ((gap_length, thickness),)
            bottom_to_side = 0.0
        profile = ((0.0, 0.0), (0.0, thickness), *outer, *top_corner)
        parts = [
            _expanding_middle_gap(profile, start, gap + _EPSILON),
            _flared_slot(gap_length, gap, chamfer, thickness - chamfer - _EPSILON / 2.0, thickness + _EPSILON / 2.0, flare_low=False, flare_high=True).translate(
                (0.0, start + bottom_to_side, 0.0)
            ),
            _flared_slot(gap_length, gap, chamfer, -_EPSILON / 2.0, chamfer + _EPSILON / 2.0, flare_low=True, flare_high=False).translate(
                (0.0, start + top_extrude, 0.0)
            ),
        ]
        flank = _flared_slot(gap_length, gap, chamfer, -_EPSILON / 2.0, thickness + _EPSILON / 2.0, flare_low=True, flare_high=True)
        flank = flank.rotate(bd.Axis.Z, 180.0).translate(
            (config.spring_thickness + gap, gap_length + thread_radius + config.spring_to_center_thickness, 0.0)
        )
        parts.extend((flank, flank.mirror(bd.Plane.XZ)))
        tools.append(_compound(parts).rotate(bd.Axis.Z, 180.0 * index))
    return _compound(tools).rotate(bd.Axis.Z, config.expand_split_angle)


def _expanding_middle_gap(profile: Sequence[Point2D], start: float, width: float) -> Shape:
    """Side profile (radial, z) swept across ``width``.

    The source also rounds the slot edges (`os_smooth(joint=gap/2)` at both
    sweep ends). That full-width bullnose is left out: OCC cannot fillet a
    plate to half its thickness for wider gaps. The face edges are covered by
    the flared face chamfers anyway, and the remaining difference is the
    slot's outer end, about 0.02 mm^2 per mm of edge.
    """
    with bd.BuildSketch(bd.Plane.YZ) as sketch:
        bd.Polygon(*((start + u, v) for u, v in profile), align=None)
    return cast(Shape, bd.extrude(sketch.sketch, amount=width / 2.0, both=True))


def _flared_slot(length: float, width: float, flare: float, low_z: float, high_z: float, *, flare_low: bool, flare_high: bool) -> Shape:
    """Sweep of the source `gap_top_profile_rounded` (y 0..length, round far end).

    ``os_chamfer(width=-flare)`` ends widen the outline by ``flare`` at the
    face, narrowing back over ``flare`` depth.
    """

    def outline(grow: float, z: float) -> list[Point3D]:
        # `round_corners(radius=width/2)` keeps the tip at y=length.
        radius = width / 2.0 + grow
        arc_center = length - width / 2.0
        points: list[Point3D] = [(-radius, -grow, z), (radius, -grow, z)]
        steps = 16
        for k in range(steps + 1):
            theta = math.pi * k / steps
            points.append((radius * math.cos(theta), arc_center + radius * math.sin(theta), z))
        return points

    lower = low_z + (flare if flare_low else 0.0)
    upper = high_z - (flare if flare_high else 0.0)
    pieces = [cast(Shape, bd.ConvexPolyhedron((*outline(0.0, lower), *outline(0.0, upper)), align=bd.Align.NONE))]
    if flare_low:
        pieces.append(cast(Shape, bd.ConvexPolyhedron((*outline(flare, low_z), *outline(0.0, lower)), align=bd.Align.NONE)))
    if flare_high:
        pieces.append(cast(Shape, bd.ConvexPolyhedron((*outline(0.0, upper), *outline(flare, high_z)), align=bd.Align.NONE)))
    return _fuse(pieces)


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


def _snap_thread_loft(config: SnapThreadConfig, *, base_segments: int = _SNAP_THREAD_BASE_SEGMENTS) -> Shape:
    """Source `snap_threads`: the thread ridge swept along its helix and fused to a root-diameter core.

    Basic follows BOSL2 `generic_threaded_rod(bevel1=top_bevel, bevel2=bottom_bevel)`: the top bevel is at
    z=0, the height-dependent bottom bevel at z=height, and both bevel cones cut through the core.
    Blunt follows `blunt_threads` as called by `snap_threads` (no bevels): a finite helix that starts below
    z=0 and ends inside the part with a 10 degree lead-in taper; `blunt_cutoff` removes the helix below z=0.
    Both types share the same helix phase, so the crest centre at actual angle a is at z = pitch * (a - rotation) / 360.
    """
    radius = config.effective_diameter / 2.0
    height = config.height
    profile = _scaled_snap_thread_profile(config.pitch)
    root_radius = radius + profile[0][1]
    if config.thread_type is ThreadType.BLUNT:
        start = min(height - _SNAP_THREAD_LEAD_IN_OFFSET, 0.0) + _SNAP_THREAD_HELIX_LIFT - _SNAP_THREAD_MIN_TURNS * config.pitch
        end = height - _SNAP_THREAD_LEAD_IN_OFFSET + _SNAP_THREAD_HELIX_LIFT - _SNAP_THREAD_END_GAP
        if not config.blunt_cutoff:
            ridge = _snap_thread_ridge(config, start - _SNAP_THREAD_END_GAP, end, base_segments, taper=True)
            return cast(Shape, bd.Solid.make_cylinder(root_radius, height) + ridge)
        ridge = _snap_thread_ridge(config, start - _SNAP_THREAD_CLIP_MARGIN, end, base_segments, taper=True)
        core = bd.Solid.make_cylinder(root_radius, height + 1.0, bd.Plane.XY.offset(-1.0))
        return cast(Shape, (core + ridge) & bd.Solid.make_cylinder(radius + 1.0, height))

    half_width = profile[-1][0]
    ridge = _snap_thread_ridge(
        config,
        -half_width - _SNAP_THREAD_CLIP_MARGIN,
        height + half_width + _SNAP_THREAD_CLIP_MARGIN,
        base_segments,
        taper=False,
    )
    core = bd.Solid.make_cylinder(root_radius, height + 2.0, bd.Plane.XY.offset(-1.0))
    envelope = _snap_thread_bevel_envelope(radius, height, config.top_bevel, _snap_thread_bottom_bevel(config))
    return cast(Shape, (core + ridge) & envelope)


def _snap_thread_ridge(config: SnapThreadConfig, start: float, end: float, base_segments: int, *, taper: bool) -> bd.Solid:
    """Ruled loft of radial profile sections whose crest centres run from z=start to z=end along the helix.

    Every section carries the exact profile corners, so only the angular chord (`base_segments` per turn)
    deviates from the true helicoid. `taper` appends BOSL2's default sqrt lead-in over the blunt angle.
    """
    count = max(2, math.ceil((end - start) / config.pitch * base_segments))
    sections = [_snap_thread_section(config, start + (end - start) * index / count, 1.0, 1.0) for index in range(count + 1)]
    if taper:
        taper_height = config.pitch * _SNAP_THREAD_BLUNT_ANGLE / 360.0
        for index in range(_SNAP_THREAD_TAPER_SAMPLES - 1, -1, -1):
            remaining = (index / _SNAP_THREAD_TAPER_SAMPLES) ** 2
            sections.append(_snap_thread_section(config, end + taper_height * (1.0 - remaining), *_snap_thread_lead_in_scale(remaining)))
    return bd.Solid.make_loft(sections, ruled=True)


def _snap_thread_lead_in_scale(remaining: float) -> tuple[float, float]:
    """BOSL2 `_leadin_sqrt`: (axial width scale, radial height scale) at the given remaining lead-in fraction."""
    end_scale = 0.05
    height_scale = math.sqrt(remaining + end_scale**2 * (1.0 - remaining))
    return height_scale + (1.0 - height_scale) * 0.25, height_scale


def _snap_thread_section(config: SnapThreadConfig, crest_z: float, width_scale: float, height_scale: float) -> bd.Wire:
    profile = _scaled_snap_thread_profile(config.pitch)
    root = profile[0][1]
    radius = config.effective_diameter / 2.0
    angle = math.radians(config.offset_angle + _OG_SNAP_THREADS_COMPATIBILITY_ANGLE + 360.0 * crest_z / config.pitch)
    # The base dips just inside the core so the fuse never meets the ruled base faces tangentially.
    base = root - _SNAP_THREAD_ROOT_OVERLAP
    points = (
        (base, profile[0][0] * width_scale),
        *((root + (offset - root) * height_scale, axial * width_scale) for axial, offset in profile),
        (base, profile[-1][0] * width_scale),
    )
    cos_angle, sin_angle = math.cos(angle), math.sin(angle)
    return bd.Wire.make_polygon(
        [((radius + offset) * cos_angle, (radius + offset) * sin_angle, crest_z + axial) for offset, axial in points],
        close=True,
    )


def _snap_thread_bevel_envelope(radius: float, height: float, bottom_face_bevel: float, top_face_bevel: float) -> bd.Solid:
    """Solid of revolution bounding the thread to z 0..height with 45 degree bevel cones at either face."""
    outer = radius + 1.0
    points: list[tuple[float, float]] = [(0.0, 0.0)]
    points += [(radius - bottom_face_bevel, 0.0), (outer, bottom_face_bevel + 1.0)] if bottom_face_bevel > 0.0 else [(outer, 0.0)]
    points += [(outer, height - top_face_bevel - 1.0), (radius - top_face_bevel, height)] if top_face_bevel > 0.0 else [(outer, height)]
    points.append((0.0, height))
    face = bd.Face(bd.Wire.make_polygon([(x, 0.0, z) for x, z in points], close=True))
    return bd.Solid.revolve(face, 360.0, bd.Axis.Z)


def _snap_thread_bottom_bevel(config: SnapThreadConfig) -> float:
    if config.height >= _DEFAULT_TILE_THICKNESS:
        return config.bottom_bevel_standard
    if config.height >= 3.4:
        return config.bottom_bevel_lite
    return 0.0


def _scaled_snap_thread_profile(pitch: float) -> tuple[Point2D, ...]:
    return tuple((x * pitch, y * pitch) for x, y in _OG_SNAP_THREADS_PROFILE)


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
    # Lattice tools use the lattice thickness; the Lite adhesive base hangs below z=0.
    thickness = config.lite_tile_thickness if kind is BoardKind.LITE else _selected_thickness(config, kind)
    board = _board_lattice(config, kind)
    board = _apply_corner_modifications(board, config, thickness, both_faces=kind is BoardKind.HEAVY)
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
    return _fuse(pieces)


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
    # QuackWorks openGridHeavy: each half carries the Heavy capture lip at its outer face
    # (lower half mirrored), and the gap is the half's inner-face (z=0) section.
    full = _full_layers(config.tile_thickness, heavy_profile=True)
    bottom = tuple((config.tile_thickness - z, side, corner) for z, side, corner in reversed(full))
    top_start = config.tile_thickness + config.heavy_tile_gap
    top = tuple((top_start + z, side, corner) for z, side, corner in full)
    return (*bottom, *top)


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


def _apply_corner_modifications(board: Shape, config: GridConfig, thickness: float, *, both_faces: bool = False) -> Shape:
    board = _subtract_chamfers(board, config, thickness)
    screw_positions = _screw_positions(config)
    if not screw_positions:
        return board
    return board - _screw_tool(config, thickness, screw_positions, both_faces=both_faces)


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
    # QuackWorks: translate(parity shift) grid_copies(spacing=[c*T, r*T], size=[(W-2)*T, (H-2)*T]).
    col_step = max(1, config.screw_every_x_columns)
    row_step = max(1, config.screw_every_x_rows)
    x_shift = 0.0 if ((config.board_width - 2) % col_step) % 2 == 0 else -config.tile_size / 2.0
    y_shift = 0.0 if ((config.board_height - 2) % row_step) % 2 == 0 else config.tile_size / 2.0
    x_count = max(0, math.floor((config.board_width - 2) / col_step) + 1)
    y_count = max(0, math.floor((config.board_height - 2) / row_step) + 1)
    x_pitch = col_step * config.tile_size
    y_pitch = row_step * config.tile_size
    for iy in range(y_count):
        for ix in range(x_count):
            yield ((ix - (x_count - 1) / 2.0) * x_pitch + x_shift, (iy - (y_count - 1) / 2.0) * y_pitch + y_shift)


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


def _screw_tool(config: GridConfig, thickness: float, positions: Sequence[Point2D], *, both_faces: bool = False) -> Shape:
    """Through holes plus head counterbore/countersink on the top face (and the bottom face if ``both_faces``)."""
    through = thickness + 2.0 * _EPSILON
    mid_plane = bd.Plane.XY.offset(thickness / 2.0)
    bits: list[Shape] = []
    for x, y in positions:
        bits.append(bd.Cylinder(config.screw_diameter / 2.0, through).translate((x, y, thickness / 2.0)))
        heads = _screw_head_tools(config, thickness, x, y)
        bits.extend(heads)
        if both_faces:
            bits.extend(head.mirror(mid_plane) for head in heads)
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
                (x, y, thickness + _EPSILON - inset - cone_height / 2.0)
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
    base_tool = _connector_slot_delete_tool_base(config.connector_slot_delete_tool, _CONNECTOR_MOUTH_OVERHANG)
    tools = [
        _connector_tool(config, base_tool, position, z_base)
        for z_base in _connector_z_bases(config, thickness, kind)
        for position in positions
    ]
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


def _connector_tool(config: GridConfig, base_tool: Shape, position: tuple[str, float], z_base: float) -> Shape:
    side, offset = position
    span = config.board_width if side in {"left", "right"} else config.board_height
    return _place_connector_slot_tool(base_tool, side, edge=span * config.tile_size / 2.0, offset=offset, z_base=z_base)


def _connector_z_bases(config: GridConfig, thickness: float, kind: BoardKind) -> tuple[float, ...]:
    cutout_height = config.connector_slot_delete_tool.height
    if kind is BoardKind.HEAVY:
        # QuackWorks openGridHeavy: one slot at mid-height of each Full half, none in the gap.
        lower = _connector_z_base(config.tile_thickness, BoardKind.FULL, cutout_height)
        return (lower, lower + config.tile_thickness + config.heavy_tile_gap)
    return (_connector_z_base(thickness, kind, cutout_height),)


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


_CONNECTOR_SIDE_ROTATION = {"left": 0.0, "right": 180.0, "top": -90.0, "bottom": 90.0}


def _place_connector_slot_tool(base_tool: Shape, side: str, *, edge: float, offset: float, z_base: float) -> Shape:
    """Place an edge-origin (+X inward) slot tool on a board side; the tool carries its own mouth overhang."""
    x, y = {"left": (-edge, offset), "right": (edge, offset), "top": (offset, edge), "bottom": (offset, -edge)}[side]
    return base_tool.rotate(bd.Axis.Z, _CONNECTOR_SIDE_ROTATION[side]).translate((x, y, z_base))


def _adhesive_base(config: GridConfig) -> Shape:
    # QuackWorks adhesiveBase: the slab gets the same corner modifications (chamfers and screw holes).
    width = config.board_width * config.tile_size
    height = config.board_height * config.tile_size
    thickness = config.adhesive_base_thickness
    base = bd.Box(width, height, thickness).translate((0.0, 0.0, thickness / 2.0))
    return _apply_corner_modifications(base, config, thickness).translate((0.0, 0.0, -thickness))


def _stacked_boards(config: GridConfig, stack_count: int) -> Shape:
    # QuackWorks openGrid.scad:127-150: every Full board is zflip()ped; Lite/Heavy boards alternate
    # orientation per index so like faces meet across each interface.
    thickness = _selected_thickness(config, config.kind)
    spacing = thickness + _adjusted_interface_thickness(config) + 2.0 * config.interface_separation
    board = _single_board(config, config.kind)
    flipped = board.mirror(bd.Plane.XY.offset(thickness / 2.0))
    stack = [flipped if _stack_board_is_flipped(config.kind, i) else board for i in range(stack_count)]
    pieces = [stacked.translate((0.0, 0.0, i * spacing)) for i, stacked in enumerate(stack)]
    if config.stacking_method is StackingMethod.INTERFACE_LAYER:
        section_depth = 0.0 if config.kind is BoardKind.FULL else _EPSILON
        z_bottom = thickness + config.interface_separation
        pieces.extend(
            _interface_layer(stacked, thickness - section_depth, config.interface_thickness).translate(
                (0.0, 0.0, i * spacing + z_bottom)
            )
            for i, stacked in enumerate(stack[:-1])
        )
    return _fuse(pieces)


def _stack_board_is_flipped(kind: BoardKind, index: int) -> bool:
    if kind is BoardKind.FULL:
        return True
    return index % 2 == 1


def _adjusted_interface_thickness(config: GridConfig) -> float:
    if config.stacking_method is StackingMethod.INTERFACE_LAYER:
        return config.interface_thickness
    return 0.0


def _interface_layer(board: Shape, section_z: float, thickness: float) -> Shape:
    """Extrude the board's XY section at ``section_z`` up from z=0 by ``thickness``.

    Mirrors QuackWorks interfaceLayer/interfaceLayer2D: ``projection(cut=true)`` of the board face
    that the layer touches (Full: the face itself; Lite/Heavy: 0.01 inside the face), so it keeps
    the face wall width, corner blocks, chamfers and screw holes.
    """

    below = cast(Shape, board.split(bd.Plane.XY.offset(section_z), keep=bd.Keep.BOTTOM))
    faces = [face for face in below.faces() if abs(face.center().Z - section_z) < 1e-6 and face.normal_at().Z > 0.5]
    layers = [cast(Shape, bd.extrude(face.translate((0.0, 0.0, -section_z)), amount=thickness)) for face in faces]
    return _fuse(layers)


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
    """QuackWorks FillSpaceClipOneSide: max-size boards on a spaced grid, clipped to the space in mm."""
    board_width = config.max_tile_width * config.tile_size
    board_depth = config.max_tile_depth * config.tile_size
    full_cols, cols = _clipped_board_counts(config.space_width, board_width)
    full_rows, rows = _clipped_board_counts(config.space_depth, board_depth)
    clip_width = config.space_width + full_cols * config.tile_spacing
    clip_depth = config.space_depth + full_rows * config.tile_spacing
    board = _base_tile(config, config.max_tile_width, config.max_tile_depth, {})
    board_box = board.bounding_box()
    z_min, z_height = float(board_box.min.Z) - 1.0, float(board_box.size.Z) + 2.0
    pieces: list[Shape] = []
    for col in range(cols):
        x = col * (board_width + config.tile_spacing)
        for row in range(rows):
            y = row * (board_depth + config.tile_spacing)
            piece = board.translate((x + board_width / 2.0, y + board_depth / 2.0, 0.0))
            if x + board_width > clip_width + _EPSILON or y + board_depth > clip_depth + _EPSILON:
                clip = bd.Box(clip_width, clip_depth, z_height, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN))
                piece = cast(Shape, piece & clip.translate((0.0, 0.0, z_min)))
            pieces.append(piece)
    return _compound(pieces)


def _clipped_board_counts(space: float, board_size: float) -> tuple[int, int]:
    full = math.floor(space / board_size)
    remainder = space - full * board_size
    return full, full + (1 if remainder > _EPSILON else 0)


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
    """Lock-relief notches from `openconnect_lock` (openconnect_lib.scad:304-312).

    Each notch is the BOSL2 45-degree trapezoid (tip `nub_tip_height`, mouth
    tip + 2 * depth) with r=`nub_fillet` tip fillets and flared mouth corners.
    It spans the bottom and middle sections. The left (-X) notch is sheared
    inward along the middle chamfer (`nub_taperin`); the right notch is straight.
    """

    y = config.large_rect_width / 2.0 - config.nub_to_top_distance + config.back_pos_offset
    edge_x = config.large_rect_width / 2.0 + _SCAD_EPSILON
    profile = _openconnect_lock_profile(config)
    left_profile = profile.translate((-edge_x, y, 0.0))
    right_profile = profile.mirror(bd.Plane.YZ).translate((edge_x, y, 0.0))
    taper = config.middle_height - config.nub_depth

    def notch(face: bd.Face, shear_x: float) -> Shape:
        bottom = bd.Solid.extrude(face.translate((0.0, 0.0, -_EPSILON)), (0.0, 0.0, config.bottom_height + _EPSILON))
        middle = bd.Solid.extrude(face.translate((0.0, 0.0, config.bottom_height)), (shear_x, 0.0, config.middle_height))
        return cast(Shape, bottom.fuse(middle))

    return _fuse((notch(left_profile, taper), notch(right_profile, 0.0)))


def _openconnect_lock_profile(config: OpenConnectHeadConfig) -> bd.Face:
    """Lock-relief profile with the mouth on x=0 and the tip at x=nub_depth."""

    depth = config.nub_depth
    fillet = config.nub_fillet
    tip = config.nub_tip_height / 2.0
    mouth = tip + depth
    tangent = fillet * math.tan(math.radians(22.5))
    diagonal = tangent / math.sqrt(2.0)
    with bd.BuildSketch() as sketch:
        bd.Polygon((0.0, -mouth), (depth, -tip), (depth, tip), (0.0, mouth), align=None)
        bd.fillet(sketch.vertices().filter_by(lambda vertex: vertex.X > depth / 2.0), fillet)
        for sign in (1.0, -1.0):
            with bd.BuildSketch() as flare:
                bd.Polygon(
                    (0.0, sign * mouth),
                    (0.0, sign * (mouth + tangent)),
                    (diagonal, sign * (mouth - diagonal)),
                    align=None,
                )
                with bd.Locations((fillet, sign * (mouth + tangent))):
                    bd.Circle(fillet, mode=bd.Mode.SUBTRACT)
            bd.add(flare.sketch)
    faces = sketch.sketch.faces()
    if len(faces) != 1:
        raise ValueError("openConnect lock relief profile must be a single face")
    return faces[0]


def _multiconnect_head_dimple() -> Shape:
    """Dimple opening on the R10 (z=0) face, apex inward, per the official round.step."""

    slope = (_MULTICONNECT_HEAD_DIMPLE_RADIUS - _MULTICONNECT_HEAD_DIMPLE_TIP_RADIUS) / _MULTICONNECT_HEAD_DIMPLE_DEPTH
    cone = bd.Cone(
        _MULTICONNECT_HEAD_DIMPLE_RADIUS + slope * _EPSILON,
        _MULTICONNECT_HEAD_DIMPLE_TIP_RADIUS,
        _MULTICONNECT_HEAD_DIMPLE_DEPTH + _EPSILON,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    return cast(Shape, cone.translate((0.0, 0.0, -_EPSILON)))


def _coin_slot_tool(config: ConnectorSlotConfig, *, thickness_axis: bd.Axis) -> Shape:
    """Coin-slot cylinder whose arc is tangent to z=coin_slot_height above the z=0 face."""

    radius = config.coin_slot_radius
    rotation = (0.0, 90.0, 0.0) if thickness_axis == bd.Axis.X else (90.0, 0.0, 0.0)
    return cast(
        Shape,
        bd.Cylinder(radius, config.coin_slot_thickness, rotation=rotation).translate(
            (0.0, 0.0, config.coin_slot_height - radius)
        ),
    )


def _openconnect_screw_slot_tool(config: ConnectorSlotConfig) -> Shape:
    """openConnect screw slot tools from openconnect_lib.scad:530-543 in the head frame.

    The coin slot runs along Y (thickness along X) with a front channel to the
    head edge; the flat-blade prismoid narrows from start to end thickness and
    reaches `flat_slot_height` inside the threads.
    """

    coin = _coin_slot_tool(config, thickness_axis=bd.Axis.X)
    radius = config.coin_slot_radius
    channel = bd.Box(config.coin_slot_thickness, config.coin_slot_width, radius).translate(
        (0.0, -config.coin_slot_width / 2.0, config.coin_slot_height - radius / 2.0)
    )
    flat_bottom = config.coin_slot_height - config.flat_slot_height_offset
    start = config.flat_slot_start_thickness / 2.0
    end = config.flat_slot_end_thickness / 2.0
    with bd.BuildSketch(bd.Plane.XZ) as flat_profile:
        bd.Polygon(
            (-start, flat_bottom),
            (start, flat_bottom),
            (end, config.flat_slot_height),
            (-end, config.flat_slot_height),
            align=None,
        )
    flat = bd.extrude(flat_profile.sketch, amount=config.flat_slot_width / 2.0, both=True)
    return _fuse((coin, cast(Shape, channel), cast(Shape, flat)))


def _openconnect_overhang_cone(config: OpenConnectHeadConfig) -> Shape:
    """Overhang cone intersected with the unfolded screw head (openconnect_lib.scad:527-528)."""

    height = config.total_height
    top_radius = _OPENCONNECT_SCREW_OVERHANG_DIAMETER / 2.0
    cone = bd.Cone(top_radius + height, top_radius, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    offset_x, offset_y = _OPENCONNECT_SCREW_OVERHANG_OFFSET
    return cast(Shape, cone.translate((offset_x, offset_y, 0.0)))


def _openconnect_fold(screw: Shape, fold_position: float, body_length: float, tip_z: float) -> Shape:
    """Port of `conditional_fold` (opengrid_base.scad:192-219) for the openConnect screw.

    Input is the screw in the head frame (outer face z=0, thread tip at `tip_z`).
    The output is SCAD's print layout, with `body_length` (head + threads height)
    as the SCAD body thickness: the back piece (y >= -fold_position) lies on its
    cut face with the outer face at y=body_length; the front thread sliver, minus
    the slice-off, lies mirrored past the gap at y < 0; a gap_height-thick hinge,
    cut from the thread-tip section, bridges the gap.
    """

    gap_width = _OPENCONNECT_FOLD_GAP_WIDTH
    gap_height = _OPENCONNECT_FOLD_GAP_HEIGHT
    sliceoff = gap_width / 2.0
    span = 100.0
    back_mask = bd.Box(span, span, span, align=(bd.Align.CENTER, bd.Align.MIN, bd.Align.CENTER)).translate(
        (0.0, -fold_position, 0.0)
    )
    front_mask = bd.Box(span, span, span, align=(bd.Align.CENTER, bd.Align.MAX, bd.Align.CENTER)).translate(
        (0.0, -fold_position - sliceoff, 0.0)
    )
    back = cast(Shape, screw & back_mask).rotate(bd.Axis.X, 90.0).translate((0.0, body_length, fold_position))
    front = (
        cast(Shape, screw & front_mask)
        .rotate(bd.Axis.X, -90.0)
        .translate((0.0, -body_length - gap_width + _SCAD_EPSILON, -fold_position - sliceoff))
    )
    strip = bd.Plane.XY.offset(tip_z - _EPSILON) * bd.Rectangle(span, gap_height).face().translate(
        (0.0, -fold_position + gap_height / 2.0, 0.0)
    )
    hinges = [
        bd.Solid.extrude(
            face.translate((0.0, 0.0, _EPSILON - tip_z)).rotate(bd.Axis.X, 90.0).translate(
                (0.0, -gap_width - _EPSILON, fold_position)
            ),
            (0.0, gap_width + 3.0 * _EPSILON, 0.0),
        )
        for face in cast(Shape, screw & strip).faces()
    ]
    return _fuse((back, front, *hinges))


def _opengrid_snap_thread_hole(config: OpenGridSnapConfig) -> Shape:
    # Source attach(TOP, BOTTOM, inside=true, shiftout=EPS/2) snap_threads(thickness + EPS) inside diff():
    # a "remove" tool whose thread frame is turned 180 deg about Y with frame z=0 at the snap top.
    # reverse_threads_entryside wraps it in up(thickness) yrot(180), which undoes that flip.
    thickness = config.snap_body.thickness
    threads = build_snap_threads(replace(config.threads, height=thickness + _EPSILON))
    if config.reverse_threads_entryside:
        placed = threads.translate((0.0, 0.0, -_EPSILON / 2.0))
    else:
        placed = threads.rotate(bd.Axis.Y, 180.0).translate((0.0, 0.0, thickness + _EPSILON / 2.0))
    return cast(Shape, placed.translate((config.center_offset[0], config.center_offset[1], 0.0)))


def _opengrid_snap_attachment(config: OpenGridSnapConfig) -> Shape | None:
    if config.kind is OpenGridSnapKind.OPENCONNECT:
        return _flip_snap_head(build_openconnect_head(config.openconnect_head), config.openconnect_head.total_height)
    if config.kind is OpenGridSnapKind.MULTICONNECT:
        return _flip_snap_head(build_multiconnect_head(config.multiconnect_head), config.multiconnect_head.total_height)
    return None


def _flip_snap_head(head: Shape, height: float) -> Shape:
    # Source attach(TOP, TOP): the small face sits on the snap and the large face is outermost.
    # build_opengrid_snap sinks attachments by _EPSILON. Instead of sinking the head (which loses height),
    # extend its small face down by _EPSILON into the snap so the fuse yields one solid at full height.
    flipped = head.rotate(bd.Axis.Y, 180.0).translate((0.0, 0.0, height))
    seat = bd.extrude(flipped.faces().sort_by(bd.Axis.Z)[0], amount=_EPSILON, dir=(0.0, 0.0, -1.0))
    return cast(Shape, (flipped + seat).translate((0.0, 0.0, _EPSILON)))


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
    parser.add_argument(
        "--screw-preset",
        choices=[preset.value for preset in ScrewPreset],
        default=None,
        help="Override screw hole geometry with a named fastener; default keeps the built-in 4.1/7.2 countersink",
    )
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
    if args.screw_preset is not None:
        config = apply_screw_preset(config, ScrewPreset(args.screw_preset))
    export_grid(config, args.output)


if __name__ == "__main__":
    main()
