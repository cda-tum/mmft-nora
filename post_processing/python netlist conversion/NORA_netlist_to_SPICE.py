# Simple script to convert our netlist output to NORA and input to the 1D sim
# for verification into a netlist competible with SPICE

import csv
import pandas as pd

# Load ODS file (requires odfpy installed)
file_path = "NORA output/NORA_netlist_dimensions.csv"

netlist = []

resistor_count = 1

# open spreadsheet
with open(file_path) as f:
    reader = csv.DictReader(f, delimiter=';')
    print(reader.fieldnames)

    # helper function to parse float given localized decimal indicator
    def parse_float(val):
        return float(val.replace(',', '.'))

    # Parse different columns
    for row in reader:        
        # Spreadsheet has columns:
        # name;from;to;height;width;length;woverh;Rext;Rsimp

        n1 = int(row['from'])
        n2 = int(row['to'])
        value = parse_float(row['Rext']) 

        # Append line to spice netlist
        if pd.notna(n1) and pd.notna(n2) and pd.notna(value):
            # SPICE resistor definition of form "R node1 node2 value"
            line = f"R{resistor_count} {int(n1)} {int(n2)} {value}" 
            netlist.append(line)
            resistor_count += 1


# Add simulation command
netlist.append("\n.tran 0 1s")
netlist.append(".end")

# Save file
with open("SPICE_netlist.cir", "w") as f:
    f.write("\n".join(netlist))
