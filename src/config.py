import math
from dataclasses import dataclass, field
from typing import Any


def _default_channel_dim() -> dict[str, float]:
    return {
        "width": 150e-6,
        "max_width": 1.5e-3, # If required, this can be updated to 2e-3.
        "height": 150e-6,
        "max_height": 1.4e-3,
        "min_distance": 0.4e-3, # Based on Laurens input and experiments.
        "spacer": 12 * 0.4e-3,
        # "spacer_outflow": 15 * 0.4e-3,
        "via_diameter": 0.7e-3,
        "layer_switch_distance": 1.162e-3, # Thickness of the foil and extra plate between routing layers.
        "layer_switch_distance_organ": 1.8e-3, # Organ-module layer switch distance.
    }


def _default_organ_module() -> dict[str, float]:
    return {
        "size_x": 9.0e-3,
        "size_y": 12.0e-3,
        "flow_rate": 1.67e-11, # m^3/s
        "via_diameter": 0.4e-3,
    }


def _default_mixing_module() -> dict[str, Any]:
    return {
        "channel_width": 0.4e-3,
        "channel_height": 0.1e-3,
        "connection_required": True,
        "1to1": {
            "node_offset_x": 0e-3,
            "node_offset_y": 3e-3,
            "width": 10e-3,
            "length": 3e-3,
            "fixed_resistance_input": 7.55e11,
        },
        "1to9": {
            "node_offset_x": 0e-3,
            "node_offset_y": 0e-3,
            "width": 5.63e-3 + 2 * 0.7e-3,
            "length": 3e-3,
            "fixed_resistance_input": 5.8e11 - 2.72e10,
        },
    }


def _default_chip_layout() -> dict[str, float]:
    return {
        "size_x": 85.48e-3,
        "size_y": 127.76e-3,
        "spacing_side": 7e-3, # distance of the channels and inlets to the chip sides
    }


@dataclass
class Config:
    eps: float = 1e-12
    two_gradients: bool = True # Do we investigate gradients of 2 drugs at the same time
    no_of_modules_x: int = 3 # min value is always 1
    no_of_modules_y: int = 1 # min value is always 1

    # e.g. 3x3 modules
    # A0----B0----C0
    # |     |     |
    # A1----B1----C1
    # |     |     |
    # A2----B2----C2

    concentration_dilution_x: float = 0.1 # I.e. resulting in a 1:9 dilution at each step
    concentration_dilution_y: float = 0.1 # I.e. resulting in a 1:9 dilution at each step

    viscosity: float = 1e-3 # viscosity of the fluid

    layer_0: int = 0 #0.0
    layer_1: int = 1 # 1.0e-3
    layer_2: int = 2 # 2.0e-3

    # All geometric dimensions in this configuration are stored in meters.
    # Default channel dimensions (might eventually be user defined)
    channel_dim: dict[str, float] = field(default_factory=_default_channel_dim)

    height_for_convergence: float = 40e-6

    # These spacing defaults tune the initial guess and help keep channel
    # dimensions within their configured bounds during convergence.
    pump_connection_distance_in: float = 6e-3 # Keep above the 5.5e-3 1-to-9 mixing module length for the 3x1 design.
    pump_connection_distance_out: float = 8e-3
    inlet_distance: float = 3e-3 # distance between the inlets for the concentration and the media 1

    # Define the spacing of the modules and the length of the outflow channels
    # spacing_x can be reduced to 3 for 3x3 modules
    spacing_x: float | None = None
    spacing_y: float | None = None
    spacing_out: float | None = None

    distance_module_mixing: float | None = None # this might be redundant

    organ_module: dict[str, float] = field(default_factory=_default_organ_module)

    extra_length_straight: float = 0.7e-3
    extra_length_curve: float = 2.4e-3 + 0.7e-3 + 0.4e-3 + 0.2e-3 - 0.15e-3 * (0.5 * math.pi - 2) # 0.7e-3 to the right 0.6e-3 down and a rounded corner with the enterline radius of 0.15e-3
    mixing_channel_height: float = 0.1e-3
    mixing_channel_width: float = 0.4e-3

    mixing_module: dict[str, Any] = field(default_factory=_default_mixing_module)

    # Standardized well-plate layout.
    chip_layout: dict[str, float] = field(default_factory=_default_chip_layout)

    # Example exclusion zones are fixed with respect to the board and are not
    # adapted by the spacing variables.
    exclusion_zone_input: list[dict[str, Any]] = field(default_factory=list)

    module_exclusion_zone_offset_x: float = 10.5e-3
    module_exclusion_zone_offset_y: float = 7.5e-3
    module_exclusion_zone_width: float = 4.0e-3
    module_exclusion_zone_length: float = 4.0e-3

    grid_resolution: float = 0.1e-3 # grid resolution for A* pathfinding algorithm that reroutes the channels around exclusion zones
    output_dxf_path: str | None = None
    output_preview_path: str | None = None

    def __post_init__(self) -> None:
        if self.spacing_x is None:
            self.spacing_x = 5 * self.channel_dim["min_distance"]
        if self.spacing_y is None:
            self.spacing_y = 2 * self.channel_dim["min_distance"]
        if self.spacing_out is None:
            self.spacing_out = 2 * self.channel_dim["min_distance"]
        if self.distance_module_mixing is None:
            self.distance_module_mixing = self.channel_dim["spacer"]

        if (
            self.organ_module["size_x"] < self.mixing_module["1to1"]["node_offset_x"]
            or self.organ_module["size_y"] < self.mixing_module["1to1"]["node_offset_y"]
        ):
            raise ValueError("The mixing module is larger than the module size")
