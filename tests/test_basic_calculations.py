# tests/test_basic_calculations.py
import math

from src.utils import calculate_hydraulic_resistance, bisect_root
from src.channel_operations import calculate_minimal_length
from src.mf_geometry_components import Channel, Node, BoundingBox
from src.config import Config
from src.channel_meanders import get_meander_length, bounding_box_from_channel

cfg = Config()

# main.py
def test_calculate_hydraulic_resistance_symmetry():
    """Check that swapping width and height yields consistent result."""
    viscosity = 1e-3
    r1 = calculate_hydraulic_resistance(width=100e-6, height=50e-6, length=1e-3, viscosity=viscosity)
    r2 = calculate_hydraulic_resistance(width=50e-6, height=100e-6, length=1e-3, viscosity=viscosity)
    assert math.isclose(r1, r2, rel_tol=1e-12)

def test_calculate_hydraulic_resistance_scaling():
    viscosity = 1e-3
    r1 = calculate_hydraulic_resistance(width=100e-6, height=50e-6, length=1e-3, viscosity=viscosity)
    r2 = calculate_hydraulic_resistance(width=100e-6, height=50e-6, length=2 * 1e-3, viscosity=viscosity)
    assert math.isclose(r2, 2 * r1, rel_tol=1e-9)

def test_bisect_root_simple():
    """Ensure bisection finds the root of a simple function."""
    f = lambda x: x**2 - 4
    root = bisect_root(f, 0, 3)
    assert math.isclose(root, 2.0, rel_tol=1e-9)

def test_minimal_length_2d_channel():
    nodes = {
        'n1': Node(connection_no=2, multi_layer=False, coordinates=(0.0, 0, 1.0)),
        'n2': Node(connection_no=2, multi_layer=False, coordinates=(5.0, 0, 1.0)),
    }

    channel = Channel(nodes, node1='n1', node2='n2', flow_rate=1e-9, layer=0)
    length = calculate_minimal_length(channel, nodes, cfg.channel_dim)
    assert math.isclose(length, 5.0, rel_tol=1e-8), f"actual length {length}"

# channel_placement.py
def test_bounding_box_min_max():
    bb = BoundingBox((1, 1, 0), (3, 2, 0), (2, 5, 0), (0, 0, 0))
    assert bb.get_x_min() == 0
    assert bb.get_x_max() == 3
    assert bb.get_y_min() == 0
    assert bb.get_y_max() == 5

def test_bounding_box_from_vertical_channel():
    nodes = {"A": Node(coordinates=(0, 0, 0), multi_layer=False, connection_no=1), "B": Node(coordinates=(0, 10, 0), multi_layer=False, connection_no=1)}
    ch = Channel(nodes, flow_rate=0.0, node1="A", node2="B", width=1.0, layer=2)
    box = bounding_box_from_channel(nodes, ch)
    assert abs(box.get_x_max() - 0.5) < 1e-12
    assert abs(box.get_x_min() + 0.5) < 1e-12

def test_bounding_box_from_horizontal_channel():
    nodes = {"A": Node(coordinates=(0, 0, 0), multi_layer=False, connection_no=1), "B": Node(coordinates=(10, 0, 0), multi_layer=False, connection_no=1)}
    ch = Channel(nodes, flow_rate=0.0, node1="A", node2="B", width=1.0, layer=2)
    box = bounding_box_from_channel(nodes, ch)
    assert abs(box.get_y_max() - 0.5) < 1e-12
    assert abs(box.get_y_min() + 0.5) < 1e-12

def test_get_meander_length_with_blocking_box(): # testing non rerouted channel
    nodes = {"A": Node(coordinates=(0, 0, 0), multi_layer=False, connection_no=1), "B": Node(coordinates=(10, 0, 0), multi_layer=False, connection_no=1)}
    ch = Channel(nodes, flow_rate=0.0, node1="A", node2="B", layer=1)
    box = BoundingBox((5, -5, 0), (5, 5, 0), (6, -5, 0), (6, 5, 0), multi_layer=True)
    coord_start = nodes["A"].coordinates
    coord_end = nodes["B"].coordinates
    d_right, d_left = get_meander_length(nodes, ch, coord_start, coord_end, [box], 0.1, vertical=False)
    assert d_right < 5.0

