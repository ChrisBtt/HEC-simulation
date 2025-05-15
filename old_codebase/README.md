## Setup
### Requirements
Requirements for this repository is an installation of GEANT4 and, for MPI runs,
OpenMPI.

**NOTE**: Since Vanilla simulation is outdated, the MPI version of the 
simulation is the only one working and up-to-date.

### Installation
First, download [OpenMPI](https://www.open-mpi.org/software/ompi/v1.8/). 
Then, follow these steps to build and install the library.
```
$ tar -xzf openmpi-1.8.8.tar.gz
$ cd openmpi-1.8.8
$ mkdir -pv openmpi-install
$ ./configure --prefix=/path/to/openmpi-1.8.8/openmpi-install
$ make all
$ make install
```

Add these two exports to the ```.bashrc``` file under your ```$HOME``` directory:
```
export PATH=/path/to/openmpi-1.8.8/openmpi-install/bin:$PATH
export LD_LIBRARY_PATH=/path/to/openmpi-1.8.8/openmpi-install/lib:$LD_LIBRARY_PATH:
```

Now download [GEANT4](https://geant4.web.cern.ch/support/download);
As of now, the most recent version is ```geant4.10.07.p01.tar.gz```.
```
$ mkdir -pv geant4
$ tar -xzf geant4.10.07.p01.tar.gz
$ mv geant4.10.07.p01 geant4/
$ cd geant4
$ mkdir -pv geant4.10.07.p01-build
$ cd geant4.10.07.p01-build
```

Now build using cmake with the following mandatory flags:
```
$ cmake -DGEANT4_INSTALL_DATA=ON \
 -DGEANT4_BUILD_MULTITHREADED=ON \
 -DCMAKE_CXX_STANDARD=17 \
 -DCMAKE_INSTALL_PREFIX="/path/to/geant4/geant4.10.07.p01-install" \
  "/path/to/geant4/geant4.10.07.p01"
 
$ make -jN
$ make install
```
Replace ```N``` by the number of cores/threads available for building on your
machine. Optionally, you can build w/o Verbose Code by adding the flag
```-DGEANT4_BUILD_VERBOSE_CODE=OFF```. For visualization you will need to add
the OpenGL flag ```-DGEANT4_USE_OPENGL_X11=ON```.

Into ```.bashrc```:
```
source /path/to/geant4/geant4.10.07.p01-install/share/Geant4-10.7.1/geant4make/geant4make.sh
```

Finally, install the ```G4MPI``` library:
```
$ cd /path/to/geant4
$ mkdir -pv g4mpi-build
$ cd g4mpi-build
$ cmake -DGeant4_DIR=/path/to/geant4/geant4.10.07.p01-install/lib64/Geant4-10.7.1 \
 -DCMAKE_INSTALL_PREFIX=/path/to/geant4/g4mpi-install \
 -DCMAKE_CXX_STANDARD=17 \
 /path/to/geant4/geant4.10.07.p01/examples/extended/parallel/MPI/source

$ make -jN
$ make install
```

### Building the project
In the MPI folder of the project, run:
```
$ mkdir -pv build
$ cd build
$ cmake -DG4mpi_DIR=/path/to/geant4/g4mpi-install/lib/G4mpi-10.7.1 ..
$ make -jN
```
Optionally, you can omit the cmake flag by adding the following line in
```CMakeLists.txt```:
```cmake
set(G4mpi_DIR /path/to/geant4/g4mpi-install/lib/G4mpi-10.7.1)
```

## Running Simulations
In the build folder of the simulation, create a `output` folder
in which you place your data of the form:
```
+-- output
    +-- cube_data
        +-- g4dcms
            +-- cube_data_0.g4dcm
            +-- cube_data_1.g4dcm
            +-- ...
        +-- output_cubes
            +-- ...
        +-- cubes.json
    +-- ...
```
Output data of the simulation is then written to the `output_cubes` directory.
Important source files are `DICOM_MPI.cc` and `simulations.cc`. 
The latter source file is generally executed and
runs several simulations on one cube at a time. Cube data is accessed via
the `cubes.json` file. Currently, the MPI command has to specified in
`simulations.cc` (hardcoded), e.g. to run the simulations with 4 MPI processes,
change the line defining the MPI command to:
```cpp
std::string mpi_command = "mpirun -np 4 --bind-to None --map-by hwthread ";
```
The number of threads is currently set via `OMP_NUM_THREADS` environment variable.
The standard template to run simulations is then (in the build folder):
```
$ OMP_NUM_THREADS=<N> ./simulations <macro-file> "<path/to/cube_data>" <# of cubes to process>
```
E.g. to run the simulation for 3 input cubes (one at a time) using 8 Threads with
the `run.mac` macro file and the cube_data mentioned above:
```
$ OMP_NUM_THREADS=8 ./simulations run.mac "output/cube_data/" 3
```
Optionally, you can write the Text-Output of the simulations to a file:
```
$ OMP_NUM_THREADS=8 ./simulations run.mac "output/cube_data/" 3 > output.txt
```

## Visualization
If you want to visualize the simulation, you will need to run the program with 
only 1 MPI Process (editable in ```simulations.cc```) and the ```vis.mac``` file,
e.g.:
```
$ OMP_NUM_THREADS=1 ./simulations vis.mac "output/cube_data/" 1
```

## Software Versions
Latest:
* Linux (e.g. Ubuntu 18.04)
* GEANT4 Version 4.10.07.p01
* OpenMPI <= 1.8.8 
* Compiler: GNU <= 9.3 w/ C++ Standard 17
* CMake <= 3.11