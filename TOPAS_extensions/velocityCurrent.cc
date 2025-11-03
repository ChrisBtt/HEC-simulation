// Scorer for velocityCurrent
// Scorer to score the orthogonal particle currents*velocity for HEC calculations. 
// Will account for particle direction!
#include "velocityCurrent.hh"
#include "G4UnitsTable.hh"

#include "G4PSDirectionFlag.hh"

velocityCurrent::velocityCurrent(TsParameterManager* pM, TsMaterialManager* mM, TsGeometryManager* gM, TsScoringManager* scM, TsExtensionManager* eM,
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


velocityCurrent::~velocityCurrent() {;}


G4bool velocityCurrent::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
  if (!fIsActive) { fSkippedWhileInactive++; return false; }

  G4StepPoint* pre = aStep->GetPreStepPoint();
  if (!pre) return false;

  const G4double weight = pre->GetWeight();
  if (weight == 0.) return false;

  const G4double charge = pre->GetCharge();

  G4ThreeVector dir = pre->GetMomentumDirection();
  G4double vMag = pre->GetVelocity(); // mm/ns

  G4ThreeVector velocity = dir * vMag;
  const G4TouchableHandle& th = pre->GetTouchableHandle();

  const G4RotationMatrix* rot = th->GetRotation();
  G4ThreeVector vLocal = rot ? rot->inverse() * velocity : velocity;

  G4double vProj = 0.0;
  switch (dirAxis_) {
    case 'x': vProj = vLocal.x(); break;
    case 'y': vProj = vLocal.y(); break;
    default:  vProj = vLocal.z(); break;
  }

  const G4double volume = th->GetVolume()->GetLogicalVolume()->GetSolid()->GetCubicVolume();

  if (volume <= 0.0) {
    G4cout << "WARNING: Invalid volume (" << volume << "), skipping hit" << G4endl;
    return false;
  }

  const G4double deltaT = aStep->GetDeltaTime();
  const G4double val = (weight * vProj * charge * deltaT) / volume;

  AccumulateHit(aStep, val);
  return true;
}