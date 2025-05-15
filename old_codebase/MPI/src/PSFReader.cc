#include "PSFReader.hh"

#include <mutex>

#include "G4MPImanager.hh"
#include "iaea_phsp.h"

PSFReader::PSFReader(const G4String& filename)
: m_Filename(filename), m_partIdx(0)
{
    InitializeSource();
}

PSFReader::~PSFReader()
{
    DestroySource();
}

void PSFReader::InitializeSource()
{   
    auto srcRead = static_cast<IAEA_I32>(s_srcRead);
    auto accessRead = static_cast<const IAEA_I32>(s_accessRead);
    auto* fname = const_cast<char*>(m_Filename.data());

    // open src file
    IAEA_I32 result;
    iaea_new_source(&srcRead, fname, &accessRead,
                    &result, m_Filename.size() + 1);
    
    if (srcRead < 0)
        G4Exception("PSFReader::InitializeSource",
                    "", RunMustBeAborted, 
                    "Could not open IAEA source file to append");

    iaea_check_file_size_byte_order(&srcRead, &result);
    switch(result)
    {
    case -1:
        G4Exception("PSFReader::InitializeSource",
                    "", RunMustBeAborted, "Header does not exist");
        break;
    case -2:
        G4Exception("PSFReader::InitializeSource",
                    "", RunMustBeAborted, "Failure of function fseek");
        break;
    case -3:
        G4Exception("PSFReader::InitializeSource",
                    "", RunMustBeAborted, "There is a file size mismatch");
        break;
    case -4:
        G4Exception("PSFReader::InitializeSource",
                    "", RunMustBeAborted, "Byte order mismatch");
        break;
    case -5:
        G4Exception("PSFReader::InitializeSource",
                    "", RunMustBeAborted, "File size and byte order mismatch");
        break;
    default:
        break;
    }

#ifdef G4VERBOSE
    if (result > 0)
        G4cout << "Successfully opened " << m_Filename + ".IAEAphsp"
               << "for reading." << G4endl;
#endif

    // get num. of particle info
    IAEA_I32 particleType = -1; // To count all kind of particles
    IAEA_I64 nParticles;
    iaea_get_max_particles(&srcRead, &particleType, &nParticles);
    m_numTotalParticles = static_cast<G4long>(nParticles);

    // get num. extra
    IAEA_I32 numExtraFloats, numExtraInts;
    iaea_get_extra_numbers(&srcRead, &numExtraFloats, &numExtraInts);
    m_numExtraFloats = static_cast<G4int>(numExtraFloats);
    m_numExtraInts = static_cast<G4int>(numExtraInts);

    SetupRankParallelism();

#ifdef G4VERBOSE
    // print info
    G4cout << "---------- PSFReader ----------" << G4endl
           << "# Particles " << m_numTotalParticles << G4endl
           << "# extra Floats " << m_numExtraFloats << G4endl
           << "# extra Ints " << m_numExtraInts << G4endl
           << "chunkSize " << m_chunkSize << G4endl
           << "-------------------------------" << G4endl;
#endif
}

void PSFReader::SetupRankParallelism()
{   
    // mpi info
    m_numRanks = G4MPImanager::GetManager()->GetTotalSize();
    m_Rank = G4MPImanager::GetManager()->GetRank();

    // The parallel instance is the MPI Rank and the total
    // amount of chunks is equal to the total amount of
    // MPI ranks.
    const auto srcRead = static_cast<IAEA_I32>(s_srcRead);
    const auto iParallel = static_cast<IAEA_I32>(m_Rank);
    const auto iChunk = iParallel + 1;
    const auto nChunks = static_cast<IAEA_I32>(m_numRanks);

    IAEA_I32 result;
    iaea_set_parallel(&srcRead, &iParallel, &iChunk, &nChunks, &result);

    if (0 > result)
    {
        G4Exception("PSFReader::SetupRankParallelism()",
                    "", RunMustBeAborted,
                    "Error in IAEA file chunking!");
    }

    // In the case where #TotalParticles / #Ranks is not an integer,
    // the MPI Rank assigned to the last chunk of the PSF has to read
    // all particles which are left over -> changes to upper bound of
    // the particle index
    auto rest = m_numTotalParticles % m_numRanks;
    if (0 == rest)
    {
        // equal partitioning possible,
        // no special treatment needed
        m_chunkSize = m_numTotalParticles / m_numRanks;
    }
    else
    {
        // unequal partitioning, last rank has to read the
        // remaining particles
        auto evenChunkSize = m_numTotalParticles / m_numRanks;
        auto overflow = m_numTotalParticles - evenChunkSize * m_numRanks;

        if (m_Rank + 1 == m_numRanks)
            m_chunkSize = evenChunkSize + overflow;
        else
            m_chunkSize = evenChunkSize;
    }
}

void PSFReader::DestroySource()
{
    const auto srcRead = static_cast<IAEA_I32>(s_srcRead);

    // destroy source
    IAEA_I32 result;
    iaea_destroy_source(&srcRead, &result);

    if (result > 0)
    {
#ifdef G4VERBOSE
      G4cout << "IAEAphsp File closed successfully!" << G4endl;
#endif
    }
    else
    {
        G4Exception("PSFReader::DestroySource()",
                    "", JustWarning,
                    "IAEAphsp file not closed properly");
    }
}

IAEAParticle PSFReader::ReadNextParticle()
{   
    // protect every read from the PSF file
    std::lock_guard<std::mutex> lock(m_Mtx);

    if (m_partIdx >= m_chunkSize)
    {   
        G4String message = "Particle index larger or equal than chunk size "
                           "in Rank " + std::to_string(m_Rank);

        G4Exception("PSFReader::ReadNextParticle",
                    "", FatalException, message);
    }

    // temps
    IAEAParticle theParticle;
    IAEA_I32 type, nStat;
    IAEA_Float E, wt, x, y, z, u, v, w;
    std::array<IAEA_Float, NUM_EXTRA_FLOAT> extraFloats;
    std::array<IAEA_I32, NUM_EXTRA_LONG> extraInts;

    // read a particle from chunk
    auto srcRead = static_cast<IAEA_I32>(s_srcRead);
    iaea_get_particle(&srcRead, &nStat, &type,
                      &E, &wt, &x, &y, &z, &u, &v, &w, 
                      extraFloats.begin(), extraInts.begin());

    // particle position in psf file
    theParticle.psfIdx = m_numTotalParticles / m_numRanks * m_Rank + m_partIdx;

    // IAEA to G4
    theParticle.stat = static_cast<G4int>(nStat);
    theParticle.type = static_cast<G4int>(type);
    theParticle.energy = static_cast<G4double>(E);
    theParticle.weight = static_cast<G4double>(wt);
    theParticle.position.set(static_cast<G4double>(x),
                             static_cast<G4double>(y),
                             static_cast<G4double>(z));
    theParticle.momentum.set(static_cast<G4double>(u),
                             static_cast<G4double>(v),
                             static_cast<G4double>(w));

    // store extra values
    theParticle.extraFloats.fill(-1);
    theParticle.extraInts.fill(-1);
    if (m_numExtraFloats > 0)
    {  
        for (int i = 0; i < m_numExtraFloats; i++)
            theParticle.extraFloats[i] = static_cast<G4double>(extraFloats[i]); 
    }
    if (m_numExtraInts > 0)
    {  
        for (int i = 0; i < m_numExtraInts; i++)
            theParticle.extraInts[i] = static_cast<G4long>(extraInts[i]); 
    }

    G4cout << "PSF IDX " << theParticle.psfIdx << G4endl
           << "Part IDX " << m_partIdx << G4endl;

    // increase the particle counter
    m_partIdx++;

    return theParticle;
}