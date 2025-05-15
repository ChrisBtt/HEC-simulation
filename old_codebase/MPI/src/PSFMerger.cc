#include "PSFMerger.hh"

#include <iostream>
#include <fstream>

#include <stdio.h>

#include "globals.hh"

#include "iaea_phsp.h"
#include "iaea_record.h"

PSFMerger::PSFMerger(G4String namingScheme, G4int nFiles)
: m_namingScheme(namingScheme), m_nFiles(nFiles),
  m_nPartInCurrFile(-1), m_nExtraFloat(-1), m_nExtraInt(-1),
  m_totalOriginals(0)
{}

void PSFMerger::Merge()
{
    if (m_nFiles > 1)
    {
        IAEA_I32 srcAppend = 0;
        IAEA_I32 srcRead = 1;

        // initialize source file that is going to grow
        InitAppendSource(srcAppend);

        // loop over all the other files
        for(int i = 1; i < m_nFiles; i++)
        {
            // initialize the read source
            InitReadSource(srcRead, i);

            // loop over all particles
            for(int iPart = 0; iPart < m_nPartInCurrFile; iPart++)
                AppendParticle(srcRead, srcAppend);

            // destroy the source. it is no longer needed
            DestroySource(srcRead, i);

            // delete the file
            DeleteFile(i);
        }
        
        // update the total number of events stored in the append file
        iaea_set_total_original_particles(&srcAppend, &m_totalOriginals);

        // destroy final source
        DestroySource(srcAppend);
    }
    else 
    {
        G4cout << "There is only one Rank, no merging of PSFs is performed." << G4endl;
    }
}

void PSFMerger::InitAppendSource(IAEA_I32& srcID)
{
    // access read 3 for appending/updatig a src file
    const IAEA_I32 accessAppend = 3;

    // append data to rank #0 file
    auto fullName = m_namingScheme + "_0";
    G4cout << fullName << G4endl;
    auto fileName = const_cast<char*>(fullName.data());

    // open src file
    IAEA_I32 result;
    iaea_new_source(&srcID, fileName, &accessAppend,
                    &result, fullName.size() + 1);

    if (srcID < 0)
        G4Exception("PSFMerger::InitAppendSource",
                    "", RunMustBeAborted, 
                    "Could not open IAEA source file to append");

    iaea_check_file_size_byte_order(&srcID, &result);
    switch(result)
    {
    case -1:
        G4Exception("PSFMerger::InitAppendSource",
                    "", RunMustBeAborted, "Header does not exist");
        break;
    case -2:
        G4Exception("PSFMerger::InitAppendSource",
                    "", RunMustBeAborted, "Failure of function fseek");
        break;
    case -3:
        G4Exception("PSFMerger::InitAppendSource",
                    "", RunMustBeAborted, "There is a file size mismatch");
        break;
    case -4:
        G4Exception("PSFMerger::InitAppendSource",
                    "", RunMustBeAborted, "Byte order mismatch");
        break;
    case -5:
        G4Exception("PSFMerger::InitAppendSource",
                    "", RunMustBeAborted, "File size and byte order mismatch");
        break;
    default:
        break;
    }

#ifdef G4VERBOSE
    if (result > 0)
        G4cout << "Successfully opened " << fullName + ".IAEAphsp"
               << "for appending." << G4endl;
#endif

    // number of original particles (events)
    iaea_get_total_original_particles(&srcID, &m_totalOriginals);

    // extra variables info
    // these have to match with the sources which are read from
    IAEA_I32 nExtraFloat, nExtraInt;
    iaea_get_extra_numbers(&srcID, &nExtraFloat, &nExtraInt);
    m_nExtraFloat = static_cast<G4int>(nExtraFloat);
    m_nExtraInt = static_cast<G4int>(nExtraInt);
}

void PSFMerger::InitReadSource(IAEA_I32& srcID, G4int fileIdx)
{
    // read access for opening file to read
    const IAEA_I32 accessRead = 1;

    // initialize src with index fileIdx
    auto fullName = m_namingScheme + "_" + std::to_string(fileIdx);
    auto fileName = const_cast<char*>(fullName.data());

    // open src file
    IAEA_I32 result;
    iaea_new_source(&srcID, fileName, &accessRead,
                    &result, fullName.size() + 1);

    if (srcID < 0)
        G4Exception("PSFMerger::InitReadSource",
                    "", RunMustBeAborted, 
                    "Could not open IAEA source file to append");

    iaea_check_file_size_byte_order(&srcID, &result);
    switch(result)
    {
    case -1:
        G4Exception("PSFMerger::InitReadSource",
                    "", RunMustBeAborted, "Header does not exist");
        break;
    case -2:
        G4Exception("PSFMerger::InitReadSource",
                    "", RunMustBeAborted, "Failure of function fseek");
        break;
    case -3:
        G4Exception("PSFMerger::InitReadSource",
                    "", RunMustBeAborted, "There is a file size mismatch");
        break;
    case -4:
        G4Exception("PSFMerger::InitReadSource",
                    "", RunMustBeAborted, "Byte order mismatch");
        break;
    case -5:
        G4Exception("PSFMerger::InitReadSource",
                    "", RunMustBeAborted, "File size and byte order mismatch");
        break;
    default:
        break;
    }

#ifdef G4VERBOSE
    if (result > 0)
        G4cout << "Successfully opened " << fullName + ".IAEAphsp"
               << "for reading." << G4endl;
#endif

    // number of original particles (events)
    IAEA_I64 nOriginals;
    iaea_get_total_original_particles(&srcID, &nOriginals);
    m_totalOriginals += nOriginals;

    // gather file info
    IAEA_I32 particleType = -1; // To count all kind of particles
    IAEA_I64 nParticles;
    iaea_get_max_particles(&srcID, &particleType, &nParticles);
    m_nPartInCurrFile = static_cast<G4long>(nParticles);

    // extra variables info
    IAEA_I32 nExtraFloat, nExtraInt;
    iaea_get_extra_numbers(&srcID, &nExtraFloat, &nExtraInt);
    
    if( (nExtraFloat != m_nExtraFloat) || (nExtraInt != m_nExtraInt) )
    {
        G4Exception("PSFMerger::InitReadSource",
                    "", RunMustBeAborted,
                    "Number of Extra variables does not match across files.");
    }
}

void PSFMerger::AppendParticle(const IAEA_I32& fromID, const IAEA_I32& toID)
{
    // Particle properties
    IAEA_I32 type, nStat;
    IAEA_Float E, wt, x, y, z, u, v, w;
    IAEA_Float extraFloats[NUM_EXTRA_FLOAT];
    IAEA_I32 extraInts[NUM_EXTRA_LONG];

    // fetches the particle from read source
    iaea_get_particle(&fromID, &nStat, &type,
                      &E, &wt, &x, &y, &z, &u, &v, &w, 
                      &extraFloats[0], &extraInts[0]);

    // append to file
    iaea_write_particle(&toID, &nStat, &type,
                        &E, &wt, &x, &y, &z, &u, &v, &w, 
                        &extraFloats[0], &extraInts[0]);
}

void PSFMerger::DestroySource(const IAEA_I32& srcID, G4int fileIdx)
{   
    // destroy source
    IAEA_I32 result;
    iaea_destroy_source(&srcID, &result);

    if (result > 0)
    {
#ifdef G4VERBOSE
      G4cout << "IAEAphsp File closed successfully!" << G4endl;
#endif
    }
    else
    {
        G4Exception("PSFMerger::DestroySource()",
                    "", JustWarning,
                    "IAEAphsp file not closed properly");
    }
}

void PSFMerger::DeleteFile(G4int fileIdx)
{
    // remove file
    const auto targetFileName = m_namingScheme + "_" + std::to_string(fileIdx);
    bool rmResult;

    // header
    const auto headerPath = targetFileName + ".IAEAheader";
    rmResult = remove(headerPath.data());
    if (rmResult != 0)
    {
        G4String warnMessage = "Failed to remove " + headerPath;
        G4Exception("PSFMerger::DeleteFile", "",
                    JustWarning, warnMessage);
    }

    // actual phsp
    const auto phspPath = targetFileName + ".IAEAphsp";
    rmResult = remove(phspPath.data());
    if (rmResult != 0)
    {
        G4String warnMessage = "Failed to remove " + phspPath;
        G4Exception("PSFMerger::DeleteFile", "",
                    JustWarning, warnMessage);
    }
}

void PSFMerger::MergeASCII()
{
    // append data to rank #0 file
    auto fullName = m_namingScheme + "_0";
    auto fileName = fullName + ".txt";
    std::ofstream writeFile;
    writeFile.open(fileName, std::ios_base::app);

    if ( !writeFile )
    {
        G4String warnMessage = fileName + " write file could not be opened";
        G4Exception("PSFMerger::MergeASCII()",
                    "", JustWarning,
                    warnMessage);
    }

    // loop over all the other files
    for(int i = 1; i < m_nFiles; i++)
    {
        // initialize the read source
        auto fullNameRead = m_namingScheme + "_" + std::to_string(i);
        auto fileNameRead = fullNameRead + ".txt";
        std::ifstream readFile;
        readFile.open((fileNameRead));

        if ( !readFile )
        {
            G4String warnMessage = fileNameRead + " read file could not be opened";
            G4Exception("PSFMerger::MergeASCII()",
                        "", JustWarning,
                        warnMessage);
        }

        // loop over all particles
        std::string content = "";
        int j;
        for(j = 0; readFile.eof() != true; j++)
            content += readFile.get();
        j--;
        content.erase(content.end()-1);

        // append to file
        writeFile << content;

        //close ascii read file
        readFile.close();

        // delete the file
        bool rmResult;
        rmResult = remove(fileNameRead.data());
        if (rmResult != 0)
        {
            G4String warnMessage = "Failed to remove " + fileNameRead;
            G4Exception("PSFMerger::MergeASCII()", "",
                        JustWarning, warnMessage);
        }
    }
    //close ascii write file
    writeFile.close();
}