from shapely.geometry import Polygon

from src.export import add_rerouted_segments
from src.mf_geometry_components import Channel, Node


def test_rerouted_segment_uses_actual_path_direction_at_node():
    nodes = {
        "n1": Node(connection_no=1, multi_layer=False, coordinates=(0.0, 0.0, 0.0)),
        "n2": Node(connection_no=1, multi_layer=False, coordinates=(0.0, 1.0, 0.0)),
    }
    nodes["n1"].quad_vertices = [
        [-0.1, 0.5, 0.0],
        [0.1, 0.5, 0.0],
        [0.1, -0.5, 0.0],
        [-0.1, -0.5, 0.0],
    ]
    nodes["n2"].quad_vertices = [
        [-0.1, 1.5, 0.0],
        [0.1, 1.5, 0.0],
        [0.1, 0.5, 0.0],
        [-0.1, 0.5, 0.0],
    ]

    channel = Channel(nodes, node1="n1", node2="n2", flow_rate=1.0, layer=2, width=0.2, height=0.1)
    channel.rerouted_path = [
        nodes["n1"].coordinates,
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        nodes["n2"].coordinates,
    ]

    segments = []
    add_rerouted_segments(channel, nodes, segments, arcs=[])

    assert segments
    for segment in segments:
        polygon = Polygon([(x, y) for x, y, _ in segment[:-2]])
        assert polygon.is_valid
