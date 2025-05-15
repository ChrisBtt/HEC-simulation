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

#include "DicomRunAction.hh"
#include "DicomRun.hh"

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

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
/// Constructor
// ###################################################################
DicomRunAction::DicomRunAction(const G4String& filename)
:   G4UserRunAction(), fDcmrun(0), fFieldValue(14), outname(filename)
{
    // - Prepare data member for DicomRun.
    //   vector represents a list of MultiFunctionalDetector names.
    fSDName.push_back(G4String("phantomSD"));
}
// ###################################################################

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
/// Destructor.
DicomRunAction::~DicomRunAction()
{
  fSDName.clear();
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
G4Run* DicomRunAction::GenerateRun()
{
  // Generate new RUN object, which is specially
  // dedicated for MultiFunctionalDetector scheme.
  //  Detail description can be found in DicomRun.hh/cc.
  //return new DicomRun(fSDName);
  return fDcmrun = new DicomRun(fSDName);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
void DicomRunAction::BeginOfRunAction(const G4Run* aRun)
{
  G4cout << "### Run " << aRun->GetRunID() << " start." << G4endl;
  //inform the runManager to save random number seed
  G4RunManager::GetRunManager()->SetRandomNumberStore(true);
  G4RunManager::GetRunManager()->SetRandomNumberStorePerEvent(false);
  G4RunManager::GetRunManager()->SetRandomNumberStoreDir(
              G4String("dicom-run-") + std::to_string(aRun->GetRunID()));

  int progress = aRun->GetNumberOfEventToBeProcessed() / 100;
  progress = (progress < 1) ? 1 : progress;
  G4RunManager::GetRunManager()->SetPrintProgress(progress);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
void DicomRunAction::EndOfRunAction(const G4Run* aRun)
{
  //G4AutoLock l(G4TypeMutex<DicomRunAction>());

  G4int nofEvents = aRun->GetNumberOfEvent();

  StatAnalysis local_total_dose;

  //static double local_total_dose = 0;
  //double total_dose = 0;

  const DicomRun* reRun = static_cast<const DicomRun*>(aRun);
  //--- Dump all scored quantities involved in DicomRun.
  for ( G4int i = 0; i < (G4int)fSDName.size(); i++ )
  {
    //
    //---------------------------------------------
    // Dump accumulated quantities for this RUN.
    //  (Display only central region of x-y plane)
    //      0       ConcreteSD/DoseDeposit
    //---------------------------------------------
    auto DoseDeposit =  reRun->GetStatVector(fSDName[i]+"/DoseDeposit");

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

  if(IsMaster()) 
  {
    G4cout << " ###### EndOfRunAction ###### " << G4endl;
    //- DicomRun object.
    const DicomRun* re02Run = static_cast<const DicomRun*>(aRun);
    //--- Dump all scored quantities involved in DicomRun.

    for ( G4int i = 0; i < (G4int)fSDName.size(); i++ )
    {
      //
      //---------------------------------------------
      // Dump accumulated quantities for this RUN.
      //  (Display only central region of x-y plane)
      //      0       ConcreteSD/DoseDeposit
      //---------------------------------------------
      auto DoseDeposit = re02Run->GetStatVector(fSDName[i]+"/DoseDeposit");

      G4cout << "============================================================="
             <<G4endl;
      G4cout << " Number of event processed : "
             << aRun->GetNumberOfEvent() << G4endl;
      G4cout << "============================================================="
             <<G4endl;

      std::ofstream fileout;
      fileout.open(this->outname);
      G4cout << " opened file " << this->outname << " for dose output" << G4endl;

      if( DoseDeposit && DoseDeposit->size() != 0 ) 
      {
        std::ostream *myout = &G4cout;
        PrintHeader(myout);

        for(auto itr = DoseDeposit->begin(); itr != DoseDeposit->end(); itr++) 
        {
          auto _idx = DoseDeposit->GetIndex(itr);
          auto _stat = DoseDeposit->GetObject(itr);
          if(_stat && _stat->GetHits() > 0)
          {
              auto _tmp_stat = *_stat;
              _tmp_stat /= CLHEP::gray;
              fileout << _idx << "     "  << _tmp_stat << G4endl;
          }
        }
        G4cout << "============================================="<<G4endl;
      } 
      else 
      {
        G4Exception("DicomRunAction", "000", JustWarning,
        "DoseDeposit HitsMap is either a null pointer of the HitsMap was empty");
      }
      fileout.close();
      G4cout << " closed file " << this->outname << " for dose output" << G4endl;

    }
  }

  if (IsMaster())
  {
      // convert to units of Gy
      auto dose = local_total_dose.GetSum() / gray;
      G4cout << "--------------------End of Global Run-----------------------"
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
  else
  {
      // convert to units of Gy
      auto dose = local_total_dose.GetSum() / gray;
      G4cout << "--------------------End of Local Run------------------------"
              << G4endl;
      G4cout << " The run was " << nofEvents << " events" << G4endl;
      G4cout << "LOCAL TOTAL DOSE : \t" << dose << " Gy" << G4endl;
      if(nofEvents > 0)
      {
          dose /= nofEvents;
          G4cout << " LOCAL DOSE/Bq-s : \t" << dose << " Gy/Bq-s"
                  << G4endl;
      }
  }
  G4cout << "Finished : End of Run Action " << aRun->GetRunID() << G4endl;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
void DicomRunAction::PrintHeader(std::ostream *out)
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
std::string DicomRunAction::FillString(const std::string &name,
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
