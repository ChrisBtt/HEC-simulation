# HEC Particle Simulation

A particle simulation project for analyzing the relation between the distribution of charged particle currents and
deposited dose in High Energy Physics Collisions (HEC). This project includes tools for simulation, data processing and
visualization.

## Overview

The project consists of the following components:

- `DICOM.cc`: Main program for running the particle simulation
- `convertOutput.cc`: Converts raw simulation output data into more useful quantities and exports them into individual
files
- `plotDepth.py`: script for creating depth-based visualization plots
- `plotRadial.py`: script for creating radial distribution plots

## Usage

To run a simulation, we first need to define the geometry within the Data.dat file in the following format:
- A line with the compression value (used only to create the intermediary .g4dcm and .g4dcmb, not to read it)
- A line with the number of files
- A line for each file name (without the .dcm extension)

The following example will create a volume consisting of 3 slices of uncompressed data along the z-axis:

    1
    3
    Slice1
    Slice2
    Slice3

Alternatively, one can also create a homogeneous cube of water directly in the Data.dat file:

    1
    0
    300 300 300
    150 150 150

The above example will create a volume of 300 x 300 x 300 mm in size, divided into 150 x 150 x 150 cubes.

Next up, we need to set the parameters of the particle beam in one of the macro files used for initializing the
simulation. One can choose between run.mac and vis.mac, of which the latter additionally sets up a visualization of the
simulated geometry and particles. Because the visualization is quite memory-intensive, its use should be limited to runs
with only a small number of particles.

The number of particles can be adjusted with the command:
- `/run/beamOn n`

The particle beam's position and orientation can be adjusted with the commands defined in the PrimaryGeneratorAction
class:
- `/particleGun/setPosition x y z`
- `/particleGun/setDirection x y z`
- `/particleGun/setRadius r`

Optionally, it is also possible to introduce an arbitrary heterogeneous region into the volume. For this, its parameters
need to be passed as arguments to the main program according to Geant4's textual geometry definition.
The heterogeneity will use the `Tumor` material defined in `DicomDetectorConstruction.cc`.

Finally, the simulation can be run with the command:

    ./DICOM