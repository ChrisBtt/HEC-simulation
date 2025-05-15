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

#pragma once

#include <G4VUserMPIrunMerger.hh>
#include "DicomRun.hh"

/*
// Modified from MPI parallel example exMPI03 for the use with
// the DicomRun class
To simplify merging by message passing, following constraints are assumed:
Every DicomRun contains one Collection only with members of DicomRun instance
being:
fCollId = 0 and fCollName = "phantomSD/DoseDeposit" 
This constraint does not affect the way the simulation were run anyways, but
message passing is easier since only the raw Hit data has to be sent.
*/
class DicomRunMerger : public G4VUserMPIrunMerger {
public:

  DicomRunMerger(const DicomRun* arun,G4int destination=G4MPImanager::kRANK_MASTER,
      G4int verb=0)
  : G4VUserMPIrunMerger(arun,destination,verb ) , fRun(arun) {}
  
protected:
  
  /*
  Pack the StatVector of the involved DicomRun for sending via MPI.
  This involves serializing the data to primitive buffers.
  */
  void Pack();

  /*
  Unpack the serialized StatVector of the involved DicomRun received via MPI.
  This involves creating a new DicomRun used only for merging, which holds
  the deserialized StatVector.
  */
  G4Run* UnPack();

private:

  const DicomRun* fRun;

};

