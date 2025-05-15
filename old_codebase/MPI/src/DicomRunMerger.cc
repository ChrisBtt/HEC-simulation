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
#include "DicomRunMerger.hh"
#include "DicomRun.hh"
#include "Serializer.hh"

#include <memory>

void DicomRunMerger::Pack() {

  // initalize the Serializer
  auto serializer = fRun->GetSerializer();
  // suboptimal solution, fixed collection name
  serializer->Pack(fRun->GetStatVector("phantomSD/DoseDeposit"));

  // buffer size = total voxel count
  auto buffsize = serializer->GetBufferSize();

  // prepare buffers for sending
  InputUserData(serializer->GetSum1Ptr(), MPI::DOUBLE, buffsize);
  InputUserData(serializer->GetSum2Ptr(), MPI::DOUBLE, buffsize);
  InputUserData(serializer->GetHitsPtr(), MPI::UNSIGNED_LONG, buffsize);
  InputUserData(serializer->GetZerosPtr(), MPI::UNSIGNED_LONG, buffsize);

}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
G4Run* DicomRunMerger::UnPack() {

  // suboptimal solution, fixed collection name
  std::vector<G4String> mfdName = {"phantomSD"};

  // Create a dummy user-Run, used to contain data received via MPI
  DicomRun* aDummyRun = new DicomRun(mfdName);

  // buffer sizes = total number of voxels
  auto buffsize = aDummyRun->GetSerializer()->GetBufferSize();

  // set the outputbuffers where user data is put after receiving
  OutputUserData(aDummyRun->GetSerializer()->GetSum1Ptr(), MPI::DOUBLE, buffsize);
  OutputUserData(aDummyRun->GetSerializer()->GetSum2Ptr(), MPI::DOUBLE, buffsize);
  OutputUserData(aDummyRun->GetSerializer()->GetHitsPtr(), MPI::UNSIGNED_LONG, buffsize);
  OutputUserData(aDummyRun->GetSerializer()->GetZerosPtr(), MPI::UNSIGNED_LONG, buffsize);
  
  // set unpacking flag of serializer
  aDummyRun->GetSerializer()->needsUnpacking = true;

  return aDummyRun;
}
