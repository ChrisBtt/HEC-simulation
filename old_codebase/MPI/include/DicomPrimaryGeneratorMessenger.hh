#ifndef DicomPrimaryGeneratorMessenger_h
#define DicomPrimaryGeneratorMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class DicomPrimaryGeneratorAction;
class G4UIdirectory;
class G4UIcmdWithADoubleAndUnit;
class G4UIcmdWithADouble;

class DicomPrimaryGeneratorMessenger : public G4UImessenger
{
public:
	DicomPrimaryGeneratorMessenger(DicomPrimaryGeneratorAction*);
	~DicomPrimaryGeneratorMessenger();

	void SetNewValue(G4UIcommand*, G4String);

private:
	DicomPrimaryGeneratorAction* IORTAction;
	G4UIdirectory* beamParametersDir;
	G4UIdirectory* EnergyDir;
	G4UIdirectory* particlePositionDir;
	G4UIdirectory* MomentumDir;
	G4UIcmdWithADoubleAndUnit* meanKineticEnergyCmd;
	G4UIcmdWithADoubleAndUnit* sigmaEnergyCmd;
	G4UIcmdWithADoubleAndUnit* XpositionCmd;
	G4UIcmdWithADoubleAndUnit* YpositionCmd;
	G4UIcmdWithADoubleAndUnit* ZpositionCmd;
	G4UIcmdWithADoubleAndUnit* sigmaXCmd;
	G4UIcmdWithADoubleAndUnit* sigmaYCmd;
	G4UIcmdWithADoubleAndUnit* sigmaZCmd;
	G4UIcmdWithADouble* momentumXCmd;
	G4UIcmdWithADouble* momentumYCmd;
	G4UIcmdWithADouble* momentumZCmd;
	G4UIcmdWithADouble*	sigmaMomentumXCmd;
	G4UIcmdWithADouble* sigmaMomentumYCmd; 
	G4UIcmdWithADouble* sigmaMomentumZCmd;
	G4UIcmdWithADoubleAndUnit* ThetaCmd;


};

#endif

