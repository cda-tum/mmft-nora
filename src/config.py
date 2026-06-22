import math
from dataclasses import dataclass, field

# Prior Definitions
@dataclass
class Config:
    eps = 1e-12
    two_gradients = True # Do we investigate gradients of 2 drugs at the same time
    no_of_modules_x = 3 # min value is always 1 
    no_of_modules_y = 1 # min value is always 1

    # e.g. 3x3 modules
    # A0----B0----C0
    # |     |     | 
    # A1----B1----C1
    # |     |     |
    # A2----B2----C2  

    concentration_dilution_x = 0.1 # I.e. resulting in a 1:9 dilution at each step
    concentration_dilution_y = 0.1 # I.e. resulting in a 1:9 dilution at each step

    viscosity = 1e-3 # viscosity of the fluid

    layer_0 = 0 #0.0
    layer_1 = 1 # 1.0e-3
    layer_2 = 2 # 2.0e-3

    # All geometric dimensions in this configuration are stored in meters.
    # Default channel dimensions (might eventually be user defined)
    channel_dim = {
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

    height_for_convergence = 40e-6

    # These spacing defaults can be tuned to improve the initial guess and improve convergence within the
    pump_connection_distance_in = 6e-3 # Keep above the 5.5e-3 1-to-9 mixing module length for the 3x1 design.
    pump_connection_distance_out = 8e-3
    inlet_distance = 3e-3 # distance between the inlets for the concentration and the media 1

    # Define the spacing of the modules and the length of the outflow channels
    # spacing_x can be reduced to 3 for 3x3 modules
    spacing_x = 5 * channel_dim['min_distance']
    spacing_y = 2 * channel_dim['min_distance']
    spacing_out = 2 * channel_dim['min_distance']

    distance_module_mixing = channel_dim["spacer"] # this might be redundant

    organ_module = {
        "size_x": 9.0e-3,
        "size_y": 12.0e-3,
        "flow_rate": 1.67e-11, #1.67e-11, # m^3/s
        "via_diameter": 0.4e-3,
    }

    extra_length_straight = 0.7e-3
    extra_length_curve = 2.4e-3 + 0.7e-3 + 0.4e-3 + 0.2e-3 - 0.15e-3 * (0.5 * math.pi - 2) # 0.7e-3 to the right 0.6e-3 down and a rounded corner with the enterline radius of 0.15e-3
    mixing_channel_height = 0.1e-3
    mixing_channel_width = 0.4e-3

    mixing_module = {
        "channel_width": 0.4e-3,
        "channel_height": 0.1e-3,
        "connection_required": True, 
        "1to1": {
            "node_offset_x": 0e-3,
            "node_offset_y": 3e-3,
            "width": 10e-3,
            "length": 3e-3, 
            "fixed_resistance_input": 7.55e11
        },
        "1to9": {
            "node_offset_x": 0e-3,
            "node_offset_y": 0e-3,
            "width": 5.63e-3 + 2 * 0.7e-3,
            "length": 3e-3,
            "fixed_resistance_input": 5.8e11 - 2.72e10
        }
    }

    # print("Mixing module 1:1 fixed resistance:", mixing_module["1to1"]["fixed_resistance"])
    # print("Mixing module 1:9 fixed resistance:", mixing_module["1to9"]["fixed_resistance"])

    if organ_module["size_x"] < mixing_module["1to1"]["node_offset_x"] or organ_module["size_y"] < mixing_module["1to1"]["node_offset_y"]: # TODO adapt this check for wider mixing modules.
        #TODO add some logic here to make sure that the mixing module fits on the chip (for the 1:10/1:5 mixing)
        # add a spacer or something to add space on the left hand side
        raise ValueError("The mixing module is larger than the module size")


    chip_layout = { # standardized well-plate layout
        "size_x": 85.48e-3,
        "size_y": 127.76e-3,
        "spacing_side": 7e-3 # distance of the channels and inlets to the chip sides
    }

    exclusion_zone_input = [ # example exclusion zones that are fixed with respect to the board and not adapted by the spacing variables.
        # {"name": "bolt_horizontal", "position": (12e-3, 7e-3, 0.0), "x_width": 7e-3, "y_length": 5e-3},
        # {"name": "bolt_vertical", "position": (10e-3, 20e-3, 0.0), "x_width": 3e-3, "y_length": 2e-3},
        # {"name": "bolt_vertical_2", "position": (10e-3, 25e-3, 0.0), "x_width": 1e-3, "y_length": 2e-3},
        # {"name": "bolt_vertical_3", "position": (4e-3, 18e-3, 0.0), "x_width": 3e-3, "y_length": 2e-3},
        # {"name": "bolt_vertical_4", "position": (9e-3, 22e-3, 0.0), "x_width": 2e-3, "y_length": 1e-3},
        # {"name": "bolt_SE", "position": (117e-3, 10e-3, 0.0), "x_width": 7e-3, "y_length": 50e-3},
        # {"name": "bolt_NE", "position": (117e-3, 75e-3, 0.0), "x_width": 15e-3, "y_length": 3e-3},
        # {"name": "bolt_NW", "position": (10e-3, 75e-3, 0.0), "x_width": 2e-3, "y_length": 3e-3},
    ]

    module_exclusion_zone_offset_x = 10.5e-3
    module_exclusion_zone_offset_y = 7.5e-3
    module_exclusion_zone_width = 4.0e-3
    module_exclusion_zone_length = 4.0e-3

    grid_resolution = 0.1e-3 # grid resolution for A* pathfinding algorithm that reroutes the channels around exclusion zones
