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
#include "DirectionalCellCurrentScorer.hh"

#include <G4Box.hh>
#include <G4VPVParameterisation.hh>

#include "G4StepStatus.hh"
#include "G4Track.hh"
#include "G4VSolid.hh"
#include "G4UnitsTable.hh"
#include "G4VScoreHistFiller.hh"

////////////////////////////////////////////////////////////////////////////////
// (Description)
//   This is a primitive scorer class for scoring the particle current along
//   a specified axis.
//
// Created: 2005-11-14  Tsukasa ASO, Akinori Kimura.
// 2010-07-22   Introduce Unit specification.
// 2010-07-22   Add weighted option
// 2020-10-06   Use G4VPrimitivePlotter and fill 1-D histo of kinetic energy (x)
//              vs. current * track weight (y)               (Makoto Asai)
// 2025-05-27   Use G4PSPassageCellCurrent as base for DirectionalCellCurrentScorer
//
///////////////////////////////////////////////////////////////////////////////

DirectionalCellCurrentScorer::DirectionalCellCurrentScorer(const G4String& name, EAxis axis, EDirection direction, G4int depth)
  : G4VPrimitivePlotter(name, depth), eAxis(axis), eDirection(direction)
{
  SetUnit("");
}

G4bool DirectionalCellCurrentScorer::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
  G4StepPoint* preStep             = aStep->GetPreStepPoint();
  G4VPhysicalVolume* physVol       = preStep->GetPhysicalVolume();
  G4VPVParameterisation* physParam = physVol->GetParameterisation();
  G4VSolid* solid                  = nullptr;
  if(physParam != nullptr)
  {  // for parameterized volume
    G4int idx =
      ((G4TouchableHistory*) (preStep->GetTouchable()))
        ->GetReplicaNumber(indexDepth);
    solid = physParam->ComputeSolid(idx, physVol);
    solid->ComputeDimensions(physParam, idx, physVol);
  }
  else
  {  // for ordinary volume
    solid = physVol->GetLogicalVolume()->GetSolid();
  }

  auto boxSolid = static_cast<G4Box *>(solid);

  G4int index = GetIndex(aStep);
  G4double weight = preStep->GetWeight();

  G4RotationMatrix rotationInverse = preStep->GetTouchable()->GetHistory()->GetTopTransform().InverseNetRotation();
  G4ThreeVector localDir = rotationInverse * aStep->GetDeltaPosition();

  G4double current = localDir[eAxis];
  if (weight != 0. && eDirection * current >= 0.) {
    G4double output = weight * current * preStep->GetCharge() / boxSolid->GetCubicVolume();
    EvtMap->add(index, output);
    return true;
  }
  return false;
}

void DirectionalCellCurrentScorer::Initialize(G4HCofThisEvent* HCE)
{
  EvtMap = new G4THitsMap<G4double>(detector->GetName(), GetName());
  if(HCID < 0)
    HCID = GetCollectionID(0);
  HCE->AddHitsCollection(HCID, EvtMap);
}

void DirectionalCellCurrentScorer::clear() { EvtMap->clear(); }

void DirectionalCellCurrentScorer::PrintAll()
{
  G4cout << " MultiFunctionalDet  " << detector->GetName() << G4endl;
  G4cout << " PrimitiveScorer " << GetName() << G4endl;
  G4cout << " Number of entries " << EvtMap->entries() << G4endl;
  for(const auto& [copy, current] : *(EvtMap->GetMap()))
  {
    G4cout << "  copy no.: " << copy
           << "  cell current : " << *(current) << " [tracks] " << G4endl;
  }
}

void DirectionalCellCurrentScorer::SetUnit(const G4String& unit)
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
    G4Exception("DirectionalCellCurrentScorer::SetUnit", "DetPS0012", JustWarning,
                msg);
  }
}
