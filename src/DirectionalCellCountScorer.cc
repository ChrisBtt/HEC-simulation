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
//
// G4PSPassageCellCurrent
#include "DirectionalCellCountScorer.hh"
#include "G4StepStatus.hh"
#include "G4Track.hh"
#include "G4VSolid.hh"
#include "G4UnitsTable.hh"
#include "G4VScoreHistFiller.hh"

////////////////////////////////////////////////////////////////////////////////
// (Description)
//   This is a primitive scorer class for scoring the particle count along
//   a specified axis.
//
// Created: 2005-11-14  Tsukasa ASO, Akinori Kimura.
// 2010-07-22   Introduce Unit specification.
// 2010-07-22   Add weighted option
// 2020-10-06   Use G4VPrimitivePlotter and fill 1-D histo of kinetic energy (x)
//              vs. count * track weight (y)               (Makoto Asai)
// 2025-05-27   Use G4PSPassageCellCurrent as base for DirectionalCellcountScorer
//
///////////////////////////////////////////////////////////////////////////////

DirectionalCellCountScorer::DirectionalCellCountScorer(const G4String& name, EAxis axis, G4int depth)
  : G4VPrimitivePlotter(name, depth), eAxis(axis)
{
  SetUnit("");
}

G4bool DirectionalCellCountScorer::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
  const G4StepPoint* preStepPoint = aStep->GetPreStepPoint();
  const G4StepPoint* postStepPoint = aStep->GetPostStepPoint();

  const G4ThreeVector& pos1 = preStepPoint->GetPosition();
  const G4ThreeVector& pos2 = postStepPoint->GetPosition();

  G4ThreeVector voxelPos = preStepPoint->GetTouchable()->GetHistory()->GetTopTransform().Inverse().TransformPoint({0,0,0});

  // Get global position of the current volume
  G4int index = GetIndex(aStep);

  G4double count;

  if (pos1[eAxis] < voxelPos[eAxis] && pos2[eAxis] > voxelPos[eAxis]) {
    count = 1.0;
  } else if (pos1[eAxis] > voxelPos[eAxis] && pos2[eAxis] < voxelPos[eAxis]) {
    count = -1.0;
  } else return false;

  EvtMap->add(index, count);
  // G4cout << "DirectionalCellCountScorer::ProcessHits: "
  //        << "Adding count for index " << index << " at position " << voxelPos
  //        << " with count value: " << count << G4endl;

  if(!hitIDMap.empty() && hitIDMap.find(index) != hitIDMap.cend())
  {
    auto filler = G4VScoreHistFiller::Instance();
    if(filler == nullptr)
    {
      G4Exception(
        "DirectionalCellCountScorer::ProcessHits", "SCORER0123", JustWarning,
        "G4TScoreHistFiller is not instantiated!! Histogram is not filled.");
    }
    else
    {
      filler->FillH1(hitIDMap[index], count);
    }
  }


  return true;
}

void DirectionalCellCountScorer::Initialize(G4HCofThisEvent* HCE)
{
  EvtMap = new G4THitsMap<G4double>(detector->GetName(), GetName());
  if(HCID < 0)
    HCID = GetCollectionID(0);
  HCE->AddHitsCollection(HCID, EvtMap);
}

void DirectionalCellCountScorer::clear() { EvtMap->clear(); }

void DirectionalCellCountScorer::PrintAll()
{
  G4cout << " MultiFunctionalDet  " << detector->GetName() << G4endl;
  G4cout << " PrimitiveScorer " << GetName() << G4endl;
  G4cout << " Number of entries " << EvtMap->entries() << G4endl;
  for(const auto& [copy, count] : *(EvtMap->GetMap()))
  {
    G4cout << "  copy no.: " << copy
           << "  cell count : " << *(count) << " [tracks] " << G4endl;
  }
}

void DirectionalCellCountScorer::SetUnit(const G4String& unit)
{
  if(unit.empty())
  {
    unitName  = unit;
    unitValue = 1.0;
  }
  else
  {
    G4String msg = "Invalid unit [" + unit + "] (Current  unit is [" +
                   GetUnit() + "] ) for " + GetName();
    G4Exception("DirectionalCellCountScorer::SetUnit", "DetPS0012", JustWarning,
                msg);
  }
}
