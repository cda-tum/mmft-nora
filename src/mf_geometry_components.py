import math

from .utils import calculate_hydraulic_resistance, calculate_hydraulic_resistance_cylinder
from .config import Config

cfg = Config()
eps = cfg.eps

class Node:
    def __init__(self, connection_no, multi_layer, coordinates):
        self.connection_no = connection_no
        self.multi_layer = multi_layer
        self.coordinates = coordinates
        self.pressure = None  # This will be updated after solving the MNA system
        self.quad_vertices = []
        self.max_channel_height = 0.0

class Channel:
    def __init__(self, nodes, node1, node2, flow_rate, layer, width=cfg.channel_dim["width"], height=cfg.channel_dim["height"], fixed_resistance=None):
        self.flow_rate = flow_rate
        self.width = width
        self.height = height
        self.node1 = node1
        self.node2 = node2
        self.layer = layer
        self.length = None # calculated based on calculate_minimal_length and then updated based on the pressure drop
        self.fixed_resistance = fixed_resistance

        self.rerouted = False
        self.rerouted_path = []

        self.vertices = []

        self.meander_nodes = []
        self.extra_length = None

        self.final_length = None # calculated based on the length of the channel and the meander nodes

        self.transfered_length = False # this is to check if meander length was transfered from or to this channel

        if self.fixed_resistance is None: # the fixed channels are not adapted 
            coord1 = nodes[self.node1].coordinates
            coord2 = nodes[self.node2].coordinates
            x1, y1, z1 = coord1
            x2, y2, z2 = coord2

            if abs(x1 - x2) < eps:
                self.vertical = True
            else:
                self.vertical = False
        else:
            self.vertical = None

    def calculate_hydraulic_resistance(self, nodes, viscosity): # TODO rename this function to something different!!
        if self.fixed_resistance is not None:
            return self.fixed_resistance
        else:
            resistance = calculate_hydraulic_resistance(width=self.width, height=self.height, length=self.length, viscosity=viscosity)

        # coord1 = nodes[self.node1].coordinates
        # coord2 = nodes[self.node2].coordinates
        # if coord1[2] == 0.0 or coord2[2] == 0.0: # TODO this is the organ module connection - adapt to only one of the nodes - see info from Laurens
        #     layer_switch_resistance_plate = calculate_hydraulic_resistance_cylinder(cfg.channel_dim["layer_switch_distance"], cfg.channel_dim["via_diameter"] / 2, cfg.viscosity)
        #     # print("added resistance percentage:", layer_switch_resistance_plate / resistance * 100.0)
        #     resistance += layer_switch_resistance_plate
        if nodes[self.node1].multi_layer:
            layer_switch_resistance_plate = calculate_hydraulic_resistance_cylinder(cfg.channel_dim["layer_switch_distance"], cfg.channel_dim["via_diameter"] / 2, cfg.viscosity)
            # print("added resistance percentage:", layer_switch_resistance_plate / resistance * 100.0)
            resistance += layer_switch_resistance_plate

        return resistance

class ExclusionZone():
    def __init__(self, position, x_width, y_length, all_layers=True, layers=None, name=None):
        # Definition for screws or bolts in the xy-plane. In addition to the user defined size an extra distance spacing is included.
        self.position = position
        self.x_width = x_width
        self.y_length = y_length
        self.all_layers = all_layers
        self.layers = set(layers) if (not all_layers and layers is not None) else None
        self.name = name # TODO maybe remove this?? or that would be then bolt_1, screw_3,...
    # zone= # here minimal channel distance or maybe minimal distance excl zone or something should be included

    # Bounds (assuming position is the center)
    # i.e.     o-----o
    #          |  x  | 
    #          o-----o
    def get_x_min(self):
        return self.position[0] - self.x_width / 2.0

    def get_x_max(self):
        return self.position[0] + self.x_width / 2.0

    def get_y_min(self):
        return self.position[1] - self.y_length / 2.0

    def get_y_max(self):
        return self.position[1] + self.y_length / 2.0
    
    def contains_point(self, point):
        """Check if a 2D or 3D point is inside this exclusion zone."""
        x, y, *rest = point
        z = rest[0] if rest else 0.0
        return (
            self.get_x_min() <= x <= self.get_x_max() and
            self.get_y_min() <= y <= self.get_y_max() #and
            # self.z_min <= z <= self.z_max
        )    

class BoundingBox:
    def __init__(self, node_1, node_2, node_3, node_4, layer=None, multi_layer=False, source=None):
        self.node_1 = node_1
        self.node_2 = node_2
        self.node_3 = node_3
        self.node_4 = node_4
        self.layer = layer
        self.multi_layer = multi_layer
        self.source = source # this is the channel, if it is mixing or else

    def get_x_min(self):
        x_min = min(self.node_1[0], self.node_2[0], self.node_3[0], self.node_4[0])
        return x_min
    
    def get_y_min(self):
        y_min = min(self.node_1[1], self.node_2[1], self.node_3[1], self.node_4[1])
        return y_min
    
    def get_x_max(self):
        x_max = max(self.node_1[0], self.node_2[0], self.node_3[0], self.node_4[0])
        return x_max
    
    def get_y_max(self):
        y_max = max(self.node_1[1], self.node_2[1], self.node_3[1], self.node_4[1])
        return y_max
