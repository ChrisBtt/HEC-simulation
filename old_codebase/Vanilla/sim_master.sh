#!/bin/bash

#MSUB -l nodes=1:ppn=1
#MSUB -l walltime=00:10:00
#MSUB -l mem=1gb
#MSUB -N Sim_Master
######MSUB -m bea

PROJ="$(ws_find project)"
DATA="$PROJ/data"

#source "~/geant4/geant4.10.05.p01-install/share/Geant4-10.5.1/geant4make/geant4make.sh"

cd $DATA
for f in *
do
    echo $f
    cd $PROJ/simulation
    msub sim_slave.sh $f
    cd $DATA
done




