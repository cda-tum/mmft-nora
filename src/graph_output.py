import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D


from matplotlib.colors import to_rgb
from matplotlib.colors import LogNorm
import matplotlib as mpl
# from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import LogLocator, FormatStrFormatter

from .channel_operations import get_longest_segment

def plot_nodes(nodes):
    """
    Function to plot nodes based on their coordinates.
    """
    # Extract node names and their coordinates
    node_names = list(nodes.keys())
    node_coords = [node.coordinates for node in nodes.values()]

    # Separate x and y coordinates
    x_coords, y_coords, z_coords = zip(*node_coords)

    # Create the plot
    plt.figure(figsize=(10, 8))
    plt.scatter(x_coords, y_coords, s=50, color='blue', label="Nodes")

    # Annotate nodes with their names
    for name, (x, y, _) in zip(node_names, node_coords):
        plt.text(x, y, name, fontsize=6, ha='right', va='bottom', rotation=45)

    # Set axis labels and title
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.title("2D Node Layout")

    # # Flip the y-axis direction
    # plt.gca().invert_yaxis()

    # Show grid for better visualization
    plt.grid(True, linestyle="--", alpha=0.5)

    # Display the plot
    plt.show()

def combine_meanders_and_path_for_plotting(channel, coord_start, coord_end):
    channel_path_combination = []
    # Find the insertion index — right after coord_start
    insert_index = None
    for i in range(1, len(channel.rerouted_path)):
        if (channel.rerouted_path[i - 1] == coord_start and
            channel.rerouted_path[i] == coord_end) or \
        (channel.rerouted_path[i - 1] == coord_end and
            channel.rerouted_path[i] == coord_start):
            insert_index = i
            break

    if insert_index is not None:
        # Insert the meander nodes at the correct position
        channel_path_combination = (
            channel.rerouted_path[:insert_index] +
            channel.meander_nodes +
            channel.rerouted_path[insert_index:]
        )
    else:
        # Fallback: if no matching segment found, append at the end (safe default)
        # print("[WARNING] Could not match longest segment — appending meanders to the end.")
        channel_path_combination.extend(channel.meander_nodes)

    return channel_path_combination

def plot_network(nodes, channels, module_size_x, module_size_y, exclusion_zones, channel_dim, color_by_flow=True, chip_layout=None):
    """
    Plots nodes and channels based on their coordinates and their connection to the modules.
    Comment or uncomment the parts that label nodes and channels as needed.
    Color by flow: if True, color channels based on flow rate; if False, color based on layer.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    if chip_layout is not None:
        size_x = float(chip_layout.get("size_x", 0.0))
        size_y = float(chip_layout.get("size_y", 0.0))
        if size_x > 0 and size_y > 0:
            chip_rect = patches.Rectangle(
                (0, 0),
                size_x,
                size_y,
                fill=False,
                linewidth=2,
                edgecolor="black",
                zorder=0,
            )
            ax.add_patch(chip_rect)
    
    plt.rcParams.update({
        'font.size': 14,          # base font size
        'axes.titlesize': 16,     # title
        'axes.labelsize': 14,     # x/y labels
        'xtick.labelsize': 12,    # tick labels
        'ytick.labelsize': 12,
        'legend.fontsize': 10,
        'figure.titlesize': 18
    })


    layer_colors = {0: 'grey', 1: 'green', 2: 'orange'}
    multi_layer_node_color = 'red'  
    normal_node_color = 'blue' 

    # Normalize flow rates for better visualization
    min_flow = min(channel.flow_rate * 6e10 for channel in channels.values()) if channels else 1 # convert to ul/min
    max_flow = max(channel.flow_rate * 6e10 for channel in channels.values()) if channels else 1 # convert to ul/min
    # norm = plt.Normalize(min_flow, max_flow)
    norm = norm = LogNorm(vmin=min_flow, vmax=max_flow)
    # cmap = plt.cm.Greys_r  # reversed grayscale: higher flow = darker
    layer_rgbs = {layer: to_rgb(col) for layer, col in layer_colors.items()}

    layer_cmaps = {
        1: plt.cm.cool,    
        2: plt.cm.cool,    
        # you can add layer 0 or others too:
        # 0: plt.cm.Greys
    }

    # Scale the flow rate to a reasonable thickness range (between 1 and 6)
    def scale_flow(flow_rate):
        return 1 + 5 * (flow_rate - min_flow) / (max_flow - min_flow + 1e-12)

    # Plot channels (connections between nodes)
    for name, channel in channels.items():
        coord1 = nodes[channel.node1].coordinates
        coord2 = nodes[channel.node2].coordinates

        # Use lefter/upper node as start_coord
        if abs(coord1[0] - coord2[0]) < 1e-6:  # Vertical
            start_coord = coord1 if coord1[1] < coord2[1] else coord2
            end_coord = coord2 if start_coord is coord1 else coord1
        else:  # Horizontal or general
            start_coord = coord1 if coord1[0] < coord2[0] else coord2
            end_coord = coord2 if start_coord is coord1 else coord1

        channel_layer = int(channel.layer) # TODO this is hardcoded, see also layer_colors
        color = layer_colors.get(channel_layer, 'black') 

        # linewidth = scale_flow(channel.flow_rate)
        linewidth = channel.width * 3e3
        # linewidth = 2
        flow = channel.flow_rate * 6e10 # convert to ul/min
        channel_layer = int(channel.layer)
        base_rgb = layer_rgbs.get(channel_layer, (0,0,0))
        t = norm(flow)
        # color = tuple((1 - t) + t * c for c in base_rgb)

        # cmap_layer  = layer_cmaps.get(channel_layer, plt.cm.Greys)
        # color       = cmap_layer(norm(flow))

        if color_by_flow:
            # FLOW-BASED COLORING
            flow = channel.flow_rate * 6e10  # µL/min
            t = norm(flow)
            cmap_layer = layer_cmaps.get(channel_layer, plt.cm.Greys)
            color = cmap_layer(t)

        else:
            # LAYER-BASED COLORING (constant color)
            color = layer_colors.get(channel_layer, 'black')

        # ax.plot(x_vals, y_vals, color=color, linewidth=linewidth, zorder=1, label=f"Layer {channel_layer}" if f"Layer {channel_layer}" not in ax.get_legend_handles_labels()[1] else "")
        if hasattr(channel, "rerouted_path") and channel.rerouted_path:
            longest_segment, start_coord, end_coord, path_int_start, path_int_end = get_longest_segment(channel, nodes, channel_dim)
            path_coords = combine_meanders_and_path_for_plotting(channel, start_coord, end_coord)
        elif hasattr(channel, "meander_nodes") and channel.meander_nodes:
            path_coords = [start_coord] + channel.meander_nodes + [end_coord]
        else:
            path_coords = [start_coord, end_coord]

        # Plot the full path in segments
        for i in range(len(path_coords) - 1):
            x_pair = [path_coords[i][0], path_coords[i + 1][0]]
            y_pair = [path_coords[i][1], path_coords[i + 1][1]]
            ax.plot(x_pair, y_pair, color=color, linewidth=linewidth, zorder=1)

        # # Add meander nodes as small black dots to the plot
        # for channel in channels.values():
        #     if hasattr(channel, "meander_nodes") and channel.meander_nodes:
        #         x_vals = [coord[0] for coord in channel.meander_nodes]
        #         y_vals = [coord[1] for coord in channel.meander_nodes]
        #         ax.scatter(x_vals, y_vals, s=5, c='black', zorder=2)

        # # Label channels at their midpoint
        # mid_x = (start_coord[0] + end_coord[0]) / 2
        # mid_y = (start_coord[1] + end_coord[1]) / 2
        # ax.text(mid_x, mid_y, name, fontsize=6, ha='center', va='center', rotation=0)

        # # Label channels with their flow rate at their midpoint
        # mid_x = (start_coord[0] + end_coord[0]) / 2
        # mid_y = (end_coord[1] + end_coord[1]) / 2
        # ax.text(mid_x, mid_y, channel.flow_rate, fontsize=6, ha='center', va='center', rotation=0)

    # # Extract node names and their coordinates
    # node_names = list(nodes.keys())
    # node_coords = [node.coordinates for node in nodes.values()]
    # # Annotate nodes with their names
    # for name, (x, y, _) in zip(node_names, node_coords):
    #     plt.text(x, y, name, fontsize=6, ha='right', va='bottom', rotation=45)

    x_coords = [node.coordinates[0] for node in nodes.values()]
    y_coords = [node.coordinates[1] for node in nodes.values()]
    node_colors = [multi_layer_node_color if node.multi_layer else normal_node_color for node in nodes.values()]

    ax.scatter(x_coords, y_coords, s=10, c=node_colors, zorder=3)  # Small dots with color differentiation

    # Create legend entries for nodes
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=normal_node_color, markersize=6, label="Nodes"),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=multi_layer_node_color, markersize=6, label="Multi-layer Nodes")
    ]
    # Add legend entries for channel layers
    layer_legend_elements = [
        Line2D([0], [0], color=color, linewidth=2, label=f"Layer {layer}") for layer, color in layer_colors.items()
    ]

    for node_name, node in nodes.items():
        # add patches for the organ modules
        if "_nw" in node_name:  # Look for north-west nodes of modules
            module_prefix = node_name.split("_nw")[0]
            # Check if the module has all required corner nodes
            if (f"{module_prefix}_ne" in nodes and 
                f"{module_prefix}_sw" in nodes and 
                f"{module_prefix}_se" in nodes):
                
                nw_coords = nodes[f"{module_prefix}_nw"].coordinates
                # Add a transparent rectangle
                rect = patches.Rectangle(
                    (nw_coords[0], nw_coords[1]),  # Bottom-left corner
                    module_size_x,                # Width
                    module_size_y,                # Height
                    linewidth=1, edgecolor='gray', facecolor='gray', alpha=0.2
                )
                ax.add_patch(rect)
        # Add patches for the mixing modules 
        if node_name.startswith("N_mix_media_x_connect"):
            mix_coords = nodes[node_name].coordinates  # already the top-left corner

            # Define size for the mixing module (10mm x 3mm)
            mixing_width = 7.03e-3 # TODO
            mixing_height = -2.4e-3

            # Add a pink rectangle for the mixing module
            rect = patches.Rectangle(
                (mix_coords[0], mix_coords[1]),  # Bottom-left corner
                mixing_width,
                mixing_height,
                linewidth=1,
                edgecolor='green',
                facecolor='green',
                alpha=0.5,
                zorder=0
            )
            ax.add_patch(rect)
        elif node_name.startswith("N_mix_media_y_connect"):
            mix_coords = nodes[node_name].coordinates  # already the top-left corner

            # Define size for the mixing module (10mm x 3mm)
            mixing_width = 2.4e-3
            mixing_height = 10e-3
            # Add a pink rectangle for the mixing module
            rect = patches.Rectangle(
                (mix_coords[0], mix_coords[1]),  # Bottom-left corner
                mixing_width,
                mixing_height,
                linewidth=1,
                edgecolor='green',
                facecolor='green',
                alpha=0.5,
                zorder=0
            )
            ax.add_patch(rect)
        # 1to1 mixing
        elif node_name.startswith("N_mix_") and not node_name.startswith("N_mix_media_"):
            module_prefix = node_name.replace("N_mix_", "")
            mix_coords = nodes[node_name].coordinates  # already the top-left corner

            # Define size for the mixing module (10mm x 3mm)
            mixing_width = 10e-3
            mixing_height = 3e-3

            # Add a pink rectangle for the mixing module
            rect = patches.Rectangle(
                (mix_coords[0], mix_coords[1]),  # Bottom-left corner
                mixing_width,
                mixing_height,
                linewidth=1,
                edgecolor='green',
                facecolor='green',
                alpha=0.5,
                zorder=0
            )
            ax.add_patch(rect)

    for zone in exclusion_zones.values():
        # Add a transparent rectangle for the exclusion zone
        rect = patches.Rectangle(
            (zone.get_x_min(), zone.get_y_min()),  # Bottom-left corner
            zone.x_width,
            zone.y_length,
            linewidth=1, edgecolor='red', facecolor='red', alpha=0.3
        )
        ax.add_patch(rect)

    # Set axis labels and title
    plt.xlabel("Chip dimension X [m]", fontsize=14)
    plt.ylabel("Chip dimension Y [m]", fontsize=14)
    plt.title("2D Network Layout")

    # # Flip the y-axis direction
    # plt.gca().invert_yaxis()

    # Show grid for better visualization
    plt.grid(True, linestyle="--", alpha=0.5)

    # Display legend
    ax.legend(handles=legend_elements,
        loc='upper left')

    if color_by_flow:
        # for i, (layer, cmap) in enumerate(layer_cmaps.items()):
        sm = mpl.cm.ScalarMappable(norm=norm, cmap=layer_cmaps[1])
        sm.set_array([])  # dummy data for the colorbar
        
        # position each bar so they don’t overlap
        cbar = plt.colorbar(
            sm, 
            ax=ax, 
            orientation='horizontal', 
            pad=0.1, 
            fraction=0.03
        )
        cbar.set_label(f'Flow rate [µL/min]')

        cbar.locator = LogLocator(
            base=10.0,        # decade base
            subs=(1.0, 2.0, 5.0),  # include 1, 2, and 5 × 10^n
            numticks=10
        )
        cbar.formatter = FormatStrFormatter('%.2f')
        cbar.update_ticks()

    ax.set_aspect('equal', adjustable='box')

    plt.grid(False)
    # Return figure instead of showing
    return fig

def plot_pressure_network(nodes, channels, module_size_x, module_size_y, viscosity):
    """
    Plots nodes and channels based on their coordinates and their connection to the modules.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    layer_colors = {0: 'blue', 1: 'green', 2: 'orange'}
    multi_layer_node_color = 'red'  
    normal_node_color = 'blue' 

    # Plot channels (connections between nodes)
    for name, channel in channels.items():
        node1 = nodes[channel.node1]
        node2 = nodes[channel.node2]

        node1_coords = nodes[channel.node1].coordinates
        node2_coords = nodes[channel.node2].coordinates

        x_vals = [node1_coords[0], node2_coords[0]]
        y_vals = [node1_coords[1], node2_coords[1]]

        channel_layer = max(node1.coordinates[2], node2.coordinates[2])

        color = layer_colors.get(channel_layer, 'black') 

        # linewidth = scale_flow(channel.flow_rate)
        linewidth = 2

        ax.plot(x_vals, y_vals, color=color, linewidth=linewidth, zorder=1, label=f"Layer {channel_layer}" if f"Layer {channel_layer}" not in ax.get_legend_handles_labels()[1] else "")

        # get the pressure drop for each channel
        pressure = channel.calculate_pressure_drop(nodes, viscosity)

        # Format the pressure to 4 decimal places
        pressure_formatted = f"{pressure:.4f}"

        # Label channels at their midpoint
        mid_x = (node1_coords[0] + node2_coords[0]) / 2
        mid_y = (node1_coords[1] + node2_coords[1]) / 2
        ax.text(mid_x, mid_y, pressure_formatted, fontsize=6, ha='center', va='center', rotation=0)

    x_coords = [node.coordinates[0] for node in nodes.values()]
    y_coords = [node.coordinates[1] for node in nodes.values()]
    node_colors = [multi_layer_node_color if node.multi_layer else normal_node_color for node in nodes.values()]

    ax.scatter(x_coords, y_coords, s=10, c=node_colors, zorder=3)  # Small dots with color differentiation

    # Create legend entries for nodes
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=normal_node_color, markersize=6, label="Nodes"),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=multi_layer_node_color, markersize=6, label="Multi-layer Nodes")
    ]

    for node_name, node in nodes.items():
        if "_nw" in node_name:  # Look for north-west nodes of modules
            module_prefix = node_name.split("_nw")[0]
            # Check if the module has all required corner nodes
            if (f"{module_prefix}_ne" in nodes and 
                f"{module_prefix}_sw" in nodes and 
                f"{module_prefix}_se" in nodes):
                
                nw_coords = nodes[f"{module_prefix}_nw"].coordinates
                # Add a transparent rectangle
                rect = patches.Rectangle(
                    (nw_coords[0], nw_coords[1]),  # Bottom-left corner
                    module_size_x,                # Width
                    module_size_y,                # Height
                    linewidth=1, edgecolor='gray', facecolor='gray', alpha=0.2
                )
                ax.add_patch(rect)

    # Set axis labels and title
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.title("2D Network Layout")

    # Flip the y-axis direction
    plt.gca().invert_yaxis()

    # Show grid for better visualization
    plt.grid(True, linestyle="--", alpha=0.5)

    # Display legend
    ax.legend(handles=legend_elements)

    # Display the plot
    plt.show()


def plot_pressure_nodes(nodes, channels):
    """
    Plots the network with nodes colored based on pressure values and 
    channels as thin black lines.
    
    Args:
        nodes (dict): Dictionary of node objects.
        channels (dict): Dictionary of channel objects.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Extract pressures to normalize colors
    pressures = [node.pressure for node in nodes.values() if node.pressure is not None]
    min_pressure = min(pressures) if pressures else 0
    max_pressure = max(pressures) if pressures else 1

    # Normalize pressure for color mapping
    def normalize_pressure(p):
        return (p - min_pressure) / (max_pressure - min_pressure) if max_pressure != min_pressure else 0.5

    # Plot channels (as thin black lines)
    for channel in channels.values():
        node1_coords = nodes[channel.node1].coordinates
        node2_coords = nodes[channel.node2].coordinates

        x_vals = [node1_coords[0], node2_coords[0]]
        y_vals = [node1_coords[1], node2_coords[1]]

        ax.plot(x_vals, y_vals, color='black', linewidth=0.5, zorder=1)  # Thin black lines

    # Plot nodes with pressure-based color mapping
    x_coords = [node.coordinates[0] for node in nodes.values()]
    y_coords = [node.coordinates[1] for node in nodes.values()]
    node_colors = [plt.cm.viridis(normalize_pressure(node.pressure)) for node in nodes.values()]

    sc = ax.scatter(x_coords, y_coords, c=node_colors, s=50, cmap='viridis', edgecolors='black', zorder=2)

    # Annotate nodes with pressure values
    for node_name, node in nodes.items():
        ax.text(node.coordinates[0], node.coordinates[1], f"{node.pressure:.2f}", 
                fontsize=6, ha='right', va='bottom', rotation=45)

    # Colorbar for pressure values
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Pressure (Pa)")

    # Set axis labels and title
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.title("2D Node Pressure Distribution")

    # Flip the y-axis direction for better visualization
    plt.gca().invert_yaxis()

    # Show grid for reference
    plt.grid(True, linestyle="--", alpha=0.5)

    # Display the plot
    plt.show()
