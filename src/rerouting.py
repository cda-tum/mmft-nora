# Defines Exlusion Zones (based on user input (eventually) for channels)
# TODO this will eventually need to include A* to make sure the initial channels have the shortest distance between the nodes if there is a exclusion zone between them

import math
import heapq

from .mf_geometry_components import ExclusionZone

eps = 1e-12

def reroute_channel(channel, nodes, exclusion_zones, grid_resolution): # maybe move this to another part of the code
    start = nodes[channel.node1].coordinates
    goal = nodes[channel.node2].coordinates

    # path = a_star_reroute(start, goal, self.vertical, exclusion_zone, grid_resolution)
    path = a_star_reroute(start, goal, channel, exclusion_zones, clearance=channel.width/2)
    channel.rerouted_path = path
    channel.rerouted = True

    # TODO this is also going to be tough if the exclusion zone overlaps with a node, then technically all channels have to be rerouted.
    # print("this channel would need to be rerouted", channel, "because of Exclusion Zone", exclusion_zone) # TODO implement the actual code here based on A*

def check_overlap(exclusion_zone, channel, nodes):
    overlap = False
    # Get node coordinates TODO this is a code duplication!! --> maybe include this in the channel class already!!
    coord1 = nodes[channel.node1].coordinates
    coord2 = nodes[channel.node2].coordinates

    x1, y1, _ = coord1
    x2, y2, _ = coord2

    channel_layer = channel.layer # TODO incorporate this at a later time
    y_min, y_max = sorted([y1, y2])
    x_min, x_max = sorted([x1, x2])

    zone_x_min = exclusion_zone.get_x_min()
    zone_x_max = exclusion_zone.get_x_max()
    zone_y_min = exclusion_zone.get_y_min()
    zone_y_max = exclusion_zone.get_y_max()

    # check if the bounding box is between the nodes (take channel width and minimal distance into account)
    if channel.fixed_resistance is None: # there is a predefined module or box -> get the bounding box of that channel
        if channel.vertical: # vertical channel (only defined for non fixed resistances)
            x_min += channel.width/2
            x_max -= channel.width/2
            overlap = rects_intersect(x_min, x_max, y_min, y_max, zone_x_min, zone_x_max, zone_y_min, zone_y_max)
        elif not channel.vertical: # horizontal channel
            y_min += channel.width/2
            y_max -= channel.width/2
            overlap = rects_intersect(x_min, x_max, y_min, y_max, zone_x_min, zone_x_max, zone_y_min, zone_y_max)
    # else: 
        # TODO include either a warning or somthing else if there is an overlap between the modules or fixed resistance channels and the excluision zones
        # if the exclusion zones are board or module dependent, technically they should never overlap in the latter case

    return overlap

def rects_intersect(ax1, ax2, ay1, ay2, bx1, bx2, by1, by2): # maybe move this to a more general area so it can be reused better
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1) # touching edges count as overlap

def heuristic(a, b):
    """Euclidean distance heuristic."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def is_in_exclusion(point, exclusion_zones, clearance=0.0):
    """Check if point (x, y) is inside any exclusion zone."""
    x, y = point
    # for zone in exclusion_zones.values():
    zones = exclusion_zones.values() if isinstance(exclusion_zones, dict) else exclusion_zones

    for zone in zones:
        x_min = zone.get_x_min() - clearance
        x_max = zone.get_x_max() + clearance
        y_min = zone.get_y_min() - clearance
        y_max = zone.get_y_max() + clearance
        if x_min <= x <= x_max and y_min <= y <= y_max:
            return True
    return False


def get_neighbors(point, step, rectilinear=True): #TODO pass rectilinear from config and make it work for the dxf
    """Return neighbors of a point depending on rectilinear or octolinear moves."""
    x, y = point
    if rectilinear:
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    else:
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1),
                      (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dx, dy in directions:
        yield (x + dx * step, y + dy * step)



def reconstruct_path(came_from, current, start, goal):
    """Reconstruct path from A* search."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    path.insert(0, start)
    if path[-1] != goal:
        path.append(goal)
    return path

def distance_to_original_channel(point, line_start, line_end):
    """
    2D distance from point to a line segment defined by line_start and line_end.
    point, line_start, line_end: (x, y)
    """
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end

    dx = x2 - x1
    dy = y2 - y1
    if dx == dy == 0:  # line_start == line_end
        return math.hypot(x0 - x1, y0 - y1)

    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx*dx + dy*dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(x0 - proj_x, y0 - proj_y)

def simplify_path(path, eps=1e-9):
    """
    Simplify the rerouted path by removing intermediate collinear points.
    """
    if len(path) <= 2:
        return path

    simplified = [path[0]]
    for i in range(1, len(path) - 1):
        x1, y1, _ = simplified[-1]
        x2, y2, _ = path[i]
        x3, y3, _ = path[i + 1]

        # Compute direction vectors
        dx1, dy1 = x2 - x1, y2 - y1
        dx2, dy2 = x3 - x2, y3 - y2

        # Check if the three points are nearly collinear
        cross = abs(dx1 * dy2 - dy1 * dx2)
        if cross > eps:
            # Not collinear → keep the middle point
            simplified.append(path[i])

    simplified.append(path[-1])
    return simplified

def exclusion_from_bounding_box(box): # TODO move to bounding box class?
    x_min, x_max = box.get_x_min(), box.get_x_max()
    y_min, y_max = box.get_y_min(), box.get_y_max()

    pos = ((x_min + x_max) / 2, (y_min + y_max) / 2, 0.0)
    x_width = x_max - x_min
    y_length = y_max - y_min

    return ExclusionZone(
        position=pos,
        x_width=x_width,
        y_length=y_length,
        all_layers=box.multi_layer,
        layers={box.layer} if box.layer is not None else set(),
        name=f"bbox_{box.source}"
    )

def a_star_reroute(start, goal, channel, exclusion_zones, clearance, grid_step=1e-3, line_bonus_factor=1e-3): # TODO define a good and useful grid_step
    """
    A* routing between channel nodes avoiding exclusion zones.

    Parameters
    ----------
    channel : object
        Must have node1, node2, and nodes dict where coordinates can be accessed as:
        channel.nodes[channel.node1].coordinates → (x, y, z)
    exclusion_zones : dict[str, ExclusionZone]
        Dictionary of exclusion zones to avoid.
    grid_step : float
        Step size in meters for grid spacing.
    clearance : float
        Extra buffer distance around exclusion zones.

    Returns
    -------
    path : list of (x, y, z)
    """
    # start = channel.nodes[channel.node1].coordinates
    # goal = channel.nodes[channel.node2].coordinates
    local_exclusion_zones = list(exclusion_zones.values())

    # for box in bounding_boxes: # TODO this does not work yet!!
    #     # Skip box if it's based on the current channel
    #     if isinstance(box.source, type(channel)) and box.source == channel:
    #         continue
    #     if not box.multi_layer and box.layer != channel.layer: # Check if the box will block the channel in the same/channel layer
    #         continue
    #     #add the bounding box to the exclusion zones for this channel?
    #     extra_exclusion_zone = exclusion_from_bounding_box(box)
    #     local_exclusion_zones.append(extra_exclusion_zone)

    z = start[2]  # fixed layer
    start_2d = (start[0], start[1])
    goal_2d = (goal[0], goal[1])

    open_set = []
    heapq.heappush(open_set, (0, start_2d))
    came_from = {}
    g_score = {start_2d: 0}
    f_score = {start_2d: heuristic(start_2d, goal_2d)}

    visited = set()

    while open_set:
        _, current = heapq.heappop(open_set)
        if current in visited:
            continue
        visited.add(current)

        if heuristic(current, goal_2d) < grid_step:
            path_2d = reconstruct_path(came_from, current, start_2d, goal_2d)
            path = [(x, y, z) for x, y in path_2d]
            simple_path = simplify_path(path)
            return simple_path

        for neighbor in get_neighbors(current, grid_step):
            if is_in_exclusion(neighbor, local_exclusion_zones, clearance):
                continue

            tentative_g = g_score[current] + heuristic(current, neighbor)

            # compute bonus for being close to the original channel line
            line_dist = distance_to_original_channel(neighbor, start_2d, goal_2d)
            bonus = -line_bonus_factor / (line_dist + 1e-9)  # closer → more negative → preferred
            tentative_f = tentative_g + heuristic(neighbor, goal_2d) + bonus

            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_f
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    print(f"A* failed to find path between {start} and {goal}")
    return [start, goal]
