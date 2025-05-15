#!/bin/bash

#MSUB -l nodes=1:ppn=16
#MSUB -l walltime=24:00:00
#MSUB -l pmem=1gb
#MSUB -N sim_slave:$1
#MSUB -q singlenode

module load compiler/gnu/9.1
module load devel/cmake


f="$1"

PROJ="$(ws_find project)"
DATA="$PROJ/data"


TEMP="${TMPDIR}"
mkdir -pv $TEMP

# source G4
source "$HOME/geant4-q/geant4.10.05.p01-install/share/Geant4-10.5.1/geant4make/geant4make.sh"
export DICOM_NTHREADS=$((2*${MOAB_PROCCOUNT}))

# build project
cp -r $PROJ/simulation $TEMP
cd $TEMP/simulation
mkdir -pv build
cd build
mkdir -pv output
cmake ..
make -j${MOAB_PROCCOUNT}

cd $DATA
echo "Working on file $f"
mv $f $TEMP/simulation/build/output

tar -xf $TEMP/simulation/build/output/$f -C $TEMP/simulation/build/output
rm $TEMP/simulation/build/output/$f
cd $TEMP/simulation/build
# 1min for one simulation, i.e. 360 simulations in 6h (100k particles)
time ./simulations run.mac output/${f/.tar/}/ 
cd output
tar -cf $f ${f/.tar/}
mv $f $DATA


