import math

eps = 1e-12

from .utils import calculate_hydraulic_resistance
from .mf_geometry_components import BoundingBox
from .channel_operations import calculate_minimal_length, check_connection_no_per_node, get_longest_segment

def initialize_bounding_boxes(nodes, channels, exclusion_zones, mixing_module, chip_layout):
    bounding_boxes = []

    bounding_boxes.extend(bounding_box_from_exclusion_zones(exclusion_zones))

    for channel in channels.values():
        if channel.fixed_resistance is not None:
            # Skip channels with fixed resistance
            continue
        # if channel.rerouted:
        #     continue  # Rerouted channels have their own bounding boxes
        bounding_boxes.append(bounding_box_from_channel(nodes, channel))
    
    bounding_boxes.extend(bounding_box_from_mixing_module(channels, nodes, mixing_module))

    bounding_boxes.extend(bounding_box_from_chip_layout(nodes, chip_layout))

    return bounding_boxes
    
def bounding_box_from_channel(nodes, channel):
    coord1 = nodes[channel.node1].coordinates
    coord2 = nodes[channel.node2].coordinates
    x1, y1, z1 = coord1
    x2, y2, z2 = coord2

    if channel.vertical:  # vertical channel
        # rectangle expands in x, runs in y
        min_x = min(x1, x2) - channel.width/2
        max_x = max(x1, x2) + channel.width/2
        min_y = min(y1, y2)
        max_y = max(y1, y2)
    else:  # horizontal
        min_y = min(y1, y2) - channel.width/2
        max_y = max(y1, y2) + channel.width/2
        min_x = min(x1, x2)
        max_x = max(x1, x2)

    node_1 = (min_x, min_y, z1)
    node_2 = (max_x, min_y, z1)
    node_3 = (max_x, max_y, z1)
    node_4 = (min_x, max_y, z1)

    return BoundingBox(node_1, node_2, node_3, node_4, channel.layer, source=channel)

def bounding_box_from_meander(meander_nodes, coord_start, channel):
    # Compute rectangle bounding box from all meander nodes

    width = channel.width
    xs = [p[0] for p in meander_nodes]
    ys = [p[1] for p in meander_nodes]

    min_x = min(xs) - width/2
    max_x = max(xs) + width/2
    min_y = min(ys) - width/2
    max_y = max(ys) + width/2

    bounding_box_node_1 = (min_x, min_y, coord_start[2])
    bounding_box_node_2 = (max_x, min_y, coord_start[2])
    bounding_box_node_3 = (max_x, max_y, coord_start[2])
    bounding_box_node_4 = (min_x, max_y, coord_start[2])

    bounding_box = BoundingBox(
        bounding_box_node_1,
        bounding_box_node_2,
        bounding_box_node_3,
        bounding_box_node_4,
        channel.layer,
        multi_layer=False,
        source="channel_meander"
    )
    return bounding_box

# def bounding_box_from_in_and_outlets(nodes, channel):
#     # TODO

# def bounding_box_from_modules(nodes, channel):
#     # TODO maybe use the organ module nodes for this

def bounding_box_from_exclusion_zones(exclusion_zones):
#    # This defines a bounding box for exclusion zones during meander design, in case it overlaps with the intialy channels this is already done previously
    bounding_boxes = []
    for zone in exclusion_zones.values():
        node1 = (zone.get_x_min(), zone.get_y_min(), 0.0)
        node2 = (zone.get_x_min(), zone.get_y_max(), 0.0)
        node3 = (zone.get_x_max(), zone.get_y_min(), 0.0)
        node4 = (zone.get_x_max(), zone.get_y_max(), 0.0)
        # TODO define the layer and multi_layer from the exclusion zone 
        bounding_box_exclusion = BoundingBox(node1, node2, node3, node4, layer=0, multi_layer=True, source="exclusion_zone")
        bounding_boxes.append(bounding_box_exclusion)

    return bounding_boxes

def bounding_box_from_mixing_module(channels, nodes, mixing_module):
    bounding_boxes = []
    for channel_name, channel in channels.items():
        coord1 = nodes[channel.node1].coordinates
        coord2 = nodes[channel.node2].coordinates
        x1, y1, z1 = coord1
        x2, y2, z2 = coord2
        if "inflow_mix" in channel_name: # 1:1 mixing
            node1 = (x1 , y1 - 0.5 * channel.width, z1)
            node2 = (x1 + mixing_module["1to1"]["width"], y1 - 0.5 * channel.width, z1)
            node3 = (x2 , y2 + 0.5 * channel.width, z2)
            node4 = (x2 + mixing_module["1to1"]["width"], y2 + 0.5 * channel.width, z2)
            bounding_box_mixing = BoundingBox(node1, node2, node3, node4, layer=channel.layer, multi_layer=False, source="mixer_module")
            bounding_boxes.append(bounding_box_mixing)

        elif "seg_mix" in channel_name: # 1:9 mixing  
            if "x_seg" in channel_name: # TODO this is not very elegant
                node1 = (x1 + eps, y1 - 0.5 * channel.width, z1)
                node2 = (x1 + mixing_module["1to9"]["width"], y1 - 0.5 * channel.width, z1)
                node3 = (x2 - mixing_module["1to9"]["width"] + eps, y2 + 0.5 * channel.width, z2)
                node4 = (x2, y2 + 0.5 * channel.width, z2)
            else:
                node1 = (x1 - 0.5 * channel.width, y1 + eps, z1)
                node2 = (x1 - 0.5 * channel.width, y1 + mixing_module["1to9"]["width"], z1)
                node3 = (x2 + 0.5 * channel.width, y2 - mixing_module["1to9"]["width"] + eps, z2)
                node4 = (x2  + 0.5 * channel.width, y2 + eps, z2)
            bounding_box_mixing = BoundingBox(node1, node2, node3, node4, layer=channel.layer, multi_layer=False, source="mixer_module")
            bounding_boxes.append(bounding_box_mixing)

    return bounding_boxes

def bounding_box_from_chip_layout(nodes, chip_layout):
    '''
    Defines the bounding boxes, i.e., the constraints at the chip sides, for the chip layout.
    This only works if the channel network fits within the limits of the chip layout, e.g., a standard well plate.
    '''
    size_x = chip_layout["size_x"]
    size_y = chip_layout["size_y"]
    spacing_side = chip_layout["spacing_side"]
    extra_spacing = 0.7e-3/2 # Account for channel width and via size TODO update this
    bounding_boxes = []

    # Check if the nodes are within the chip layout
    for node_name, node in nodes.items():
        if not (((0 + spacing_side - extra_spacing) < node.coordinates[0] < (size_x - spacing_side + extra_spacing)) and ((0 + spacing_side - extra_spacing) < node.coordinates[1] < size_y - spacing_side + extra_spacing)):
            print(f"Node {node_name} is outside the chip layout boundaries.")
            # TODO maybe raise an error here or adapt the chip layout

    bounding_box_bottom = BoundingBox(
        (0, 0, 0), 
        (0, spacing_side, 0), 
        (size_x, 0, 0), 
        (size_x, spacing_side, 0), 
        layer=0, multi_layer=True, source="chip_layout" # TODO 
    )
    bounding_box_left = BoundingBox(
        (0, 0, 0), 
        (spacing_side, 0, 0), 
        (0, size_y, 0), 
        (spacing_side, size_y, 0), 
        layer=0, multi_layer=True, source="chip_layout" # TODO
    )
    bounding_box_right = BoundingBox(
        (size_x - spacing_side, 0, 0), 
        (size_x, 0, 0), 
        (size_x - spacing_side, size_y, 0), 
        (size_x, size_y, 0), 
        layer=0, multi_layer=True, source="chip_layout" # TODO
    )
    bounding_box_top = BoundingBox(
        (0, size_y - spacing_side, 0), 
        (0, size_y, 0), 
        (size_x, size_y - spacing_side, 0), 
        (size_x, size_y, 0), 
        layer=0, multi_layer=True, source="chip_layout" # TODO
    )
    bounding_boxes.extend([bounding_box_bottom, bounding_box_left, bounding_box_right, bounding_box_top])

    return bounding_boxes

def get_meander_length(nodes, channel, start, end, bounding_boxes, min_channel_distance, vertical): # this will replace get_max_meander_length (go into get_max_meander_length? after the vertical check?)
    """
    Define the length that would fit on the board for each meander. I.e, the maximum distance going right or left, or up or down respectively.
    """
    minimal_meander_lenth = 2 * channel.width

    coord1 = start
    coord2 = end

    x1, y1, _ = coord1
    x2, y2, _ = coord2

    channel_layer = channel.layer
    x_min, x_max = sorted([x1, x2])
    y_min, y_max = sorted([y1, y2])


    available_distance = float("inf")
    available_distance_left = float("inf")

    for box in bounding_boxes:
        # Skip box if it's based on the current channel
        if isinstance(box.source, type(channel)) and box.source == channel:
            continue
        if not box.multi_layer and box.layer != channel_layer: # Check if the box will block the channel in the same/channel layer
            continue
        
        x_min_box = box.get_x_min()
        x_max_box = box.get_x_max()
        y_min_box = box.get_y_min()
        y_max_box = box.get_y_max()
        if vertical:
            # Meanders go left/right → limit in X
            if y_max_box >= y_min and y_min_box <= y_min or y_max_box >= y_max and y_min_box <= y_max or y_max_box <= y_max and y_min_box >= y_min:   
                if x_min_box > x1: # only blocks to the right are considered
                    available_distance = min(available_distance, x_min_box - x1)
                if x_max_box < x1:
                    available_distance_left = min(available_distance_left, x1 - x_max_box)
        else:
            # Meanders go up/down → limit in Y
            if x_max_box >= x_min and x_min_box <= x_min or x_max_box >= x_max and x_min_box <= x_max or x_max_box <= x_max and x_min_box >= x_min:
                if y_min_box > y1:
                    available_distance = min(available_distance, y_min_box - y1)
                if y_max_box < y1:
                    available_distance_left = min(available_distance_left, y1 - y_max_box)

    # this is defined as a fallback, the distance to the sides will be defined via bounding boxes
    if available_distance == float("inf"):
        available_distance = 0.5e-3 
    if available_distance_left == float("inf"):
        available_distance_left = 0.5e-3

    if available_distance_left <= minimal_meander_lenth:
        available_distance_left = 0.0
    if available_distance <= minimal_meander_lenth:
        available_distance = 0.0

    return available_distance, available_distance_left


def get_distance_to_next_channel(minimal_channel_distance, channel, max_channel_width): 
    distance = minimal_channel_distance + 0.5 * channel.width + 0.5 * max_channel_width # the channel with of the other channel is considered in the bounding box

    return distance

def get_nodes_for_meander(channel, coord_start, coord_end, meander_length_one_way, minimal_channel_distance, no_of_meanders, distance_node_1, vertical, space_for_meandering, reverse): # TODO
    '''Defines a list of coordinates that define the meanders for each channel.'''

    width = channel.width
    if reverse:
        factor = -1
    else:
        factor = 1

    if vertical:
        direction = (0, 1)
        # take the upper node
        prev_coord = coord_start if coord_start[1] < coord_end[1] else coord_end
    else:
        # take the left node
        direction = (1, 0)
        prev_coord = coord_start if coord_start[0] < coord_end[0] else coord_end

    # distance_node_1 is the distance required between the channel start and the first meander
    meander_distance = distance_node_1
    
    # This centers the meanders in the middle of the available space, stylistic choice that helps with fitting more meanders, could easily be adapted.
    meander_distance = max(distance_node_1, distance_node_1 + (space_for_meandering - no_of_meanders * (channel.width + minimal_channel_distance) * 2) / 2)

    meander_width = channel.width + minimal_channel_distance
    meander_nodes = []

    for meander in range(no_of_meanders):
        # | 
        # 1------2
        #        |  
        # 4------3  
        # |
        coord1 = prev_coord

        meander_node_1 = (coord1[0] + direction[0] * meander_distance, 
                          coord1[1] + direction[1] * meander_distance, 
                          coord1[2])
        meander_node_2 = (coord1[0] + direction[0] * meander_distance + direction[1] * meander_length_one_way * factor, 
                          coord1[1] + direction[1] * meander_distance + direction[0] * meander_length_one_way * factor, 
                          coord1[2])
        meander_node_3 = (coord1[0] + direction[0] * (meander_distance + meander_width) + direction[1] * meander_length_one_way * factor, 
                          coord1[1] + direction[1] * (meander_distance + meander_width) + direction[0] * meander_length_one_way * factor, 
                          coord1[2])
        meander_node_4 = (coord1[0] + direction[0] * (meander_distance + meander_width), 
                          coord1[1] + direction[1] * (meander_distance + meander_width), 
                          coord1[2])
        
        prev_coord = meander_node_4
        meander_distance = meander_width
        
        meander_nodes.extend([meander_node_1, meander_node_2, meander_node_3, meander_node_4])
        
    bounding_box = bounding_box_from_meander(meander_nodes, coord_start, channel) # TODO double check this

    return meander_nodes, bounding_box

def define_meander(channel, nodes, channel_dim, bounding_boxes):
    '''
    Main function of adding meanders to a channel. Gets called for each channel separately and calculates the available number and length of meanders.
    '''
    meander_nodes = []
    required_spacing_increase = 0.0

    vertical = channel.vertical

    min_channel_distance = channel_dim["min_distance"]
    max_channel_width = channel_dim["max_width"]
    # layer_distance = channel_dim["layer_switch_distance"] + channel.height
    # module_layer_distance = channel_dim["layer_switch_distance"] + channel.height / 2 #channel_dim["layer_switch_distance_organ"]

    # GET THE REQUIRED EXTRA CHANNEL LENGTH
    minimal_channel_length = calculate_minimal_length(channel, nodes, channel_dim)
    required_channel_length = channel.length

    required_extra_length = required_channel_length - minimal_channel_length

    if required_extra_length > 0.0 + eps:
        longest_segment_length, coord_start, coord_end, path_int_start, path_int_end = get_longest_segment(channel, nodes, channel_dim)

        # GET THE LENGTH OF EACH MEANDER 
        reverse = False
        available_distance, available_distance_reverse = get_meander_length(nodes, channel, coord_start, coord_end, bounding_boxes, min_channel_distance, vertical)
        if available_distance_reverse > available_distance:
            available_distance = available_distance_reverse
            reverse = True
        # considers the channel width of the current channel, since the widths of all channels are considered in the bounding boxes
        available_distance -= (channel.width / 2) 

        # GET THE NUMBER OF REQUIRED MEANDERS - incl. rounded corners
        radius = channel.width / 2 # of the center line in the 1D network
        required_no_of_meanders = math.ceil(0.5 * required_extra_length / (available_distance - (4 - math.pi) * radius)) # (4 - math.pi) * radius: impact of the rounded corners

        # CHECK IF THE AMOUNT OF MEANDERS WOULD FIT
        # 1. calculate the available space for the meanders 
        # add the z coordinate for channels that switch layers
        layer_distance_start = 0.0 
        layer_distance_end = 0.0
        if channel.rerouted:
            node_distance = abs(math.sqrt((coord_end[0] - coord_start[0])**2 + (coord_end[1] - coord_start[1])**2))        
        else:
            node_distance = minimal_channel_length

        # coord_node1 = nodes[channel.node1].coordinates
        # coord_node2 = nodes[channel.node2].coordinates

        # if coord_node1 == coord_start or coord_node1 == coord_end:
        #     if coord_node1[2] == 0.0:  # bottom layer case
        #         layer_distance_start += module_layer_distance
        #     elif nodes[channel.node1].multi_layer:
        #         layer_distance_start += layer_distance

        # if coord_node2 == coord_start or coord_node2 == coord_end:
        #     if coord_node2[2] == 0.0:
        #         layer_distance_end += module_layer_distance
        

            # add distance to the sides of the channel to prevent overlapping once the channels are extruded
            # distance_to_channel_start = max_channel_width * 0.5 + channel.width * 0.5 + layer_distance_start + min_channel_distance # TODO the max channel width could be exchanged by employing the width that is stored via the bounding boxes - not yet 
            # distance_to_channel_end   = max_channel_width * 0.5 + channel.width * 0.5 + layer_distance_end + min_channel_distance + min_channel_distance
        distance_to_channel_start = max_channel_width * 0.5 + layer_distance_start + min_channel_distance # TODO the max channel width could be exchanged by employing the width that is stored via the bounding boxes - not yet 
        distance_to_channel_end   = max_channel_width * 0.5 + layer_distance_end + min_channel_distance

        space_for_meandering = max(0.0, node_distance - distance_to_channel_start - distance_to_channel_end)

        meander_height = (channel.width + min_channel_distance) * 2

        # Check how many (if any) meanders can fit into the available space, because the last meander needs no extra min channel distance it is added to the available space
        required_space_for_meandering = required_no_of_meanders * meander_height
        required_spacing_increase = required_space_for_meandering - (space_for_meandering + min_channel_distance)
        if required_spacing_increase > eps: 
            # THE REQUIRED EXTRA LENGTH WILL NOT FIT
            required_spacing_increase = required_no_of_meanders * meander_height - (space_for_meandering + min_channel_distance)
            if required_spacing_increase > eps:
                print(f"The required number of meanders does not fit into the available space.", channel.node1, channel.node2, "required spacing increase:", required_spacing_increase)
        else:
            # meander_length = required_extra_length / required_no_of_meanders
            meander_length_one_way = required_extra_length * 0.5 / required_no_of_meanders
            meander_nodes, bounding_box = get_nodes_for_meander(channel, coord_start, coord_end, meander_length_one_way, min_channel_distance, required_no_of_meanders, distance_to_channel_start, vertical, space_for_meandering, reverse)
            
            bounding_boxes.append(bounding_box)

    return meander_nodes, required_spacing_increase, required_extra_length # TODO pass only what would need to be added (i.e. the meanders are split across both channels)

def assign_extra_length_to_connected_channel(nodes, channels, node1, node2, channel, required_spacing_increase, extra_length, bounding_boxes, viscosity, channel_dim): # WIP
    """
    Add extra meanders to connected channels.
    """
    alternative_channel = check_connection_no_per_node(nodes, channels, node1, node2, channel)
    if alternative_channel != False:
        if math.isclose(channel.width, alternative_channel.width, rel_tol=1e-9) and math.isclose(channel.height, alternative_channel.height, rel_tol=1e-9):
            alternative_channel.length += extra_length
            # alternative_channel.meander_nodes, required_spacing_increase, _ = define_meander(alternative_channel, channels, nodes, cfg.channel_dim, bounding_boxes, alternative_channel.vertical)
        else:
            required_extra_resistance = calculate_hydraulic_resistance(channel.width, channel.height, extra_length, viscosity)
            # calculate the length based on the alternative channel geometry
            # TODO this is already programmed somewhere else, can be improved
            a = (1 - (192 * alternative_channel.height / (math.pi**5 * alternative_channel.width) * math.tanh(math.pi * alternative_channel.width / (2 * alternative_channel.height))))
            extra_length_new = a * required_extra_resistance * alternative_channel.width * alternative_channel.height**3 / (12 * viscosity)
            alternative_channel.length += extra_length_new
        alternative_channel.meander_nodes, leftover_spacing_increase, _ = define_meander(alternative_channel, nodes, channel_dim, bounding_boxes)

        if leftover_spacing_increase < eps:
            successful = True
            print(f"Assigning extra length of {extra_length*1e3:.2f} mm to connected channel between nodes {alternative_channel.node1} and {alternative_channel.node2}. New length: {alternative_channel.length*1e3:.2f} mm")
            channel.length -= extra_length # remove the length that was reassigned to another channel to facilitate testing
    else: 
        leftover_spacing_increase = required_spacing_increase # TODO this is technically unnecessary if I just return required_spacing_increase

    return leftover_spacing_increase, alternative_channel
