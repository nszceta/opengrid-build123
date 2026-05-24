"""build123d conversion of the parametric openGrid generator."""

from opengrid_build123.opengrid import (
    BoardKind,
    ChamferMode,
    AdjacentGridConnectorConfig,
    ConnectorSlotDeleteToolConfig,
    FillSpaceMode,
    GridConfig,
    ScrewMounting,
    StackingMethod,
    build_adjacent_grid_connector,
    build_connector_slot_delete_tool,
    build_fill_space,
    build_open_grid,
    export_grid,
    open_grid,
    open_grid_heavy,
    open_grid_lite,
)

__all__ = [
    "BoardKind",
    "ChamferMode",
    "AdjacentGridConnectorConfig",
    "ConnectorSlotDeleteToolConfig",
    "FillSpaceMode",
    "GridConfig",
    "ScrewMounting",
    "StackingMethod",
    "build_adjacent_grid_connector",
    "build_connector_slot_delete_tool",
    "build_fill_space",
    "build_open_grid",
    "export_grid",
    "open_grid",
    "open_grid_heavy",
    "open_grid_lite",
]
