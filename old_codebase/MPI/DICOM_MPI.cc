#include "G4RunManagerFactory.hh"
#include "G4MPImanager.hh"
#include "G4MPIsession.hh"

#include "G4UImanager.hh"
#include "G4VisExecutive.hh"
#include "G4UIExecutive.hh"

#include "G4Types.hh"
#include "globals.hh"
#include "Randomize.hh"

#include "DicomRegularDetectorConstruction.hh"
#include "DicomActionInitialization.hh"
#include "PSFActionInitialization.hh"
#include "PhysicsList.hh"

#ifdef PSF_READ
#include <memory>
#include "PSFReader.hh"
#endif

//#include "CrossSectionAnalysis.hh"

int main(int argc, char **argv)
{
  // ui executive
  G4UIExecutive *ui = nullptr;
  if (std::string(argv[1]) == "vis.mac")
  {
    ui = new G4UIExecutive(argc, argv);
  }

  // create MPI Manager
  auto *g4MPI = new G4MPImanager(argc, argv);
  // MPI Session
  auto *session = g4MPI->GetMPIsession();

  // extract filenames from user input
  G4String inpG4DCM = argv[2];
  G4String outDoseFile = argv[3];

  // set random engine
  /*CLHEP::HepRandom::setTheEngine(new CLHEP::RanecuEngine);
    CLHEP::HepRandom::setTheSeed(42);
    long seeds[2];
    seeds[0] = 42;
    seeds[1] = 42;
    CLHEP::HepRandom::setTheSeeds(seeds);*/

  // user settings, number of threads to use
  // is the number of threads available per MPI process
  // -> OMP_NUM_THREADS environment variable
  auto *runManager = G4RunManagerFactory::CreateRunManager();
  auto nthreads = G4GetEnv<G4int>("OMP_NUM_THREADS", G4Thread::hardware_concurrency());
  runManager->SetNumberOfThreads(nthreads);

  // Initialisation of physics, geometry, primary particles ...
  auto *detectorConstruction = new DicomRegularDetectorConstruction(inpG4DCM);
  runManager->SetUserInitialization(detectorConstruction);
  runManager->SetUserInitialization(new PhysicsList());

#ifdef PSF_READ
  // Setup PSFReader
  G4String fname = "output/dev_cube/output_cubes/PSF_dev_cube_0_0-testsmall";
  auto sharedReader = std::make_shared<PSFReader>(fname);
  const auto nEvents = sharedReader->GetChunkSize();

  runManager->SetUserInitialization(new PSFActionInitialization(outDoseFile,
                                                                sharedReader));
#elif PSF_WRITE
  runManager->SetUserInitialization(new PSFActionInitialization(outDoseFile));
#else
  runManager->SetUserInitialization(new DicomActionInitialization(outDoseFile));
#endif
  runManager->Initialize();

  // visualization
  if (ui)
  {
    auto *visManager = new G4VisExecutive;
    visManager->Initialize();
    auto *UImanager = G4UImanager::GetUIpointer();
    UImanager->ApplyCommand("/control/execute vis.mac");
    ui->SessionStart();
    delete ui;
    delete visManager;
  }
  else
  {
    session->SessionStart();
  }

#ifdef PSF_READ
  g4MPI->BeamOn(nEvents, false);
#endif

  // CrossSectionAnalysis
  /*const auto usedMaterials = detectorConstruction->GetMaterialsPtr();
    auto xsAnalysis = CrossSectionAnalysis(usedMaterials, 50*CLHEP::keV);
    auto resultMap = xsAnalysis.ComputeCrossSectionsPerVolumeForGamma();
    xsAnalysis.Dump(resultMap, "xsAnalysis");*/

  delete g4MPI;
  delete runManager;

  return 0;
}