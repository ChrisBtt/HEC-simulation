#pragma once

#include <memory>

#include "G4VPrimaryGenerator.hh"
#include "globals.hh"

class PSFReader;

class PSFPrimaryGenerator: public G4VPrimaryGenerator
{
public:
    PSFPrimaryGenerator(std::shared_ptr<PSFReader>);
    PSFPrimaryGenerator() = delete;
    ~PSFPrimaryGenerator();

public:
    void GeneratePrimaryVertex(G4Event *evt); // Mandatory

    // Set/Get Methods 
    inline auto GetNumRanks() const {return m_numRanks; }
    inline auto GetRank() const { return m_Rank; }
    inline auto GetNumThreads() const { return m_numThreads; }
    inline auto GetThreadID() const { return m_ThreadID; }
    inline auto GetNumRecycle() const { return m_numRecycle; }

    inline void SetNumRecycle(G4int numRecycle) { m_numRecycle = numRecycle; }

private:
    // The mpi rank 
    G4int m_Rank;
    G4int m_numRanks;

    // threads
    G4int m_ThreadID;
    G4int m_numThreads;

    // recycle particles for each event
    // e.g. numRecycle = 9 -> 1 event
    // starts 10x the current particle
    G4int m_numRecycle = 0;

    std::shared_ptr<PSFReader> m_Reader;
};