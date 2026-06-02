[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)

# OoC-GG - Design Automation for Gradient Generators for Organs-on-a-Chip

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

This tool requires Python. All necessary packages can be installed with:

```bash
pip install -r requirements.txt
```

## Usage
To run the tool, execute:
```bash
python main.py
```

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

To execute the tests for the code, change to the tests directory and execute:
```bash
python -m pytest -v
```
Make sure the venv is activated.

