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
/// \file  medical/DICOM/src/DicomDetectorConstruction.cc
/// \brief Implementation of the DicomDetectorConstruction class
//

#include "DicomDetectorConstruction.hh"

#include <G4AffineTransform.hh>
#include <Randomize.hh>

#include "CLHEP/Units/SystemOfUnits.h"
#include "DicomHandler.hh"
#include "DicomPhantomZSliceHeader.hh"

#include "G4Box.hh"
#include "G4Element.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4PhysicalConstants.hh"
#include "G4UIcommand.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VSolid.hh"
#include "G4tgbVolume.hh"
#include "G4tgrSolid.hh"
#include "globals.hh"

#include "G4VisAttributes.hh"

using CLHEP::cm3;
using CLHEP::g;
using CLHEP::m;
using CLHEP::mg;
using CLHEP::mole;
using CLHEP::perCent;

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo..
DicomDetectorConstruction::DicomDetectorConstruction()
  : G4VUserDetectorConstruction(),
    fAir(0),

    fWorld_solid(0),
    fWorld_logic(0),
    fWorld_phys(0),

    fContainer_solid(0),
    fContainer_logic(0),
    fContainer_phys(0),

    fNoFiles(0),
    fMateIDs(0),

    fZSliceHeaderMerged(0),

    fNoVoxelsX(0),
    fNoVoxelsY(0),
    fNoVoxelsZ(0),
    fVoxelHalfDimX(0),
    fVoxelHalfDimY(0),
    fVoxelHalfDimZ(0),

    fReplacementParams(0),
    fReplacementSolid(0),
    fReplacementMaterial(0),

    fConstructed(false)
{}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo...
DicomDetectorConstruction::~DicomDetectorConstruction() {}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo.....
G4VPhysicalVolume* DicomDetectorConstruction::Construct()
{
  if (!fConstructed || fWorld_phys == 0) {
    fConstructed = true;
    InitialisationOfMaterials();

    //----- Build world
    G4double worldXDimension = 1. * m;
    G4double worldYDimension = 1. * m;
    G4double worldZDimension = 1. * m;

    fWorld_solid = new G4Box("WorldSolid", worldXDimension, worldYDimension, worldZDimension);

    fWorld_logic = new G4LogicalVolume(fWorld_solid, fAir, "WorldLogical", 0, 0, 0);

    fWorld_phys = new G4PVPlacement(0, G4ThreeVector(0, 0, 0), "World", fWorld_logic, 0, false, 0);

    fWorld_logic->SetVisAttributes(G4VisAttributes::GetInvisible());

    ConstructReplacementData();

    ConstructPanelDetectors();

    ReadPhantomData();
    ConstructPhantomContainer();

    for (G4int i = 0; i < fNoVoxelsX * fNoVoxelsY * fNoVoxelsZ; i++) {
      if (CheckVoxelIntersection(i)) fMateIDs[i] = fOriginalMaterials.size();
    }

    ConstructPhantom();
  }
  return fWorld_phys;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........
void DicomDetectorConstruction::InitialisationOfMaterials()
{
  // Creating elements :
  G4double z, a, density;
  G4String name, symbol;

  G4Element* elC = new G4Element(name = "Carbon", symbol = "C", z = 6.0, a = 12.011 * g / mole);
  G4Element* elH = new G4Element(name = "Hydrogen", symbol = "H", z = 1.0, a = 1.008 * g / mole);
  G4Element* elN = new G4Element(name = "Nitrogen", symbol = "N", z = 7.0, a = 14.007 * g / mole);
  G4Element* elO = new G4Element(name = "Oxygen", symbol = "O", z = 8.0, a = 16.00 * g / mole);
  G4Element* elNa =
    new G4Element(name = "Sodium", symbol = "Na", z = 11.0, a = 22.98977 * g / mole);
  G4Element* elMg =
    new G4Element(name = "Magnesium", symbol = "Mg", z = 12.0, a = 24.3050 * g / mole);
  G4Element* elP =
    new G4Element(name = "Phosphorus", symbol = "P", z = 15.0, a = 30.973976 * g / mole);
  G4Element* elS = new G4Element(name = "Sulfur", symbol = "S", z = 16.0, a = 32.065 * g / mole);
  G4Element* elCl =
    new G4Element(name = "Chlorine", symbol = "Cl", z = 17.0, a = 35.453 * g / mole);
  G4Element* elK =
    new G4Element(name = "Potassium", symbol = "K", z = 19.0, a = 30.0983 * g / mole);

  G4Element* elFe = new G4Element(name = "Iron", symbol = "Fe", z = 26, a = 56.845 * g / mole);

  G4Element* elCa = new G4Element(name = "Calcium", symbol = "Ca", z = 20.0, a = 40.078 * g / mole);

  G4Element* elZn = new G4Element(name = "Zinc", symbol = "Zn", z = 30.0, a = 65.382 * g / mole);

  // Creating Materials :
  G4int numberofElements;

  // Air
  fAir = new G4Material("Air", 1.290 * mg / cm3, numberofElements = 2);
  fAir->AddElement(elN, 0.7);
  fAir->AddElement(elO, 0.3);

  // Soft tissue (ICRP - NIST)
  G4Material* softTissue = new G4Material("SoftTissue", 1.00 * g / cm3, numberofElements = 13);
  softTissue->AddElement(elH, 10.4472 * perCent);
  softTissue->AddElement(elC, 23.219 * perCent);
  softTissue->AddElement(elN, 2.488 * perCent);
  softTissue->AddElement(elO, 63.0238 * perCent);
  softTissue->AddElement(elNa, 0.113 * perCent);
  softTissue->AddElement(elMg, 0.0113 * perCent);
  softTissue->AddElement(elP, 0.113 * perCent);
  softTissue->AddElement(elS, 0.199 * perCent);
  softTissue->AddElement(elCl, 0.134 * perCent);
  softTissue->AddElement(elK, 0.199 * perCent);
  softTissue->AddElement(elCa, 0.023 * perCent);
  softTissue->AddElement(elFe, 0.005 * perCent);
  softTissue->AddElement(elZn, 0.003 * perCent);

  //  Lung Inhale
  G4Material* lunginhale =
    new G4Material("LungInhale", density = 0.217 * g / cm3, numberofElements = 9);
  lunginhale->AddElement(elH, 0.103);
  lunginhale->AddElement(elC, 0.105);
  lunginhale->AddElement(elN, 0.031);
  lunginhale->AddElement(elO, 0.749);
  lunginhale->AddElement(elNa, 0.002);
  lunginhale->AddElement(elP, 0.002);
  lunginhale->AddElement(elS, 0.003);
  lunginhale->AddElement(elCl, 0.002);
  lunginhale->AddElement(elK, 0.003);

  // Lung exhale
  G4Material* lungexhale =
    new G4Material("LungExhale", density = 0.508 * g / cm3, numberofElements = 9);
  lungexhale->AddElement(elH, 0.103);
  lungexhale->AddElement(elC, 0.105);
  lungexhale->AddElement(elN, 0.031);
  lungexhale->AddElement(elO, 0.749);
  lungexhale->AddElement(elNa, 0.002);
  lungexhale->AddElement(elP, 0.002);
  lungexhale->AddElement(elS, 0.003);
  lungexhale->AddElement(elCl, 0.002);
  lungexhale->AddElement(elK, 0.003);

  // Adipose tissue
  G4Material* adiposeTissue =
    new G4Material("AdiposeTissue", density = 0.967 * g / cm3, numberofElements = 7);
  adiposeTissue->AddElement(elH, 0.114);
  adiposeTissue->AddElement(elC, 0.598);
  adiposeTissue->AddElement(elN, 0.007);
  adiposeTissue->AddElement(elO, 0.278);
  adiposeTissue->AddElement(elNa, 0.001);
  adiposeTissue->AddElement(elS, 0.001);
  adiposeTissue->AddElement(elCl, 0.001);

  // Brain (ICRP - NIST)
  G4Material* brainTissue = new G4Material("BrainTissue", 1.03 * g / cm3, numberofElements = 13);
  brainTissue->AddElement(elH, 11.0667 * perCent);
  brainTissue->AddElement(elC, 12.542 * perCent);
  brainTissue->AddElement(elN, 1.328 * perCent);
  brainTissue->AddElement(elO, 73.7723 * perCent);
  brainTissue->AddElement(elNa, 0.1840 * perCent);
  brainTissue->AddElement(elMg, 0.015 * perCent);
  brainTissue->AddElement(elP, 0.356 * perCent);
  brainTissue->AddElement(elS, 0.177 * perCent);
  brainTissue->AddElement(elCl, 0.236 * perCent);
  brainTissue->AddElement(elK, 0.31 * perCent);
  brainTissue->AddElement(elCa, 0.009 * perCent);
  brainTissue->AddElement(elFe, 0.005 * perCent);
  brainTissue->AddElement(elZn, 0.001 * perCent);

  // Breast
  G4Material* breast = new G4Material("Breast", density = 0.990 * g / cm3, numberofElements = 8);
  breast->AddElement(elH, 0.109);
  breast->AddElement(elC, 0.506);
  breast->AddElement(elN, 0.023);
  breast->AddElement(elO, 0.358);
  breast->AddElement(elNa, 0.001);
  breast->AddElement(elP, 0.001);
  breast->AddElement(elS, 0.001);
  breast->AddElement(elCl, 0.001);

  // Spinal Disc
  G4Material* spinalDisc = new G4Material("SpinalDisc", 1.10 * g / cm3, numberofElements = 8);
  spinalDisc->AddElement(elH, 9.60 * perCent);
  spinalDisc->AddElement(elC, 9.90 * perCent);
  spinalDisc->AddElement(elN, 2.20 * perCent);
  spinalDisc->AddElement(elO, 74.40 * perCent);
  spinalDisc->AddElement(elNa, 0.50 * perCent);
  spinalDisc->AddElement(elP, 2.20 * perCent);
  spinalDisc->AddElement(elS, 0.90 * perCent);
  spinalDisc->AddElement(elCl, 0.30 * perCent);

  // Water
  G4Material* water = new G4Material("Water", density = 1.0 * g / cm3, numberofElements = 2);
  water->AddElement(elH, 0.112);
  water->AddElement(elO, 0.888);

  // Muscle
  G4Material* muscle = new G4Material("Muscle", density = 1.061 * g / cm3, numberofElements = 9);
  muscle->AddElement(elH, 0.102);
  muscle->AddElement(elC, 0.143);
  muscle->AddElement(elN, 0.034);
  muscle->AddElement(elO, 0.710);
  muscle->AddElement(elNa, 0.001);
  muscle->AddElement(elP, 0.002);
  muscle->AddElement(elS, 0.003);
  muscle->AddElement(elCl, 0.001);
  muscle->AddElement(elK, 0.004);

  // Liver
  G4Material* liver = new G4Material("Liver", density = 1.071 * g / cm3, numberofElements = 9);
  liver->AddElement(elH, 0.102);
  liver->AddElement(elC, 0.139);
  liver->AddElement(elN, 0.030);
  liver->AddElement(elO, 0.716);
  liver->AddElement(elNa, 0.002);
  liver->AddElement(elP, 0.003);
  liver->AddElement(elS, 0.003);
  liver->AddElement(elCl, 0.002);
  liver->AddElement(elK, 0.003);

  // Tooth Dentin
  G4Material* toothDentin = new G4Material("ToothDentin", 2.14 * g / cm3, numberofElements = 10);
  toothDentin->AddElement(elH, 2.67 * perCent);
  toothDentin->AddElement(elC, 12.77 * perCent);
  toothDentin->AddElement(elN, 4.27 * perCent);
  toothDentin->AddElement(elO, 40.40 * perCent);
  toothDentin->AddElement(elNa, 0.65 * perCent);
  toothDentin->AddElement(elMg, 0.59 * perCent);
  toothDentin->AddElement(elP, 11.86 * perCent);
  toothDentin->AddElement(elCl, 0.04 * perCent);
  toothDentin->AddElement(elCa, 26.74 * perCent);
  toothDentin->AddElement(elZn, 0.01 * perCent);

  // Trabecular Bone
  G4Material* trabecularBone =
    new G4Material("TrabecularBone", density = 1.159 * g / cm3, numberofElements = 12);
  trabecularBone->AddElement(elH, 0.085);
  trabecularBone->AddElement(elC, 0.404);
  trabecularBone->AddElement(elN, 0.058);
  trabecularBone->AddElement(elO, 0.367);
  trabecularBone->AddElement(elNa, 0.001);
  trabecularBone->AddElement(elMg, 0.001);
  trabecularBone->AddElement(elP, 0.034);
  trabecularBone->AddElement(elS, 0.002);
  trabecularBone->AddElement(elCl, 0.002);
  trabecularBone->AddElement(elK, 0.001);
  trabecularBone->AddElement(elCa, 0.044);
  trabecularBone->AddElement(elFe, 0.001);

  // Trabecular bone used in the DICOM Head

  G4Material* trabecularBone_head =
    new G4Material("TrabecularBone_HEAD", 1.18 * g / cm3, numberofElements = 12);
  trabecularBone_head->AddElement(elH, 8.50 * perCent);
  trabecularBone_head->AddElement(elC, 40.40 * perCent);
  trabecularBone_head->AddElement(elN, 2.80 * perCent);
  trabecularBone_head->AddElement(elO, 36.70 * perCent);
  trabecularBone_head->AddElement(elNa, 0.10 * perCent);
  trabecularBone_head->AddElement(elMg, 0.10 * perCent);
  trabecularBone_head->AddElement(elP, 3.40 * perCent);
  trabecularBone_head->AddElement(elS, 0.20 * perCent);
  trabecularBone_head->AddElement(elCl, 0.20 * perCent);
  trabecularBone_head->AddElement(elK, 0.10 * perCent);
  trabecularBone_head->AddElement(elCa, 7.40 * perCent);
  trabecularBone_head->AddElement(elFe, 0.10 * perCent);

  // Dense Bone
  G4Material* denseBone =
    new G4Material("DenseBone", density = 1.575 * g / cm3, numberofElements = 11);
  denseBone->AddElement(elH, 0.056);
  denseBone->AddElement(elC, 0.235);
  denseBone->AddElement(elN, 0.050);
  denseBone->AddElement(elO, 0.434);
  denseBone->AddElement(elNa, 0.001);
  denseBone->AddElement(elMg, 0.001);
  denseBone->AddElement(elP, 0.072);
  denseBone->AddElement(elS, 0.003);
  denseBone->AddElement(elCl, 0.001);
  denseBone->AddElement(elK, 0.001);
  denseBone->AddElement(elCa, 0.146);

  // Cortical Bone (ICRP - NIST)
  G4Material* corticalBone = new G4Material("CorticalBone", 1.85 * g / cm3, numberofElements = 9);
  corticalBone->AddElement(elH, 4.7234 * perCent);
  corticalBone->AddElement(elC, 14.4330 * perCent);
  corticalBone->AddElement(elN, 4.199 * perCent);
  corticalBone->AddElement(elO, 44.6096 * perCent);
  corticalBone->AddElement(elMg, 0.22 * perCent);
  corticalBone->AddElement(elP, 10.497 * perCent);
  corticalBone->AddElement(elS, 0.315 * perCent);
  corticalBone->AddElement(elCa, 20.993 * perCent);
  corticalBone->AddElement(elZn, 0.01 * perCent);

  // Tooth enamel
  G4Material* toothEnamel = new G4Material("ToothEnamel", 2.89 * g / cm3, numberofElements = 10);
  toothEnamel->AddElement(elH, 0.95 * perCent);
  toothEnamel->AddElement(elC, 1.11 * perCent);
  toothEnamel->AddElement(elN, 0.23 * perCent);
  toothEnamel->AddElement(elO, 41.66 * perCent);
  toothEnamel->AddElement(elNa, 0.79 * perCent);
  toothEnamel->AddElement(elMg, 0.23 * perCent);
  toothEnamel->AddElement(elP, 18.71 * perCent);
  toothEnamel->AddElement(elCl, 0.34 * perCent);
  toothEnamel->AddElement(elCa, 35.97 * perCent);
  toothEnamel->AddElement(elZn, 0.02 * perCent);

  fOriginalMaterials.push_back(fAir);  // rho = 0.00129
  fOriginalMaterials.push_back(lunginhale);  // rho = 0.217
  fOriginalMaterials.push_back(lungexhale);  // rho = 0.508
  fOriginalMaterials.push_back(adiposeTissue);  // rho = 0.967
  fOriginalMaterials.push_back(breast);  // rho = 0.990
  fOriginalMaterials.push_back(water);  // rho = 1.018
  fOriginalMaterials.push_back(muscle);  // rho = 1.061
  fOriginalMaterials.push_back(liver);  // rho = 1.071
  fOriginalMaterials.push_back(trabecularBone);  // rho = 1.159 - HEAD PHANTOM
  fOriginalMaterials.push_back(denseBone);  // rho = 1.575
  G4cout << "Default materials of the DICOM Extended examples have been used" << G4endl;

  fReplacementMaterial = new G4Material("Tumor", 2.0 * g / cm3, 1);
  fReplacementMaterial->AddElement(elH, 100.0 * perCent);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo.......
void DicomDetectorConstruction::ReadPhantomData()
{
  G4String dataFile = DicomHandler::GetDicomDataFile();
  std::ifstream finDF(dataFile.c_str());
  G4String fname;

  if (finDF.good() != 1) {
    G4String descript = "Problem reading data file: " + dataFile;
    G4Exception(" DicomDetectorConstruction::ReadPhantomData", " ", FatalException, descript);
  }

  G4int compression;
  finDF >> compression;  // not used here
  finDF >> fNoFiles;

  if (fNoFiles > 0) {
    for (G4int i = 0; i < fNoFiles; ++i) {
      finDF >> fname;

      //--- Read one data file
      fname += ".g4dcm";

      ReadPhantomDataFile(fname);
    }
  } else { // Construct a basic water phantom
    G4float sliceWidth, sliceHeight, zLength;
    G4int nVoxelsX, nVoxelsY, nVoxelsZ;
    finDF >> sliceWidth >> sliceHeight >> zLength;
    finDF >> nVoxelsX >> nVoxelsY >> nVoxelsZ;

    G4float sliceThickness = zLength / nVoxelsZ;

    fNoFiles = nVoxelsZ;

    for (unsigned int ii = 0; ii < fOriginalMaterials.size(); ++ii) {
      fMaterials.push_back(fOriginalMaterials[ii]);
    }
    fMaterials.push_back(fReplacementMaterial);

    // Create slice headers for water phantom
    for (G4int i = 0; i < nVoxelsZ; ++i) {
      auto* zslice = new DicomPhantomZSliceHeader("waterPhantom" + std::to_string(i) + ".g4dcm");

      for (const auto& mate : fMaterials)
        zslice->AddMaterial(mate->GetName());

      zslice->SetNoVoxelsX(nVoxelsX);
      zslice->SetNoVoxelsY(nVoxelsY);
      zslice->SetNoVoxelsZ(1);

      zslice->SetMinX(-sliceWidth / 2.);
      zslice->SetMaxX(sliceWidth / 2.);
      zslice->SetMinY(-sliceHeight / 2.);
      zslice->SetMaxY(sliceHeight / 2.);
      zslice->SetMinZ((i-nVoxelsZ/2) * sliceThickness);
      zslice->SetMaxZ((i-nVoxelsZ/2) * sliceThickness + sliceThickness);

      for (G4int j = 0; j < nVoxelsY; ++j) {
        zslice->AddRow();
        for (G4int k = 0; k < nVoxelsX; ++k) {
          zslice->AddValue(1.0);  // water (rho = 1.018
          zslice->AddMateID(0);
        }
      }

      fZSliceHeaders.push_back(zslice);
    }

    fMateIDs = new size_t[fNoFiles * nVoxelsX * nVoxelsY];
    for (G4int i = 0; i < fNoVoxelsX * fNoVoxelsY * fNoVoxelsZ; i++) {
      fMateIDs[i] = 5;
    }
  }
  
  //----- Merge data headers
  MergeZSliceHeaders();
  
  finDF.close();
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........
void DicomDetectorConstruction::ReadPhantomDataFile(const G4String& fname)
{
  G4cout << " DicomDetectorConstruction::ReadPhantomDataFile opening file " << fname
         << G4endl;  // GDEB

#ifdef G4VERBOSE
  G4cout << " DicomDetectorConstruction::ReadPhantomDataFile opening file " << fname << G4endl;
#endif

  std::ifstream fin(fname.c_str(), std::ios_base::in);
  if (!fin.is_open()) {
    G4Exception("DicomDetectorConstruction::ReadPhantomDataFile", "", FatalErrorInArgument,
                G4String("File not found " + fname).c_str());
  }
  //----- Define density differences (maximum density difference to create
  // a new material)
  char* part = std::getenv("DICOM_CHANGE_MATERIAL_DENSITY");
  G4double densityDiff = -1.;
  if (part) densityDiff = G4UIcommand::ConvertToDouble(part);
  if (densityDiff != -1.) {
    for (unsigned int ii = 0; ii < fOriginalMaterials.size(); ++ii) {
      fDensityDiffs[ii] = densityDiff;  // currently all materials with
      // same difference
    }
  }
  else {
    if (fMaterials.size() == 0) {  // do it only for first slice
      for (unsigned int ii = 0; ii < fOriginalMaterials.size(); ++ii) {
        fMaterials.push_back(fOriginalMaterials[ii]);
      }
      fMaterials.push_back(fReplacementMaterial);
    }
  }

  //----- Read data header
  DicomPhantomZSliceHeader* sliceHeader = new DicomPhantomZSliceHeader(fin);
  fZSliceHeaders.push_back(sliceHeader);

  //----- Read material indices
  G4int nVoxels = sliceHeader->GetNoVoxels();

  //--- If first slice, initiliaze fMateIDs
  if (fZSliceHeaders.size() == 1) {
    // fMateIDs = new unsigned int[fNoFiles*nVoxels];
    fMateIDs = new size_t[fNoFiles * nVoxels];
  }

  unsigned int mateID;
  // number of voxels from previously read slices
  G4int voxelCopyNo = G4int((fZSliceHeaders.size() - 1) * nVoxels);
  for (G4int ii = 0; ii < nVoxels; ++ii, voxelCopyNo++) {
    fin >> mateID;
    fMateIDs[voxelCopyNo] = mateID;
  }

  //----- Read material densities and build new materials if two voxels have
  //  same material but its density is in a different density interval
  // (size of density intervals defined by densityDiff)
  G4double density;
  // number of voxels from previously read slices
  voxelCopyNo = G4int((fZSliceHeaders.size() - 1) * nVoxels);
  for (G4int ii = 0; ii < nVoxels; ++ii, voxelCopyNo++) {
    fin >> density;

    //-- Get material from list of original materials
    mateID = unsigned(fMateIDs[voxelCopyNo]);
    G4Material* mateOrig = fOriginalMaterials[mateID];

    //-- Get density bin: middle point of the bin in which the current
    // density is included
    G4String newMateName = mateOrig->GetName();
    G4float densityBin = 0.;
    if (densityDiff != -1.) {
      densityBin = G4float(fDensityDiffs[mateID]) * (G4int(density / fDensityDiffs[mateID]) + 0.5);
      //-- Build the new material name
      newMateName += G4UIcommand::ConvertToString(densityBin);
    }

    //-- Look if a material with this name is already created
    //  (because a previous voxel was already in this density bin)
    unsigned int im;
    for (im = 0; im < fMaterials.size(); ++im) {
      if (fMaterials[im]->GetName() == newMateName) {
        break;
      }
    }
    //-- If material is already created use index of this material
    if (im != fMaterials.size()) {
      fMateIDs[voxelCopyNo] = im;
      //-- else, create the material
    }
    else {
      if (densityDiff != -1.) {
        fMaterials.push_back(BuildMaterialWithChangingDensity(mateOrig, densityBin, newMateName));
        fMateIDs[voxelCopyNo] = fMaterials.size() - 1;
      }
      else {
        G4cerr << " im " << im << " < " << fMaterials.size() << " name " << newMateName << G4endl;
        G4Exception("DicomDetectorConstruction::ReadPhantomDataFile", "", FatalErrorInArgument,
                    "Wrong index in material");  // it should never reach here
      }
    }
  }
}

G4bool DicomDetectorConstruction::CheckVoxelIntersection(G4int copyNo)
{
  if (!fReplacementSolid) return false;

  //----- Get voxel position
  G4int ix = copyNo % fNoVoxelsX;
  G4int iy = (copyNo / fNoVoxelsX) % fNoVoxelsY;
  G4int iz = copyNo / (fNoVoxelsX * fNoVoxelsY);
  G4ThreeVector voxelCenter((-fNoVoxelsX + 2 * ix + 1) * fVoxelHalfDimX,
    (-fNoVoxelsY + 2 * iy + 1) * fVoxelHalfDimY,
    (-fNoVoxelsZ + 2 * iz + 1) * fVoxelHalfDimZ);

  fReplacementTransform.ApplyPointTransform(voxelCenter);
  return fReplacementSolid->Inside(voxelCenter) != kOutside;
}

void DicomDetectorConstruction::SetReplacementData(std::vector<G4String> params) {
  fReplacementParams = params;
}

void DicomDetectorConstruction::ConstructPanelDetectors() {
  fPanel_solid = new G4Box("PanelDetector", 400., 400., 15.);
  fPanel_logic =
    new G4LogicalVolume(fPanel_solid,
                        fAir, "PanelDetector", 0, 0, 0);

  auto vis = G4VisAttributes{};
  vis.SetForceWireframe(true);

  fPanel_logic->SetVisAttributes(vis);

  fPanel_physUp = new G4PVPlacement(0,  // rotation
                                      G4ThreeVector{0., 0., -240.},
                                      fPanel_logic,  // The logic volume
                                      "PanelDetectorUp",  // Name
                                      fWorld_logic,  // Mother
                                      false,  // No op. bool.
                                      -1);  // Copy number

  fPanel_physDown = new G4PVPlacement(0,  // rotation
                                      G4ThreeVector{0., 0., 240.},
                                      fPanel_logic,  // The logic volume
                                      "PanelDetectorDown",  // Name
                                      fWorld_logic,  // Mother
                                      false,  // No op. bool.
                                      -2);  // Copy number

  SetScorer(fPanel_logic);
}


void DicomDetectorConstruction::ConstructReplacementData() {
  if (fReplacementParams.empty()) return;

  //----- Build G4VSolid
  BuildUserSolid(fReplacementParams);

  //----- Calculate volume inverse 3D transform
  G4ThreeVector pos = G4ThreeVector(G4UIcommand::ConvertToDouble(fReplacementParams[0]),
                                    G4UIcommand::ConvertToDouble(fReplacementParams[1]),
                                    G4UIcommand::ConvertToDouble(fReplacementParams[2]));
  G4RotationMatrix* rotmat = new G4RotationMatrix;
  std::vector<G4double> angles;
  rotmat->rotateX(G4UIcommand::ConvertToDouble(fReplacementParams[3]));
  rotmat->rotateY(G4UIcommand::ConvertToDouble(fReplacementParams[4]));
  rotmat->rotateY(G4UIcommand::ConvertToDouble(fReplacementParams[5]));

  G4AffineTransform phantomTransform{G4RotationMatrix(), G4ThreeVector()};

  fReplacementTransform = G4AffineTransform(rotmat, pos).Invert() * phantomTransform;
}

void DicomDetectorConstruction::BuildUserSolid(std::vector<G4String> params)
{
  for (G4int ii = 0; ii < 6; ++ii)
    params.erase(params.begin());
  // take otu position and rotation angles
  params.insert(params.begin(), ":SOLID");
  params.insert(params.begin(), params[1]);
  G4tgrSolid* tgrSolid = new G4tgrSolid(params);
  G4tgbVolume* tgbVolume = new G4tgbVolume();
  fReplacementSolid = tgbVolume->FindOrConstructG4Solid(tgrSolid);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo....
void DicomDetectorConstruction::MergeZSliceHeaders()
{
  //----- Images must have the same dimension ...
  fZSliceHeaderMerged = new DicomPhantomZSliceHeader(*fZSliceHeaders[0]);
  for (unsigned int ii = 1; ii < fZSliceHeaders.size(); ++ii) {
    *fZSliceHeaderMerged += *fZSliceHeaders[ii];
  }
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
G4Material* DicomDetectorConstruction::BuildMaterialWithChangingDensity(const G4Material* origMate,
                                                                        G4float density,
                                                                        G4String newMateName)
{
  //----- Copy original material, but with new density
  G4int nelem = G4int(origMate->GetNumberOfElements());
  G4Material* mate =
    new G4Material(newMateName, density * g / cm3, nelem, kStateUndefined, STP_Temperature);

  for (G4int ii = 0; ii < nelem; ++ii) {
    G4double frac = origMate->GetFractionVector()[ii];
    G4Element* elem = const_cast<G4Element*>(origMate->GetElement(ii));
    mate->AddElement(elem, frac);
  }

  return mate;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo.....
void DicomDetectorConstruction::ConstructPhantomContainer()
{
  //---- Extract number of voxels and voxel dimensions
  fNoVoxelsX = fZSliceHeaderMerged->GetNoVoxelsX();
  fNoVoxelsY = fZSliceHeaderMerged->GetNoVoxelsY();
  fNoVoxelsZ = fZSliceHeaderMerged->GetNoVoxelsZ();

  fVoxelHalfDimX = fZSliceHeaderMerged->GetVoxelHalfX();
  fVoxelHalfDimY = fZSliceHeaderMerged->GetVoxelHalfY();
  fVoxelHalfDimZ = fZSliceHeaderMerged->GetVoxelHalfZ();
#ifdef G4VERBOSE
  G4cout << " fNoVoxelsX " << fNoVoxelsX << " fVoxelHalfDimX " << fVoxelHalfDimX << G4endl;
  G4cout << " fNoVoxelsY " << fNoVoxelsY << " fVoxelHalfDimY " << fVoxelHalfDimY << G4endl;
  G4cout << " fNoVoxelsZ " << fNoVoxelsZ << " fVoxelHalfDimZ " << fVoxelHalfDimZ << G4endl;
  G4cout << " totalPixels " << fNoVoxelsX * fNoVoxelsY * fNoVoxelsZ << G4endl;
#endif

  //----- Define the volume that contains all the voxels
  fContainer_solid = new G4Box("phantomContainer", fNoVoxelsX * fVoxelHalfDimX,
                               fNoVoxelsY * fVoxelHalfDimY, fNoVoxelsZ * fVoxelHalfDimZ);
  fContainer_logic =
    new G4LogicalVolume(fContainer_solid,
                        // the material is not important, it will be fully filled by the voxels
                        fMaterials[0], "phantomContainer", 0, 0, 0);
  //--- Place it on the world
  G4double fOffsetX = (fZSliceHeaderMerged->GetMaxX() + fZSliceHeaderMerged->GetMinX()) / 2.;
  G4double fOffsetY = (fZSliceHeaderMerged->GetMaxY() + fZSliceHeaderMerged->GetMinY()) / 2.;
  G4double fOffsetZ = (fZSliceHeaderMerged->GetMaxZ() + fZSliceHeaderMerged->GetMinZ()) / 2.;
  G4ThreeVector posCentreVoxels(fOffsetX, fOffsetY, fOffsetZ);
#ifdef G4VERBOSE
  G4cout << " placing voxel container volume at " << posCentreVoxels << G4endl;
#endif
  G4RotationMatrix* rotmat = new G4RotationMatrix;
  //rotmat->rotateY(90.* CLHEP::deg);
  fContainer_phys = new G4PVPlacement(rotmat,  // rotation
                                      posCentreVoxels,
                                      fContainer_logic,  // The logic volume
                                      "phantomContainer",  // Name
                                      fWorld_logic,  // Mother
                                      false,  // No op. bool.
                                      1);  // Copy number
}

#include "G4MultiFunctionalDetector.hh"
#include "G4PSDoseDeposit.hh"
#include "G4PSDoseDeposit3D.hh"
#include "DirectionalCellCurrentScorer.hh"
#include "G4SDChargedFilter.hh"
#include "G4SDManager.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo.
void DicomDetectorConstruction::SetScorer(G4LogicalVolume* voxel_logic)
{
#ifdef G4VERBOSE
  G4cout << "\t SET SCORER : " << voxel_logic->GetName() << G4endl;
#endif

  fScorers.insert(voxel_logic);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo....

void DicomDetectorConstruction::ConstructSDandField()
{
#ifdef G4VERBOSE
  G4cout << "\t CONSTRUCT SD AND FIELD" << G4endl;
#endif

  // G4SDManager* SDman = G4SDManager::GetSDMpointer();

  // SDman->SetVerboseLevel(1);

  //
  // Sensitive Detector Name
  G4String concreteSDname = "phantomSD";
  std::vector<G4String> scorer_names;
  scorer_names.push_back(concreteSDname);
  //------------------------
  // MultiFunctionalDetector
  //------------------------
  //
  // Define MultiFunctionalDetector with name.
  // declare MFDet as a MultiFunctionalDetector scorer
  G4MultiFunctionalDetector* MFDet = new G4MultiFunctionalDetector(concreteSDname);
  G4SDManager::GetSDMpointer()->AddNewDetector(MFDet);

  G4SDChargedFilter* particleFilter = new G4SDChargedFilter("particleFilter");

  G4VPrimitiveScorer* dosedep = new G4PSDoseDeposit("DoseDeposit");
  MFDet->RegisterPrimitive(dosedep);

  G4VPrimitiveScorer* cellCurrentX = new DirectionalCellCurrentScorer("CellCurrentX", kXAxis);
  cellCurrentX->SetFilter(particleFilter);
  MFDet->RegisterPrimitive(cellCurrentX);

  G4VPrimitiveScorer* cellCurrentY = new DirectionalCellCurrentScorer("CellCurrentY", kYAxis);
  cellCurrentY->SetFilter(particleFilter);
  MFDet->RegisterPrimitive(cellCurrentY);

  G4VPrimitiveScorer* cellCurrentZ = new DirectionalCellCurrentScorer("CellCurrentZ", kZAxis);
  cellCurrentZ->SetFilter(particleFilter);
  MFDet->RegisterPrimitive(cellCurrentZ);

  G4VPrimitiveScorer* cellCurrentZF = new DirectionalCellCurrentScorer("CellCurrentZF", kZAxis, DirectionalCellCurrentScorer::kForward);
  cellCurrentZF->SetFilter(particleFilter);
  MFDet->RegisterPrimitive(cellCurrentZF);

  G4VPrimitiveScorer* cellCurrentZB = new DirectionalCellCurrentScorer("CellCurrentZB", kZAxis, DirectionalCellCurrentScorer::kBackward);
  cellCurrentZB->SetFilter(particleFilter);
  MFDet->RegisterPrimitive(cellCurrentZB);

  for (auto ite = fScorers.cbegin(); ite != fScorers.cend(); ++ite) {
    SetSensitiveDetector(*ite, MFDet);
  }
}
