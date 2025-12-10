// Scorer for velWeightedCurrent
// Scorer to score the orthogonal particle currents*velocity for HEC calculations. 
// Will account for particle direction!
#include "velWeightedCurrent.hh"
#include "G4UnitsTable.hh"

#include "G4PSDirectionFlag.hh"

velWeightedCurrent::velWeightedCurrent(TsParameterManager* pM, TsMaterialManager* mM, TsGeometryManager* gM, TsScoringManager* scM, TsExtensionManager* eM,
    G4String scorerName, G4String quantity, G4String outFileName, G4bool isSubScorer)
: TsVBinnedScorer(pM, mM, gM, scM, eM, scorerName, quantity, outFileName, isSubScorer)
{
const G4double eplus_per_mm2 = eplus / mm2;
new G4UnitDefinition("e+PerMm2", "e+/mm2", "ChargeDensity", eplus_per_mm2);
SetUnit("e+/mm2");

G4String d = "z";
if (fPm->ParameterExists(GetFullParmName("direction"))) d = fPm->GetStringParameter(GetFullParmName("direction"));
d.toLower();
if      (d=="x") dirAxis_ = 'x';
else if (d=="y") dirAxis_ = 'y';
else             dirAxis_ = 'z'; // default
}


velWeightedCurrent::~velWeightedCurrent() {;}


G4bool velWeightedCurrent::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
  if (!fIsActive) { fSkippedWhileInactive++; return false; }

  G4StepPoint* pre = aStep->GetPreStepPoint();
  if (!pre) return false;

  const G4double weight = pre->GetWeight();
  if (weight == 0.) return false;

  const G4double charge = pre->GetCharge();

  const G4ThreeVector dGlobal = pre->GetMomentumDirection();
  const G4double stepLength = aStep->GetStepLength();
  G4ThreeVector distance = dGlobal * stepLength;

  const G4TouchableHandle& th = pre->GetTouchableHandle();
  const G4RotationMatrix* rot = th->GetRotation();
  G4ThreeVector dLocal = rot ? rot->inverse() * distance : distance;

  G4double proj = 0.0;
  switch (dirAxis_) {
    case 'x': proj = dLocal.x(); break;
    case 'y': proj = dLocal.y(); break;
    default:  proj = dLocal.z(); break;
  }

  const G4double beta = pre->GetBeta();
  const G4double volume = th->GetVolume()->GetLogicalVolume()->GetSolid()->GetCubicVolume();

  if (volume <= 0.0) {
    G4cout << "WARNING: Invalid volume (" << volume << "), skipping hit" << G4endl;
    return false;
  }

  const G4double val = (weight * proj * charge * beta) / volume;

  AccumulateHit(aStep, val);
  return true;
}