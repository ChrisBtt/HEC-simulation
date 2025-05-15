
#include "G4Types.hh"

#ifdef G4MULTITHREADED
#include "G4MTRunManager.hh"
#else
#include "G4RunManager.hh"
#endif

#include "globals.hh"
#include "G4UImanager.hh"
#include "Randomize.hh"

//#include "G4GenericPhysicsList.hh"

#include "DicomRegularDetectorConstruction.hh"
//#include "DicomNestedParamDetectorConstruction.hh"
//#include "DicomPartialDetectorConstruction.hh"

#include "DicomActionInitialization.hh"

//#include "DicomIntersectVolume.hh"
#include "QGSP_BIC.hh"
#include "G4tgrMessenger.hh"

#include "G4VisExecutive.hh"
#include "G4UIExecutive.hh"

//#include "Shielding.hh"
#include "PhysicsList.hh"

// #########################
#include <ctime>
// #########################
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

int main(int argc,char** argv)
{

  //std::cout << argv[0] << argv[1] << argv[2] << argv[3] << std::endl;

  // Instantiate G4UIExecutive if interactive mode
  G4UIExecutive* ui = nullptr;
  if ( (G4String)argv[1] == "vis.mac" ) {
    ui = new G4UIExecutive(argc, argv);
  }

  new G4tgrMessenger;

  CLHEP::HepRandom::setTheEngine(new CLHEP::RanecuEngine);
  CLHEP::HepRandom::setTheSeed(42);
  long seeds[2];
  seeds[0] = 42;
  seeds[1] = 42;
  CLHEP::HepRandom::setTheSeeds(seeds);

  // Construct the default run manager
#ifdef G4MULTITHREADED
  char* nthread_c = getenv("DICOM_NTHREADS");

  unsigned nthreads = 4;
  unsigned env_threads = 0;

  if(nthread_c) { env_threads = G4UIcommand::ConvertToDouble(nthread_c); }
  if(env_threads > 0) { nthreads = env_threads; }

  G4MTRunManager* runManager = new G4MTRunManager;
  runManager->SetNumberOfThreads(nthreads);

  G4cout << "\n\n\tDICOM running in multithreaded mode with " << nthreads
         << " threads\n\n" << G4endl;


#else
  G4RunManager* runManager = new G4RunManager;
  G4cout << "\n\n\tDICOM running in serial mode\n\n" << G4endl;

#endif

  // Initialisation of physics, geometry, primary particles ...
  DicomRegularDetectorConstruction* theGeometry = new DicomRegularDetectorConstruction(argv[2]);
  runManager->SetUserInitialization(theGeometry);

  G4VModularPhysicsList* phys = new PhysicsList();
  runManager->SetUserInitialization(phys);

  // Set user action classes
  runManager->SetUserInitialization(new DicomActionInitialization(argv[3]));
  runManager->Initialize();

  // visualisation manager
  G4VisManager* visManager = new G4VisExecutive;
  visManager->Initialize();

  G4UImanager* UImanager = G4UImanager::GetUIpointer();

  G4String command = "/control/execute ";
  G4String fileName = argv[1];

  if (ui)
    {
      UImanager->ApplyCommand(command + fileName);
      ui->SessionStart();
      delete ui;
    }
  else
    {
      UImanager->ApplyCommand(command + fileName);
    }

  delete visManager;
  delete runManager;

  return 0;
}

