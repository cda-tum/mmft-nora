# Define channels for non-linear Gradient Generator for barrier OoCs
import matplotlib.pyplot as plt

from initialization import initialize_nodes, initialize_channels, initialize_exclusion_zones, get_organ_module_flow_rate_bottom, get_total_chip_flow_rate_out
from channel_operations import calculate_minimal_length, assign_initial_lengths, update_length, adapt_width, limit_width, sort_channels_by_required_length_increase, calculate_pressure_drop
from modified_nodal_analysis import iterative_nodal_analysis
from rerouting import reroute_channel, is_in_exclusion, check_overlap
from channel_meanders import initialize_bounding_boxes, define_meander, assign_extra_length_to_connected_channel
from graph_output import plot_nodes, plot_network, plot_pressure_network #, plot_network_3d
from export import export_to_dxf
from evaluation import generate_simulation_test_file, generate_simulation_test_file_sweep

from config import Config

cfg = Config() # TODO maybe move the class definitions to Config 
eps = cfg.eps

def increase_spacing(channel, channel_name, channel_dim, required_spacing_increase, spacing_x, spacing_y, spacing_out):
    """
    Increase the spacing between the modules to make sure all meanders fit.
    """
    if channel.vertical:
        # Either increase spacing_y or spacing_out
        spacing_out += required_spacing_increase # (channel.width + channel_dim["min_distance"]) * 2
        spacing_y += required_spacing_increase #(channel.width + channel_dim["min_distance"]) * 2
    else:
        spacing_x += required_spacing_increase #(channel.width + channel_dim["min_distance"]) * 2

    return spacing_x, spacing_y, spacing_out

def refresh_saved_connection_no(nodes, channels):
    for n in nodes.values(): 
        n.connection_no = 0
    for ch in channels.values():
        nodes[ch.node1].connection_no += 1
        nodes[ch.node2].connection_no += 1

        
    
def main(cfg):
    channels  = {}
    nodes = {}
    exclusion_zones = {} # TODO figure out where to move this

    spacing_x, spacing_y, spacing_out = (cfg.spacing_x, cfg.spacing_y, cfg.spacing_out)
    need_restart = True

    while need_restart:
        need_restart = False

        channels.clear()
        nodes.clear()
        exclusion_zones.clear()
        
        # DEFINE THE NODES, CHANNEL FLOWRATES AND LENGTHS
        initialize_nodes(nodes, cfg, cfg.layer_0, cfg.layer_1, cfg.layer_2, spacing_x, spacing_y, spacing_out)
        initialize_channels(nodes, channels, cfg)
        
        # print("Spacing_x:", spacing_x)

        initialize_exclusion_zones(exclusion_zones, nodes, spacing_x, spacing_y, spacing_out, cfg) # moved up to make sure I can use the bounding boxes for rerouting (unfortunately they no longer consider the channel width! # TODO)
        # Add the bounding boxes for straight channels to make sure the rerouted channel do not overlap with existing channels
        # Check if a bounding box overlaps with a node, if so raise an error or increase the spacing
        for node in nodes.values():
            point = node.coordinates[:2]
            if is_in_exclusion(point, exclusion_zones):
                # print(f"Node at {node.coordinates} is inside an exclusion zone. Increasing spacing...")
                # raise ValueError(f"Node at {node.coordinates} is inside an exclusion zone. Please increase the spacing or change the exclusion zones.")
                spacing_x *= 1.2
                spacing_y *= 1.2
                need_restart = True
                break

        if need_restart:
            continue

        for exclusion_zone in exclusion_zones.values():
            for channel in channels.values():
                requires_rerouting = check_overlap(exclusion_zone, channel, nodes)
                if requires_rerouting:
                    reroute_channel(channel, nodes, exclusion_zones, cfg.grid_resolution)
                    # need_restart = True # this currently results in an endless loop
        # if need_restart:
        #     break

        assign_initial_lengths(nodes, channels, cfg.channel_dim)
        refresh_saved_connection_no(nodes, channels)

        # CALCULATE THE TOTAL FLOW RATE & PRESSURE AT THE OUTLET
        flow_rate_out = get_total_chip_flow_rate_out(cfg)

        if cfg.no_of_modules_x * cfg.no_of_modules_y > 1:

            pressures, iterations = iterative_nodal_analysis(nodes, channels, cfg.viscosity, flow_rate_out, cfg.no_of_modules_x, cfg.no_of_modules_y, cfg.channel_dim)

            # Assign computed pressures to nodes
            for node_name, pressure in pressures.items():
                nodes[node_name].pressure = pressure

            for channel in channels.values():
                update_length(channel, nodes, cfg.viscosity, cfg.channel_dim)
                minimal_length = calculate_minimal_length(channel, nodes, cfg.channel_dim)
                required_extra_length = channel.length - minimal_length
                # if required_extra_length < 0.0 + eps: TODO
                #     # set the length to the minimal length and adapt the width instead
                #     resistance_target = channel.calculate_hydraulic_resistance(cfg.viscosity)
                # TODO here is a problem if the geometry of channels with fixed resistance is supposed to be updated - maybe add a check
                if (0.0 + eps) < required_extra_length < (channel.width * 2) and channel.fixed_resistance is None: # TODO add some tolerance to minimal length
                    # Adjust the channel geometry if it cannot be placed because the required extra length is shorter than the smalles possible meander.
                    adapt_width(channel, minimal_length, cfg.channel_dim, cfg.viscosity)
                if channel.width > cfg.channel_dim["max_width"] and channel.fixed_resistance is None: # the fixed channels are not adapted
                    limit_width(channel, cfg.channel_dim, cfg.viscosity)

        bounding_boxes = []
        bounding_boxes = initialize_bounding_boxes(nodes, channels, exclusion_zones, cfg.mixing_module, cfg.chip_layout)

        sorted_channels = sort_channels_by_required_length_increase(channels, nodes, cfg.channel_dim)

        # for channel_name, channel in channels.items():
        for channel_name, channel, _ in sorted_channels:
            if channel.fixed_resistance is None: # the fixed channels are not adapted 
                    channel.meander_nodes, required_spacing_increase, leftover_length = define_meander(channel, nodes, cfg.channel_dim, bounding_boxes)
                    
                    if required_spacing_increase > 0 + eps:
                        # check if the length of the channel can be covered by a connected channel (for this use case specifically the channel connecting N_{module}_sw N_{module}_out_sw)
                        required_spacing_increase_leftover, connected_channel = assign_extra_length_to_connected_channel(nodes, channels, channel.node1, channel.node2, channel, required_spacing_increase, leftover_length, bounding_boxes, cfg.viscosity, cfg.channel_dim)
                        if required_spacing_increase_leftover > 0 + eps:
                            spacing_x, spacing_y, spacing_out = increase_spacing(channel, channel_name, cfg.channel_dim, required_spacing_increase, spacing_x, spacing_y, spacing_out)
                            need_restart = True
                            break
                        else:
                            # add the info to the channel for testing that the meander length was transferred successfully to the connected channel
                            print(f"The required spacing increase of {required_spacing_increase} for channel {channel_name} was successfully transferred to the connected channel {connected_channel.node1} - {connected_channel.node2}")
                            channel.transfered_length = True
                            connected_channel.transfered_length = True
                            pass
                            # print("The meander length was transferred successfully from channel", channel_name)
                        # spacing_x, spacing_y, spacing_out = increase_spacing(channel, channel_name, cfg.channel_dim, required_spacing_increase, spacing_x, spacing_y, spacing_out)
                        # need_restart = True  # Restart the main function to reinitialize nodes and channels with the new spacing
                        # break
    
    # Export DXF and plot
    export_result = None

    if hasattr(cfg, 'output_dxf_path') and cfg.output_dxf_path:
        # Backend mode: save files
        print(f"Backend mode: saving DXF to {cfg.output_dxf_path}")

        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        export_result = export_to_dxf(nodes, channels, cfg.channel_dim, output_path=cfg.output_dxf_path)
        print(f"export_to_dxf completed, now generating preview")
        fig = plot_network(nodes, channels, cfg.organ_module["size_x"], cfg.organ_module["size_y"], exclusion_zones, cfg.channel_dim)
        fig.savefig(cfg.output_preview_path, dpi=150, bbox_inches='tight')
        print(f"Preview saved to {cfg.output_preview_path}")
        plt.close(fig)
    else:
        # Interactive mode: show plot
        export_result = export_to_dxf(nodes, channels, cfg.channel_dim)
        # fig = plot_network(nodes, channels, cfg.organ_module["size_x"], cfg.organ_module["size_y"], exclusion_zones, cfg.channel_dim)
        # import matplotlib.pyplot as plt
        # plt.show()
        
    
    return nodes, channels, exclusion_zones, export_result

                
if __name__ == "__main__":
    cfg = Config()
    nodes, channels, exclusion_zones, export_result = main(cfg)

    # Generate a 1D simulation file for the mmft-modular-1D-simulator, an abstract simulation tool for microfluidic channel networks
    # generate_simulation_test_file("GeneratedTest.cpp", nodes, channels, outlet_pump_flow_rate=(cfg.no_of_modules_x * cfg.no_of_modules_y * cfg.organ_module["flow_rate"] * 2), viscosity=cfg.viscosity)
    flow_rate_out = get_total_chip_flow_rate_out(cfg)
    generate_simulation_test_file_sweep("GeneratedTest.cpp", nodes, channels, cfg.channel_dim, viscosity=cfg.viscosity, outlet_pump_flow_rate=flow_rate_out, height_variation=25e-6, step_size=5e-6)

    # for channel_name, channel_obj in channels.items():
    #     if channel_obj.rerouted:
    #         # print(f"channel was rerouted: {channel_name}, minimal_length: {calculate_minimal_length(channel_obj, nodes, cfg)}, computed_length: {channel_obj.length}, meander_nodes: {channel_obj.meander_nodes}, channel_vertices: {channel_obj.vertices}")

    # for channel_name, channel_obj in channels.items():
    #     # print(f"{channel_name}, Flow Rate: {channel_obj.flow_rate}, Minimal Channel Length: {calculate_minimal_length(channel_obj, nodes, cfg.channel_dim)}, Computed Channel Length: {channel_obj.length}, Actual Length: {channel_obj.final_length}, Channel Width: {channel_obj.width}, {channel_obj.height},Pressure Drop: {calculate_pressure_drop(channel_obj, nodes, cfg.viscosity)}")

    # for node_name, node_obj in nodes.items():
    #     print(f"{node_name}, Connection No: {node_obj.connection_no}, Pressure: {node_obj.pressure}")

    fig =plot_network(nodes, channels, cfg.organ_module["size_x"], cfg.organ_module["size_y"], exclusion_zones, cfg.channel_dim)
    plt.show()