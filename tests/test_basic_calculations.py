# tests/test_basic_calculations.py
import math
import pytest

from src.utils import calculate_hydraulic_resistance, bisect_root
from src.channel_operations import calculate_minimal_length, limit_width
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

def _channel_with_target_resistance(channel_dim, target_resistance, viscosity=1.0, length=1.0):
    nodes = {
        'n1': Node(connection_no=1, multi_layer=False, coordinates=(0.0, 0.0, 0.0)),
        'n2': Node(connection_no=1, multi_layer=False, coordinates=(1.0, 0.0, 0.0)),
    }
    f_width = lambda width: calculate_hydraulic_resistance(width, channel_dim["height"], length, viscosity) - target_resistance
    width = bisect_root(f_width, channel_dim["max_width"], 1000.0)
    channel = Channel(nodes, node1='n1', node2='n2', flow_rate=1.0, layer=0, width=width, height=channel_dim["height"])
    channel.length = length
    return channel

def test_limit_width_tries_max_height_when_step_overshoots():
    viscosity = 1.0
    channel_dim = {"width": 1.0, "height": 1.0, "max_width": 4.0, "max_height": 1.5}
    target_resistance = calculate_hydraulic_resistance(
        channel_dim["max_width"],
        channel_dim["max_height"],
        length=1.0,
        viscosity=viscosity,
    )
    channel = _channel_with_target_resistance(channel_dim, target_resistance, viscosity=viscosity)

    limit_width(channel, channel_dim, viscosity)

    assert math.isclose(channel.height, channel_dim["max_height"], rel_tol=0.0, abs_tol=1e-12)
    assert channel.width <= channel_dim["max_width"] + 1e-9
    assert math.isclose(
        calculate_hydraulic_resistance(channel.width, channel.height, channel.length, viscosity),
        target_resistance,
        rel_tol=1e-9,
    )

def test_limit_width_raises_when_no_height_can_match_target():
    viscosity = 1.0
    channel_dim = {"width": 1.0, "height": 1.0, "max_width": 4.0, "max_height": 1.5}
    simplified_resistance_at_max = (
        12 * viscosity / (channel_dim["max_width"] * channel_dim["max_height"]**3)
    )
    actual_resistance_at_max = calculate_hydraulic_resistance(
        channel_dim["max_width"],
        channel_dim["max_height"],
        length=1.0,
        viscosity=viscosity,
    )
    target_resistance = (simplified_resistance_at_max + actual_resistance_at_max) / 2
    channel = _channel_with_target_resistance(channel_dim, target_resistance, viscosity=viscosity)

    with pytest.raises(ValueError, match="maximum height"):
        limit_width(channel, channel_dim, viscosity)

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
