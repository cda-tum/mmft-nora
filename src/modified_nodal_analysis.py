import numpy as np
# import csv # TODO maybe remove this once we no longer analyze via a csv file

from .channel_operations import calculate_minimal_length

eps = 1e-12

def conduct_nodal_analysis(nodes, channels, viscosity, pressure_out, pressure_matching_pairs):
# def conduct_nodal_analysis(nodes, channels, viscosity, pressure_out, pressure_medium_in, pressure_conc_x_in, pressure_conc_y_in, pressure_medium_2_in):
    """
    Performs Modified Nodal Analysis (MNA) to solve for pressures at each node.
    """
    # Step 1: Identify node indices
    node_names = list(nodes.keys())
    node_index = {name: i for i, name in enumerate(node_names)}
    num_nodes = len(nodes)

    # Step 2: Initialize MNA Matrices
    A = np.zeros((num_nodes, num_nodes))  # Conductance matrix
    B = np.zeros(num_nodes)  # Flow source vector

    # Step 3: Populate Conductance Matrix and Source Vector
    for channel_name, channel in channels.items():
        n1 = channel.node1
        n2 = channel.node2
        idx1, idx2 = node_index[n1], node_index[n2]
        
        # Compute hydraulic resistance
        R_h = channel.calculate_hydraulic_resistance(nodes, viscosity)
        if R_h == 0:
            print(f"Warning: Channel {channel_name} has zero resistance!")    
        
        # Populate conductance matrix (analogous to admittance in electrical circuits)
        A[idx1, idx1] += 1 / R_h
        A[idx2, idx2] += 1 / R_h
        A[idx1, idx2] -= 1 / R_h
        A[idx2, idx1] -= 1 / R_h

        # # Apply known flow rate constraints (treat predefined flow as a source term)
        # if channel.flow_rate is not None:
        #     B[idx1] -= channel.flow_rate
        #     B[idx2] += channel.flow_rate
        #     # print(f"Injected flow for channel {channel_name}:; {channel.flow_rate}; (B[{n1}]; -; {channel.flow_rate}; B[{n2}]; +; {channel.flow_rate})")

    # Step 4: Fix reference nodes (Ground Node)
    # Nodes (num_nodes-5) to (num_nodes-2) are inlet nodes fixed at 0
    # Node (num_nodes-1) is the outlet node fixed at pressure_out.
    for i in range(num_nodes - 5, num_nodes - 1):
        A[i, :] = 0
        A[i, i] = 1
        B[i] = 0
    A[num_nodes - 1, :] = 0
    A[num_nodes - 1, num_nodes - 1] = 1
    B[num_nodes - 1] = pressure_out

    # Step 5: Solve for Pressures (Ax = B -> P = A^-1 B)
    # pressures = np.linalg.solve(A, B)
    pressures = solve_with_additional_pressure_constraints(A, B, pressure_matching_pairs, nodes)

    # Step 6: Assign computed pressures to nodes
    pressure_results = {node_names[i]: pressures[i] for i in range(num_nodes)}

    return pressure_results

def define_extra_pressure_constraints(no_of_modules_x, no_of_modules_y):
    """
    Define Nodes that should have the same absolute pressure. 
    Use case specific for two compartment Organ-on-Chip modules
    """
    pressure_matching_pairs = [] # TODO maybe import these from config
    for i in range(no_of_modules_x):
        for j in range(no_of_modules_y):
            module = f"{chr(65 + i)}{j}"

            node_nw = f"N_{module}_nw"
            node_ne = f"N_{module}_ne"

            pressure_matching_pairs.append([node_nw, node_ne])

    return pressure_matching_pairs


def solve_with_additional_pressure_constraints(A, B, pressure_matching_pairs, nodes): 
    # TODO this is use case specific for the organ module so maybe move this to a better place? define it in config and then import additional constraints?
    """
    To prevent pressure differences and subsequently flow across or deformation of the membrane separating the compartments in the organ module seperated by a membrane, 
    the absolute pressure at each point in the compartment on either side needs to be the same. 
    This constraint is an additional requirement to the already defined flow rates and compartment geometry.
    """
    m = len(pressure_matching_pairs)
    if m == 0:
        return np.linalg.solve(A, B)
    
    node_names = list(nodes.keys())
    node_index = {name: i for i, name in enumerate(node_names)}
    
    C = np.zeros((m, A.shape[0]))
    for r, (ni, nj) in enumerate(pressure_matching_pairs): # why use r and fix node_index
        C[r, node_index[ni]] = 1.0
        C[r, node_index[nj]] = -1.0
        # C[r, ni] = 1.0
        # C[r, nj] = -1.0
    d = np.zeros(m)

    Z = np.zeros((m, m))
    A_aug = np.block([[A, C.T],
                      [C, Z]])
    B_aug = np.concatenate([B, d])

    x_aug = np.linalg.solve(A_aug, B_aug)
    pressures = x_aug[:A.shape[0]]

    return pressures


def iterative_nodal_analysis(nodes, channels, viscosity, flow_rate_out, no_of_modules_x, no_of_modules_y, channel_dim, tol=1e-6, max_iter=1000, alpha=0.1):
    """
    Iteratively solves the nodal analysis by updating channel geometries.
    """
    channel_out = channels[f"chip_outflow_{no_of_modules_x - 1}"]
    pressure_out = channel_out.calculate_hydraulic_resistance(nodes, viscosity) * flow_rate_out
    
    pressure_matching_pairs = define_extra_pressure_constraints(no_of_modules_x, no_of_modules_y)

    channel_log = {cid: [] for cid in channels.keys()}

    for iter_count in range(max_iter):
        initial_pressures = conduct_nodal_analysis(nodes, channels, viscosity, pressure_out, pressure_matching_pairs)

        for name, p in initial_pressures.items():
            nodes[name].pressure = p

        all_converged = True
        length_updates = {}

        for cid, channel in channels.items():
            R_h_current = channel.calculate_hydraulic_resistance(nodes, viscosity)
            node1 = nodes[channel.node1]
            node2 = nodes[channel.node2]
            dP_computed = abs(node2.pressure - node1.pressure)

            if channel.fixed_resistance is not None:
                Q_computed = dP_computed / R_h_current
                error = Q_computed - channel.flow_rate
                rel_error = abs(error) / (abs(channel.flow_rate) + eps)
                channel_log[cid].append(rel_error)

                if rel_error > tol:
                    all_converged = False
                continue

            dP_target = channel.flow_rate * R_h_current
            error = dP_computed - dP_target
            rel_error = abs(error) / (dP_target + eps)
            channel_log[cid].append(rel_error)

            if rel_error > tol:
                all_converged = False

            factor = 1 + alpha * (error / (dP_target + eps))
            new_length_tpm = channel.length * factor
            if new_length_tpm < calculate_minimal_length(channel, nodes, channel_dim): # if = 0 nothing changes anyway
                channel.width = channel.width / factor
                new_length = channel.length
            else:
                new_length = new_length_tpm 
            length_updates[cid] = new_length

        for cid, new_length in length_updates.items():
            channels[cid].length = new_length

        if all_converged:       
            print("Convergence achieved. After iteration:", iter_count)
            break

    else:
        raise ValueError(f"Maximum iterations reached without full convergence. The initial guess of the network is too far off, no convergence can be achieved in the iterative MNA.")

    return initial_pressures, iter_count
