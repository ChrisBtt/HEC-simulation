#pragma once

/* 
Implements a struct that holds serialized versions of all quantities
involved in dose and stats scoring of a run. To be used for serialization
before sending data per MPI between several processes/different runs.
*/

#include <array>
#include "DicomDetectorConstruction.hh"
#include "G4THitsVector.hh"
#include "StatAnalysis.hh"

// suboptimal, conflicts due to cross importing if uncommented, typedef needed
//#include "DicomRun.hh"
typedef G4VTHitsVector<StatAnalysis, std::vector<StatAnalysis>> StatVector;

/* 
Each voxel gives rise to a StatAnalysis instance
(-> StatVector) which holds 4 mandatory members each:
fSum1, fSum2, fHits, fZeros
These can be send via MPI to build new StatAnalysis
objects on the receiving side to perform the merging
of different MPI runs.
*/
class Serializer 
{

  public:
    Serializer();
    ~Serializer();
    
    /*
    Serialize a StatVector instance, by unpacking every StatAnalysis
    object and storing its members in arrays of primitive datatypes.
    */
    void Pack(const StatVector* statVec);

    /*
    Deserialize buffers into a StatVector instance
    */
    StatVector* Unpack() const;

    /*
    Pointers do data buffers
    */
    double* GetSum1Ptr() { return arrSum1.data(); } 
    double* GetSum2Ptr() { return arrSum2.data(); }
    unsigned long* GetHitsPtr() { return arrHits.data(); }
    unsigned long* GetZerosPtr() { return arrZeros.data(); }

    int GetBufferSize() const { return DicomDetectorConstruction::N_VOXEL; }
  
  public:
    bool needsUnpacking;

  private:
    // buffers to hold mandatory values
    std::array<double, DicomDetectorConstruction::N_VOXEL> arrSum1;
    std::array<double, DicomDetectorConstruction::N_VOXEL> arrSum2;
    std::array<unsigned long, DicomDetectorConstruction::N_VOXEL> arrHits;
    std::array<unsigned long, DicomDetectorConstruction::N_VOXEL> arrZeros;
};