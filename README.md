# HEC Particle Simulation

A particle simulation project for analyzing the relation between the distribution of charged particle currents and
deposited dose in High Energy Physics Collisions (HEC). This project includes tools for simulation, data processing and
visualization.

## Getting Started

First, you will need to install the software packages. 

Install Geant4 and Topas from: https://opentopas.github.io/installation.html to install openTOPAS and Geant4. 
    - Make sure to install the extensions that accompany this project in folder "TOPAS_extensions" folder. To install them, add the following line to your cmake command when building openTOPAS:
    `` -DTOPAS_EXTENSIONS_DIR=/PATHTO/TOPAS_extensions
    ``

After testing your first simulation using a macrofile, you are ready to go! 

TOPAS also allows macrofiles in a modular structure for cleaner configuration and easy experiment adjustment. Therefore, `simulation.txt` serves as top-level macrofile and included files can be adjusted using the hierarchical files with chained include-statements. 