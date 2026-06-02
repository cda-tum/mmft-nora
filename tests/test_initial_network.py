# Define a small network and test functions within
import math
import pytest

from src.initialization import initialize_nodes, initialize_channels
from src.channel_operations import calculate_minimal_length
from src.config import Config

cfg = Config()

param_combinations = [(1,1),(2,1),(1,2),(2,2),(3,1),(1,3),(3,3)] # number of modules in x and y direction

@pytest.fixture(params=param_combinations)
def initial_guess_network(request):
    """Return the initialized nodes and channels for a given network size."""
    nx, ny = request.param
    cfg = Config()
    cfg.no_of_modules_x = nx
    cfg.no_of_modules_y = ny

    nodes = {}
    channels = {}

    spacing_x, spacing_y, spacing_out = cfg.spacing_x, cfg.spacing_y, cfg.spacing_out
    initialize_nodes(nodes, cfg, cfg.layer_0, cfg.layer_1, cfg.layer_2, spacing_x, spacing_y, spacing_out)
    initialize_channels(nodes, channels, cfg)

    return nodes, channels, cfg

def test_minimal_lengths(initial_guess_network):
    nodes, channels, cfg = initial_guess_network
    for ch in channels.values():
        min_len = calculate_minimal_length(ch, nodes, cfg.channel_dim)
        assert min_len > 0


def test_mass_conservation_initial_guess_network(initial_guess_network):
    nodes, channels, cfg = initial_guess_network

    for node_id, node in nodes.items():
        if node.connection_no == 1:  # inflow/outflow nodes
            continue
        Q_in, Q_out = 0.0, 0.0
        for ch in channels.values():
            if ch.node2 == node_id:  # inflow
                Q_in += ch.flow_rate
            if ch.node1 == node_id:  # outflow
                Q_out += ch.flow_rate
        # Check that inflows and outflows are balanced for each node
        assert abs(Q_in - Q_out) < 1e-12, f"Mass conservation failed at node {node_id}: Q_in={Q_in}, Q_out={Q_out}"
