#pragma once

#include <memory>
#include <array>
#include <mutex>

#include "globals.hh"
#include "G4ThreeVector.hh"

#include "iaea_phsp.h"
#include "iaea_record.h"

struct IAEAParticle
{   
    // pos in phase space file
    G4long psfIdx;

    // particle info
    G4int type;
    G4int stat;
    G4double energy;
    G4double weight;
    G4ThreeVector position;
    G4ThreeVector momentum;

    // holds the extra values for read particle
    std::array<G4double, NUM_EXTRA_FLOAT> extraFloats;
    std::array<G4long, NUM_EXTRA_LONG> extraInts;
};

/*
 * Read events/particles from a single phase-space file.
 * The PSF gets split into N chunks, where N is the number of MPI ranks.
 * Each rank initializes its own source and returns particles from
 * a certain chunk of the PSF. Object shared across threads, guarded
 * by locking every access to the class instance.
 */
class PSFReader
{
public:
    PSFReader(const G4String&);
    ~PSFReader();

    // Reads the next particle from the PSF
    IAEAParticle ReadNextParticle();

    // Set/Get Methods 
    inline auto GetNumRanks() const {return m_numRanks; }
    inline auto GetRank() const { return m_Rank; }
    inline auto GetFileName() const { return m_Filename; }
    inline auto GetNumTotalParticles() const { return m_numTotalParticles; }
    inline auto GetChunkSize() const { return m_chunkSize; }
    inline auto GetNumberOfExtraFloats() const { return m_numExtraFloats; }
    inline auto GetNumberOfExtraInts() const { return m_numExtraInts; }

private:
    // Initialize/destroy the source file
    void InitializeSource();
    void DestroySource();

    void SetupRankParallelism();
    
private:
    // ID and access for IAEA routines
    static const G4int s_srcRead = 0;
    static const G4int s_accessRead = 1;

    // the PSF filename w/o extension
    G4String m_Filename;

    // The mpi rank 
    G4int m_Rank;
    G4int m_numRanks;

    // number of extra variables
    G4int m_numExtraFloats;
    G4int m_numExtraInts;

    // number of particles in the PSF
    G4long m_numTotalParticles;

    // chunk size, upper bound for the particle index
    G4long m_chunkSize;

    // the running particle index of particles in the PSF
    G4long m_partIdx;

    // mutex to avoid concurrent reader access
    std::mutex m_Mtx;
};