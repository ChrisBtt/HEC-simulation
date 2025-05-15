#!/bin/bash
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=10
#SBATCH --cpus-per-task=8
#SBATCH --time=05:00:00
#SBATCH --mem=64gb
#SBATCH -p multiple
#SBATCH -J multiple_sim
#SBATCH --mail-type=ALL
#SBATCH --export=ALL
##SBATCH --output=None
#SBATCH --error="errors.out"

f="$1"

PROJ="$(ws_find mc-sim-new)"
DATA="$PROJ/data"
OUTDATA="$PROJ/data_out"
SIM="$PROJ/cube-simulation/MPI"

cd $PROJ

echo "Working on file $f"
tar -xvf $DATA/$f -C $SIM/build/output

cd $SIM/build
command time -v ./simulations run.mac output/${f/.tar/}/
cd output
tar -cvf $f ${f/.tar/}
mv $f $OUTDATA