

#include "DicomPrimaryGeneratorMessenger.hh"
#include "DicomPrimaryGeneratorAction.hh"
#include "G4UIdirectory.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWithADouble.hh"

DicomPrimaryGeneratorMessenger::DicomPrimaryGeneratorMessenger(
	DicomPrimaryGeneratorAction* IORTGun)
	:IORTAction(IORTGun)
{
	//
	// Definition of the interactive commands to modify the parameters of the
	// generation of primary particles
	// 
	beamParametersDir = new G4UIdirectory("/beam/");
	beamParametersDir->SetGuidance("set parameters of beam");

	EnergyDir = new G4UIdirectory("/beam/energy/");
	EnergyDir->SetGuidance("set energy of beam");

	particlePositionDir = new G4UIdirectory("/beam/position/");
	particlePositionDir->SetGuidance("set position of particle");


	MomentumDir = new G4UIdirectory("/beam/momentum/");
	MomentumDir->SetGuidance("set momentum of particle ");
	
	ThetaCmd = new G4UIcmdWithADoubleAndUnit("/beam/momentum/Theta", this);
	ThetaCmd->SetGuidance("set Theta");
	ThetaCmd->SetParameterName("Theta", false);
	ThetaCmd->SetDefaultUnit("deg");
	ThetaCmd->SetUnitCandidates("deg rad");
	ThetaCmd->AvailableForStates(G4State_PreInit, G4State_Idle);




	// Direction Of beam and Direction Variance

	//X
	momentumXCmd = new G4UIcmdWithADouble("/beam/momentum/momentumX", this);
	momentumXCmd->SetGuidance("set momentum x");
	momentumXCmd->SetParameterName("momentum", false);
	momentumXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	sigmaMomentumXCmd = new G4UIcmdWithADouble("/beam/momentum/momentumX/sigmaX", this);
	sigmaMomentumXCmd->SetGuidance("set sigma momentum x");
	sigmaMomentumXCmd->SetParameterName("momentum", false);
	sigmaMomentumXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
	
	//Y
	momentumYCmd = new G4UIcmdWithADouble("/beam/momentum/momentumY", this);
	momentumYCmd->SetGuidance("set momentum y");
	momentumYCmd->SetParameterName("momentum", false);
	momentumYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	sigmaMomentumYCmd = new G4UIcmdWithADouble("/beam/momentum/momentumY/sigmaY", this);
	sigmaMomentumYCmd->SetGuidance("set sigma momentum y");
	sigmaMomentumYCmd->SetParameterName("momentum", false);
	sigmaMomentumYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	//Z
	momentumZCmd = new G4UIcmdWithADouble("/beam/momentum/momentumZ", this);
	momentumZCmd->SetGuidance("set momentum Z");
	momentumZCmd->SetParameterName("momentum", false);
	momentumZCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	sigmaMomentumZCmd = new G4UIcmdWithADouble("/beam/momentum/momentumZ/sigmaZ", this);
	sigmaMomentumZCmd->SetGuidance("set sigma momentum Z");
	sigmaMomentumZCmd->SetParameterName("momentum", false);
	sigmaMomentumZCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
	


	 // Particle energy and Varience


	meanKineticEnergyCmd = new G4UIcmdWithADoubleAndUnit("/beam/energy/meanEnergy", this);
	meanKineticEnergyCmd->SetGuidance("set mean Kinetic energy");
	meanKineticEnergyCmd->SetParameterName("Energy", false);
	meanKineticEnergyCmd->SetDefaultUnit("MeV");
	meanKineticEnergyCmd->SetUnitCandidates("eV keV MeV GeV TeV");
	meanKineticEnergyCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	sigmaEnergyCmd = new G4UIcmdWithADoubleAndUnit("/beam/energy/sigmaEnergy", this);
	sigmaEnergyCmd->SetGuidance("set sigma energy");
	sigmaEnergyCmd->SetParameterName("Energy", false);
	sigmaEnergyCmd->SetDefaultUnit("keV");
	sigmaEnergyCmd->SetUnitCandidates("eV keV MeV GeV TeV");
	sigmaEnergyCmd->AvailableForStates(G4State_PreInit, G4State_Idle);



	// Particles origin point + Varaiance


	XpositionCmd = new G4UIcmdWithADoubleAndUnit("/beam/position/Xposition", this);
	XpositionCmd->SetGuidance("set x coordinate of particle");
	XpositionCmd->SetParameterName("position", false);
	XpositionCmd->SetDefaultUnit("mm");
	XpositionCmd->SetUnitCandidates("mm cm m");
	XpositionCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	sigmaXCmd = new G4UIcmdWithADoubleAndUnit("/beam/position/Xposition/sigmaX", this);
	sigmaXCmd->SetGuidance("set sigma x");
	sigmaXCmd->SetParameterName("position", false);
	sigmaXCmd->SetDefaultUnit("mm");
	sigmaXCmd->SetUnitCandidates("mm cm m");
	sigmaXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	YpositionCmd = new G4UIcmdWithADoubleAndUnit("/beam/position/Yposition", this);
	YpositionCmd->SetGuidance("set y coordinate of particle");
	YpositionCmd->SetParameterName("position", false);
	YpositionCmd->SetDefaultUnit("mm");
	YpositionCmd->SetUnitCandidates("mm cm m");
	YpositionCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	sigmaYCmd = new G4UIcmdWithADoubleAndUnit("/beam/position/Yposition/sigmaY", this);
	sigmaYCmd->SetGuidance("set sigma y");
	sigmaYCmd->SetParameterName("position", false);
	sigmaYCmd->SetDefaultUnit("mm");
	sigmaYCmd->SetUnitCandidates("mm cm m");
	sigmaYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	ZpositionCmd = new G4UIcmdWithADoubleAndUnit("/beam/position/Zposition", this);
	ZpositionCmd->SetGuidance("set z coordinate of particle");
	ZpositionCmd->SetParameterName("position", false);
	ZpositionCmd->SetDefaultUnit("mm");
	ZpositionCmd->SetUnitCandidates("mm cm m");
	ZpositionCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

	sigmaZCmd = new G4UIcmdWithADoubleAndUnit("/beam/position/Zposition/sigmaZ", this);
	sigmaZCmd->SetGuidance("set sigma z");
	sigmaZCmd->SetParameterName("position", false);
	sigmaZCmd->SetDefaultUnit("mm");
	sigmaZCmd->SetUnitCandidates("mm cm m");
	sigmaZCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

DicomPrimaryGeneratorMessenger::~DicomPrimaryGeneratorMessenger()
{
	delete beamParametersDir;
	delete EnergyDir;
	delete meanKineticEnergyCmd;
	delete sigmaEnergyCmd;
	delete particlePositionDir;
	delete MomentumDir;
	delete XpositionCmd;
	delete YpositionCmd;
	delete ZpositionCmd;
	delete sigmaXCmd;
	delete sigmaYCmd;
	delete sigmaZCmd;
	delete ThetaCmd;
	delete momentumXCmd;
	delete momentumYCmd;
	delete momentumZCmd;
	delete sigmaMomentumXCmd;
	delete sigmaMomentumYCmd; 
	delete sigmaMomentumZCmd; 
}

void DicomPrimaryGeneratorMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
	if (command == meanKineticEnergyCmd)
	{
		IORTAction->SetmeanKineticEnergy(meanKineticEnergyCmd
			->GetNewDoubleValue(newValue));
	}
	if (command == sigmaEnergyCmd)
	{
		IORTAction->SetsigmaEnergy(sigmaEnergyCmd
			->GetNewDoubleValue(newValue));
	}
	if (command == XpositionCmd)
	{
		IORTAction->SetXposition(XpositionCmd
			->GetNewDoubleValue(newValue));
	}

	if (command == YpositionCmd)
	{
		IORTAction->SetYposition(YpositionCmd
			->GetNewDoubleValue(newValue));
	}

	if (command == ZpositionCmd)
	{
		IORTAction->SetZposition(ZpositionCmd
			->GetNewDoubleValue(newValue));
	}

	if (command == sigmaXCmd)
	{
		IORTAction->SetsigmaX(sigmaXCmd
			->GetNewDoubleValue(newValue));
	}


	if (command == sigmaYCmd)
	{
		IORTAction->SetsigmaY(sigmaYCmd
			->GetNewDoubleValue(newValue));
	}

	if (command == sigmaZCmd)
	{
		IORTAction->SetsigmaZ(sigmaZCmd
			->GetNewDoubleValue(newValue));
	}

	if (command == ThetaCmd)
	{
		IORTAction->SetTheta(ThetaCmd
			->GetNewDoubleValue(newValue));
	}




	if (command == momentumXCmd)
	{
		IORTAction->SetmomentumX(momentumXCmd
			->GetNewDoubleValue(newValue));
	}

	if (command == sigmaMomentumXCmd)
	{
		IORTAction->SetsigmaMomentumX(sigmaMomentumXCmd
			->GetNewDoubleValue(newValue));
	}



	if (command == momentumYCmd)
	{
		IORTAction->SetmomentumY(momentumYCmd
			->GetNewDoubleValue(newValue));
	}
	
	if (command == sigmaMomentumYCmd)
	{
		IORTAction->SetsigmaMomentumY(sigmaMomentumYCmd
			->GetNewDoubleValue(newValue));
	}




	  if (command == momentumZCmd)
	  {
		  IORTAction->SetmomentumZ(momentumZCmd
			  ->GetNewDoubleValue(newValue));
	  }

	  if (command == sigmaMomentumZCmd)
	  {
		  IORTAction->SetsigmaMomentumZ(sigmaMomentumZCmd
			  ->GetNewDoubleValue(newValue));
	  }
	
}
