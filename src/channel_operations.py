import math

from utils import calculate_hydraulic_resistance, calculate_hydraulic_resistance_cylinder, bisect_root

eps = 1e-9

def calculate_via_resistance(channel, nodes, viscosity, channel_dim):
    if channel.fixed_resistance is not None:
        return 0.0
    if nodes[channel.node1].multi_layer:
        return calculate_hydraulic_resistance_cylinder(
            channel_dim["layer_switch_distance"],
            channel_dim["via_diameter"] / 2,
            viscosity
        )
    return 0.0

def get_layer_switch_resistance_correction(channel, nodes, channel_dim, viscosity):
    """
    Add the required theoretical length that would be needed to account for the layer switch resistance in the channel length.
    """
    resistance = 0.0
    extra_length = 0.0

    coord1 = nodes[channel.node1].coordinates
    coord2 = nodes[channel.node2].coordinates
    # if coord1[2] == 0.0 or coord2[2] == 0.0:
    #     layer_switch_resistance_plate = calculate_hydraulic_resistance_cylinder(channel_dim["layer_switch_distance"], channel_dim["via_diameter"] / 2, viscosity)
    #     resistance += layer_switch_resistance_plate
    if nodes[channel.node1].multi_layer:
        layer_switch_resistance_plate = calculate_hydraulic_resistance_cylinder(channel_dim["layer_switch_distance"], channel_dim["via_diameter"] / 2, viscosity)
        resistance += layer_switch_resistance_plate

    return resistance

    # if resistance > 0.0:
    #     extra_length = resistance / calculate_hydraulic_resistance(channel.width, channel.height, 1.0, viscosity)

    #     # print(f"extra length for layer switch in channel between nodes {channel.node1} to {channel.node2}: {extra_length:.6g} m")
    # return extra_length


def calculate_minimal_length(channel, nodes, channel_dim):
    '''
    Compute Euclidean distance between the start and end nodes of the channel.
    '''
    node1_coords = nodes[channel.node1].coordinates
    node2_coords = nodes[channel.node2].coordinates

    if not channel.rerouted:
        euclidean_distance = math.sqrt(
            (node1_coords[0] - node2_coords[0])**2 +
            (node1_coords[1] - node2_coords[1])**2
        )
        total_length = euclidean_distance
    else:
        total_length = 0.0
        for i in range(1, len(channel.rerouted_path)):
            x1, y1, *_ = channel.rerouted_path[i - 1]
            x2, y2, *_ = channel.rerouted_path[i]
            segment_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            total_length += segment_length

    return total_length


def update_length(channel, nodes, viscosity, channel_dim):
    '''
    Updates the channel length based on node pressures.
    '''
    P1 = nodes[channel.node1].pressure
    P2 = nodes[channel.node2].pressure
    P_drop = abs(P1 - P2)  # Pressure drop across channel

    if P_drop < eps:  # Avoid division by zero
        channel.length = calculate_minimal_length(channel, nodes, channel_dim) # TODO
        # print("Pressure drop is zero, using minimal length", P_drop, "Channel nodes:", channel.node1, channel.node2)
        return channel.length

    # Solve for required length
    # channel.length = (P_drop * channel.width * channel.height**3 * (1 - 0.63 * channel.height / channel.width)) / (12 * viscosity * channel.flow_rate)
    w = channel.width
    h = channel.height
    if h > w: # switch h and w to make sure the constraints for the channel resistance calculation applies
        h, w = w, h

    resistance = P_drop / channel.flow_rate
    via_resistance = get_layer_switch_resistance_correction(channel, nodes, channel_dim, viscosity)
    resistance -= via_resistance
    if resistance < eps:
        channel.length = calculate_minimal_length(channel, nodes, channel_dim) # TODO
        # print("Resistance after via correction is zero, using minimal length", resistance, "Channel nodes:", channel.node1, channel.node2)
        return channel.length
    a = (1 - (192 * h / (math.pi**5 * w) * math.tanh(math.pi * w / (2 * h))))
    channel.length = a * resistance * w * h**3 / (12 * viscosity)

    return channel.length

def calculate_pressure_drop(channel, nodes, viscosity):
    resistance = channel.calculate_hydraulic_resistance(nodes, viscosity)
    # resistance += calculate_via_resistance(channel, nodes, viscosity, channel_dim)
    return resistance * channel.flow_rate

def get_longest_segment(channel, nodes, channel_dim):
    path_int_start = 0
    path_int_end = 0
    if channel.rerouted:
        # find the longest straight segment and use it as a basis for adding the meanders 
        max_segment_length = 0.0
        longest_segment = None
        for i in range(1, len(channel.rerouted_path)):
            x1, y1, _ = channel.rerouted_path[i - 1]
            x2, y2, _ = channel.rerouted_path[i]
            segment_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            path_int_start = i-1
            path_int_end = i
            if segment_length > max_segment_length:
                max_segment_length = segment_length
                longest_segment = (channel.rerouted_path[i - 1], channel.rerouted_path[i])
                path_int_start = i-1
                path_int_end = i
        coord_start, coord_end = longest_segment
         
        # vertical = abs(coord_start[0] - coord_end[0]) < abs(coord_start[1] - coord_end[1])
        if channel.vertical:
            # sort by y
            if coord_start[1] > coord_end[1]:
                coord_start, coord_end = coord_end, coord_start
                path_int_start, path_int_end = path_int_end, path_int_start
        else:
            # sort by x
            if coord_start[0] > coord_end[0]:
                coord_start, coord_end = coord_end, coord_start
                path_int_start, path_int_end = path_int_end, path_int_start
    else: 
        coord_start = nodes[channel.node1].coordinates
        coord_end = nodes[channel.node2].coordinates
        longest_segment = calculate_minimal_length(channel, nodes, channel_dim)
    
    return longest_segment, coord_start, coord_end, path_int_start, path_int_end

def adapt_width(channel, minimal_length, channel_dim, viscosity):
    '''
    Check if the width alongside the length can be reduced (byproduct of the iterative MNA approach). If so, set the channel length to 
    the minimal length, otherwise increse the length to accomondate for at least one meander and adjust the width 
    (and potentially the height) accordingly.
    '''
    # resistance_target = channel.calculate_hydraulic_resistance(nodes, viscosity)
    resistance_target = calculate_hydraulic_resistance(channel.width, channel.height, channel.length, viscosity) # This way the layer switch resistance is not influencing the result 

    w_min = channel_dim["width"]
    w_max = channel_dim["max_width"]

    # First try to adapt the width so the length doesn't need to be elongated
    if channel.width > channel_dim["width"]: # maybe remove this check?
        def f_w_at_min_length(w):
            return calculate_hydraulic_resistance(w, channel.height, minimal_length, viscosity) - resistance_target
        
        f_at_w_min = f_w_at_min_length(w_min)
        f_at_w_max = f_w_at_min_length(w_max)

        if f_at_w_min * f_at_w_max < 0:
            new_width = bisect_root(f_w_at_min_length, w_min, w_max)
            channel.width = new_width
            channel.length = minimal_length
            return
    
    else:
        # # print("TODO this is an edge case")
        new_length = channel.length + 2 * channel.width
        def f_w_at_new_length(w):
            return calculate_hydraulic_resistance(w, channel.height, new_length, viscosity) - resistance_target
        
        f_at_w_min = f_w_at_new_length(w_min)
        f_at_w_max = f_w_at_new_length(w_max)

        # TODO add a while statement here to keep elongating the length
        if f_at_w_min * f_at_w_max < 0:
            new_width = bisect_root(f_w_at_new_length, w_min, w_max)
            channel.width = new_width
            channel.length = new_length
            return

        raise ValueError(f"The adapt width function needs to be extended to account for this case.")
        # Increase the channel length
        channel.length += channel.width * 2
        limit_width(channel, channel_dim, viscosity)
        
def limit_width(channel, channel_dim, viscosity):
    """
    Limit the width of the channels to a maximum value, in case it surpasses that value, increase the height of the channel.
    """
    # In this case h << w, we can use the simplified version of the hydraulic resistance calculation (based on Oh 2012)
    # resistance_target = channel.calculate_hydraulic_resistance(nodes, viscosity)
    resistance_target = calculate_hydraulic_resistance(channel.width, channel.height, channel.length, viscosity) # This way the layer switch resistance is not influencing the result 

    # This is a simplification. Since we fix it using the width it is fine, if we use stepwise height
    required_height = math.pow(12 * viscosity * channel.length / (channel_dim["max_width"] * resistance_target), (1/3)) 

    if required_height > channel_dim["max_height"]:
        raise ValueError(f"Channel exceeds the maximum height limit after width adjustment!")
    
    step_height = channel_dim["height"] / 5 # TODO this could be a parameter 
    lower_height_step = math.ceil((required_height - channel_dim["height"]) / step_height)

    new_height = channel_dim["height"] + lower_height_step * step_height

    while new_height < channel_dim["max_height"]:
        # f = lambda width: 
        f_at_Wmax = calculate_hydraulic_resistance(channel_dim["max_width"], new_height, channel.length, viscosity) - resistance_target
        if f_at_Wmax > 0:
            new_height += step_height
            continue

        f_w = lambda width: calculate_hydraulic_resistance(width, new_height, channel.length, viscosity) - resistance_target
        new_width = bisect_root(f_w, 1e-15, channel_dim["max_width"])

        channel.width = new_width
        channel.height = new_height
        return
    
def sort_channels_by_required_length_increase(channels: dict, nodes: dict, channel_dim: dict):
    """
    Returns a list of (channel_name, channel_obj, percent_increase) tuples,
    sorted by percent_increase descending.

    percent_increase = (ch.length - minimal_length) / minimal_length * 100

    This sorting is performed to make sure the meanders fit better on the board at a later point.
    """
    entries = []
    for name, channel in channels.items():
        minimal = calculate_minimal_length(channel, nodes, channel_dim)
        if channel.length is None:
            raise ValueError(f"Channel '{name}' has no length set. Call update_length() first.")
        pct = (channel.length - minimal) / minimal * 100
        entries.append((name, channel, pct))

    entries.sort(key=lambda x: x[2], reverse=True)
    return entries

def check_connection_no_per_node(nodes, channels, node1, node2, channel):
    """
    Checks how many channels are connected to a node, if it is only 2 there is a direct connection and technically they can be seen as one channel.
    """
    other_channel = None

    if nodes[node1].connection_no == 2:
        other_channel = get_other_connected_channel(channels, node1, channel)
    elif nodes[node2].connection_no == 2:
        other_channel = get_other_connected_channel(channels, node2, channel)
    else:
        return False
    
    # if other_channel is None:
    #     return False  # No other channel found

    if other_channel.fixed_resistance is None:
        return other_channel
    else:
        if nodes[node2].connection_no == 2:
            other_channel = get_other_connected_channel(channels, node2, channel)
            if other_channel != None and other_channel.fixed_resistance is None:
                return other_channel
        return False
    
def get_other_connected_channel(channels, node, current_channel):
    """
    Given a node_id and one of its connected channels, return the other channel object.
    For now this only applies to nodes that have max. 2 connections.
    """
    connected_channels = []
    for channel in channels.values():
        if channel.node1 == node or channel.node2 == node:
            connected_channels.append(channel)
    
    if len(connected_channels) == 2:
        for channel in connected_channels:
            if channel != current_channel:
                return channel
    return None

def assign_initial_lengths(nodes: dict, channels: dict, channel_dim: dict):
    # Ensure all channels have the correct length after nodes are initialized and required rerouting is done
    for channel_name, channel_obj in channels.items():
        channel_obj.length = calculate_minimal_length(channel_obj, nodes, channel_dim)

        if channel_obj.length is None:
            raise ValueError(f"Channel {channel_name} has an invalid length!")
