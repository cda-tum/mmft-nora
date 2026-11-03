# Function to replace resistances values in the SPICE file generated from NORA 
# output with resistances based on measured data

import re
import csv

# import utility functions
from utils import calculate_hydraulic_resistance, calculate_hydraulic_resistance_cylinder

# Input/output files
spice_file = "conversion output/SPICE_layout_modified.asc" # SPICE file generated from NORA output with manual changes
output_file = "conversion output/SPICE_layout_sensitivity.asc" # output file name

dims_file = "NORA output/NORA_netlist_measurements.csv" # NORA output netlist with added measurements column 

# For the above spreadsheets, it is assumed that the same line in each file 
# corresponds to the same component

viscosity: float = 1e-3 # viscosity of the fluid, necessary for resistance calculations

### Parse dimensions from spreadsheet

dimensions = []

with open(dims_file) as f:
    reader = csv.DictReader(f, delimiter=';')
    print(reader.fieldnames)

    # helper function to parse float given localized decimal indicator
    def parse_float(val):
        return float(val.replace(',', '.'))
    
    for row in reader:
        # spreadsheet has columns
        # from;to;height;width;length;Hmeas;Hmeasavg
        start_node = int(row['from'])
        end_node = int(row['to'])
        h = parse_float(row['height'])
        w = parse_float(row['width'])
        length = parse_float(row['length'])
        hmeas = parse_float(row['Hmeas'])
        hmeasavg = parse_float(row['Hmeasavg'])


        dimensions.append({
            "start": start_node,
            "end": end_node,
            "h": h,
            "w": w,
            "length": length,
            "hmeas": hmeas, # measured length using one measurements
            "hmeasavg": hmeasavg # measured length averaging measurements at start/end of channels if available
        })

### Process resistors in spice file

# Read lines of spice file
with open(spice_file, "r") as f:
    lines = f.readlines()

output_lines = []

i = 0
while i < len(lines):

    line = lines[i]

    # Detect resistor block
    if line.startswith("SYMBOL res"):

        # Expect next lines:
        # SYMATTR InstName RX
        # SYMATTR Value VALUE

        symbol_line = lines[i]
        inst_line = lines[i + 1]
        value_line = lines[i + 2]

        # Extract resistor number
        inst_match = re.search(r"SYMATTR InstName R(\d+)", inst_line)

        if inst_match:

            r_index = int(inst_match.group(1))

            # Extract resistance value from spice sim
            value_match = re.search(r"SYMATTR Value ([Ee0-9+.\-]+)", value_line)

            if value_match and r_index < 61: # 61 and up are inlet resistances which we don't replace

                
                # Get dimensions corresponding to this resistor
                dims = dimensions[r_index]

                # Determine R to use in updated layout
                if dims["hmeasavg"] <= 0: # We have manually entered -1 for channels without measurements
                    R = float(value_match.group(1))
                else:
                    # Calculate resistance from dimensions
                    R = calculate_hydraulic_resistance(dims["w"], dims["hmeasavg"], dims["length"], viscosity)

                new_value_line = (
                    f"SYMATTR Value {R}\n"
                )

                # Write modified block
                output_lines.append(symbol_line)
                output_lines.append(inst_line)
                output_lines.append(new_value_line)

                print(
                    f"R{r_index}: "
                    f"R={R:.6e}, "
                )

                i += 3 # go to next block
                continue

    # Default: copy line unchanged
    output_lines.append(line)
    i += 1

### Save output file 

with open(output_file, "w") as f:
    f.writelines(output_lines)

print(f"\nModified spice file written to: {output_file}")