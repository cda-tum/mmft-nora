# Export the channel and nodes to dxf

import ezdxf
import math
import numpy as np
from collections import defaultdict

from channel_operations import get_longest_segment

eps = 1e-10
# via_diameter = 0.7e-3 # channel_dim["via_diameter"]  # mm TODO: use this from config.pyx

def export_to_dxf(nodes, channels, channel_dim, filename="../results/output", output_path=None):
    original_output_path = output_path
    if output_path:
        filename = output_path.replace('.dxf', '')
    sort_channel_nodes(nodes, channels)
    channels_per_node = define_channels_per_node(nodes, channels)
    define_quads_at_nodes(nodes, channels_per_node, channels, channel_dim["via_diameter"])
    segments, arcs = define_channel_segments(nodes, channels, channel_dim)
    # plot_layout(nodes, channels, show_node_quads=True, show_channel_ends=True)
    # segments = merge_connected_segments(segments)

    layer_files = define_dxf(nodes, channels, segments, arcs, filename, channel_dim["via_diameter"])
    combined_file = define_dxf_z_stack(nodes, channels, segments, arcs, filename, channel_dim["via_diameter"])
    
    # # Create combined DXF if output_path was specified
    # if original_output_path:
    #     import shutil
    #     from pathlib import Path
    #     # Copy the first generated layer file to the expected output path
    #     if layer_files and len(layer_files) > 0 and Path(layer_files[0]).exists():
    #         shutil.copy(layer_files[0], original_output_path)
    #         print(f"Combined DXF saved to: {original_output_path}")
    #     else:
    #         print(f"Warning: No layer files generated, cannot create {original_output_path}")


    from pathlib import Path
    print(f"[DXF EXPORT] z-stack combined file: {combined_file}")
    print(f"[DXF EXPORT] z-stack size: {Path(combined_file).stat().st_size} bytes")
    
    return {
        "combined": combined_file,
        "layers": layer_files,
        "all": [combined_file, *layer_files],
    }

def sort_channel_nodes(nodes, channels):
    for channel in channels.values():
        coord1 = nodes[channel.node1].coordinates
        coord2 = nodes[channel.node2].coordinates

        # Manhattan grid: x or y should be the same
        if coord1[0] == coord2[0]:  # Same x, compare y
            if coord1[1] > coord2[1]: # reversed y axis
                channel.node1, channel.node2 = channel.node2, channel.node1
        elif coord1[1] == coord2[1]:  # Same y, compare x
            if coord1[0] > coord2[0]:
                channel.node1, channel.node2 = channel.node2, channel.node1

def define_channels_per_node(nodes: dict, channels: dict) -> dict:
    '''
    Define the channels that are connected to each node in the channel network.
    '''
    channels_per_node = defaultdict(list)

    for channel in channels.values():
        channels_per_node[channel.node1].append(channel)
        channels_per_node[channel.node2].append(channel)

    return channels_per_node

def define_quads_at_nodes(nodes: dict, channels_per_node: dict, channels: dict, via_diameter) -> dict:
    '''
    Extrude the nodes to quads based on the channels connected to them, each quad is associated with a width and a length.
    '''
    # i.e.  ---4-----3
    #          |  x  | l
    #       ---1-----2
    #          |  w  |
    # quads = {} # contains node ID and width and height of the quad surrounding that node
    z = 0.0 # TODO
    # height = 0.0 # TODO

    segments = []

    for node in channels_per_node: # this doesn't yet include angled channels! TODO clean up
        height = max(channel.height for channel in channels_per_node[node])
        nodes[node].max_channel_height = height
        quad_width = []
        quad_length = []
        node_vertices = []
        for channel in channels_per_node[node]:
            width = channel.width
            # loop through all channels here 
            coord1 = nodes[channel.node1].coordinates
            coord2 = nodes[channel.node2].coordinates
            if math.isclose(coord1[1], coord2[1], rel_tol=eps): # horizontal channel # TODO use the vertical def in the channel class
                if node == channel.node1: # channel goes to + x
                    quad_right = width
                else:
                    quad_left = width
                # quad_lengths.append(width)
                quad_length.append(width)
            elif math.isclose(coord1[0], coord2[0], rel_tol=eps): # vertical channel
                if node == channel.node1: # channel goes to + y
                    quad_top = width
                else:
                    quad_bottom = width
                quad_width.append(width)
            # else:
            #     # print("Error: channel is not horizontal or vertical") # e.g., mixing (1:9) and organ channels
            #     # print("channel:", channel)

        if len(quad_width) > 1:
            width1 = quad_top #quad_width[0]
            width2 = quad_bottom #quad_width[1]
        elif len(quad_width) == 1:
            width1 = width2 = quad_width[0]
        else:
            width1 = width2 = 0.0

        if len(quad_length) > 1:
            length1 = quad_right #quad_length[0]
            length2 = quad_left #quad_length[1]
        elif len(quad_length) == 1:
            length1 = length2 = quad_length[0]
        else:
            length1 = length2 = 0.0

        # Add quads to ALL nodes
        if width1 == 0.0 and width2 == 0.0 and length1 != 0.0:
            width1 = width2 = length1
        if length1 == 0.0 and length2 == 0.0 and width1 != 0.0:
            length1 = length2 = width1

        # include the via diameter limit for some of the nodes (connected to the modules)
        if "_n" in node: # Nodes north of the module (-y)
            width1 = via_diameter
            # width2 = width2
            length1 = min(length1, via_diameter)
            length2 = min(length2, via_diameter)
        if "_s" in node and not "out" in node: # nodes south of the module (+y)
            # width1 = min(width1, via_diameter)
            width2 = via_diameter
            length1 = min(length1, via_diameter)
            length2 = min(length2, via_diameter)

        x0, y0, z0 = nodes[node].coordinates

        quad_vertice_1 = [x0 - width1/2, y0 + length2/2, z0 + height]  # bottom-left
        quad_vertice_2 = [x0 + width1/2, y0 + length1/2, z0 + height]  # bottom-right
        quad_vertice_3 = [x0 + width2/2, y0 - length1/2, z0 + height]  # top-right
        quad_vertice_4 = [x0 - width2/2, y0 - length2/2, z0 + height]  # top-left
        
        nodes[node].quad_vertices = [quad_vertice_1, quad_vertice_2, quad_vertice_3, quad_vertice_4]

        for channel in channels_per_node[node]:
            channel_vertices = []
            # find the “other” node in this channel
            if node == channel.node1:
                other = channel.node2
            else:
                other = channel.node1

            x1, y1, z1 = nodes[other].coordinates

            # horizontal?
            # if math.isclose(y1, y0, rel_tol=eps):
            if not channel.vertical:  # horizontal channel
                if x1 > x0:
                    # channel goes to +x, so pick the right edge verts (2,3)
                    channel_vertices = [quad_vertice_2, quad_vertice_3]
                else:
                    # channel goes to -x, pick left edge (1,4)
                    channel_vertices = [quad_vertice_4, quad_vertice_1]

            # vertical?
            # elif math.isclose(x1, x0, rel_tol=eps):
            elif channel.vertical:  # vertical channel
                if y1 > y0:
                    # channel goes up, pick top edge (3,4)
                    channel_vertices = [quad_vertice_1, quad_vertice_2]
                else:
                    # channel goes down, pick bottom edge (1,2)
                    channel_vertices = [quad_vertice_3, quad_vertice_4]

            channel.vertices.extend(channel_vertices)


def add_rerouted_segments(channel, nodes, segments, arcs, skip_segment=None):
    """
    Converts channel.rerouted_path (a polyline) into rectangular channel segments.

    Each segment is extended by width/2 at both ends to ensure clean overlap.
    """

    path   = channel.rerouted_path
    width  = channel.width
    height = channel.height
    layer  = channel.layer

    half_width = width / 2  # used for extension + perpendicular offset

    for i in range(1, len(path)):
        # # Start and end points of this centerline segment
        # x_start, y_start, z_start = path[i - 1]
        # x_end,   y_end,   z_end   = path[i]

        p0 = tuple(path[i-1])
        p1 = tuple(path[i])

        # ---------------------------------------------------
        # SKIP long segment if there is an input, e.g., when it is being used for meanders
        # ---------------------------------------------------
        if skip_segment and (p0 == skip_segment[0] and p1 == skip_segment[1]):
            continue
        if skip_segment and (p0 == skip_segment[1] and p1 == skip_segment[0]):
            # in case order flipped
            continue

        # normal segment creation below
        x_start, y_start, z_start = p0
        x_end,   y_end,   z_end   = p1

        # Direction vector
        dir_x = x_end - x_start
        dir_y = y_end - y_start

        # Segment length
        segment_length = math.sqrt(dir_x * dir_x + dir_y * dir_y)
        if segment_length < 1e-9:
            continue

        # Unit direction vector
        # if channel.vertical:
        ux = dir_x / segment_length
        uy = dir_y / segment_length
        # if not channel.vertical:
        #     ux, uy = -ux, -uy

        # ---------------------------------------------------------
        # Shorten the start and end points by half_width
        # ---------------------------------------------------------
        x_start_ext = x_start + ux * half_width
        y_start_ext = y_start + uy * half_width

        x_end_ext = x_end - ux * half_width
        y_end_ext = y_end - uy * half_width

        # Unit perpendicular direction
        perp_x = -uy
        perp_y =  ux

        # Renormalize perpendicular
        perp_len = math.sqrt(perp_x * perp_x + perp_y * perp_y)
        perp_x /= perp_len
        perp_y /= perp_len

        # ---------------------------------------------------------
        # Build the quad using the extended endpoints
        # ---------------------------------------------------------
        v_top_start    = [x_start_ext + perp_x * half_width, y_start_ext + perp_y * half_width, z_start]
        v_bottom_start = [x_start_ext - perp_x * half_width, y_start_ext - perp_y * half_width, z_start]
        v_bottom_end   = [x_end_ext   - perp_x * half_width, y_end_ext   - perp_y * half_width, z_end]
        v_top_end      = [x_end_ext   + perp_x * half_width, y_end_ext   + perp_y * half_width, z_end]

        ### Quad geometry! (with reversed y-axis)
        #       ---3-----2
        #          |     | 
        #       ---0-----1

        if p0 == nodes[channel.node1].coordinates:
            if channel.vertical:
                # print(v_bottom_start, nodes[channel.node1].quad_vertices[0])
                v_bottom_start = nodes[channel.node1].quad_vertices[1] # double check
                v_top_start = nodes[channel.node1].quad_vertices[0] # double check
            else:
                v_bottom_start = nodes[channel.node1].quad_vertices[2]
                v_top_start = nodes[channel.node1].quad_vertices[1]
        elif p1 == nodes[channel.node2].coordinates:
                if channel.vertical:
                    v_bottom_end = nodes[channel.node2].quad_vertices[2]
                    v_top_end = nodes[channel.node2].quad_vertices[3]
                else:
                    v_bottom_end = nodes[channel.node2].quad_vertices[3]
                    v_top_end = nodes[channel.node2].quad_vertices[0]

        # Save segment
        segments.append([v_top_start, v_bottom_start, v_bottom_end, v_top_end, layer, height])
        if 1 < i < len(path):
            add_arc_to_rerouted_channel(point1=path[i-2], point2=path[i-1], point3=path[i], width=width, layer=layer, height=height, arcs=arcs)
            
def add_arc_to_rerouted_channel(point1, point2, point3, width, layer, height, arcs): # maybe this is the function for all arcs?
    dx1 = point2[0] - point1[0]
    dy1 = point2[1] - point1[1]

    dx2 = point3[0] - point2[0]
    dy2 = point3[1] - point2[1]
    
    # path[i-1] is the coordinate that will be rounded off
    # technically this list could be facilitated
    if abs(dx1) < eps and dy1 > eps and dx2 < -eps and abs(dy2) < eps:
        # up then left
        center = (point2[0] - width/2, point2[1] - width/2, point2[2]) 
        arcs.append([center, 0, 90, width, layer, height])
    # elif abs(dx1) < eps and dy1 > eps and dx2 > eps and abs(dy2) < eps:
    elif dx1 < -eps and abs(dy1) < eps and abs(dx2) < eps and dy2 > eps:
        # left then up
        center = (point2[0] + width/2, point2[1] + width/2, point2[2])
        arcs.append([center, 180, -90, width, layer, height])
    elif dx1 > eps and abs(dy1) < eps and abs(dx2) < eps and dy2 > eps:
        # right then up
        center = (point2[0] - width/2, point2[1] + width/2, point2[2])
        arcs.append([center, -90, 0, width, layer, height]) 
    elif abs(dx1) < eps and dy1 > eps and dx2 > eps and abs(dy2) < eps:       
        # up and then right       
        center = (point2[0] + width/2, point2[1] - width/2, point2[2])
        arcs.append([center, 90, 180, width, layer, height])
    elif dx1 > eps and abs(dy1) < eps and abs(dx2) < eps and dy2 < -eps:
        # right then down
        center = (point2[0] - width/2, point2[1] - width/2, point2[2])
        arcs.append([center, 0, 90, width, layer, height])
    elif abs(dx1) < eps and dy1 < -eps and dx2 > eps and abs(dy2) < eps:
        # down then right
        center = (point2[0] + width/2, point2[1] + width/2, point2[2])
        arcs.append([center, 180, -90, width, layer, height])
    elif dx1 < -eps and abs(dy1) < eps and abs(dx2) < eps and dy2 < -eps: 
        # left and then down
        center = (point2[0] + width/2, point2[1] - width/2, point2[2])
        arcs.append([center, 90, 180, width, layer, height])
    elif abs(dx1) < eps and dy1 < -eps and dx2 < -eps and abs(dy2) < eps:
        # down and then left
        center = (point2[0] - width/2, point2[1] + width/2, point2[2])
        arcs.append([center, 180, -90, width, layer, height])
    else: 
        print("Warning: arc direction not recognized for points", point1, point2, point3, dx1, dy1, dx2, dy2)

def define_channel_segments(nodes, channels, channel_dim):
    segments: list = []
    arcs: list = []

    def _add_seg(v1, v2, v3, v4, layer, height):
        segments.append([v1, v2, v3, v4, layer, height])

    def _add_arc(center, angle_start, angle_end, radius, layer, height): # this function is redundant 
        arcs.append([center, angle_start, angle_end, radius, layer, height])

    for channel in channels.values():
        width = channel.width
        half_width = width / 2
        radius = width
        height = channel.height
        layer = channel.layer
        meander_nodes = channel.meander_nodes

        # rerouted channels without meanders
        if channel.rerouted and meander_nodes == []:
            add_rerouted_segments(channel, nodes, segments, arcs) # TODO there is a mistake here because the first and last segment should be extended towards the existing quads at the nodes, right now artifical quads are being used

        # everything below is only for meandering, variable-resistance channels
        if meander_nodes == [] or channel.fixed_resistance is not None:
            continue

        if channel.rerouted:
            longest_segment, coord1, coord2, path_int_start, path_int_end = get_longest_segment(channel, nodes, channel_dim)
            add_rerouted_segments(channel, nodes, segments, arcs, skip_segment=(tuple(coord1), tuple(coord2)))
            extra_quad_1 = [
                [coord1[0] - half_width, coord1[1] + half_width, coord1[2]],
                [coord1[0] + half_width, coord1[1] + half_width, coord1[2]],
                [coord1[0] + half_width, coord1[1] - half_width, coord1[2]],
                [coord1[0] - half_width, coord1[1] - half_width, coord1[2]],
            ]
            extra_quad_2 = [
                [coord2[0] - half_width, coord2[1] + half_width, coord2[2]],
                [coord2[0] + half_width, coord2[1] + half_width, coord2[2]],
                [coord2[0] + half_width, coord2[1] - half_width, coord2[2]],
                [coord2[0] - half_width, coord2[1] - half_width, coord2[2]],
            ]
            x0, y0, z0 = coord1
            x1, y1, z1 = coord2
            if nodes[channel.node1].coordinates != coord1:
                quad_vertices_1 = extra_quad_1
                # print(channel.rerouted_path[path_int_start-1], coord1, meander_nodes[0])
                # check that the correct three points are passed to the add arc function 
                point1=channel.rerouted_path[path_int_start-1]
                point2=coord1
                point3=meander_nodes[0]
                dx1 = point2[0] - point1[0]
                dy1 = point2[1] - point1[1]

                dx2 = point3[0] - point2[0]
                dy2 = point3[1] - point2[1]
                if (abs(dx1) < eps and abs(dx2) < eps) or (abs(dy1) < eps and abs(dy2) < eps):
                    # the points are aligned in one line, a different point needs to be chosen to make the arc function work 
                    point1=channel.rerouted_path[path_int_start-3] # TODO this might not always work
                    point2=coord1
                    point3=meander_nodes[0]
                add_arc_to_rerouted_channel(point1, point2, point3, width=width, layer=layer, height=height, arcs=arcs)
            else:
                quad_vertices_1 = nodes[channel.node1].quad_vertices
            if nodes[channel.node2].coordinates != coord2:
                quad_vertices_2 = extra_quad_2
                # This arc is redundant because it is covered by the arcs added in the meander segment creation -> TODO check if it works for horizontal channels and other meander directions
                # add_arc_to_rerouted_channel(point1=channel.rerouted_path[path_int_end-2], point2=coord2, point3=meander_nodes[0], width=width*2, layer=layer, height=height, arcs=arcs)
            else:
                quad_vertices_2 = nodes[channel.node2].quad_vertices
        else:
            coord1 = nodes[channel.node1].coordinates
            coord2 = nodes[channel.node2].coordinates
            quad_vertices_1 = nodes[channel.node1].quad_vertices
            quad_vertices_2 = nodes[channel.node2].quad_vertices

        x0, y0, z0 = meander_nodes[0]
        x1, y1, z1 = meander_nodes[-1]

        reverse = False  # which way the meanders are directed
        direction = 1
        if meander_nodes[0][1] < meander_nodes[1][1] or meander_nodes[0][0] < meander_nodes[1][0]:
            reverse = True
            direction = -1

        if not channel.vertical:  # horizontal channel
            _add_seg(
                quad_vertices_1[1],
                quad_vertices_1[2],
                [x0 - half_width, y0 - half_width, z0],
                [x0 - half_width, y0 + half_width, z0],
                layer,
                height,
            )
            _add_seg(
                quad_vertices_2[0],
                quad_vertices_2[3],
                [x1 + half_width, y1 - half_width, z1],
                [x1 + half_width, y1 + half_width, z1],
                layer,
                height,
            )

            if not reverse:
                for i in range(len(meander_nodes) // 4):
                    p0 = meander_nodes[i * 4]
                    p1 = meander_nodes[i * 4 + 1]
                    p2 = meander_nodes[i * 4 + 2]
                    p3 = meander_nodes[i * 4 + 3]

                    _add_arc([x0 - half_width, y0 - half_width, z0], 0, 90, radius, layer, height)
                    _add_seg(
                        [p0[0] + half_width, p0[1] - half_width, p0[2]],
                        [p0[0] - half_width, p0[1] - half_width, p0[2]],
                        [p1[0] - half_width, p1[1] + half_width, p1[2]],
                        [p1[0] + half_width, p1[1] + half_width, p1[2]],
                        layer,
                        height,
                    )
                    _add_arc([p1[0] + half_width, p1[1] + half_width, p1[2]], 180, -90, radius, layer, height)
                    _add_seg(
                        [p1[0] + half_width, p1[1] + half_width, p1[2]],
                        [p1[0] + half_width, p1[1] - half_width, p1[2]],
                        [p2[0] - half_width, p2[1] - half_width, p2[2]],
                        [p2[0] - half_width, p2[1] + half_width, p2[2]],
                        layer,
                        height,
                    )
                    _add_arc([p2[0] - half_width, p2[1] + half_width, p2[2]], -90, 0, radius, layer, height)
                    _add_seg(
                        [p2[0] + half_width, p2[1] + half_width, p2[2]],
                        [p2[0] - half_width, p2[1] + half_width, p2[2]],
                        [p3[0] - half_width, p3[1] - half_width, p3[2]],
                        [p3[0] + half_width, p3[1] - half_width, p3[2]],
                        layer,
                        height,
                    )
                    _add_arc([x1 + channel.width / 2, y1 - channel.width / 2, z1], 90, 180, radius, layer, height)

                    if i > 0:
                        p3_prev = meander_nodes[(i - 1) * 4 + 3]
                        p4_prev = meander_nodes[(i - 1) * 4 + 4]
                        _add_arc([p3_prev[0] + half_width, p3_prev[1] - half_width, p3_prev[2]], 90, 180, radius, layer, height)
                        _add_seg(
                            [p3_prev[0] + half_width, p3_prev[1] + half_width, p3_prev[2]],
                            [p3_prev[0] + half_width, p3_prev[1] - half_width, p3_prev[2]],
                            [p4_prev[0] - half_width, p4_prev[1] - half_width, p4_prev[2]],
                            [p4_prev[0] - half_width, p4_prev[1] + half_width, p4_prev[2]],
                            layer,
                            height,
                        )
                        _add_arc([p4_prev[0] - half_width, p4_prev[1] - half_width, p4_prev[2]], 0, 90, radius, layer, height)

            if reverse:
                for i in range(len(meander_nodes) // 4):
                    p0 = meander_nodes[i * 4]
                    p1 = meander_nodes[i * 4 + 1]
                    p2 = meander_nodes[i * 4 + 2]
                    p3 = meander_nodes[i * 4 + 3]

                    _add_arc([x0 - half_width, y0 + half_width, z0], -90, 0, radius, layer, height)
                    _add_seg(
                        [p0[0] + half_width, p0[1] + half_width, p0[2]],
                        [p0[0] - half_width, p0[1] + half_width, p0[2]],
                        [p1[0] - half_width, p1[1] - half_width, p1[2]],
                        [p1[0] + half_width, p1[1] - half_width, p1[2]],
                        layer,
                        height,
                    )
                    _add_arc([p1[0] + half_width, p1[1] - half_width, p1[2]], 90, 180, radius, layer, height)
                    _add_seg(
                        [p1[0] + half_width, p1[1] + half_width, p1[2]],
                        [p1[0] + half_width, p1[1] - half_width, p1[2]],
                        [p2[0] - half_width, p2[1] - half_width, p2[2]],
                        [p2[0] - half_width, p2[1] + half_width, p2[2]],
                        layer,
                        height,
                    )
                    _add_arc([p2[0] - half_width, p2[1] - half_width, p2[2]], 0, 90, radius, layer, height)
                    _add_seg(
                        [p2[0] + half_width, p2[1] - half_width, p2[2]],
                        [p2[0] - half_width, p2[1] - half_width, p2[2]],
                        [p3[0] - half_width, p3[1] + half_width, p3[2]],
                        [p3[0] + half_width, p3[1] + half_width, p3[2]],
                        layer,
                        height,
                    )
                    _add_arc([x1 + channel.width / 2, y1 + channel.width / 2, z1], 180, -90, radius, layer, height)

                    if i > 0:
                        p3_prev = meander_nodes[(i - 1) * 4 + 3]
                        p4_prev = meander_nodes[(i - 1) * 4 + 4]
                        _add_arc([p3_prev[0] + half_width, p3_prev[1] + half_width, p3_prev[2]], 180, -90, radius, layer, height)
                        _add_seg(
                            [p3_prev[0] + half_width, p3_prev[1] + half_width, p3_prev[2]],
                            [p3_prev[0] + half_width, p3_prev[1] - half_width, p3_prev[2]],
                            [p4_prev[0] - half_width, p4_prev[1] - half_width, p4_prev[2]],
                            [p4_prev[0] - half_width, p4_prev[1] + half_width, p4_prev[2]],
                            layer,
                            height,
                        )
                        _add_arc([p4_prev[0] - half_width, p4_prev[1] + half_width, p4_prev[2]], -90, 0, radius, layer, height)

        else:  # vertical channel
            _add_seg(
                quad_vertices_1[1],
                quad_vertices_1[0],
                [x0 - channel.width / 2, y0 - channel.width / 2, z0],
                [x0 + channel.width / 2, y0 - channel.width / 2, z0],
                layer,
                height,
            )
            _add_seg(
                quad_vertices_2[2],
                quad_vertices_2[3],
                [x1 - channel.width / 2, y1 + channel.width / 2, z1],
                [x1 + channel.width / 2, y1 + channel.width / 2, z1],
                layer,
                height,
            )

            if not reverse:  # goes right
                for i in range(len(meander_nodes) // 4):
                    p0 = meander_nodes[i * 4]
                    p1 = meander_nodes[i * 4 + 1]
                    p2 = meander_nodes[i * 4 + 2]
                    p3 = meander_nodes[i * 4 + 3]

                    _add_arc([x0 - half_width, y0 - half_width, z0], 0, 90, radius, layer, height)
                    _add_seg(
                        [p0[0] - half_width, p0[1] - half_width, p0[2]],
                        [p0[0] - half_width, p0[1] + half_width, p0[2]],
                        [p1[0] + half_width, p1[1] + half_width, p1[2]],
                        [p1[0] + half_width, p1[1] - half_width, p1[2]],
                        layer,
                        height,
                    )
                    _add_arc([p1[0] + half_width, p1[1] + half_width, p1[2]], 180, -90, radius, layer, height)
                    _add_seg(
                        [p1[0] - half_width, p1[1] + half_width, p1[2]],
                        [p1[0] + half_width, p1[1] + half_width, p1[2]],
                        [p2[0] + half_width, p2[1] - half_width, p2[2]],
                        [p2[0] - half_width, p2[1] - half_width, p2[2]],
                        layer,
                        height,
                    )
                    # NOTE: preserve original z-index usage (uses p1[2])
                    _add_arc([p2[0] + half_width, p2[1] - half_width, p1[2]], 90, 180, radius, layer, height)
                    _add_seg(
                        [p2[0] + half_width, p2[1] - half_width, p2[2]],
                        [p2[0] + half_width, p2[1] + half_width, p2[2]],
                        [p3[0] - half_width, p3[1] + half_width, p3[2]],
                        [p3[0] - half_width, p3[1] - half_width, p3[2]],
                        layer,
                        height,
                    )
                    _add_arc([x1 - channel.width / 2, y1 + channel.width / 2, z1], -90, 0, radius, layer, height)

                    if i > 0:
                        p3_prev = meander_nodes[(i - 1) * 4 + 3]
                        p4_prev = meander_nodes[(i - 1) * 4 + 4]
                        _add_arc([p3_prev[0] - half_width, p3_prev[1] + half_width, p3_prev[2]], -90, 0, radius, layer, height)
                        _add_seg(
                            [p3_prev[0] - half_width, p3_prev[1] + half_width, p3_prev[2]],
                            [p3_prev[0] + half_width, p3_prev[1] + half_width, p3_prev[2]],
                            [p4_prev[0] + half_width, p4_prev[1] - half_width, p4_prev[2]],
                            [p4_prev[0] - half_width, p4_prev[1] - half_width, p4_prev[2]],
                            layer,
                            height,
                        )
                        _add_arc([p4_prev[0] - half_width, p4_prev[1] - half_width, p4_prev[2]], 0, 90, radius, layer, height)

            if reverse:
                for i in range(len(meander_nodes) // 4):
                    p0 = meander_nodes[i * 4]
                    p1 = meander_nodes[i * 4 + 1]
                    p2 = meander_nodes[i * 4 + 2]
                    p3 = meander_nodes[i * 4 + 3]

                    _add_arc([x0 + half_width, y0 - half_width, z0], 90, 180, radius, layer, height)
                    _add_seg(
                        [p0[0] + half_width, p0[1] + half_width, p0[2]],
                        [p0[0] + half_width, p0[1] - half_width, p0[2]],
                        [p1[0] - half_width, p1[1] - half_width, p1[2]],
                        [p1[0] - half_width, p1[1] + half_width, p1[2]],
                        layer,
                        height,
                    )
                    _add_arc([p1[0] - half_width, p1[1] + half_width, p1[2]], -90, 0, radius, layer, height)
                    _add_seg(
                        [p1[0] - half_width, p1[1] + half_width, p1[2]],
                        [p1[0] + half_width, p1[1] + half_width, p1[2]],
                        [p2[0] + half_width, p2[1] - half_width, p2[2]],
                        [p2[0] - half_width, p2[1] - half_width, p2[2]],
                        layer,
                        height,
                    )
                    _add_arc([p2[0] - half_width, p2[1] - half_width, p2[2]], 0, 90, radius, layer, height)
                    _add_seg(
                        [p2[0] - half_width, p2[1] + half_width, p2[2]],
                        [p2[0] - half_width, p2[1] - half_width, p2[2]],
                        [p3[0] + half_width, p3[1] - half_width, p3[2]],
                        [p3[0] + half_width, p3[1] + half_width, p3[2]],
                        layer,
                        height,
                    )
                    _add_arc([x1 + channel.width / 2, y1 + channel.width / 2, z1], 180, -90, radius, layer, height)

                    if i > 0:
                        p3_prev = meander_nodes[(i - 1) * 4 + 3]
                        p4_prev = meander_nodes[(i - 1) * 4 + 4]
                        _add_arc([p3_prev[0] + half_width, p3_prev[1] + half_width, p3_prev[2]], 180, -90, radius, layer, height)
                        _add_seg(
                            [p3_prev[0] - half_width, p3_prev[1] + half_width, p3_prev[2]],
                            [p3_prev[0] + half_width, p3_prev[1] + half_width, p3_prev[2]],
                            [p4_prev[0] + half_width, p4_prev[1] - half_width, p4_prev[2]],
                            [p4_prev[0] - half_width, p4_prev[1] - half_width, p4_prev[2]],
                            layer,
                            height,
                        )
                        _add_arc([p4_prev[0] + half_width, p4_prev[1] - half_width, p4_prev[2]], 90, 180, radius, layer, height)

    return segments, arcs

def get_no_dxf_layers(channels):
    '''
    Returns the number of layers in the dxf file. 
    The number of layers is equal to the number of no_of_layers + no_of_channel_heights.
    '''
    no_layers = 2 # TODO don't hardcode this
    channel_heights_0 = []
    channel_heights_1 = []
    for channel in channels.values():
        height = channel.height
        if channel.layer == 1:
            if height not in channel_heights_0:
                channel_heights_0.append(height)
        if channel.layer == 2:
            if height not in channel_heights_1:
                channel_heights_1.append(height)

    # no_dxf_layers = no_layers + len(channel_heights)

    return channel_heights_0, channel_heights_1     

from shapely.geometry import Polygon
from shapely.ops import unary_union

def arc_to_polygon(center, radius, angle_start, angle_end, width, n_points=16):
    """
    Create a filled 90° outer arc polygon.
    Center is the inner corner point.
    """
    cx, cy = center
    r_outer = radius
    r_inner = 0

    if angle_end < angle_start:
        angle_end += 360

    theta_outer = np.linspace(np.deg2rad(angle_start), np.deg2rad(angle_end), n_points)
    theta_inner = theta_outer[::-1]

    outer = [(cx + r_outer * np.cos(t), cy + r_outer * np.sin(t)) for t in theta_outer]
    inner = [(cx + r_inner * np.cos(t), cy + r_inner * np.sin(t)) for t in theta_inner]

    return Polygon(outer + inner)
    # return Polygon(outer)


def define_dxf(nodes, channels, segments, arcs, filename_base, via_diameter, scale=1):
    '''
    Save the channel network as DXF with merged geometries.
    Channels with meanders are merged from their segments + arcs into one outline.
    Returns list of created DXF filenames.
    '''

    channel_heights_0, channel_heights_1 = get_no_dxf_layers(channels)
    channel_heights_layers = [channel_heights_0, channel_heights_1]
    created_files = []

    for layer in range(2):
        layer_z = layer + 1
        channel_heights = channel_heights_layers[layer]

        for z in range(len(channel_heights)):
            filename = f"{filename_base}_layer{layer}_depth{channel_heights[z]}.dxf"
            doc = ezdxf.new()
            msp = doc.modelspace()
            polygons = []

            for channel in channels.values():
                if channel.fixed_resistance is None and channel.layer == layer_z and channel.height == channel_heights[z]:

                    # --- normal (non-meandering) channels ---
                    if not channel.meander_nodes and not channel.rerouted:
                        vertices2d = [(x * scale, y * scale) for x, y, _ in channel.vertices]
                        polygons.append(Polygon(vertices2d))

                    # --- meandering channels: merge segments + arcs ---
                    else:
                        sub_polys = []

                        # find all segments on same layer + height
                        for seg in segments:
                            seg_layer, seg_height = seg[-2], seg[-1]
                            if seg_layer == layer_z and seg_height == channel_heights[z]:
                                verts = seg[:-2]
                                pts = [(x * scale, y * scale) for x, y, _ in verts]
                                sub_polys.append(Polygon(pts))

                        # find all arcs on same layer + height
                        for arc in arcs:
                            arc_layer, arc_height = arc[4], arc[5]
                            if arc_layer == layer_z and arc_height == channel_heights[z]:
                                center = (arc[0][0] * scale, arc[0][1] * scale)
                                angle_start, angle_end = arc[1], arc[2]
                                radius = arc[3] * scale
                                width = channel.width * scale
                                sub_polys.append(arc_to_polygon(center, radius, angle_start, angle_end, width))

                        if sub_polys:
                            merged = unary_union(sub_polys)
                            if merged.geom_type == "Polygon":
                                polygons.append(merged)
                            else:
                                polygons.extend(list(merged.geoms))

            # node quads
            for node in nodes.values():
                if node.coordinates[2] == (layer_z * 1e-3) or node.multi_layer:
                    pts = [(x * scale, y * scale) for x, y, _ in node.quad_vertices]
                    polygons.append(Polygon(pts))

            # --- merge everything for this layer ---
            if polygons:
                merged = unary_union(polygons)
                merged_polys = [merged] if merged.geom_type == "Polygon" else list(merged.geoms)
                for poly in merged_polys:
                    coords = list(poly.exterior.coords)
                    msp.add_lwpolyline(coords, close=True, dxfattribs={"color": 4, "lineweight": 1})

            doc.saveas(filename)
            created_files.append(filename)
            print(f"DXF file saved: {filename}")

    # VIA LAYER
    doc = ezdxf.new()
    msp = doc.modelspace()
    filename = f"{filename_base}_vias.dxf"

    for layer in range(2):
        for node_name, node in nodes.items():
            if "mix" in node_name or "inflow" in node_name or ("branch" in node_name and not "0" in node_name) or ("branch" in node_name and not "A" in node_name):
                color = 2
                center = node.coordinates[:2]
                radius = via_diameter * scale / 2
                msp.add_circle(center, radius, dxfattribs={"color": color, "lineweight": 1})
            if node.multi_layer:
                color = 4 if node.coordinates[2] != 0 else 1
                center = node.coordinates[:2]
                radius = via_diameter * scale / 2
                msp.add_circle(center, radius, dxfattribs={"color": color, "lineweight": 1})

    doc.saveas(filename)
    created_files.append(filename)
    print(f"DXF file saved: {filename}")
    
    return created_files


def define_dxf_z_stack(nodes, channels, segments, arcs, filename, via_diameter, scale=1):

    '''
    Saves the channel network as a dxf file. Represents the 2D network, channels are represented as rectangles and arcs are two rounded arcs. 
    The result looks very similar to the generated SVG file.
    '''

    # Create a new DXF document
    doc = ezdxf.new()
    msp = doc.modelspace()
    polygons_by_layer = {}

    output_file = f"{filename}.dxf"

    # channel outlines
    for channel in channels.values():
        if channel.fixed_resistance is None:
            key = channel.layer
            polygons_by_layer.setdefault(key, [])
            # Get the actual (x, y) coordinates for each vertex in the face
            # vertices2d = [[x * scale, y * scale] for x, y, _ in channel.vertices]
            # Add the polyline to the DXF
            if not channel.meander_nodes and not channel.rerouted:
                vertices2d = [(x * scale, y * scale) for x, y, _ in channel.vertices]
                polygons_by_layer[key].append(Polygon(vertices2d))

            else:
                sub_polys = [] # for meandering channels

            # find all segments on same layer
                for seg in segments:
                    seg_layer, seg_height = seg[-2], seg[-1]
                    if seg_layer == key:
                        verts = seg[:-2]
                        pts = [(x * scale, y * scale) for x, y, _ in verts]
                        sub_polys.append(Polygon(pts))

                # find all arcs on same layer + height
                for arc in arcs:
                    arc_layer, arc_height = arc[4], arc[5]
                    if arc_layer == key:
                        center = (arc[0][0] * scale, arc[0][1] * scale)
                        angle_start, angle_end = arc[1], arc[2]
                        radius = arc[3] * scale
                        width = channel.width * scale
                        sub_polys.append(arc_to_polygon(center, radius, angle_start, angle_end, width))

                if sub_polys:
                    merged = unary_union(sub_polys)
                    if merged.geom_type == "Polygon":
                        polygons_by_layer[key].append(merged)
                    else:
                        polygons_by_layer[key].extend(list(merged.geoms))

    # node quads
    polygons_by_layer[0] = [] # hardcoded fix for ooc-gg problem
    # for key in polygons_by_layer.keys():
    for node_name, node in nodes.items():
        node_layer = int(node.coordinates[2] * 1e3)
        pts = [(x * scale, y * scale) for x, y, _ in node.quad_vertices]
        polygons_by_layer[node_layer].append(Polygon(pts))

        color = 7
        if "mix" in node_name or "inflow" in node_name or ("branch" in node_name and not "0" in node_name) or ("branch" in node_name and not "A" in node_name):
            color = 2
        if node.multi_layer:
            color = 4 if node.coordinates[2] != 0 else 1

        center = (node.coordinates[0] * scale, node.coordinates[1] * scale)
        radius = via_diameter * scale / 2
        msp.add_circle(center, radius, dxfattribs={"color": color, "lineweight": 1})



    for layer, polygons in polygons_by_layer.items():
        merged = unary_union(polygons)
        merged_polys = [merged] if merged.geom_type == "Polygon" else list(merged.geoms)
        for poly in merged_polys:
            coords = list(poly.exterior.coords)
            msp.add_lwpolyline(coords, close=True, dxfattribs={"color": 7, "lineweight": 1})



    # # Draw node outlines in DXF
    # for node_name, node in nodes.items():
    #     color = 7
    #     if "mix" in node_name or "inflow" in node_name or ("branch" in node_name and not "0" in node_name) or ("branch" in node_name and not "A" in node_name):
    #         color = 2 # yellow
    #         center = node.coordinates[:2]
    #         radius = via_diameter * scale / 2
    #         msp.add_circle(center, radius, dxfattribs={"color": color, "lineweight": 1})
    #     if node.multi_layer == True:
    #         color = 4 # light blue
    #         if node.coordinates[2] == 0:
    #             color = 1 # red
    #         center = node.coordinates[:2]
    #         radius = via_diameter * scale / 2
    #         msp.add_circle(center, radius, dxfattribs={"color": color, "lineweight": 1})

    #     pts = [[x * scale, y * scale] for x, y, _ in node.quad_vertices]  # Extract only (x, y)
    #     msp.add_lwpolyline(pts, close=True, dxfattribs={"color": color, "lineweight": 1})

    # for segment in segments:
    #     vertices = segment[:-2]
    #     pts = [[x * scale, y * scale] for x, y, _ in vertices]
    #     msp.add_lwpolyline(pts, close=True, dxfattribs={"color": 7, "lineweight": 1})


    # for arc in arcs:
    #     center = arc[0][:2] # TODO add scale factor
    #     angle_start = arc[1]
    #     angle_end = arc[2]
    #     radius = arc[3] * 2 * scale

    #     msp.add_arc(center, radius, angle_start, angle_end, dxfattribs={"lineweight": 1})

    # Save the DXF file
    doc.saveas(output_file)
    # print(f"DXF file saved: {filename}")
    print(f"Combined DXF saved to: {output_file}")

    return output_file