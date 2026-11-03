# Simple script to combine a generated spice netlist with a spreadsheet containing
# the position of each node to generate an initial SPICE layout to work from

import csv

# input files
NETLIST_FILE = "conversion output/SPICE_netlist.cir" # netlist 
NODE_FILE = "NORA output/NORA_node_to_position.csv" # CSV containing node number -> position 

### Load node coordinates from NORA output

# create dictionary with node positions
node_pos = {} # node number -> pos

# open spreadsheet
with open(NODE_FILE) as f:
    reader = csv.DictReader(f, delimiter=';')
    node_pos[0] = (0.0, 0.0) # manual ground
    print(reader.fieldnames)

    # helper function to parse float given localized decimal indicator
    def parse_float(val):
        return float(val.replace(',', '.'))

    # Parse different columns
    for row in reader:
        node = int(row["Num"]) 
        x = parse_float(row["X"])
        y = parse_float(row["Y"])
        node_pos[node] = (x, y)

# safe node dict access
def get_pos(n):
    if n not in node_pos:
        raise ValueError(f"Node {n} missing in coordinate file")
    return node_pos[n]
    
### Parse netlist into components
components = [] # list with for each component (ID, n1, n2, value)

# open netlist file
with open(NETLIST_FILE) as f:
    for line in f:
        line = line.strip()

        # ignore comments
        if not line or line.startswith("*"):
            continue

        parts = line.split()

        name = parts[0]
        
        # resistors
        if name.startswith("R"):
            n1, n2 = int(parts[1]), int(parts[2])
            value = float(parts[3])
            components.append(("R", n1, n2, value))

        # current sources
        elif name.startswith("I"):
            n1, n2 = int(parts[1]), int(parts[2])
            value = float(parts[-1])
            components.append(("I", n1, n2, value))


### Write spice layout

def midpoint(p1, p2):
    
    # compare coordinates to determine channel direction
    # Returns (m1x, m1y, m2x, m2y, rotation), m1 and m2 being the start and end point for the component

    diff = (abs(p2[0] - p1[0]), abs(p2[1] - p2[1]))

    if diff[0] > diff[1]:
        # horizontal 
        return ((p1[0]+p2[0])//2-48, (p1[1]+p2[1])//2, (p1[0]+p2[0])//2+32, (p1[1]+p2[1])//2, "R90")
    else:
        # vertical 
        return ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2+48, (p1[0]+p2[0])//2, (p1[1]+p2[1])//2-32, "R0")

with open("generated_layout.asc", "w") as f:
    f.write("Version 4\nSHEET 1 880 680\n")
    scale = 2000 # Magic number. Increase or decrease at will.
    for i, (typ, n1, n2, val) in enumerate(components):
        x1, y1 = node_pos[n1]
        x2, y2 = node_pos[n2]

        # quantize positions to grid
        x1 = 16*int(scale*x1)
        x2 = 16*int(scale*x2)
        y1 = -16*int(scale*y1)
        y2 = -16*int(scale*y2)

        m1x, m1y, m2x, m2y, r = midpoint((x1,y1),(x2,y2))

        # write wires to m1, m2
        f.write(f"WIRE {x1} {y1} {m1x} {m1y}\n")
        f.write(f"WIRE {m2x} {m2y} {x2} {y2}\n")

        # write component between m1, m2

        # write resistor
        if typ == "R":  
            if r == "R0":
                f.write(f"SYMBOL res {m2x-16} {m2y-16} {r}\n")
            else:
                f.write(f"SYMBOL res {m2x+16} {m2y-16} {r}\n")
            f.write(f"SYMATTR InstName R{i}\n")
            f.write(f"SYMATTR Value {val}\n")

        # write current source
        elif typ == "I":
            if r == "R0":
                f.write(f"SYMBOL current {m2x-16} {m2y-16} {r}\n")
            else:
                f.write(f"SYMBOL current {m2x+16} {m2y-16} {r}\n")
            f.write(f"SYMATTR InstName I{i}\n")
            f.write(f"SYMATTR Value {val}\n")

    # ground
    if 0 in node_pos:
        x, y = node_pos[0]
        f.write(f"SYMBOL GND {x} {y} R0\n")

print("Done: written generated_layout.asc")