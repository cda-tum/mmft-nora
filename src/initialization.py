import math

from .config import Config
from .utils import calculate_hydraulic_resistance, calculate_hydraulic_resistance_cylinder
from .mf_geometry_components import Node, Channel, ExclusionZone

cfg = Config()

def get_concentration_ratio(two_gradients, ratio):
    if two_gradients:
        ratio = 1
        ratio_between_gradients = ratio / 2 # ratio between the two gradients x/y

    return ratio_between_gradients

def get_concentration_dilutions(cfg):
    ratio_between_gradients = get_concentration_ratio(two_gradients=True, ratio=1)

    concentration_dilution_x = cfg.concentration_dilution_x / ratio_between_gradients
    concentration_dilution_y = cfg.concentration_dilution_y / (1 - ratio_between_gradients)

    return concentration_dilution_x, concentration_dilution_y

def get_fixed_resistance_organ_module_top(cfg): # based on synovium-on-chip
    layer_switch_resistance_module = get_layer_switch_resistance_module(cfg)
    fixed_resistance_top = calculate_hydraulic_resistance(width=1.25e-3, height=0.325e-3, length=18e-3, viscosity=cfg.viscosity) + 2 * layer_switch_resistance_module # length = 6e-3 m + 6e-3 m connection to the sides ?, width = 1.25e-3 m, height = 400e-6 m
    return fixed_resistance_top

def get_fixed_resistance_organ_module_bottom(cfg): # based on synovium-on-chip
    layer_switch_resistance_module = get_layer_switch_resistance_module(cfg)
    fixed_resistance_bottom = calculate_hydraulic_resistance(width=1.25e-3, height=0.25e-3, length=18e-3, viscosity=cfg.viscosity) + 2 * layer_switch_resistance_module # length and width are the same and height = 250e-6 m
    
    layer_switch_resistance_plate = calculate_hydraulic_resistance_cylinder(cfg.channel_dim["layer_switch_distance"], cfg.organ_module["via_diameter"] / 2, cfg.viscosity)
    fixed_resistance_bottom += layer_switch_resistance_plate

    return fixed_resistance_bottom

def get_organ_module_flow_rate_bottom(cfg): # TODO make this dependent on whichever input I get (resistance or geometry or flowrate etc.)
    # To ensure TMP matching the pressure drop of the bottom channel needs to be the same as the top (and the absolute pressures need to be the same at the inlet nodes), since the flow rate is fixed in the top compartment 

    fixed_resistance_top = get_fixed_resistance_organ_module_top(cfg)
    fixed_resistance_bottom = get_fixed_resistance_organ_module_bottom(cfg)
    pressure_drop_top = (cfg.organ_module["flow_rate"] * fixed_resistance_top)
    pressure_drop_bottom = pressure_drop_top
    organ_module_flow_rate_bottom = pressure_drop_bottom / fixed_resistance_bottom
    # flow_rate_bottom_for_TMP = organ_module["flow_rate"]

    # print("Organ module fixed resistance top:", fixed_resistance_top)
    # print("Organ module fixed resistance bottom:", fixed_resistance_bottom)
    # print("Flow rate in the bottom compartment of the organ module:", organ_module_flow_rate_bottom)
    return organ_module_flow_rate_bottom

def get_no_of_modules(no_of_modules_x, no_of_modules_y):
    return no_of_modules_x * no_of_modules_y

def get_total_chip_flow_rate_out(cfg):
    flow_rate_top = cfg.organ_module["flow_rate"]
    flow_rate_bottom = get_organ_module_flow_rate_bottom(cfg)
    flow_rate_per_organ_module = flow_rate_top + flow_rate_bottom

    no_of_modules_total = get_no_of_modules(cfg.no_of_modules_x, cfg.no_of_modules_y)

    return no_of_modules_total * flow_rate_per_organ_module

def get_mixing_module_resistances(cfg):
    # add the connection required to include the resistance things into the calculation
    if cfg.mixing_module["connection_required"]:
        R_h_extra_connection_straight = calculate_hydraulic_resistance(width=cfg.mixing_channel_width, height=cfg.mixing_channel_height, length=cfg.extra_length_straight, viscosity=cfg.viscosity)
        R_h_extra_connection_curve = calculate_hydraulic_resistance(width=cfg.mixing_channel_width, height=cfg.mixing_channel_height, length=cfg.extra_length_curve, viscosity=cfg.viscosity)
        
        fixed_resistance_1_1_total = cfg.mixing_module["1to1"]["fixed_resistance_input"] + R_h_extra_connection_straight * 2 # 1:1

        fixed_resistance_1_9_total = cfg.mixing_module["1to9"]["fixed_resistance_input"] + R_h_extra_connection_curve + R_h_extra_connection_straight # 1:9
    else:
        fixed_resistance_1_1_total = cfg.mixing_module["1to1"]["fixed_resistance_input"]
        fixed_resistance_1_9_total = cfg.mixing_module["1to9"]["fixed_resistance_input"]

    return fixed_resistance_1_1_total, fixed_resistance_1_9_total

def get_layer_switch_resistance_module(cfg):
    layer_switch_resistance_module = calculate_hydraulic_resistance_cylinder(cfg.channel_dim["layer_switch_distance_organ"], cfg.organ_module["via_diameter"] / 2, cfg.viscosity) 
    return layer_switch_resistance_module

##################################################### Geometry initialization ##################################################################

def initialize_nodes(nodes, cfg, layer_0, layer_1, layer_2, spacing_x, spacing_y, spacing_out):
    # the number of nodes is based on the number of module
    no_of_modules_x = cfg.no_of_modules_x
    no_of_modules_y = cfg.no_of_modules_y

    conc_x_channel_length = spacing_x
    conc_y_channel_length = spacing_y

    pump_connection_distance_in = cfg.pump_connection_distance_in
    pump_connection_distance_out = cfg.pump_connection_distance_out
    inlet_distance = cfg.inlet_distance
    chip_spacing_side = cfg.chip_layout["spacing_side"]
    distance_module_mixing = cfg.distance_module_mixing
                
    organ_module_size_x = cfg.organ_module["size_x"]
    organ_module_size_y = cfg.organ_module["size_y"]
    node_offset_mix_1to1_x = cfg.mixing_module["1to1"]["node_offset_x"]
    node_offset_mix_1to1_y = cfg.mixing_module["1to1"]["node_offset_y"]
    mixing_module_1to9_width = cfg.mixing_module["1to9"]["width"]

    module_position_x = 0.0 + chip_spacing_side + pump_connection_distance_in + inlet_distance + conc_x_channel_length + node_offset_mix_1to1_x
    module_position_y = 0.0 + chip_spacing_side + pump_connection_distance_in + inlet_distance + conc_y_channel_length + node_offset_mix_1to1_y + distance_module_mixing
    z_layer_0 = layer_0 * 1e-3
    z_layer_1 = layer_1 * 1e-3
    z_layer_2 = layer_2 * 1e-3

    module_spacing_x = conc_x_channel_length + node_offset_mix_1to1_x + spacing_x + spacing_out
    module_spacing_y = conc_y_channel_length + node_offset_mix_1to1_y + spacing_y + spacing_out + distance_module_mixing

    # Define in and outflowing nodes of each module
    # n north, w west, s south, e east
    for i in range(no_of_modules_x):
        for j in range(no_of_modules_y):
            module = f"{chr(65 + i)}{j}"

            coordinate_x_nw = module_position_x + i * (organ_module_size_x + module_spacing_x)
            coordinate_y_nw = module_position_y + j * (organ_module_size_y + module_spacing_y)

            nodes[f"N_{module}_nw"] = Node(
                connection_no = 2,
                multi_layer = False, # TODO define how to handle this for organ modules
                coordinates = (coordinate_x_nw, coordinate_y_nw, z_layer_0) # defines the layout with y pointing "downwards", i.e., the y coordinate going down (typical for computer science but not traditional CAD)
            )
            nodes[f"N_{module}_ne"] = Node(
                connection_no = 2,
                multi_layer = True,
                coordinates = (coordinate_x_nw + organ_module_size_x, coordinate_y_nw, z_layer_0)
            )
            nodes[f"N_{module}_sw"] = Node(
                connection_no = 2,
                multi_layer = False,
                coordinates = (coordinate_x_nw, coordinate_y_nw + organ_module_size_y, z_layer_0)
            )
            nodes[f"N_{module}_se"] = Node(
                connection_no = 2,
                multi_layer = False,
                coordinates = (coordinate_x_nw + organ_module_size_x, coordinate_y_nw + organ_module_size_y, z_layer_0)
            )

            # define the nodes associated with each module for the outflow
            nodes[f"N_mix_{module}"] = Node(
                connection_no = 3,
                multi_layer = True, 
                coordinates = (
                    coordinate_x_nw - node_offset_mix_1to1_x, 
                    # coordinate_y_nw - node_offset_mix_1to1_y - distance_module_mixing, 
                    coordinate_y_nw - node_offset_mix_1to1_y - spacing_y, 
                    z_layer_1 # TODO can we do a 2 layer shift?
                )
            )
            nodes[f"N_inflow_{module}"] = Node(
                connection_no = 2,
                multi_layer = False,
                coordinates = (
                    coordinate_x_nw, 
                    coordinate_y_nw - spacing_y, 
                    z_layer_2
                )
            )  
            # define the nodes for the media 2 inflow in the other organ chip compartment
            nodes[f"N_{module}_media2"] = Node(
                connection_no = 2, # or 3
                multi_layer = False,
                coordinates = (
                    coordinate_x_nw + organ_module_size_x, 
                    coordinate_y_nw - spacing_y, 
                    z_layer_1
                )
            )

            # define the nodes for the outflow 
            nodes[f"N_{module}_out_sw"] = Node(
                connection_no = 2,
                multi_layer = False,
                coordinates = (
                    coordinate_x_nw, 
                    coordinate_y_nw + organ_module_size_y + spacing_out, 
                    z_layer_2
                )
            )
            nodes[f"N_{module}_out_se"] = Node(
                connection_no = 2,
                multi_layer = False,
                coordinates = (
                    coordinate_x_nw + organ_module_size_x, 
                    coordinate_y_nw + organ_module_size_y + spacing_out, 
                    z_layer_2
                )
            )
            nodes[f"N_{module}_out"] = Node(
                connection_no = 2,
                multi_layer = False,
                coordinates = (
                    coordinate_x_nw + organ_module_size_x + spacing_x * 0.75, # TODO find an ideal value for this
                    coordinate_y_nw + organ_module_size_y + spacing_out, 
                    z_layer_2
                )
            )

            # define the node connections for the concentrations
            nodes[f"N_{module}_conc_x"] = Node(
                connection_no = 2, # TODO more if there are more modules
                multi_layer = False,
                coordinates = (
                    coordinate_x_nw - node_offset_mix_1to1_x - conc_x_channel_length, 
                    # coordinate_y_nw - node_offset_mix_1to1_y - distance_module_mixing,
                    coordinate_y_nw - node_offset_mix_1to1_y - spacing_y,
                    z_layer_2
                )
            )
            nodes[f"N_{module}_conc_y"] = Node(
                connection_no = 2, # TODO more (3) if there are more modules
                multi_layer = False,
                coordinates = (
                    coordinate_x_nw - node_offset_mix_1to1_x, 
                    coordinate_y_nw - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length, 
                    z_layer_1
                )
            )
            if j == 0: # for all other modules the branch node is the previous conc_x node
                nodes[f"N_{module}_x_branch"] = Node(
                    connection_no = 2,
                    multi_layer = False,
                    coordinates = (
                        coordinate_x_nw - node_offset_mix_1to1_x - conc_x_channel_length, 
                        coordinate_y_nw - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in, # TODO double check this, is minimal channel distance missing? 
                        z_layer_2
                    )
                )
            if i == 0: # for all other modules the branch node is the previous conc_y node
                nodes[f"N_{module}_y_branch"] = Node(
                    connection_no = 2,
                    multi_layer = False,
                    coordinates = (
                        coordinate_x_nw - node_offset_mix_1to1_x - conc_x_channel_length - pump_connection_distance_in, 
                        coordinate_y_nw - node_offset_mix_1to1_y - conc_y_channel_length - distance_module_mixing, 
                        z_layer_1
                    )
                )
                # media 2
                nodes[f"N_{j}_media2"] = Node(
                    connection_no = 2, # or 3
                    multi_layer = False,
                    coordinates = (
                        module_position_x + (no_of_modules_x - 1) * (organ_module_size_x + module_spacing_x) + organ_module_size_x + spacing_x + pump_connection_distance_in, 
                        module_position_y + j * (organ_module_size_y + module_spacing_y) - spacing_y, 
                        z_layer_1
                    )
                )
        
        nodes[f"N_{chr(65 + i)}{no_of_modules_y}_out"] = Node( # This means there is always one more node than modules (defined this way to make it easier for the channel definition)
            connection_no = 2, # TODO depends on which node it is
            multi_layer = False,
            coordinates = (
                module_position_x + i * (organ_module_size_x + module_spacing_x) + organ_module_size_x + spacing_x * 0.75, # TODO see above for the out node 
                module_position_y + (no_of_modules_y - 1) * (organ_module_size_y + module_spacing_y) + (organ_module_size_y) + spacing_y + spacing_out, 
                z_layer_2) # TODO
        )

    # Add the nodes for the media 1 flow, these nodes are a bit more flexible, maybe it makes sense to move them around at a later point
    for i in range(no_of_modules_x - 1):
        nodes[f"N_chip_media_x_{i}"] = Node(
            connection_no = 2, # bzw. 3
            multi_layer = True,
            coordinates = (
                module_position_x + i * (organ_module_size_x + module_spacing_x),
                module_position_y - node_offset_mix_1to1_y  - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in,
                z_layer_1
            )
        )
        nodes[f"N_mix_media_x_connect_{i}"] = Node(
            connection_no = 2, # bzw. 3
            multi_layer = False,
            coordinates = (
                # module_position_x + i * (organ_module_size_x + spacing_x) + cfg.channel_dim["spacer"],
                module_position_x + (i + 1) * (organ_module_size_x + module_spacing_x) - mixing_module_1to9_width - conc_x_channel_length, # TODO add a check above to make sure this is always valid
                module_position_y - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in,
                z_layer_2
            )
        )
        nodes[f"N_chip_media_feed_x_{i}"] = Node(
            connection_no = 2, # bzw. 3
            multi_layer = False,
            coordinates = (
                module_position_x + i * (organ_module_size_x + module_spacing_x),
                module_position_y - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in - inlet_distance,
                z_layer_1
            )
        )

    for j in range(no_of_modules_y - 1):
        nodes[f"N_chip_media_y_{j}"] = Node(
            connection_no = 2, # bzw. 3
            multi_layer = False,
            coordinates = (
                module_position_x - node_offset_mix_1to1_x - conc_x_channel_length - pump_connection_distance_in,
                module_position_y + j * (organ_module_size_y + module_spacing_y), 
                z_layer_1
            )
        )
        nodes[f"N_mix_media_y_connect_{j}"] = Node(
            connection_no = 2, # bzw. 3
            multi_layer = False,
            coordinates = ( # width and height of the mixing module 2 is switched because it is turned by 90°
                module_position_x - node_offset_mix_1to1_x - conc_x_channel_length - pump_connection_distance_in,
                # module_position_y + j * (organ_module_size_y + spacing_y) + cfg.channel_dim["spacer"], 
                module_position_y + (j + 1) * (organ_module_size_y + module_spacing_y) - node_offset_mix_1to1_y - mixing_module_1to9_width - conc_y_channel_length - distance_module_mixing, # TODO
                z_layer_1
            )
        )
        nodes[f"N_chip_media_feed_y_{j}"] = Node(
            connection_no = 2, # bzw. 3
            multi_layer = False,
            coordinates = (
                module_position_x - node_offset_mix_1to1_x - conc_x_channel_length - pump_connection_distance_in - inlet_distance,
                module_position_y + j * (organ_module_size_y + module_spacing_y), 
                z_layer_1
            )
        )

    # Define the inlet and outlet (pump) nodes
    nodes[f"N_chip_media_inflow"] = Node(
        connection_no = 1,
        multi_layer = False,
        coordinates = (
            module_position_x - node_offset_mix_1to1_x - conc_x_channel_length - pump_connection_distance_in - inlet_distance, # TODO I adapted this!! needs to be 2 for the y direction, or the other nodes need to be adapted
            module_position_y - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in - inlet_distance, 
            z_layer_1
        )
    )

    nodes[f"N_chip_conc_x_inflow"] = Node(
        connection_no = 1,
        multi_layer = False,
        coordinates = (
            module_position_x - node_offset_mix_1to1_x - conc_x_channel_length - pump_connection_distance_in + inlet_distance,
            module_position_y - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in,
            z_layer_2
        )
    )

    nodes[f"N_chip_conc_y_inflow"] = Node(
        connection_no = 1,
        multi_layer = False,
        coordinates = (
            module_position_x - node_offset_mix_1to1_x - conc_x_channel_length - pump_connection_distance_in,
            module_position_y - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in + inlet_distance,
            z_layer_1
        )
    )

    nodes[f"N_chip_media2_inflow"] = Node(
        connection_no = 1,
        multi_layer = False,
        coordinates = (
            module_position_x + (no_of_modules_x - 1) * (organ_module_size_x + module_spacing_x) + organ_module_size_x + spacing_x + pump_connection_distance_in, # TODO
            module_position_y - node_offset_mix_1to1_y - distance_module_mixing - conc_y_channel_length - pump_connection_distance_in - inlet_distance,
            z_layer_1
        )
    )

    nodes[f"N_{chr(65 + no_of_modules_x)}{no_of_modules_y}_out"] = Node( # last node is the outlet node
        connection_no = 1,
        multi_layer = False,
        coordinates = (
            module_position_x + (no_of_modules_x - 1) * (organ_module_size_x + module_spacing_x) + organ_module_size_x + spacing_x * 2 + pump_connection_distance_out, # TODO add here the module out length if that changes 
            module_position_y + (no_of_modules_y - 1) * (organ_module_size_y + module_spacing_y) + organ_module_size_y + spacing_y + spacing_out, # TODO add here the module out length if that changes and maybe the minimal pump_connection_distance
            z_layer_2
        ) 
    )

def initialize_channels(nodes, channels, cfg): 
    # For each connection between nodes, or channels, the flow rate and nodes are defined
    flow_rate_organ_module_top = cfg.organ_module["flow_rate"]
    flow_rate_organ_module_bottom = get_organ_module_flow_rate_bottom(cfg)
    fixed_resistance_organ_module_top = get_fixed_resistance_organ_module_top(cfg)
    fixed_resistance_organ_module_bottom = get_fixed_resistance_organ_module_bottom(cfg)
    
    layer_0 = cfg.layer_0
    layer_1 = cfg.layer_1
    layer_2 = cfg.layer_2

    no_of_modules_x = cfg.no_of_modules_x
    no_of_modules_y = cfg.no_of_modules_y

    mixing_channel_width = cfg.mixing_module["channel_width"]
    ratio_between_gradients= get_concentration_ratio(two_gradients=True, ratio=1)
    conc_dilution_x, conc_dilution_y = get_concentration_dilutions(cfg)

    mixing_module_fixed_resistance_1to1, mixing_module_fixed_resistance_1to9 = get_mixing_module_resistances(cfg)

    for i in range(no_of_modules_x):
        for j in range(no_of_modules_y):
            module = f"{chr(65 + i)}{j}"
            channels[f"channel_inflow_mix_{module}"] = Channel( # this channel is also the one where we need to make sure that the fluid is mixed
                nodes,
                flow_rate = flow_rate_organ_module_top,
                node1 = f"N_mix_{module}",
                node2 = f"N_inflow_{module}",
                width = mixing_channel_width,
                layer = layer_2,
                fixed_resistance = mixing_module_fixed_resistance_1to1
            )

            channels[f"organ_channel_inflow_{module}"] = Channel( # this channel is also the one where we need to make sure that the fluid is mixed
                nodes,
                flow_rate = flow_rate_organ_module_top,
                node1 = f"N_inflow_{module}",
                node2 = f"N_{module}_nw",
                layer = layer_2
            )

            channels[f"organ_channel_media2_inflow_{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_bottom,
                node1 = f"N_{module}_media2",
                node2 = f"N_{module}_ne",
                layer = layer_1
            )

            channels[f"organ_channel_top_{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_top,
                node1 = f"N_{module}_nw",
                node2 = f"N_{module}_se",
                width=1.5e-3,
                height=1e-3,
                layer = layer_0,
                fixed_resistance = fixed_resistance_organ_module_top
            )

            channels[f"organ_channel_bottom_{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_bottom,
                node1 = f"N_{module}_ne",
                node2 = f"N_{module}_sw",
                width=1.5e-3,
                height=1e-3,
                layer = layer_0,
                fixed_resistance = fixed_resistance_organ_module_bottom
            )

            channels[f"organ_channel_outflow_sw{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_bottom,
                node1 = f"N_{module}_sw",
                node2 = f"N_{module}_out_sw",
                layer = layer_2
            )

            channels[f"organ_channel_outflow_s{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_bottom,
                node1 = f"N_{module}_out_sw",
                node2 = f"N_{module}_out_se",
                layer = layer_2
            )

            channels[f"organ_channel_outflow_se{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_top,
                node1 = f"N_{module}_se",
                node2 = f"N_{module}_out_se",
                layer = layer_2
            )

            channels[f"organ_channel_outflow_{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_top + flow_rate_organ_module_bottom,
                node1 = f"N_{module}_out_se",
                node2 = f"N_{module}_out",
                layer = layer_2
            )

            channels[f"conc_x_{module}"] = Channel(
                nodes,
                flow_rate = ratio_between_gradients * channels[f"organ_channel_inflow_{module}"].flow_rate,
                node1 = f"N_{module}_conc_x",
                node2 = f"N_mix_{module}",
                layer = layer_2
            )

            channels[f"conc_y_{module}"] = Channel(
                nodes,
                flow_rate = ratio_between_gradients * channels[f"organ_channel_inflow_{module}"].flow_rate,
                node1 = f"N_{module}_conc_y",
                node2 = f"N_mix_{module}",
                layer = layer_1
            )

            if j == 0:
                flow_rate_outflow = channels[f"organ_channel_outflow_{module}"].flow_rate
            else:
                flow_rate_outflow = channels[f"organ_channel_outflow_{module}"].flow_rate + channels[f"outflow_{chr(65 + i)}{j - 1}"].flow_rate
            
            channels[f"outflow_{module}"] = Channel(
                nodes,
                flow_rate = flow_rate_outflow,
                node1 = f"N_{module}_out",
                node2 = f"N_{chr(65 + i)}{j + 1}_out",
                layer = layer_2
            )

        if i == 0:
            flow_rate_outflow = channels[f"outflow_{chr(65 + i)}{no_of_modules_y - 1}"].flow_rate
        else:
            flow_rate_outflow = channels[f"outflow_{chr(65 + i)}{no_of_modules_y - 1}"].flow_rate + channels[f"chip_outflow_{i - 1}"].flow_rate

        channels[f"chip_outflow_{i}"] = Channel(
            nodes,
            flow_rate = flow_rate_outflow,
            node1 = f"N_{chr(65 + i)}{no_of_modules_y}_out",
            node2 = f"N_{chr(65 + i + 1)}{no_of_modules_y}_out",
            layer = layer_2
        )

    # go reverse through all x modules then all y modules
    for j in range(no_of_modules_y - 1, -1, -1):
        module = f"{chr(65 + no_of_modules_x - 1)}{j}"
        if j == 0:
            channels[f"chip_media2_{j}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_bottom * no_of_modules_x * no_of_modules_y,
                node1 = f"N_chip_media2_inflow",
                node2 = f"N_{j}_media2",
                layer = layer_1
            )
        else:
            channels[f"chip_media2_{j}"] = Channel(
                nodes,
                flow_rate = flow_rate_organ_module_bottom * no_of_modules_x * no_of_modules_y - j * flow_rate_organ_module_bottom * no_of_modules_x,
                node1 = f"N_{j - 1}_media2",
                node2 = f"N_{j}_media2",
                layer = layer_1
            )

        channels[f"chip_media2_{module}"] = Channel(
            nodes,
            flow_rate = flow_rate_organ_module_bottom * no_of_modules_x,
            node1 = f"N_{j}_media2",
            node2 = f"N_{module}_media2",
            layer = layer_1
        )

        if no_of_modules_x == 1:
            node1_y_branch = f"N_{module}_y_branch"
        else:
            node1_y_branch = f"N_{chr(65 + no_of_modules_x - 2)}{j}_conc_y"
        
        channels[f"conc_y_branch_{module}"] = Channel(
            nodes,
            flow_rate = channels[f"conc_y_{module}"].flow_rate,
            node1 = node1_y_branch,
            node2 = f"N_{module}_conc_y",
            layer = layer_1
        )

        # for the rest of the rows (if there are any)
        for i in range(no_of_modules_x - 2, -1, -1):
            module = f"{chr(65 + i)}{j}"
            channels[f"chip_media2_{module}"] = Channel(
               nodes,
                flow_rate = flow_rate_organ_module_bottom * (i + 1), # TODO
                node1 = f"N_{chr(65 + i + 1)}{j}_media2",
                node2 = f"N_{module}_media2",
                layer = layer_1
            )

            if i == 0:
                node1_y_branch = f"N_{module}_y_branch"
            else:
                node1_y_branch = f"N_{chr(65 + i - 1)}{j}_conc_y"

            channels[f"conc_y_branch_{module}"] = Channel(
                nodes,
                flow_rate = channels[f"conc_y_{module}"].flow_rate + channels[f"conc_y_branch_{chr(65 + i + 1)}{j}"].flow_rate,
                node1 = node1_y_branch,
                node2 = f"N_{module}_conc_y",
                layer = layer_1
            )
        
    for i in range(no_of_modules_x - 1, -1, -1):
        # For the last column of modules
        module = f"{chr(65 + i)}{no_of_modules_y - 1}"

        if no_of_modules_y == 1: # first module y-direction
            node1_x_branch = f"N_{module}_x_branch"
        else:
            node1_x_branch = f"N_{chr(65 + i)}{no_of_modules_y - 2}_conc_x"

        channels[f"conc_x_branch_{module}"] = Channel(
            nodes,
            flow_rate = channels[f"conc_x_{module}"].flow_rate,
            node1 = node1_x_branch,
            node2 = f"N_{module}_conc_x",
            layer = layer_2
        )

        # for the rest of the columns (if there are any)
        for j in range(no_of_modules_y - 2, -1, -1):
            module = f"{chr(65 + i)}{j}"

            if j == 0: 
                node1_x_branch = f"N_{module}_x_branch"
            else:
                node1_x_branch = f"N_{chr(65 + i)}{j - 1}_conc_x"

            channels[f"conc_x_branch_{module}"] = Channel(
                nodes,
                flow_rate = channels[f"conc_x_{module}"].flow_rate + channels[f"conc_x_branch_{chr(65 + i)}{j + 1}"].flow_rate,
                node1 = node1_x_branch,
                node2 = f"N_{module}_conc_x",
                layer = layer_2
            )

    for i in range(no_of_modules_x - 1, -1, -1):
        if i != 0:
            if i == no_of_modules_x - 1: # last module x-direction
                flow_rate_conc_x_seg = channels[f"conc_x_branch_{chr(65 + i)}{0}"].flow_rate
                # flow_rate_media_feed = channels[f"media_x_{i - 1}"].flow_rate
            else:
                flow_rate_conc_x_seg = channels[f"conc_x_seg_{i * 2 + 1}"].flow_rate + channels[f"conc_x_branch_{chr(65 + i)}{0}"].flow_rate
                # flow_rate_media_feed = channels[f"media_x_{i - 1}"].flow_rate + channels[f"media_x_{i}"].flow_rate

            channels[f"conc_x_seg_{i * 2}"] = Channel(
                nodes,
                flow_rate = flow_rate_conc_x_seg,
                node1 = f"N_chip_media_x_{i - 1}",
                node2 = f"N_mix_media_x_connect_{i - 1}",
                layer = layer_2
            )

            channels[f"conc_x_seg_mix_{i * 2}"] = Channel(
                nodes,
                flow_rate = flow_rate_conc_x_seg,
                # node1 = f"N_mix_media_x_in_{i - 1}",
                node1 = f"N_mix_media_x_connect_{i - 1}",
                node2 = f"N_{chr(65 + i)}{0}_x_branch",
                width = mixing_channel_width,
                layer = layer_2,
                fixed_resistance = mixing_module_fixed_resistance_1to9
            )

            channels[f"conc_x_seg_{i * 2 - 1}"] = Channel(
                nodes,
                flow_rate = (cfg.concentration_dilution_x) * channels[f"conc_x_seg_{i * 2}"].flow_rate,
                node1 = f"N_{chr(65 + i - 1)}{0}_x_branch",
                node2 = f"N_chip_media_x_{i - 1}",
                layer = layer_2
            )
            
            channels[f"media_x_{i - 1}"] = Channel(
                nodes,
                flow_rate = (1 - cfg.concentration_dilution_x) * channels[f"conc_x_seg_{i * 2}"].flow_rate,
                node1 = f"N_chip_media_feed_x_{i - 1}",
                node2 = f"N_chip_media_x_{i - 1}",
                layer = layer_1
            )

            if i == no_of_modules_x - 1: # last module x-direction
                flow_rate_media_feed = channels[f"media_x_{i - 1}"].flow_rate
            else:
                flow_rate_media_feed = channels[f"media_x_{i - 1}"].flow_rate + channels[f"media_x_{i}"].flow_rate

            if i == 1:
                node1_media_inflow = f"N_chip_media_inflow"
            else:
                node1_media_inflow = f"N_chip_media_feed_x_{i - 2}"

            channels[f"media_feed_x_{i - 1}"] = Channel(
                nodes,
                flow_rate = flow_rate_media_feed,
                node1 = node1_media_inflow,
                node2 = f"N_chip_media_feed_x_{i - 1}",
                layer = layer_1
            )

        else: # first module x-direction
            if no_of_modules_x == 1:
                flow_rate_conc_x_seg = channels[f"conc_x_branch_{chr(65 + i)}{0}"].flow_rate
            else:
                flow_rate_conc_x_seg = channels[f"conc_x_seg_{i + 1}"].flow_rate + channels[f"conc_x_branch_{chr(65 + i)}{0}"].flow_rate
                       
            channels[f"conc_x_seg_{i}"] = Channel(
                nodes,
                flow_rate = flow_rate_conc_x_seg,
                node1 = f"N_chip_conc_x_inflow",
                node2 = f"N_{chr(65 + i)}{0}_x_branch",
                layer = layer_2
            )

    for j in range(no_of_modules_y - 1, -1, -1):
        if j != 0:
            if j == no_of_modules_y - 1: # last module x-direction
                flow_rate_conc_y_seg = channels[f"conc_y_branch_A{j}"].flow_rate
            else:
                flow_rate_conc_y_seg = channels[f"conc_y_seg_{j * 2 + 1}"].flow_rate + channels[f"conc_y_branch_A{j}"].flow_rate

            channels[f"conc_y_seg_{j * 2}"] = Channel(
                nodes,
                flow_rate = flow_rate_conc_y_seg,
                node1 = f"N_chip_media_y_{j - 1}",
                node2 = f"N_mix_media_y_connect_{j - 1}",
                layer = layer_1
            )

            channels[f"conc_y_seg_mix_{j * 2}"] = Channel(
                nodes,
                flow_rate = flow_rate_conc_y_seg,
                #     node1 = f"N_mix_media_y_in_{j - 1}",
                node1 = f"N_mix_media_y_connect_{j - 1}",
                node2 = f"N_A{j}_y_branch",
                width = mixing_channel_width,
                layer = layer_1,
                fixed_resistance = mixing_module_fixed_resistance_1to9
            )

            channels[f"conc_y_seg_{j * 2 - 1}"] = Channel(
                nodes,
                flow_rate = (cfg.concentration_dilution_y) * channels[f"conc_y_seg_{j * 2}"].flow_rate,
                node1 = f"N_A{j - 1}_y_branch",
                node2 = f"N_chip_media_y_{j - 1}",
                layer = layer_1
            )

            channels[f"media_y_{j - 1}"] = Channel(
                nodes,
                flow_rate = (1 - cfg.concentration_dilution_y) * channels[f"conc_y_seg_{j * 2}"].flow_rate,
                node1 = f"N_chip_media_feed_y_{j - 1}",
                node2 = f"N_chip_media_y_{j - 1}",
                layer = layer_1
            )

            if j == 1:
                node1_media_inflow = f"N_chip_media_inflow"
            else:
                node1_media_inflow = f"N_chip_media_feed_y_{j - 2}"

            if j == no_of_modules_y - 1: # last module x-direction
                flow_rate_media_feed = channels[f"media_y_{j - 1}"].flow_rate
            else:
                flow_rate_media_feed = channels[f"media_y_{j - 1}"].flow_rate + channels[f"media_y_{j}"].flow_rate

            channels[f"media_feed_y_{j - 1}"] = Channel(
                nodes,
                flow_rate = flow_rate_media_feed,
                node1 = node1_media_inflow,
                node2 = f"N_chip_media_feed_y_{j - 1}",
                layer = layer_1
            )

        else: # first module y-direction
            if no_of_modules_y == 1:
                flow_rate = channels[f"conc_y_branch_A{j}"].flow_rate
            else:
                flow_rate = channels[f"conc_y_seg_{j + 1}"].flow_rate + channels[f"conc_y_branch_A{j}"].flow_rate

            channels[f"conc_y_seg_{j}"] = Channel(
                nodes,
                flow_rate = flow_rate,
                node1 = f"N_chip_conc_y_inflow",
                node2 = f"N_A{j}_y_branch",
                layer = layer_1
            )

def define_module_dependent_exclusion_zones(exclusion_zones, nodes, spacing_x, spacing_y, spacing_out, cfg):
    # TODO define the module position elsewhere and import (double definition in initialize_nodes)

    # module_position_x = 0.0 + cfg.chip_layout["spacing_side"] + cfg.pump_connection_distance_in + cfg.inlet_distance + spacing_x + cfg.mixing_module["1to1"]["node_offset_x"]
    # module_position_y = 0.0 + cfg.chip_layout["spacing_side"] + cfg.pump_connection_distance_in + cfg.inlet_distance + spacing_y + cfg.mixing_module["1to1"]["node_offset_y"] + cfg.distance_module_mixing

    # module_spacing_x = spacing_x + cfg.mixing_module["1to1"]["node_offset_x"] + spacing_x + spacing_out
    # module_spacing_y = spacing_y + cfg.mixing_module["1to1"]["node_offset_y"] + spacing_y + spacing_out + cfg.distance_module_mixing

    x_offset = cfg.module_exclusion_zone_offset_x
    y_offset = cfg.module_exclusion_zone_offset_y

    width = cfg.module_exclusion_zone_width
    length = cfg.module_exclusion_zone_length

    for i in range(cfg.no_of_modules_x):
        for j in range(cfg.no_of_modules_y):
            module = f"{chr(65 + i)}{j}"

            # Module corners (already generated) and updated with each spacing iteration
            nw = nodes[f"N_{module}_nw"].coordinates
            ne = nodes[f"N_{module}_ne"].coordinates
            sw = nodes[f"N_{module}_sw"].coordinates

            # Compute module center
            center_x = (nw[0] + ne[0]) / 2
            center_y = (nw[1] + sw[1]) / 2
            center_z = nw[2]

            # TODO this is specific to the current organ module holders
                        # ------- LEFT SIDE (2 zones) -------
            positions_left = [
                (center_x - x_offset, center_y - y_offset),
                (center_x - x_offset, center_y + y_offset),
            ]

            for idx, (px, py) in enumerate(positions_left, start=1):
                exclusion_zones[f"excl_{module}_left_{idx}"] = ExclusionZone(
                    name=f"excl_{module}_left_{idx}",
                    position=(px, py, center_z),
                    x_width=width,
                    y_length=length,
                )

            # ------- RIGHT SIDE (1 zone) -------
            px = center_x + x_offset
            py = center_y  # centered vertically

            exclusion_zones[f"excl_{module}_right"] = ExclusionZone(
                name=f"excl_{module}_right",
                position=(px, py, center_z),
                x_width=width,
                y_length=length,
            )

def initialize_exclusion_zones(exclusion_zones, nodes, spacing_x, spacing_y, spacing_out, cfg):
    for zone in cfg.exclusion_zone_input:
        position = zone["position"]
        x_width = zone["x_width"]
        y_length = zone["y_length"]
        exclusion_zones[zone["name"]] = ExclusionZone(position, x_width, y_length)

        name = zone.get("name", f"zone_{len(exclusion_zones)}")

    define_module_dependent_exclusion_zones(exclusion_zones, nodes, spacing_x, spacing_y, spacing_out, cfg)
