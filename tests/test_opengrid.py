from __future__ import annotations
from dataclasses import fields as dataclass_fields, replace
import functools
import re
from pathlib import Path
import importlib.util
import math
import yaml
from typing import Any, cast

import pytest
import build123d as bd


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
    _connector_slot_delete_tool_base,
    _connector_positions,
    build_open_grid,
    _OG_SNAP_THREADS_PROFILE,
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


@functools.cache
def _built_expanding_snap(config: ExpandingSnapConfig) -> Any:
    # Expanding snaps take about a minute to build; share them across tests.
    return build_expanding_snap(config)


def _expanding_snap_bbox_size(config: ExpandingSnapConfig) -> tuple[float, float, float]:
    size = _built_expanding_snap(config).bounding_box().size
    return (float(size.X), float(size.Y), float(size.Z))


def _expanding_snap_volume(config: ExpandingSnapConfig) -> float:
    return float(_built_expanding_snap(config).volume)


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
    # Off-centre so the probe misses the uninstall notch (x within +-notch_width/2).
    return (
        (config.notch_width + config.width / 2.0 - config.cut_width_inset) / 2.0,
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
    assert set(_mapping_section(config, "verification")) == {"enabled", "variant_galleries"}
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
    }
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
        (3.4, (16.318, 16.5)),
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


def test_snap_threads_follow_source_phase_bevels_and_blunt_end() -> None:
    # snap_threads (opengrid_threads_lib.scad:132-136): Blunt and Basic share one helix phase; the crest
    # centre at actual angle a is at z = 3 * (a - 53.5) / 360 (mod 3). A vertical probe at r=7.9
    # crosses a crest as crest +- 0.35 (0.25 flat + 0.1 down the 45 degree flank).
    blunt = build_snap_threads(SnapThreadConfig(clearance=0.0))
    basic = build_snap_threads(SnapThreadConfig(thread_type=ThreadType.BASIC, clearance=0.0))

    def crests(shape: Any, angle: float) -> list[float]:
        x, y = 7.9 * math.cos(math.radians(angle)), 7.9 * math.sin(math.radians(angle))
        return _material_intervals(shape, (x, y, -1.0), (x, y, 8.0), 2)

    # Blunt (blunt_threads, :77-111): no bevels, full profile down to z=0, and the helix ends at crest
    # z=h-1.25 (5.55 at 0 degrees), so at 90 degrees the 6.30 crest is absent.
    assert crests(blunt, 90.0) == pytest.approx([0.0, 0.654, 2.954, 3.654], abs=0.01)
    # Basic (generic_threaded_rod bevel1=0.5 at z=0, bevel2=2.0 at z=h): the 0.5 cone trims the low
    # crest to z>=0.4 and the 2.0 cone removes everything above z=4.9 at r=7.9.
    assert crests(basic, 90.0) == pytest.approx([0.4, 0.654, 2.954, 3.654], abs=0.01)
    assert crests(blunt, 0.0)[:2] == pytest.approx([2.204, 2.904], abs=0.01)
    assert crests(basic, 0.0) == pytest.approx([2.204, 2.904], abs=0.01)
    # The 2.0 bevel cone cuts through the core: screw tip core 12 mm (PDF positive tip chamfer 1x1).
    assert _material_intervals(basic, (-9.0, 0.0, 6.75), (9.0, 0.0, 6.75), 0) == pytest.approx([-6.05, 6.05], abs=0.01)
    # Without blunt_cutoff the helix start hangs below z=0: start crest -1.25 minus the 1.25 half width.
    overhang = build_snap_threads(SnapThreadConfig(blunt_cutoff=False)).bounding_box()
    assert (float(overhang.min.Z), float(overhang.max.Z)) == pytest.approx((-2.5, 6.8), abs=0.01)


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

    # Source `base_snap` disables the front side cut while the notch is enabled.
    assert with_notch.is_inside(_front_side_cut_probe(without_notch_config))
    assert not without_notch.is_inside(_front_side_cut_probe(without_notch_config))


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


def _diagonal_point(radial: float, z: float, sy: float = 1.0) -> tuple[float, float, float]:
    return (radial / math.sqrt(2.0), sy * radial / math.sqrt(2.0), z)


def test_snap_body_profile_matches_board_slot_and_source_cuts() -> None:
    """Probe values from the official David D snap STEPs and opengrid_snap_lib."""
    directional = build_snap_body(SnapBodyConfig())
    lite = build_snap_body(SnapBodyConfig(thickness=3.4))

    # Corner pads: full 15.23 reach only near the face, then a 45 deg slope (board chamfer).
    assert directional.is_inside(_diagonal_point(15.0, 6.6))
    assert not directional.is_inside(_diagonal_point(15.0, 5.6))
    assert directional.is_inside(_diagonal_point(14.6, 0.3))
    assert not directional.is_inside(_diagonal_point(14.6, 1.3))
    # Directional lead-in: face at y=-11.612 and bottom cut -10.912..-10.312 at z=0.05.
    assert not directional.is_inside((0.0, -11.7, 0.05))
    assert directional.is_inside((0.0, -11.5, 0.05))
    assert not directional.is_inside((0.0, -10.6, 0.05))
    assert not directional.is_inside(_diagonal_point(13.6, 0.05, sy=-1.0))
    # Uninstall notch gap is flush with the front face and trims the front nub.
    assert not directional.is_inside((0.0, -12.2, 5.0))
    assert not directional.is_inside((0.0, -12.5, 5.0))
    # Lite directional back nub lower flank starts below the body (13.05 reach at z=0.25).
    assert lite.is_inside((0.0, 13.0, 0.25))


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


def _flipped_expanding_probe(config: SnapBodyConfig, point: tuple[float, float, float]) -> tuple[float, float, float]:
    # Source `expanding_snap` flips the base snap: up(t) yrot(180).
    return (-point[0], point[1], config.thickness - point[2])


def test_expanding_snap_omits_source_side_and_bottom_cuts() -> None:
    snap_body = SnapBodyConfig()
    expanding = _built_expanding_snap(ExpandingSnapConfig(snap_body=snap_body))

    assert expanding.is_inside(_flipped_expanding_probe(snap_body, _front_side_cut_probe(snap_body)))
    assert expanding.is_inside(_flipped_expanding_probe(snap_body, _front_bottom_cut_probe(snap_body)))


def test_expanding_snap_is_flipped_and_preserves_body_envelope() -> None:
    snap_body = SnapBodyConfig()
    expanding = _built_expanding_snap(ExpandingSnapConfig(snap_body=snap_body))

    assert _expanding_snap_bbox_size(ExpandingSnapConfig(snap_body=snap_body)) == pytest.approx(_snap_body_bbox_size(snap_body), abs=0.02)
    assert expanding.volume < _snap_body_volume(snap_body)
    # Basic nubs (z 3.4-5.4 on the body) sit at z 1.4-3.4 after the flip.
    assert expanding.is_inside((12.6, 0.0, 2.4))
    assert not expanding.is_inside((12.6, 0.0, 4.4))


def test_expanding_snap_thread_relief_narrows_across_split_plane() -> None:
    """Source `partition(spread=-d)`: the hole chord along 45 deg shrinks by d (15.50 -> 14.49)."""
    config = ExpandingSnapConfig(threads=SnapThreadConfig(thread_type=ThreadType.BASIC))
    expanding = _built_expanding_snap(config)

    def hole_radius(angle_degrees: float, z: float) -> float:
        direction = (math.cos(math.radians(angle_degrees)), math.sin(math.radians(angle_degrees)))
        inside, outside = 5.0, 9.5  # void at 5.0, material at 9.5
        for _ in range(24):
            middle = (inside + outside) / 2.0
            if expanding.is_inside((direction[0] * middle, direction[1] * middle, z)):
                outside = middle
            else:
                inside = middle
        return inside

    def chord(angle_degrees: float, z: float) -> float:
        return hole_radius(angle_degrees, z) + hole_radius(angle_degrees + 180.0, z)

    # SCAD render chords: entry z 0.2 15.50 on both axes; end z 6.3 14.49 along 45, 14.77 along 0.
    assert chord(45.0, 0.2) == pytest.approx(15.50, abs=0.03)
    assert chord(45.0, 6.3) == pytest.approx(14.49, abs=0.03)
    assert chord(0.0, 6.3) == pytest.approx(14.77, abs=0.03)


def test_expanding_snap_distance_and_spring_gap_change_geometry() -> None:
    collapsed = ExpandingSnapConfig(expand_distance_standard=0.0)
    expanded = ExpandingSnapConfig(expand_distance_standard=1.0)
    wide_gap = ExpandingSnapConfig(spring_gap=0.8)

    # The expand distance narrows the thread negative, so less is removed.
    assert _expanding_snap_volume(expanded) > _expanding_snap_volume(collapsed)
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

def _chord_width(shape: Any, x: float, z: float) -> float:
    section = shape & bd.Edge.make_line((x, -50.0, z), (x, 50.0, z))
    return sum(float(edge.length) for edge in section.edges())


def test_connector_slot_delete_tool_matches_official_edge_connector_negative() -> None:
    # Reference: David D's official 'openGrid Edge Connector Negative.step' (55.5616 mm3).
    tool = build_connector_slot_delete_tool()
    size = tool.bounding_box().size

    assert (float(size.X), float(size.Y), float(size.Z)) == pytest.approx((5.1, 5.2, 2.4))
    assert tool.volume == pytest.approx(55.5616, abs=1e-3)
    for depth, width in ((0.0, 5.134), (0.05, 4.834), (0.27, 4.637), (1.0, 4.980), (1.25, 5.174), (2.0, 5.2)):
        assert _chord_width(tool, depth, 1.2) == pytest.approx(width, abs=0.002)


def test_adjacent_grid_connector_matches_official_and_fits_board_pocket() -> None:
    # Reference: official 'openGrid Edge Connector.step' (5.0 x 9.9227 x 2.2, 95.8668 mm3).
    connector = build_adjacent_grid_connector()
    box = connector.bounding_box()

    assert (float(box.min.X), float(box.max.X)) == pytest.approx((-5.0, 4.9227), abs=1e-3)
    assert (float(box.size.Y), float(box.size.Z)) == pytest.approx((5.0, 2.2))
    assert connector.volume == pytest.approx(95.8668, abs=1e-3)
    assert _chord_width(connector, 0.0, 1.1) == pytest.approx(4.5, abs=1e-3)

    board = build_open_grid(
        GridConfig(kind=BoardKind.FULL, board_width=2, board_height=2, connector_holes=True, screw_mounting=ScrewMounting.NONE)
    )
    for rotation in (0.0, 180.0):
        seated = connector.rotate(bd.Axis.Z, rotation).translate((28.0, 0.0, 2.3))
        overlap = board & seated
        assert overlap is None or overlap.volume < 1e-6


def test_connector_slot_delete_tool_cache_returns_distinct_public_shapes() -> None:
    config = ConnectorSlotDeleteToolConfig()
    _connector_slot_delete_tool_base.cache_clear()

    first = build_connector_slot_delete_tool(config)
    second = build_connector_slot_delete_tool(config)
    cache_info = _connector_slot_delete_tool_base.cache_info()

    assert first is not second
    assert cache_info.misses == 1
    assert cache_info.hits == 1
    first_size = first.bounding_box().size
    second_size = second.bounding_box().size
    assert (float(first_size.X), float(first_size.Y), float(first_size.Z)) == pytest.approx(
        (float(second_size.X), float(second_size.Y), float(second_size.Z))
    )


def test_connector_slot_config_rejects_neck_without_room() -> None:
    with pytest.raises(ValueError):
        ConnectorSlotDeleteToolConfig(neck_offset=10.0).validate()


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

@pytest.mark.parametrize(
    "part_kind",
    (MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_ROUND, MulticonnectPartKind.CONNECTOR_DOUBLE_SIDED_RAIL),
)
def test_multiconnect_double_sided_parts_join_stem_to_stem(part_kind: MulticonnectPartKind) -> None:
    part = build_multiconnect_part(MulticonnectConfig(part_kind=part_kind, length=28.0, dimples_enabled=False))

    assert part.is_valid
    # Wide r10 head on both outer faces (Y=0, Y=8), narrow r7.5 stem in the middle (Y=4).
    assert part.is_inside((9.0, 0.2, 0.5))
    assert part.is_inside((9.0, 7.8, 0.5))
    assert not part.is_inside((9.0, 4.0, 0.5))
    assert part.is_inside((7.0, 4.0, 0.5))


def test_multiconnect_rail_dimples_taper_from_face_on_every_pitch_and_both_caps() -> None:
    rail = build_multiconnect_rail(MulticonnectConfig(length=150.0, grid_size=28.0, rounding=MulticonnectRounding.BOTH_SIDES))

    for z in (0.0, 28.0, 56.0, 84.0, 112.0, 140.0, 150.0):
        # Source cone: r=1 at the head face, tapering to 0 at 1 mm depth.
        assert not rail.is_inside((0.9, 0.05, z))
        assert not rail.is_inside((0.35, 0.6, z))
        assert rail.is_inside((0.45, 0.6, z))
    assert rail.is_inside((0.0, 0.05, 14.0))


def test_multiconnect_open_ended_receiver_detents_and_ramps_start_at_closed_end() -> None:
    receiver = build_multiconnect_receiver(MulticonnectConfig(length=50.0, grid_size=28.0, on_ramps_enabled=False))
    seat_z = 50.0 - 10.15 - 2.5

    assert receiver.is_inside((0.0, 2.5, seat_z))
    assert receiver.is_inside((0.0, 2.5, seat_z - 28.0))
    assert not receiver.is_inside((0.0, 2.5, seat_z - 22.0))

    ramped = build_multiconnect_receiver(MulticonnectConfig(length=150.0, grid_size=28.0, dimples_enabled=False))
    ramp_z = 150.0 - 10.15 - 2.5 - 84.0
    assert not ramped.is_inside((10.9, 5.9, ramp_z))
    assert ramped.is_inside((10.9, 5.9, ramp_z + 18.0))

def test_output_dir_rejects_blank_directory() -> None:
    example_main = _example_main()

    with pytest.raises(SystemExit):
        example_main._output_dir({"output": {"directory": "   "}})

def test_verification_config_requires_explicit_flags() -> None:
    example_main = _example_main()

    config = {"verification": {"enabled": True, "variant_galleries": False}}
    verification = example_main._verification_config(config)
    assert verification.enabled is True
    assert verification.variant_galleries is False

    with pytest.raises(SystemExit):
        example_main._verification_config({"verification": {"enabled": True}})


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


def test_export_verification_outputs_honors_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    example_main = _example_main()
    configured_calls: list[dict[str, Any]] = []
    variant_calls: list[dict[str, Any]] = []

    def configured_export(**kwargs: Any) -> tuple[Path, ...]:
        configured_calls.append(kwargs)
        return (tmp_path / "configured" / "gallery.html",)

    def variant_export(**kwargs: Any) -> tuple[Path, ...]:
        variant_calls.append(kwargs)
        return (tmp_path / "variant" / "gallery.html",)

    monkeypatch.setattr(example_main, "_export_output_verification", configured_export)
    monkeypatch.setattr(example_main, "_export_variant_output_verification", variant_export)

    shape = cast(Any, object())
    snap_threads = SnapThreadConfig(height=4.0)
    snap_body = SnapBodyConfig(thickness=4.0)
    expanding = ExpandingSnapConfig(snap_body=snap_body, threads=snap_threads)
    common_args = {
        "grid": shape,
        "slot_delete_tool": shape,
        "adjacent_connector": shape,
        "multiconnect_rail": shape,
        "multiconnect_receiver": shape,
        "multiconnect_backer": shape,
        "multiconnect_delete_tool": shape,
        "snap_threads": shape,
        "snap_body": shape,
        "expanding_snap": shape,
        "openconnect_head": shape,
        "multiconnect_head": shape,
        "opengrid_snap": shape,
        "openconnect_screw": shape,
        "multiconnect_screw": shape,
        "board_config": GridConfig(),
        "slot_delete_tool_config": ConnectorSlotDeleteToolConfig(),
        "adjacent_connector_config": AdjacentGridConnectorConfig(),
        "multiconnect_config": MulticonnectConfig(),
        "snap_thread_config": snap_threads,
        "snap_body_config": snap_body,
        "expanding_snap_config": expanding,
        "openconnect_head_config": OpenConnectHeadConfig(),
        "connector_slot_config": ConnectorSlotConfig(),
        "multiconnect_head_config": MulticonnectHeadConfig(),
        "opengrid_snap_config": OpenGridSnapConfig(snap_body=snap_body, threads=snap_threads, expanding_snap=expanding),
        "openconnect_screw_config": OpenConnectScrewConfig(threads=snap_threads),
        "multiconnect_screw_config": MulticonnectScrewConfig(threads=snap_threads),
        "verification_dir": tmp_path,
    }

    disabled = example_main._export_verification_outputs(
        verification_config=example_main._VerificationConfig(enabled=False, variant_galleries=True),
        **common_args,
    )
    configured = example_main._export_verification_outputs(
        verification_config=example_main._VerificationConfig(enabled=True, variant_galleries=False),
        **common_args,
    )
    variant = example_main._export_verification_outputs(
        verification_config=example_main._VerificationConfig(enabled=True, variant_galleries=True),
        **common_args,
    )

    assert disabled == ()
    assert configured == (tmp_path / "configured" / "gallery.html",)
    assert variant == (tmp_path / "variant" / "gallery.html",)
    assert len(configured_calls) == 1
    assert len(variant_calls) == 1

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
    }

    assert centers[BoardKind.FULL] == pytest.approx(6.8 / 2.0)
    assert centers[BoardKind.LITE] == pytest.approx(4.0 - 2.4 / 2.0 - 1.0)


def test_heavy_board_has_capture_lip_on_both_outer_faces() -> None:
    # QuackWorks openGridHeavy: lip (offset 1.5) at z 0.4..1.4 and 12.4..13.4; middle and gap at 0.8.
    board = build_open_grid(
        GridConfig(kind=BoardKind.HEAVY, board_width=1, board_height=1, chamfers=ChamferMode.NONE, connector_holes=False, screw_mounting=ScrewMounting.NONE)
    )
    for z, offset in ((0.9, 1.5), (4.0, 0.8), (6.9, 0.8), (9.8, 0.8), (12.9, 1.5)):
        assert board.is_inside((-14.0 + offset - 0.05, 5.0, z))
        assert not board.is_inside((-14.0 + offset + 0.05, 5.0, z))


def test_lite_adhesive_base_keeps_slot_height_and_has_screw_holes() -> None:
    board = build_open_grid(
        GridConfig(kind=BoardKind.LITE, board_width=3, board_height=3, add_adhesive_base=True, screw_mounting=ScrewMounting.CORNERS, connector_holes=True)
    )
    # Slot stays at z 0.6..3.0 (QuackWorks cuts it before adding the base).
    assert not board.is_inside((-39.5, 14.0, 1.0))
    assert board.is_inside((-39.5, 14.0, 0.4))
    assert board.is_inside((-39.5, 14.0, 3.4))
    # Screw head clearance (diameter 7.2) passes through the 0.6 base.
    assert not board.is_inside((-14.0 + 3.4, -14.0, -0.3))
    assert board.is_inside((-14.0 + 3.8, -14.0, -0.3))


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
        (BoardKind.HEAVY, 3.4),
        (BoardKind.HEAVY, 10.4),
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


def test_board_is_one_fused_solid() -> None:
    board = build_open_grid(
        GridConfig(kind=BoardKind.FULL, board_width=3, board_height=5, chamfers=ChamferMode.EVERYWHERE, screw_mounting=ScrewMounting.EVERYWHERE)
    )

    assert len(board.solids()) == 1


def test_row_and_column_screw_holes_sit_on_grid_nodes() -> None:
    # QuackWorks/BOSL2: centred grid_copies plus parity shift -> 3x3, every 2 columns: holes at x=-14.
    board = build_open_grid(
        GridConfig(
            kind=BoardKind.FULL,
            board_width=3,
            board_height=3,
            chamfers=ChamferMode.NONE,
            connector_holes=False,
            screw_mounting=ScrewMounting.BY_ROW_AND_COLUMN,
            screw_every_x_columns=2,
        )
    )

    for y in (-14.0, 14.0):
        assert not board.is_inside((-14.0 + 1.5, y, 3.4))
        assert board.is_inside((-14.0 + 3.0, y, 3.4))
        assert board.is_inside((-28.0, y, 3.4))


def test_countersink_meets_counterbore_without_lip() -> None:
    board = build_open_grid(
        GridConfig(kind=BoardKind.FULL, board_width=3, board_height=3, chamfers=ChamferMode.NONE, connector_holes=False, screw_mounting=ScrewMounting.CORNERS)
    )

    # Counterbore (r 3.6) ends at z 5.81, cone (r 2.05 -> 3.6) spans z 4.27..5.81.
    assert not board.is_inside((14.0 + 3.5, 14.0, 5.805))
    assert not board.is_inside((14.0 + 2.1, 14.0, 4.4))
    assert board.is_inside((14.0 + 2.1, 14.0, 4.1))


def test_heavy_screw_heads_are_on_both_outer_faces() -> None:
    board = build_open_grid(
        GridConfig(kind=BoardKind.HEAVY, board_width=3, board_height=3, chamfers=ChamferMode.NONE, connector_holes=False, screw_mounting=ScrewMounting.CORNERS)
    )

    for z in (0.5, 13.3):
        assert not board.is_inside((14.0 + 3.4, 14.0, z))
    assert board.is_inside((14.0 + 3.4, 14.0, 6.9))


def test_full_stack_flips_boards_and_interface_matches_board_face() -> None:
    stack = build_open_grid(
        GridConfig(
            kind=BoardKind.FULL,
            board_width=2,
            board_height=3,
            chamfers=ChamferMode.CORNERS,
            connector_holes=False,
            screw_mounting=ScrewMounting.CORNERS,
            stack_count=2,
        )
    )

    # QuackWorks zflip()s every Full board: counterbore faces the bed.
    assert not stack.is_inside((0.0 + 3.4, 14.0, 0.5))
    assert stack.is_inside((0.0 + 3.4, 14.0, 6.3))
    # Interface (z 6.9..7.3) is the board face: 1.1 wall, 4.2 corner chamfer, 4.1 screw holes.
    assert stack.is_inside((-28.0 + 1.0, 0.0, 7.1))
    assert not stack.is_inside((-28.0 + 1.2, 0.0, 7.1))
    assert not stack.is_inside((-28.0 + 0.5, -42.0 + 0.5, 7.1))
    assert not stack.is_inside((0.0 + 1.5, 14.0, 7.1))


def test_lite_stack_alternates_board_orientation() -> None:
    stack = build_open_grid(
        GridConfig(kind=BoardKind.LITE, board_width=1, board_height=1, chamfers=ChamferMode.NONE, connector_holes=False, screw_mounting=ScrewMounting.NONE, stack_count=2)
    )

    # Board 0: flat 0.8 back down, 1.1 face up; board 1 flipped so the 1.1 faces meet across the interface.
    assert not stack.is_inside((-14.0 + 1.0, 0.0, 0.05))
    for z in (3.95, 4.3, 4.65):
        assert stack.is_inside((-14.0 + 1.0, 0.0, z))
    assert not stack.is_inside((-14.0 + 1.0, 0.0, 8.55))


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


def test_available_space_fill_clips_max_boards_to_space_in_mm() -> None:
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

    # QuackWorks FillSpaceClipOneSide: boards [0,56] and [61,75] (clip = space + full columns * spacing).
    assert size == pytest.approx((75.0, 45.0, 6.8))


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


def _material_intervals(shape: Any, start: tuple[float, float, float], end: tuple[float, float, float], axis: int) -> list[float]:
    """Flattened [lo, hi, ...] material spans along a probe line, merging touching edges."""
    section = shape & bd.Edge.make_line(start, end)
    spans: list[list[float]] = []
    for lo, hi in sorted(
        tuple(sorted((float(tuple(edge.position_at(0.0))[axis]), float(tuple(edge.position_at(1.0))[axis]))))
        for edge in section.edges()
    ):
        if spans and lo - spans[-1][1] < 1e-6:
            spans[-1][1] = max(spans[-1][1], hi)
        else:
            spans.append([lo, hi])
    return [value for span in spans for value in span]


def test_openconnect_head_matches_source_envelope_and_lock_reliefs() -> None:
    plain = build_openconnect_head(OpenConnectHeadConfig(add_nubs=False))
    locked = build_openconnect_head(OpenConnectHeadConfig(add_nubs=True))
    bbox = locked.bounding_box()

    assert (float(bbox.size.X), float(bbox.size.Y), float(bbox.size.Z)) == pytest.approx((17.0, 10.6, 2.6), abs=1e-6)
    assert float(bbox.min.Z) == pytest.approx(0.0, abs=1e-6)
    assert locked.volume < plain.volume
    assert OpenConnectHeadConfig().small_rect_width == pytest.approx(14.2)
    assert OpenConnectHeadConfig().small_rect_height == pytest.approx(9.2)

    # openconnect_lib.scad openconnect_lock: 0.6 deep trapezoid notch at y=1.7 (tip 7.905 from the
    # axis, 0.005 SCAD EPS outboard), flared mouth, z 0..2.0; the left notch tapers in 0.8 over the
    # middle chamfer while the right notch stays straight.
    def notch_line(z: float) -> list[float]:
        return _material_intervals(locked, (-20.0, 1.7, z), (20.0, 1.7, z), 0)

    assert notch_line(0.3) == pytest.approx([-7.905, 7.905], abs=0.002)
    assert notch_line(1.3) == pytest.approx([-7.505, 7.8], abs=0.002)
    assert notch_line(1.7) == pytest.approx([-7.277, 7.4], abs=0.002)
    mouth = _material_intervals(locked, (-8.45, -5.0, 0.3), (-8.45, 12.0, 0.3), 1)
    assert mouth == pytest.approx([-1.7, 0.461, 2.939, 4.951], abs=0.002)


def test_openconnect_screw_slots_follow_source_layout() -> None:
    screw = build_openconnect_screw()

    # Coin slot (openconnect_lib.scad:530-543): 13 mm chord on the outer face, open to the front
    # edge, 2.2 thick along X; the head stays one piece.
    assert len(screw.solids()) == 1
    assert _material_intervals(screw, (0.0, -20.0, 0.005), (0.0, 20.0, 0.005), 1) == pytest.approx([6.494, 8.9], abs=0.002)
    assert _material_intervals(screw, (-20.0, 3.0, 0.005), (20.0, 3.0, 0.005), 0) == pytest.approx(
        [-8.471, -1.1, 1.1, 8.471], abs=0.002
    )
    # Flat-blade prismoid: 6.5 along Y, 1.8 -> 1.2 along X, reaching z=5.0 inside the threads.
    flat_y = _material_intervals(screw, (0.0, -20.0, 4.9), (0.0, 20.0, 4.9), 1)
    assert flat_y[1:3] == pytest.approx([-3.25, 3.25], abs=0.002)
    flat_x = _material_intervals(screw, (-20.0, 2.5, 4.9), (20.0, 2.5, 4.9), 0)
    assert flat_x[1:3] == pytest.approx([-0.61, 0.61], abs=0.002)


def test_openconnect_folded_screw_matches_source_print_layout() -> None:
    folded = build_openconnect_screw(OpenConnectScrewConfig(folded=True))
    bbox = folded.bounding_box()

    # conditional_fold layout (opengrid_base.scad:192-219): one printable part joined by the hinge.
    assert len(folded.solids()) == 1
    assert (float(bbox.min.X), float(bbox.min.Y), float(bbox.min.Z)) == pytest.approx((-8.5, -7.205, 0.0), abs=0.01)
    assert (float(bbox.max.X), float(bbox.max.Y), float(bbox.max.Z)) == pytest.approx((8.5, 9.4, 10.605), abs=0.01)


def test_multiconnect_head_coin_slot_and_dimple_open_on_outer_face() -> None:
    plain = build_multiconnect_head(MulticonnectHeadConfig(top_pattern="none"))
    coin = build_multiconnect_head(MulticonnectHeadConfig(top_pattern="coin_slot"))
    dimple = build_multiconnect_head(MulticonnectHeadConfig(top_pattern="dimple"))

    assert float(plain.bounding_box().size.Z) == pytest.approx(4.0, abs=1e-6)
    # opengrid_parametric_snap.scad:377: 13 mm chord on the R10 face, 2.6 deep on axis, 2.2 thick.
    assert plain.volume - coin.volume == pytest.approx(51.125, abs=0.01)
    assert _material_intervals(coin, (-20.0, 0.0, 0.005), (20.0, 0.0, 0.005), 0) == pytest.approx(
        [-10.0, -6.494, 6.494, 10.0], abs=0.002
    )
    assert _material_intervals(coin, (-20.0, 0.0, 2.65), (20.0, 0.0, 2.65), 0) == pytest.approx([-8.35, 8.35], abs=0.002)
    assert _material_intervals(coin, (0.0, -20.0, 1.0), (0.0, 20.0, 1.0), 1) == pytest.approx(
        [-10.0, -1.1, 1.1, 10.0], abs=0.002
    )
    # Official round.step dimple: r1.05 at the R10 face, r0.05 at 1.0 deep.
    assert plain.volume - dimple.volume == pytest.approx(1.212, abs=0.002)
    assert _material_intervals(dimple, (-20.0, 0.0, 0.5), (20.0, 0.0, 0.5), 0) == pytest.approx(
        [-10.0, -0.55, 0.55, 10.0], abs=0.002
    )


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

    assert threaded.bounding_box().size.Z == pytest.approx(bare.bounding_box().size.Z, abs=1e-6)
    assert openconnect.bounding_box().size.Z > bare.bounding_box().size.Z
    assert multiconnect.bounding_box().size.Z > bare.bounding_box().size.Z
    assert threaded.volume < bare.volume
    assert openconnect.volume > bare.volume
    assert multiconnect.volume > bare.volume


def test_basic_threads_snap_cuts_a_hole_that_seats_the_screw_thread() -> None:
    # opengrid_parametric_snap.scad:418-421 cuts snap_threads (clearance 0.5) through the body, turned
    # 180 degrees about Y with its thread frame at the snap top. The screw thread (clearance 0) seated as
    # in :448-455 (up(h + head) yrot(180)) must mesh without interference.
    snap = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.BASIC_THREADS))
    thickness = OpenGridSnapConfig().snap_body.thickness
    screw = build_snap_threads(SnapThreadConfig(height=thickness, clearance=0.0))

    assert not snap.is_inside((0.0, 0.0, thickness / 2.0))
    seated = snap & screw.rotate(bd.Axis.Y, 180.0).translate((0.0, 0.0, thickness))
    assert seated is None or seated.volume < 1e-3
    unflipped = snap & screw
    assert unflipped is not None and unflipped.volume > 1.0



@pytest.mark.parametrize(
    ("kind", "small_half_width", "large_half_width", "head_height"),
    ((OpenGridSnapKind.OPENCONNECT, 7.10, 8.50, 2.6), (OpenGridSnapKind.MULTICONNECT, 7.5, 10.0, 4.0)),
)
def test_opengrid_snap_heads_mount_small_face_on_snap(
    kind: OpenGridSnapKind, small_half_width: float, large_half_width: float, head_height: float
) -> None:
    # Source attach(TOP, TOP): the slot-retained large face must be outermost, not against the snap.
    thickness = SnapBodyConfig().thickness
    snap = build_opengrid_snap(OpenGridSnapConfig(kind=kind))

    def half_width_at(z: float) -> float:
        slab = cast(Any, snap & bd.Box(60.0, 60.0, 0.02).translate((0.0, 0.0, z)))
        return float(slab.bounding_box().max.X)

    assert len(snap.solids()) == 1
    assert float(snap.bounding_box().max.Z) == pytest.approx(thickness + head_height, abs=1e-3)
    assert half_width_at(thickness + 0.05) == pytest.approx(small_half_width, abs=0.01)
    assert half_width_at(thickness + head_height - 0.05) == pytest.approx(large_half_width, abs=0.01)


def test_multiconnect_snap_outer_face_has_dimple_not_coin_slot() -> None:
    # Source snap uses multiconnect_head(top_pattern="dimple"); a 13 x 2.4 coin slot would remove ~30 mm^2 here.
    snap = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.MULTICONNECT))
    top = float(snap.bounding_box().max.Z)
    area = cast(Any, snap & bd.Box(30.0, 30.0, 0.002).translate((0.0, 0.0, top - 0.005))).volume / 0.002

    assert math.pi * (10.0**2 - 1.1**2) < area < math.pi * (10.0**2 - 0.9**2)


def test_text_engraving_removes_material_from_product_builders() -> None:
    label = TextLabel(text="OG", size=3.0, depth=0.2)
    text = TextEngravingConfig(labels=(label,))
    plain = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.BARE))
    engraved = build_opengrid_snap(OpenGridSnapConfig(kind=OpenGridSnapKind.BARE, text=text))

    assert engraved.bounding_box().size == pytest.approx(plain.bounding_box().size)
    assert engraved.volume < plain.volume
