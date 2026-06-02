# Compare the desired and the resulting flowrates after another nodal analysis (after the geometry adaption)
import math
import pytest

import src.main as main
from src.utils import calculate_hydraulic_resistance, calculate_hydraulic_resistance_cylinder
from src.modified_nodal_analysis import conduct_nodal_analysis, define_extra_pressure_constraints
from src.config import Config

cfg = Config()

param_combinations = [(2,1),(2,2),(3,1),(1,3),(3,3)] # number of modules in x and y direction TODO (1,2) does not work with the current config settings

@pytest.fixture(params=param_combinations)
def solved_network(request):
    """Run the main geometry setup once and return nodes, channels, and config."""
    nx, ny = request.param
    cfg = Config()
    cfg.no_of_modules_x = nx
    cfg.no_of_modules_y = ny

    nodes, channels, exclusion_zones, export_result = main.main(cfg)
    return nodes, channels, cfg

# @pytest.mark.parametrize("built_network", [(2, 1), (3, 1), (1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (3, 3)], indirect=True)
def test_flowrates_after_geometry_adaption(solved_network):
    nodes, channels, cfg = solved_network

    pressure_matching_pairs = define_extra_pressure_constraints(cfg.no_of_modules_x, cfg.no_of_modules_y)
    flow_rate_out = cfg.no_of_modules_x * cfg.no_of_modules_y * cfg.organ_module["flow_rate"] * 2
    pressure_out = channels[f"chip_outflow_{cfg.no_of_modules_x - 1}"].calculate_hydraulic_resistance(nodes, cfg.viscosity) * flow_rate_out

    conduct_nodal_analysis(nodes, channels, cfg.viscosity, pressure_out, pressure_matching_pairs)

    for cid, channel in channels.items():
        if channel.fixed_resistance is not None:
            R_h = channel.calculate_hydraulic_resistance(nodes, cfg.viscosity)
            # TODO add the via resistance if multilayer
            node1 = nodes[channel.node1]
            node2 = nodes[channel.node2]
            dP = abs(node2.pressure - node1.pressure)
            Q_after_geometry_adaption = dP / R_h
            error = Q_after_geometry_adaption - channel.flow_rate

            assert abs(error) < 1e-9, f"Flow mismatch of {error} in {cid}"

def test_via_addition_in_resistance(solved_network):
    nodes, channels, cfg = solved_network

    for cid, channel in channels.items():
        if channel.fixed_resistance is None:
            R_h_total = channel.calculate_hydraulic_resistance(nodes, cfg.viscosity)
            R_h_via = 0.0
            R_h_channel = calculate_hydraulic_resistance(channel.width, channel.height, channel.length, cfg.viscosity)
            if nodes[channel.node1].multi_layer:
                R_h_via = calculate_hydraulic_resistance_cylinder(cfg.channel_dim["layer_switch_distance"], cfg.channel_dim["via_diameter"] / 2, cfg.viscosity)

            mismatch = abs(R_h_total - (R_h_channel + R_h_via))
            assert mismatch < 0.0 + 1e-12, f"The total resitance does not match channel and via resistance in channel {cid}"

def test_pressure_constraints(solved_network): #TODO
    nodes, channels, cfg = solved_network

    pressure_matching_pairs = define_extra_pressure_constraints(cfg.no_of_modules_x, cfg.no_of_modules_y)

    # flow_rate_out = cfg.no_of_modules_x * cfg.no_of_modules_y * cfg.organ_module["flow_rate"] * 2
    # pressure_out = channels[f"chip_outflow_{cfg.no_of_modules_x - 1}"].calculate_hydraulic_resistance(cfg.viscosity) * flow_rate_out
    # pressures = conduct_nodal_analysis(nodes, channels, cfg.viscosity, pressure_out, pressure_matching_pairs)

    for pair in pressure_matching_pairs:
        pressure1 = nodes[pair[0]].pressure
        pressure2 = nodes[pair[1]].pressure

        assert math.isclose(pressure1, pressure2, rel_tol=1e-9), f"There is a pressure mismatch between {pair[0]} and {pair[1]}"


def compute_channel_length(channel, nodes):
    """
    Returns the total 2D length of a plotted channel, including meanders. 
    """
    total = 0.0

    # 1) pick off its endpoints
    coord1 = nodes[channel.node1].coordinates
    coord2 = nodes[channel.node2].coordinates

    if channel.vertical:
        direction = (0, 1)
        start = coord1 if coord1[1] < coord2[1] else coord2
        end = coord2 if coord1[1] < coord2[1] else coord1
    else:
        # take the left node
        direction = (1, 0)
        start = coord1 if coord1[0] < coord2[0] else coord2
        end = coord2 if coord1[0] < coord2[0] else coord1

    if hasattr(channel, "meander_nodes") and channel.meander_nodes:
        path = [start] + channel.meander_nodes + [end]
        print(f"Channel has meander nodes, calculating length based on path: {path}")
        
    else:
        path = [start, end]

    # 4) sum the straight‐line distances between successive points
    
    for (x0, y0, *_), (x1, y1, *_) in zip(path, path[1:]):
        total += math.hypot(x1 - x0, y1 - y0)

    return total

def test_channel_length_after_geometry_adaption(solved_network):
    # TODO this needs to include the transferred length
    nodes, channels, cfg = solved_network

    for channel_id, channel in channels.items():
        assigned_length = channel.length
        placed_length = compute_channel_length(channel, nodes)
        print(f"Channel {channel_id} assigned length: {assigned_length}, placed length: {placed_length}, difference: {assigned_length - placed_length}")

        if channel.transfered_length or channel.rerouted or channel.fixed_resistance is not None:
            # skip this channel for now, because the length is transfered to a connected channel and thus not added to the length of this channel
            continue
        else:
            assert math.isclose(assigned_length, placed_length, abs_tol=1e-8), f"Channel {channel_id} has a mismatch between placed and assigned length of {assigned_length-placed_length}"
