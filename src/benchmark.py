import time
import csv

import src.main as main

from src.config import Config
from src.modified_nodal_analysis import (
    conduct_nodal_analysis,
    define_extra_pressure_constraints,
)


param_combinations = [
    # (1, 1),
    # (2, 1),
    # (1, 2),
    # (2, 2),
    # (3, 1),
    # (1, 3),
    (3, 3),
]


def calculate_flow_rate_error(nodes, channels, cfg):
    """
    Calculate the maximum relative flow-rate error after geometry adaptation.

    The network is solved again using the final geometry, and the resulting
    flow rates are compared with the flow rates stored in the channels.

    Returns
    -------
    float
        Maximum absolute relative flow-rate error in percent.
    """

    pressure_matching_pairs = define_extra_pressure_constraints(
        cfg.no_of_modules_x,
        cfg.no_of_modules_y
    )

    flow_rate_out = (
        cfg.no_of_modules_x
        * cfg.no_of_modules_y
        * cfg.organ_module["flow_rate"]
        * 2
    )

    outlet_channel = channels[
        f"chip_outflow_{cfg.no_of_modules_x - 1}"
    ]

    pressure_out = (
        outlet_channel.calculate_hydraulic_resistance(
            nodes,
            cfg.viscosity
        )
        * flow_rate_out
    )

    # Recalculate pressures using the final geometry
    conduct_nodal_analysis(
        nodes,
        channels,
        cfg.viscosity,
        pressure_out,
        pressure_matching_pairs
    )

    errors = []

    for channel_id, channel in channels.items():

        if channel.fixed_resistance is not None:

            R_h = channel.calculate_hydraulic_resistance(
                nodes,
                cfg.viscosity
            )

            node1 = nodes[channel.node1]
            node2 = nodes[channel.node2]

            dP = abs(node2.pressure - node1.pressure)

            calculated_flow_rate = dP / R_h
            target_flow_rate = channel.flow_rate

            if abs(target_flow_rate) > 0:
                relative_error = (
                    abs(calculated_flow_rate - target_flow_rate)
                    / abs(target_flow_rate)
                )

                errors.append(relative_error)

    if not errors:
        return 0.0

    return max(errors) * 100


def calculate_tmp_error(nodes, cfg):
    """
    Calculate the maximum TMP error after geometry adaptation.

    TMP is constrained by requiring the two nodes on either side
    of the membrane to have the same absolute pressure.

    Returns:
        Maximum absolute pressure difference [Pa].
    """
    pressure_matching_pairs = define_extra_pressure_constraints(
        cfg.no_of_modules_x,
        cfg.no_of_modules_y
    )

    tmp_errors = []

    for node1_name, node2_name in pressure_matching_pairs:
        p1 = nodes[node1_name].pressure
        p2 = nodes[node2_name].pressure

        tmp_error = abs(p1 - p2)
        tmp_errors.append(tmp_error)

    if not tmp_errors:
        return 0.0

    return max(tmp_errors)


def save_results_csv(results, filename="benchmark_results.csv"):
    """Save benchmark results as a CSV file."""

    fieldnames = [
        "Configuration",
        "Computation time [s]",
        "Spacing iterations",
        "Final MNA iterations",
        "Total MNA iterations",
        "Flow-rate error [%]",
        "TMP error [%]",
    ]

    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)


def print_results(results):
    """Print the benchmark results in a readable table."""

    headers = [
        "Configuration",
        "Time [s]",
        "Spacing",
        "Final MNA",
        "Total MNA",
        "Flow error [%]",
        "TMP error [%]",
    ]

    print()
    print(
        f"{headers[0]:>10}"
        f"{headers[1]:>12}"
        f"{headers[2]:>12}"
        f"{headers[3]:>14}"
        f"{headers[4]:>14}"
        f"{headers[5]:>18}"
        f"{headers[6]:>16}"
    )

    print("-" * 111)

    for result in results:

        print(
            f"{result['Configuration']:<15}"
            f"{result['Computation time [s]']:>12.3f}"
            f"{result['Spacing iterations']:>12}"
            f"{result['Final MNA iterations']:>14}"
            f"{result['Total MNA iterations']:>14}"
            f"{result['Flow-rate error [%]']:>18.6e}"
            f"{result['TMP error [%]']:>16.6e}"
        )


def main_benchmark():

    results = []

    for nx, ny in param_combinations:

        print(f"Running benchmark for {nx} × {ny} modules...")

        cfg = Config()

        cfg.no_of_modules_x = nx
        cfg.no_of_modules_y = ny

        # Do not include file export/plotting time in the benchmark
        # if you want to measure only the design-generation algorithm.
        cfg.output_dxf_path = None
        cfg.output_preview_path = None

        start_time = time.perf_counter()

        (
            nodes,
            channels,
            exclusion_zones,
            export_result,
            metrics,
        ) = main.main(cfg)

        computation_time = time.perf_counter() - start_time

        flow_error = calculate_flow_rate_error(
            nodes,
            channels,
            cfg
        )

        tmp_error = calculate_tmp_error(
            nodes,
            cfg
        )

        result = {
            "Configuration": f"{nx} × {ny}",
            "Computation time [s]": computation_time,
            "Spacing iterations": metrics["spacing_iterations"],
            "Final MNA iterations": metrics["final_mna_iterations"],
            "Total MNA iterations": metrics["total_mna_iterations"],
            "Flow-rate error [%]": flow_error,
            "TMP error [%]": tmp_error,
        }

        results.append(result)

        print(
            f"Time: {computation_time:.3f} s | "
            f"Spacing: {metrics['spacing_iterations']} | "
            f"Final MNA: {metrics['final_mna_iterations']} | "
            f"Total MNA: {metrics['total_mna_iterations']} | "
            f"Flow error: {flow_error:.3e} % | "
            f"TMP error: {tmp_error:.3e} %"
        )

    print_results(results)

    save_results_csv(results)

    print()
    print("Results saved to benchmark_results.csv")

    return results


if __name__ == "__main__":
    main_benchmark()