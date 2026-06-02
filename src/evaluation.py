# This script is to generate Simulation Test Files or Evaluate Channel Geometry

import math
from utils import calculate_hydraulic_resistance, calculate_hydraulic_resistance_cylinder
from channel_operations import get_layer_switch_resistance_correction

def get_layer_switch_length_correction(channel, nodes, channel_dim, viscosity):
    """
    Add the required theoretical length that would be needed to account for the layer switch resistance in the channel length.
    """
    resistance = 0.0
    extra_length = 0.0

    resistance = get_layer_switch_resistance_correction(channel, nodes, channel_dim, viscosity)
    # coord1 = nodes[channel.node1].coordinates
    # coord2 = nodes[channel.node2].coordinates
    # # if coord1[2] == 0.0 or coord2[2] == 0.0:
    # #     layer_switch_resistance_plate = calculate_hydraulic_resistance_cylinder(channel_dim["layer_switch_distance"], channel_dim["via_diameter"] / 2, viscosity)
    # #     resistance += layer_switch_resistance_plate
    # if nodes[channel.node1].multi_layer:
    #     layer_switch_resistance_plate = calculate_hydraulic_resistance_cylinder(channel_dim["layer_switch_distance"], channel_dim["via_diameter"] / 2, viscosity)
    #     resistance += layer_switch_resistance_plate

    if resistance > 0.0:
        extra_length = resistance / calculate_hydraulic_resistance(channel.width, channel.height, 1.0, viscosity)

        # # print(f"extra length for layer switch in channel between nodes {channel.node1} to {channel.node2}: {extra_length:.6g} m")
    return extra_length


def generate_simulation_test_file(filename, nodes, channels, channel_dim, viscosity, outlet_pump_flow_rate):
    """
    Generates a C++ test file that creates a microfluidic network based on the provided nodes and channels.
    The function does the following:
      - Maps node names to unique integer IDs.
      - Uses nodes with connection_no == 1 as pump (inlet/outlet) nodes.
      - Creates flow-rate pumps from each pump node to ground (node -1).
      - Writes out channels using sim.addChannel with parameters from each Channel object.
      - Marks the sink and ground as node -1.
      - Adds a couple of fluid definitions, sets the continuous phase, and simulation parameters.
    """
    inlet_channel_length = 0.5  # Length of inlet channels (from ground to pump nodes)
    
    # Build a node mapping: assign unique integer IDs for simulator input.
    # We'll assign IDs for all nodes in the order they appear in the dictionary.
    node_mapping = {}
    curr_id = 0
    for name in nodes.keys():
        node_mapping[name] = curr_id
        curr_id += 1

    # Determine pump nodes: these are nodes with connection_no == 1.
    pump_nodes = [name for name, node in nodes.items() if node.connection_no == 1 or "N_chip_media_inflow" in name]

    # pump_nodes = [name for name, node in nodes.items() if "_inflow" in name]

    # The last pump node in the list is the outlet.
    outlet_node = pump_nodes[-1] if pump_nodes else None

    # outlet_node = 

    # pump_flow_rate = outlet_pump_flow_rate  # approx -8.33333333333333e-11

    # Begin constructing the test case as a multiline string.
    # The code will create a droplet::Simulator sim, add pumps, channels,
    # define ground/sink (-1), fluids, and simulation settings.
    lines = []
    lines.append("TEST(GradientGenerator, GeneratedFromPythonNodesAndChannels) {")
    lines.append("    // Create the simulator")
    lines.append("    droplet::Simulator sim;")
    lines.append("")

    # Now add channels from the channels dictionary.
    # For each channel, we use: sim.addChannel( from, to, height, width, length );
    # We assume the Channel objects have attributes: node1, node2, height, width, length.
    for cid, channel in channels.items():
        from_node = node_mapping.get(channel.node1, "/*unknown*/")
        to_node = node_mapping.get(channel.node2, "/*unknown*/")
        # Format the floating point values (height, width, length) in scientific notation.
        height_str = f"{channel.height:.10g}"
        width_str = f"{channel.width:.10g}"
        # Add a correction factor for the layer switch distance
        layer_switch_distance_correction = get_layer_switch_length_correction(channel, nodes, channel_dim, viscosity=viscosity)
        length = channel.length + layer_switch_distance_correction
        
        
        #+ channel.calculate_minimal_length(nodes)
        length_str = f"{length:.10g}"
        lines.append(f"    auto {cid} = sim.addChannel({from_node}, {to_node}, {height_str}, {width_str}, {length_str});")
    lines.append("")

    # --- Add inlet channels ---
    # For each pump node that is not the outlet, add a channel from ground (-1) to that node.
    inlet_index = 1
    for pn in pump_nodes:
        if pn == outlet_node:
            continue
        nid = node_mapping[pn]
        lines.append(f"    auto inlet_{inlet_index} = sim.addChannel(-1, {nid}, 0.3, 0.5, {inlet_channel_length});  // from ground to '{pn}'")
        inlet_index += 1
    lines.append("")

    # --- Add outlet pump ---
    if outlet_node is not None:
        outlet_id = node_mapping[outlet_node]
        lines.append(f"    auto pump_outlet = sim.addFlowRatePump({outlet_id}, -1, {outlet_pump_flow_rate});  // from node '{outlet_node}'")
    lines.append("")

    # Define sink and ground as node -1.
    lines.append("    // Define the sink and ground node as -1")
    lines.append("    sim.addSink(-1);")
    lines.append("    sim.addGround(-1);")
    lines.append("")

    # Add fluids. (Here we add two example fluids; adjust if needed.)
    lines.append("    // Define fluids")
    lines.append(f"    auto fluid = sim.addFluid({viscosity}, 1.56e3, 1.0, 9e-10);")
    lines.append("")
    lines.append("    // Set continuous phase")
    lines.append("    sim.setContinuousPhase(fluid);")
    lines.append("")
    
    # Set simulation duration and result time step (hardcoded here; adjust as needed).
    lines.append("    sim.setSimulationDuration(85.0);")
    lines.append("    sim.setSimulationResultTimeStep(85.0);")
    lines.append("")
    # Check chip validity and simulate.
    lines.append("    sim.checkChipValidity();")
    lines.append("")
    lines.append("    auto result = sim.simulate();")
    lines.append("")
    # Write the result to a file.
    lines.append('    std::ofstream file("GeneratedTestOutput.json");')
    lines.append("    file << result.toJson(4);")
    lines.append("")
    lines.append("}")

    
    # Join all lines into a single string.
    test_code = "\n".join(lines)
    
    # Write the generated test case to the file.
    with open(filename, "w") as f:
        f.write(test_code)
    
    # print(f"Generated test file '{filename}' using {len(nodes)} nodes and {len(channels)} channels.")


def generate_simulation_test_file_sweep(filename, nodes, channels, channel_dim, viscosity, outlet_pump_flow_rate, height_variation, step_size):
    """
    Generates several C++ test files based on the provided nodes and channels. With varying heights.
    """
    inlet_channel_length = 0.5  # Length of inlet channels (from ground to pump nodes)
    lines = []

    no_of_files = int((height_variation * 2) / step_size) + 1
    for i in range(no_of_files):
        delta = -height_variation + i * step_size

        filename_add_on = f"{delta:+.10g}".replace("+", "p").replace("-", "m")

        test_name = f"GeneratedFromPythonNodesAndChannels_height{i}"
        json_name = filename.replace(".cpp", f"_{filename_add_on}.json")
        
        # Build a node mapping: assign unique integer IDs for simulator input.
        # We'll assign IDs for all nodes in the order they appear in the dictionary.
        node_mapping = {}
        curr_id = 0
        for name in nodes.keys():
            node_mapping[name] = curr_id
            curr_id += 1

        # Determine pump nodes: these are nodes with connection_no == 1.
        pump_nodes = [name for name, node in nodes.items() if node.connection_no == 1 or "N_chip_media_inflow" in name]
        # The last pump node in the list is the outlet.
        outlet_node = pump_nodes[-1] if pump_nodes else None

        # pump_flow_rate = outlet_pump_flow_rate  # approx -8.33333333333333e-11

        # Begin constructing the test case as a multiline string.
        # The code will create a droplet::Simulator sim, add pumps, channels,
        # define ground/sink (-1), fluids, and simulation settings.
        # lines = []
        lines.append(f"TEST(GradientGenerator, {test_name}) {{")
        lines.append("    // Create the simulator")
        lines.append("    droplet::Simulator sim;")
        lines.append("")

        # Now add channels from the channels dictionary.
        # For each channel, we use: sim.addChannel( from, to, height, width, length );
        # We assume the Channel objects have attributes: node1, node2, height, width, length.
        for cid, channel in channels.items():
            new_height = max(0.0, channel.height + delta)
            from_node = node_mapping.get(channel.node1, "/*unknown*/")
            to_node = node_mapping.get(channel.node2, "/*unknown*/")
            # Format the floating point values (height, width, length) in scientific notation.
            height_str = f"{new_height:.10g}"
            width_str = f"{channel.width:.10g}"
            layer_switch_distance_correction = get_layer_switch_length_correction(channel, nodes, channel_dim, viscosity=viscosity)
            length = channel.length + layer_switch_distance_correction
            length_str = f"{length:.10g}"
            lines.append(f"    auto {cid} = sim.addChannel({from_node}, {to_node}, {height_str}, {width_str}, {length_str});")
        lines.append("")

        # --- Add inlet channels ---
        # For each pump node that is not the outlet, add a channel from ground (-1) to that node.
        inlet_index = 1
        for pn in pump_nodes:
            if pn == outlet_node:
                continue
            nid = node_mapping[pn]
            lines.append(f"    auto inlet_{inlet_index} = sim.addChannel(-1, {nid}, 0.3, 0.5, {inlet_channel_length});  // from ground to '{pn}'")
            inlet_index += 1
        lines.append("")

        # --- Add outlet pump ---
        if outlet_node is not None:
            outlet_id = node_mapping[outlet_node]
            lines.append(f"    auto pump_outlet = sim.addFlowRatePump({outlet_id}, -1, {outlet_pump_flow_rate});  // from node '{outlet_node}'")
        lines.append("")

        # Define sink and ground as node -1.
        lines.append("    // Define the sink and ground node as -1")
        lines.append("    sim.addSink(-1);")
        lines.append("    sim.addGround(-1);")
        lines.append("")

        # Add fluids. (Here we add two example fluids; adjust if needed.)
        lines.append("    // Define fluids")
        lines.append(f"    auto fluid = sim.addFluid({viscosity}, 1.56e3, 1.0, 9e-10);")
        lines.append("")
        lines.append("    // Set continuous phase")
        lines.append("    sim.setContinuousPhase(fluid);")
        lines.append("")
        
        # Set simulation duration and result time step (hardcoded here; adjust as needed).
        lines.append("    sim.setSimulationDuration(85.0);")
        lines.append("    sim.setSimulationResultTimeStep(85.0);")
        lines.append("")
        # Check chip validity and simulate.
        lines.append("    sim.checkChipValidity();")
        lines.append("")
        lines.append("    auto result = sim.simulate();")
        lines.append("")
        # Write the result to a file.
        # lines.append('    std::ofstream file("GeneratedTestOutput.json");')
        lines.append(f"    std::ofstream file(\"{json_name}\");")
        lines.append("    file << result.toJson(4);")
        lines.append("")
        lines.append("}")

        
        # Join all lines into a single string.
        # test_code = "\n".join(lines)
        
        # Write the generated test case to the file.
        with open(filename, "w") as f:
            # f.write(test_code)
            f.write("\n".join(lines))
    
    # print(f"Generated test file '{filename}' using {len(nodes)} nodes and {len(channels)} channels.")