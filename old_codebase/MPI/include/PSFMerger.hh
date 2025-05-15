#pragma once

#include "globals.hh"
#include "iaea_config.h"

/*
 * This class gathers all .IAEAphsp files from different 
 * MPI Ranks and merges them into the .IAEAphsp file of rank #0.
 */
class PSFMerger
{
public:
    PSFMerger(G4String namingScheme, G4int nFiles);
    void Merge();
    void MergeASCII();

private:
    void InitAppendSource(IAEA_I32& srcID);
    void InitReadSource(IAEA_I32& srcID, G4int fileIdx);
    // Get particle from read src, add to append src
    void AppendParticle(const IAEA_I32& fromID, const IAEA_I32& toID);
    // Destroy IAEA source
    void DestroySource(const IAEA_I32& srcID, G4int fileIdx = 0);
    // Delete header and phsp file of given fileIdx
    void DeleteFile(G4int fileIdx);

private:
    // # of files to merge
    G4int m_nFiles;

    /* Naming scheme of the PSF files.
     * when merging, this class will open
     * m_nFiles source files where the files
     * are numerated by m_NameScheme_MPI-RANK.IAEAphsp
     */
    G4String m_namingScheme;

    // Particles in the currently open read-only file
    G4long m_nPartInCurrFile;

    IAEA_I64 m_totalOriginals;
    IAEA_I32 m_nExtraFloat;
    IAEA_I32 m_nExtraInt;
};