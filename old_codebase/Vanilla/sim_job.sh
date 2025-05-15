#!/bin/bash

#MSUB -l nodes=1:ppn=16
#MSUB -l walltime=00:15:00
#MSUB -l pmem=500mb
#MSUB -N Sim_Test
#MSUB -m bea

module load compiler/gnu/9.1
module load devel/cmake

PROJ="$(ws_find project)"
DATA="$PROJ/simulation/sim_data"


TEMP="${TMPDIR}"
mkdir -pv $TEMP

# move G4 to tmp
cd $PROJ
cp -pv geant4.tar $TEMP
cd $TEMP
tar -xf geant4.tar

# source G4
source $TEMP/geant4/geant4.10.05.p01-install/share/Geant4-10.5.1/geant4make/geant4make.sh
export DICOM_NTHREADS=$((1*${MOAB_PROCCOUNT}))

# build project
cp -r $PROJ/simulation $TEMP
cd $TEMP/simulation
mkdir -pv build
cd build
mkdir -pv output
cmake ..
make -j${MOAB_PROCCOUNT}

cd $PROJ
mkdir -pv output

cd $DATA

for f in *; do
	echo $f
	tar -xf $f -C $TEMP/simulation/build/output
	cd $TEMP/simulation/build
	time ./simulations run.mac "output/${f%????}/" 3
	cd output
	tar -cf ${f%????}.tar ${f%????}
	mv ${f%????}.tar $PROJ/output
	cd $DATA
done

