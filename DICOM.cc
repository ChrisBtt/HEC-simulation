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
/// \file medical/DICOM/DICOM.cc
/// \brief Main program of the medical/DICOM example
//
// The code was written by :
//        *Louis Archambault louis.archambault@phy.ulaval.ca,
//      *Luc Beaulieu beaulieu@phy.ulaval.ca
//      +Vincent Hubert-Tremblay at tigre.2@sympatico.ca
//
//
// *Centre Hospitalier Universitaire de Quebec (CHUQ),
// Hotel-Dieu de Quebec, departement de Radio-oncologie
// 11 cote du palais. Quebec, QC, Canada, G1R 2J6
// tel (418) 525-4444 #6720
// fax (418) 691 5268
//
// + Université Laval, Québec (QC) Canada
// *******************************************************
#include "DicomActionInitialization.hh"
#include "DicomRegularDetectorConstruction.hh"

#include "G4GenericPhysicsList.hh"
#include "G4RunManagerFactory.hh"
#include "G4Types.hh"
#include "G4UImanager.hh"
#include "Randomize.hh"
#include "globals.hh"

#include "DicomHandler.hh"

#include "QGSP_BIC.hh"
#include "PhysicsList.hh"

#include "G4UIExecutive.hh"
#include "G4VisExecutive.hh"
#include "G4tgrMessenger.hh"
#include "PrimaryGeneratorMessenger.hh"

int main(int argc, char** argv)
{
  // Instantiate G4UIExecutive if interactive mode
  G4UIExecutive* ui = nullptr;
  if (argc == 1) {
    ui = new G4UIExecutive(argc, argv);
  }

  std::vector<G4String> replacementData;
  if (argc >= 3) {
    // Parse replacement data from second argument
    std::istringstream iss(argv[2]);
    std::string token;
    while (std::getline(iss, token, ',')) {
      replacementData.push_back(token);
    }
  } else {
    // Default replacement data
    //replacementData = {"0.", "0.", "0.", "0.", "0.", "0.", "ELLIPSOID", "15.", "15.", "15.", "0.", "0."};
  }

  // CLHEP::HepRandom::setTheEngine(new CLHEP::RanecuEngine);
  // CLHEP::HepRandom::setTheSeed(G4long(24534575684783));
  // G4long seeds[2];
  // seeds[0] = G4long(534524575674523);
  // seeds[1] = G4long(526345623452457);
  // CLHEP::HepRandom::setTheSeeds(seeds);

  // Construct the default run manager
  char* nthread_c = std::getenv("DICOM_NTHREADS");

  unsigned nthreads = 4;
  unsigned env_threads = 0;

  if (nthread_c) {
    env_threads = unsigned(G4UIcommand::ConvertToDouble(nthread_c));
  }
  if (env_threads > 0) {
    nthreads = env_threads;
  }

  auto* runManager = G4RunManagerFactory::CreateRunManager();
  runManager->SetNumberOfThreads(nthreads);

  // Treatment of DICOM images before creating the G4runManager
  DicomHandler* dcmHandler = DicomHandler::Instance();
  dcmHandler->CheckFileFormat();

  DicomDetectorConstruction* theGeometry = new DicomRegularDetectorConstruction();
  theGeometry->SetReplacementData(replacementData);

  runManager->SetUserInitialization(theGeometry);

  G4VModularPhysicsList* phys = new PhysicsList();
  runManager->SetUserInitialization(phys);

  // Set user action classes
  runManager->SetUserInitialization(new DicomActionInitialization());

  runManager->Initialize();

  // visualisation manager
  G4VisManager* visManager = new G4VisExecutive;
  visManager->Initialize();

  G4UImanager* UImanager = G4UImanager::GetUIpointer();

  if (ui) {
    UImanager->ApplyCommand("/control/execute vis.mac");
    ui->SessionStart();
    delete ui;
  }
  else {
    G4String command = "/control/execute ";
    G4String fileName = argv[1];
    UImanager->ApplyCommand(command + fileName);
  }

  delete visManager;
  delete runManager;

  return 0;
}
