

#include "DicomRun.hh"
#include "G4SDManager.hh"

#include "G4MultiFunctionalDetector.hh"
#include "G4VPrimitiveScorer.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//
//  Constructor. 
DicomRun::DicomRun()
: G4Run()
{
  fSerializer = std::make_unique<Serializer>();
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//
//  Constructor.
//   (The vector of MultiFunctionalDetector name has to given.)
DicomRun::DicomRun(const std::vector<G4String> mfdName): G4Run()
{
  fSerializer = std::make_unique<Serializer>();

  ConstructMFD(mfdName);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//
// Destructor
//    clear all data members.
DicomRun::~DicomRun()
{
  //--- Clear HitsMap for RUN
  G4int Nmap = fRunMap.size();
  for ( G4int i = 0; i < Nmap; i++){
    if(fRunMap[i] ) fRunMap[i]->clear();
  }
  fCollName.clear();
  fCollID.clear();
  fRunMap.clear();
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//
// Destructor
//    clear all data members.
void DicomRun::ConstructMFD(const std::vector<G4String>& mfdName)
{
  G4SDManager* SDman = G4SDManager::GetSDMpointer();
  //=================================================
  //  Initalize RunMaps for accumulation.
  //  Get CollectionIDs for HitCollections.
  //=================================================
  G4int Nmfd = mfdName.size();
  for ( G4int idet = 0; idet < Nmfd ; idet++){  // Loop for all MFD.
    G4String detName = mfdName[idet];
    //--- Seek and Obtain MFD objects from SDmanager.
    G4MultiFunctionalDetector* mfd =
      (G4MultiFunctionalDetector*)(SDman->FindSensitiveDetector(detName));
    //
    if ( mfd ){
      //--- Loop over the registered primitive scorers.
      for (G4int icol = 0; icol < mfd->GetNumberOfPrimitives(); icol++){
        // Get Primitive Scorer object.
        G4VPrimitiveScorer* scorer = mfd->GetPrimitive(icol);
        // collection name and collectionID for HitsCollection,
        // where type of HitsCollection is G4THitsMap in case 
        // of primitive scorer.
        // The collection name is given by <MFD name>/<Primitive 
        // Scorer name>.
        G4String collectionName = scorer->GetName();
        G4String fullCollectionName = detName+"/"+collectionName;
        G4int    collectionID = SDman->GetCollectionID(fullCollectionName);
        //
        if ( collectionID >= 0 ){
          G4cout << "++ "<<fullCollectionName<< " id " << collectionID 
                 << G4endl;
          // Store obtained HitsCollection information into data members.
          // And, creates new G4THitsMap for accumulating quantities during RUN.
          fCollName.push_back(fullCollectionName);
          fCollID.push_back(collectionID);
          fRunMap.push_back(new StatVector(detName,collectionName));

        } else {
          G4cout << "** collection " << fullCollectionName << " not found. "
                 <<G4endl;
        }
      }
    }
  }
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//
//  RecordEvent is called at end of event.
//  For scoring purpose, the resultant quantity in a event,
//  is accumulated during a Run.
void DicomRun::RecordEvent(const G4Event* aEvent)
{
  // disable below because this is done in G4Run::RecordEvent(aEvent);
  //numberOfEvent++;  // This is an original line.
  
  //G4cout << "Dicom Run :: Recording event " << aEvent->GetEventID() 
  //<< "..." << G4endl;
  //=============================
  // HitsCollection of This Event
  //============================

  if (aEvent != nullptr) 
  {
    auto HCE = aEvent->GetHCofThisEvent();

    if (!HCE) return;
    
    //=======================================================
    // Sum up HitsMap of this Event  into HitsMap of this RUN
    //=======================================================
    G4int Ncol = fCollID.size();
    for ( G4int i = 0; i < Ncol ; i++ ) // Loop over HitsCollection
    {  
      G4THitsMap<G4double>* EvtMap = nullptr;

      if ( fCollID[i] >= 0 )
      {          
        EvtMap = static_cast<G4THitsMap<G4double>*>(HCE->GetHC(fCollID[i]));
      }
      else
      {
        G4cout <<" Error EvtMap Not Found "<< i << G4endl;
      }
      if ( EvtMap )  {
        //=== Sum up HitsMap of this event to HitsMap of RUN.===
        *fRunMap[i] += *EvtMap;
        /*auto iter = EvtMap->begin();
        for (; iter != EvtMap->end(); iter++) {
          G4cout << "Voxel idx" << iter->first << "Dose" << *(iter->second) << G4endl;
        }*/
        //G4cout << "Summing EvtMap into RunMap at " << i << "..." << G4endl;
        //======================================================
      } 
    }
  }
  
  G4Run::RecordEvent(aEvent); 
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
// Merge hits map from threads
void DicomRun::Merge(const G4Run* aRun)
{
  auto localRun = static_cast<const DicomRun*>(aRun);
  
  // if serializer is not a nullptr, there are arrays to be unpacked
  if (localRun->GetSerializer()->needsUnpacking)
  {
    // statVec now holds all the processed events of aRun
    auto statVec = localRun->GetSerializer()->Unpack();

    // apply the statVector to the localRun
    *(localRun->fRunMap)[0] = *statVec;
  }

  // this is untouched
  Copy(fCollName, localRun->fCollName);
  Copy(fCollID, localRun->fCollID);
  unsigned ncopies = Copy(fRunMap, localRun->fRunMap);
  // copy function returns the fRunMap size if all data is copied
  // so this loop isn't executed the first time around
  for(unsigned i = ncopies; i < fRunMap.size(); ++i) {
    *fRunMap[i] += *localRun->fRunMap[i];
  }
  
  G4Run::Merge(aRun);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//=================================================================
//  Access method for HitsMap of the RUN
//
//-----
// Access HitsMap.
//  By  MultiFunctionalDetector name and Collection Name.
DicomRun::StatVector* DicomRun::GetStatVector(const G4String& detName,
                                           const G4String& colName) const
{
  G4String fullName = detName+"/"+colName;
  return GetStatVector(fullName);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
// Access HitsMap.
//  By full description of collection name, that is
//    <MultiFunctional Detector Name>/<Primitive Scorer Name>
DicomRun::StatVector* DicomRun::GetStatVector(const G4String& fullName) const
{
  
  //G4THitsMap<G4double>* hitsmap = 0;
  
  G4int Ncol = fCollName.size();
  for ( G4int i = 0; i < Ncol; i++){
    if ( fCollName[i] == fullName ){
      return fRunMap[i];
            //if(hitsmap) { *hitsmap += *fRunMap[i]; }
            //if(!hitsmap) { hitsmap = fRunMap[i]; }
    }
  }
  
  //if(hitsmap) { return hitsmap; }
  
  G4Exception("DicomRun", fullName.c_str(), JustWarning,
              "GetHitsMap failed to locate the requested HitsMap");
  return nullptr;
}

const std::vector<DicomRun::StatVector*>* DicomRun::GetRunMap() const
{ 
  return &fRunMap;
}