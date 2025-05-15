//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
//
/// \file DicomRunAction.cc
/// \brief Implementation of the DicomRunAction class
//

#include "DicomRunActionMaster.hh"
#include "DicomRun.hh"
#include "DicomRunMerger.hh"

//-- In order to obtain detector information.
#include <fstream>
#include <iomanip>
#include "G4THitsMap.hh"

#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "StatAnalysis.hh"

#include "G4RunManager.hh"

#include "DicomHandler.hh"
#include "G4Exception.hh"

#include "G4MPImanager.hh"

// phsp writing
#include "PSFWriter.hh"
#include "PSFMerger.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
/// Constructor
// ###################################################################
DicomRunActionMaster::DicomRunActionMaster(const G4String& filename)
:   G4UserRunAction(), fDcmrun(0), fFieldValue(14), outname(filename)
{
    // - Prepare data member for DicomRun.
    //   vector represents a list of MultiFunctionalDetector names.
    fSDName.push_back(G4String("phantomSD"));
}
// ###################################################################

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
/// Destructor.
DicomRunActionMaster::~DicomRunActionMaster()
{
  fSDName.clear();
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
G4Run* DicomRunActionMaster::GenerateRun()
{
  // Generate new RUN object, which is specially
  // dedicated for MultiFunctionalDetector scheme.
  //  Detail description can be found in DicomRun.hh/cc.
  //return new DicomRun(fSDName);
  return fDcmrun = new DicomRun(fSDName);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
void DicomRunActionMaster::BeginOfRunAction(const G4Run* aRun)
{
  G4cout << "### Run " << aRun->GetRunID() << " start." << G4endl;
#ifdef PSF_WRITE
  auto phspWriter = PSFWriter::GetInstance();
  phspWriter->SetFileName(GetOutName(), true);
  phspWriter->SetCutEnergy(30. * CLHEP::keV);
  phspWriter->SetWriteASCII();
  phspWriter->BeginOfRunAction(aRun);
#endif
  /*inform the runManager to save random number seed
  G4RunManager::GetRunManager()->SetRandomNumberStore(true);
  G4RunManager::GetRunManager()->SetRandomNumberStorePerEvent(false);
  G4RunManager::GetRunManager()->SetRandomNumberStoreDir(
              G4String("dicom-run-") + std::to_string(aRun->GetRunID()));

  int progress = aRun->GetNumberOfEventToBeProcessed() / 100;
  progress = (progress < 1) ? 1 : progress;
  G4RunManager::GetRunManager()->SetPrintProgress(progress);*/
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
void DicomRunActionMaster::EndOfRunAction(const G4Run* aRun)
{
  // DicomRunActionMaster has the task to merge across ranks
  // of MPI instances using the RunMerger.
  // Local threads should have already merged their
  // results to the master thread.
  G4AutoLock l(G4TypeMutex<DicomRunActionMaster>());

  // mpi rank
  const auto rank = G4MPImanager::GetManager()->GetRank();

  G4cout << "=====================================================" << G4endl;
  G4cout << "Start EndOfRunAction for master thread in rank: " << rank << G4endl;
  G4cout << "=====================================================" << G4endl;

#ifdef PSF_WRITE
  // Call EndOfRunAction of the IAEAWriter
  PSFWriter::GetInstance()->EndOfRunAction(aRun);
#endif

  // report local dose, i.e. dose accumulated accross the MPI rank run
  StatAnalysis local_total_dose;
  auto theRun = static_cast<const DicomRun*>(aRun);

  //--- Dump all scored quantities involved in DicomRun.
  for ( G4int i = 0; i < (G4int)fSDName.size(); i++ )
  {
    auto DoseDeposit =  theRun->GetStatVector(fSDName[i]+"/DoseDeposit");

    if(DoseDeposit && DoseDeposit->size() != 0 )
    {
        for(auto itr = DoseDeposit->begin(); itr != DoseDeposit->end(); ++itr)
        {
            // this will sometimes return null pointers
            if(!DoseDeposit->GetObject(itr))
                continue;
            local_total_dose += (*DoseDeposit->GetObject(itr));
        }
    }
  }

  G4int nofEvents = theRun->GetNumberOfEvent();

  // convert to units of Gy
  auto dose = local_total_dose.GetSum() / gray;
  G4cout << "--------------------End of a MPI Run-----------------------"
          << G4endl;
  G4cout << " The run was " << nofEvents << " events " << G4endl;
  G4cout << "      TOTAL DOSE : \t" << dose << " Gy" << G4endl;
  if(nofEvents > 0)
  {
      dose /= nofEvents;
      G4cout << " TOTAL DOSE/Bq-s : \t" << dose << " Gy/Bq-s"
              << G4endl;
  }

  // --- MERGE ---
  //Merging of G4Run object:
  //All ranks > 0 merge to rank #0
  auto runMerger = std::make_unique<DicomRunMerger>(theRun);
#ifdef G4VERBOSE
  runMerger->SetVerbosity(4); // 4 max
#else
  runMerger->SetVerbosity(0);
#endif
  runMerger->Merge();

  // dump total dose and per voxel statistics to output file
  // in rank 0 after merge
  if(rank == 0) 
  {
    G4cout << " ###### EndOfRunAction RANK 0 ###### " << G4endl;

#ifdef PSF_WRITE
    // merge PSF files
    auto nPSFFiles = G4MPImanager::GetManager()->GetTotalSize();
    auto namingScheme = PSFWriter::GetInstance()->GetFileName();
    auto psfMerger = std::make_unique<PSFMerger>(namingScheme, nPSFFiles);
    psfMerger->Merge();
    if (PSFWriter::GetInstance()->GetWriteASCII())
    {
        psfMerger->MergeASCII();
    }
#endif

    for ( G4int i = 0; i < (G4int)fSDName.size(); i++ )
    {
      //
      //---------------------------------------------
      // Dump accumulated quantities for this RUN.
      //  (Display only central region of x-y plane)
      //      0       ConcreteSD/DoseDeposit
      //---------------------------------------------
      auto DoseDeposit = theRun->GetStatVector(fSDName[i]+"/DoseDeposit");

      G4cout << "============================================================="
             <<G4endl;
      G4cout << " Number of event processed : "
             << aRun->GetNumberOfEvent() << G4endl;
      G4cout << "============================================================="
             <<G4endl;

      // master rank opens file for output
      std::ofstream fileout;
      fileout.open(this->outname);
      G4cout << " opened file " << this->outname << " for dose output" << G4endl;

      local_total_dose.Reset();
      if( DoseDeposit && DoseDeposit->size() != 0 ) 
      {
        //std::ostream *myout = &G4cout;
        //PrintHeader(myout);

        for(auto itr = DoseDeposit->begin(); itr != DoseDeposit->end(); itr++) 
        {
          auto _idx = DoseDeposit->GetIndex(itr);
          auto _stat = DoseDeposit->GetObject(itr);
          if(_stat && _stat->GetHits() > 0)
          {
              auto _tmp_stat = *_stat;
              
              local_total_dose += _tmp_stat;

              _tmp_stat /= CLHEP::gray;
              fileout << _idx << "     "  << _tmp_stat << G4endl;
          }
        }
        G4cout << "============================================="<<G4endl;
      } 
      else 
      {
        G4Exception("DicomRunActionMaster", "000", JustWarning,
        "DoseDeposit HitsMap is either a null pointer of the HitsMap was empty");
      }
      fileout.close();
      G4cout << " closed file " << this->outname << " for dose output" << G4endl;

    }

    nofEvents = theRun->GetNumberOfEvent();
    // convert to units of Gy
    dose = local_total_dose.GetSum() / gray;
    G4cout << "--------------------GLOBAL END-----------------------"
            << G4endl;
    G4cout << " The run was " << nofEvents << " events " << G4endl;
    G4cout << "      TOTAL DOSE : \t" << dose << " Gy" << G4endl;
    if(nofEvents > 0)
    {
        dose /= nofEvents;
        G4cout << " TOTAL DOSE/Bq-s : \t" << dose << " Gy/Bq-s"
                << G4endl;
    }
  }

 
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
void DicomRunActionMaster::PrintHeader(std::ostream *out)
{
  std::vector<G4String> vecScoreName;
  vecScoreName.push_back("DoseDeposit");

  // head line
  //
  std::string vname;
  *out << std::setw(10) << "Voxel" << " |";
  for (std::vector<G4String>::iterator it = vecScoreName.begin();
       it != vecScoreName.end(); it++) {
    //vname = FillString((*it),
    //                       ' ',
    //                       FieldValue+1,
    //                       false);
    //    *out << vname << '|';
    *out << std::setw(fFieldValue) << (*it) << "  |";
  }
  *out << G4endl;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
std::string DicomRunActionMaster::FillString(const std::string &name,
                                       char c, G4int n, G4bool back)
{
  std::string fname("");
  G4int k = n - name.size();
  if (k > 0) {
    if (back) {
      fname = name;
      fname += std::string(k,c);
    }
    else {
      fname = std::string(k,c);
      fname += name;
    }
  }
  else {
    fname = name;
  }
  return fname;
}
