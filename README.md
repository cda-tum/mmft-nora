[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)

# MMFT NORA Network-aware Optimization by Resistance Adjustment

<p align="center">
  <img src="https://www.cda.cit.tum.de/research/microfluidics/logo-microfluidics-toolkit.png" width="60%" alt="MMFT Logo">
</p>

This Python-based tool automates the design of microfluidic gradient generators for connecting multiple modules, such as organs-on-a-chip. It was developed in collaboration between the [Chair for Design Automation](https://www.cda.cit.tum.de/) at the [Technical University of Munich (TUM)](https://www.tum.de/) and the [BIOS group](https://www.utwente.nl/en/eemcs/bios/) at the [University of Twente](https://www.utwente.nl/en/), as part of the [Munich Microfluidic Toolkit (MMFT)](https://www.cda.cit.tum.de/research/microfluidics/munich-microfluidics-toolkit/).

The tool supports automatic placement of modules and connects them through a microfluidic network capable of generating concentration gradients in both the x- and y-directions. Layouts are designed to follow ISO standards and are, where feasible, sized to fit standard well plate dimensions.

## Features

- Automated placement and routing of modules, e.g., organ-on-a-chip designs  
- Gradient generation in both x and y directions  
- Configurable parameters: number of modules, dilution settings, spacing, channel dimensions, and more  
- ISO-compatible layouts optimized for standard well plate footprints  

## System Requirements

This tool requires Python. Create the repository-wide Python environment in
the location used by the command-line tool, backend, and GUI development
scripts:

```bash
python -m venv backend/venv
source backend/venv/bin/activate
python -m pip install -r requirements.txt
```

## Usage
Run the command-line tool from the repository root as a Python module:

```bash
backend/venv/bin/python -m src.main
```

If the virtual environment is already activated, the equivalent command is:

```bash
python -m src.main
```

Do not run `python src/main.py` directly. The source now uses package-relative
imports, so it must be executed with `-m src.main` from the repository root.
The default command uses the settings in `src/config.py`, writes DXF output
under `results/`, generates `GeneratedTest.cpp`, and opens a Matplotlib
preview window.

Extra parameters, including the number of modules in each direction, the dilution, minimal channel distances and spacing as well as channel width and height can be defined in the config.py script.

## GUI
There is a graphical user face available. To start the app locally change into the gui directory and run
```bash
npm run dev 
```

## Tests
There are several tests, as well as the option to generate a 1D simulation file for the [mmft-modular-1D-simulator](https://github.com/cda-tum/mmft-modular-1D-simulator), the file is generated for the designed geometry or across a sweep of different heights to account for fabrication inconsistencies. 
To run the simulation copy the file content into the tests GradientGenerator file in the simulator and execute the following commands:
```bash
mkdir build
cd build
cmake ..
make
./dropletTest --gtest_filter=GradientGenerator
```

To execute the tests for the code, run from the repository root:
```bash
backend/venv/bin/python -m pytest -v
```
You can also activate the venv first and then run `python -m pytest -v`.
