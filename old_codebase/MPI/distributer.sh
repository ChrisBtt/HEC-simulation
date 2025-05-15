#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --mem=2gb
#SBATCH -p dev_single
#SBATCH -J job_distribution
##SBATCH --mail-type=ALL
#SBATCH --export=ALL
#SBATCH --error="job_dist.err"
#SBATCH --output="job_dist.out"

# load compiler and cmake
module load compiler/gnu/9.3

PROJ="$(ws_find mc-sim-new)"
DATA="$PROJ/data"
OUTDATA="$PROJ/data_out"

cd $PROJ

mkdir -pv $OUTDATA

source $PROJ/geant4/geant4.10.07-install/share/Geant4-10.7.0/geant4make/geant4make.sh
# env vars
#export KMP_AFFINITY=verbose,compact,1,0
#export DICOM_NTHREADS=2
export OMP_NUM_THREADS=8
export PATH=$PROJ/openmpi-1.8.8/openmpi-install/bin:$PATH
export LD_LIBRARY_PATH=$PROJ/openmpi-1.8.8/openmpi-install/lib:$LD_LIBRARY_PATH:

# build
SIM=$PROJ/cube-simulation/MPI

cd $SIM
rm -r build
mkdir -pv build
cd build
cmake -DCMAKE_BUILD_TYPE=Release \
      -DG4mpi_DIR=$PROJ/geant4/g4mpi-install/lib64/G4mpi-10.7.0 \
      ..

make -j10
mkdir -pv output

cd $DATA
for f in *
do
    echo $f
    cd $PROJ
    sbatch cube-simulation/MPI/sim_mul_node.sh $f
    cd $DATA
done

