[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)

# MMFT NORA Network-aware Optimization by Resistance Adjustment

<p align="center">
  <img src="https://www.cda.cit.tum.de/research/microfluidics/logo-microfluidics-toolkit.png" width="60%" alt="MMFT Logo">
</p>

NORA is a microfluidic design automation workflow for simultaneous network-aware hydraulic optimization and fabrication-aware layout generation. Given a network specification with device footprints and hydraulic operating requirements, it optimizes channel resistances and component placement to produce a fabrication-ready fluidic circuit board design. It was developed in collaboration between the [Chair for Design Automation](https://www.cda.cit.tum.de/) at the [Technical University of Munich (TUM)](https://www.tum.de/) and the [BIOS group](https://www.utwente.nl/en/eemcs/bios/) at the [University of Twente](https://www.utwente.nl/en/), as part of the [Munich Microfluidic Toolkit (MMFT)](https://www.cda.cit.tum.de/research/microfluidics/munich-microfluidics-toolkit/).

The tool includes an initialization for the automatic placement of organ-on-chip modules and connects them through a microfluidic network capable of generating concentration gradients in both the x- and y-directions. Layouts are designed to follow ISO standards and are, where feasible, sized to fit standard well plate dimensions.

## Features

- Generates fabrication-ready microfluidic circuit board layouts
- Simultaneous optimization of channel resistances and component placement for desired flow behaviour
- Supports device footprints and hydraulic operating constraints, e.g. for herring bone mixers or organ-on-chips
- ISO-compatible layouts optimized for standard well plate footprints  


## Table of Contents
 
- [Quick Tutorial (GUI)](#quick-tutorial-gui)
- [Exporting the Generated Files](#exporting-the-generated-files)
- [Larger Designs (e.g., 3 x 3 Modules)](#larger-designs-eg-3-x-3-modules)
- [System Requirements](#system-requirements)
- [Command-Line Usage](#command-line-usage)
- [Running the GUI Locally](#running-the-gui-locally)
- [Tests and 1D Simulation](#tests-and-1d-simulation)

## Quick Tutorial (GUI)
 
The [GUI](https://www.cda.cit.tum.de/app/mmft-nora/) lets you generate a design in the browser.
 
1. **Set the number of modules.** Enter *Modules X* and *Modules Y*; the default is a 3 x 1 layout.
2. **Adjust the design settings if needed.** The main options are *Dilution X / Y*, *Spacing X*, *Outflow spacing*, and the channel dimensions. The defaults work well for small layouts; for larger ones, see [Larger Designs](#larger-designs-eg-3-x-3-modules).
3. **Generate and inspect the design.** Start the run, wait for the preview, and review the flow-colored layout.
4. **Download the result.** Use the download link below the preview (see [Exporting the Generated Files](#exporting-the-generated-files)).

> Tip: Change one parameter at a time. If a setting does not produce a valid layout, revert to the last working values. Alternatively, run NORA on your local machine via the command line. This allows for more config settings and faster computation times.

 You can also run it locally (see [Running the GUI Locally](#running-the-gui-locally)).

## Exporting the Generated Files
 
The tool generates multiple **DXF** files, one for each layer and height, respectively, and one stack of all created channels for a better overview. The naming of each of these 2D DFX files includes height and layer and facilitates subsequent fabrciation.

### From the GUI
 
After a successful run, a download link for the **DXF** file appears above the preview. Clicking it starts a normal browser download:
 
- The file is saved to your browser's default download folder (typically `Downloads`). Many browsers do not show a pop-up or dialog. Check the download list of your browser (usually `Ctrl+J` / `Cmd+Shift+J` or the download icon in the toolbar) to find the file.
- If you have configured your browser to ask where to save files, a save dialog will appear instead.
- If nothing is downloaded, check whether your browser or an extension blocks downloads from the site (look for a blocked-download or pop-up notice in the address bar) and allow the download, then click the link again.
- The DXF file can be opened with any CAD software that supports DXF (e.g., AutoCAD, FreeCAD, LibreCAD, Inkscape) and used for fabrication, e.g., as a mask or milling design.
### From the command line
 
When running the command-line tool, all outputs are written to disk automatically:
 
| Output | Location |
| --- | --- |
| DXF layout | `results/` |
| 1D simulation file | `GeneratedTest.cpp` (repository root) |
 
## Larger Designs (e.g., 3 x 3 Modules)
 
The number of modules affects the size of the optimization problem and therefore the runtime, additionally, the tool runs considerably faster when executed locally than on the web server. A benchmark table with runtimes is provided in the supplementary material of the manuscript associated with this tool.
 
The GUI has a time limit and shows an error message if a run takes too long or cannot be completed. The values below were chosen so that the 3 x 3 case finishes within this limit.
 
### Recommended settings in the GUI (3 x 3)
 
| Parameter | Default (3 x 1) | Recommended for 3 x 3 |
| --- | --- | --- |
| Spacing X | 2000 µm | **800 µm** |
| Outflow spacing | 800 µm | **400 µm** |
| Dilution X | 0.1 | **0.5** |
| Dilution Y | 0.1 | **0.5** |
 
### Recommended settings in the code (3 x 3)
 
When running locally, more options are available to adjust and the dilution can be kept at 0.1. As the optimizer is sensitive to its starting point, the following parameters in `src/config.py` should be adapted for a 3 x 3 layout. This also illustrates how important the initial configuration parameters can be.
 
| Parameter | Value |
| --- | --- |
| `max_width` | `2.0e-3` |
| `pump_connection_distance_in` | `5.5e-3` |
| `pump_connection_distance_out` | `9.0e-3` |
| `spacing_x` | `2 * min_distance` |
| `spacing_out` | `1 * min_distance` |
 
All lengths in `config.py` are given in meters.

These recommended settings also generate the included 3x3 layout depiction in the associated manuscript.

## System Requirements

This project requires Python 3.11 or newer.

To create a virtual environment and install the packages listed in requirements.txt, execute:

```bash
python -m venv backend/venv
source backend/venv/bin/activate
python -m pip install -r requirements.txt
```

Alternatively, you can use the Graphical User Interface ([GUI](https://www.cda.cit.tum.de/app/mmft-nora/)), see [Quick Tutorial (GUI)](#quick-tutorial-gui).
 
## Command-Line Usage
 
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
 
Additional parameters such as module counts, dilution, spacing, and channel dimensions can be set in `src/config.py`.

## Running the GUI Locally

Change into the gui directory and run:
```bash
npm run dev 
```

## Tests and 1D Simulation

The repository includes an optional 1D simulation export for the [mmft-modular-1D-simulator](https://github.com/cda-tum/mmft-modular-1D-simulator) and unit tests.

### 1D Simulation

The simulation file can be generated for the designed geometry or across a sweep of different heights to account for fabrication inconsistencies. Copy the generated content into the simulator's `GradientGenerator` test and run:
```bash
mkdir build
cd build
cmake ..
make
./dropletTest --gtest_filter=GradientGenerator
```

### Unit Tests

Run the code tests from the repository root:
```bash
backend/venv/bin/python -m pytest -v
```

If the virtual environment is already activated, run `python -m pytest -v`.
