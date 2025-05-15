
#include "DicomPrimaryGeneratorAction.hh"
#include "DicomPrimaryGeneratorMessenger.hh"

#include "G4SystemOfUnits.hh"
#include "globals.hh"
#include "G4Event.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ParticleDefinition.hh"
#include "Randomize.hh"


DicomPrimaryGeneratorAction::DicomPrimaryGeneratorAction()
{
	// Define the messenger
	gunMessenger = new DicomPrimaryGeneratorMessenger(this);

	particleGun = new G4ParticleGun();

	SetDefaultPrimaryParticle();
}

DicomPrimaryGeneratorAction::~DicomPrimaryGeneratorAction()
{
	delete particleGun;

	delete gunMessenger;
}

void DicomPrimaryGeneratorAction::SetDefaultPrimaryParticle()
{
	// ***************************
	// Default primary particle
	// ****************************

	// Define primary particles: electrons // protons
	G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
	//G4ParticleDefinition* particle = particleTable->FindParticle("e-");   // ("proton")
	G4ParticleDefinition* particle = particleTable->FindParticle("gamma");
	particleGun->SetParticleDefinition(particle);

	// Define the energy of primary particles:
	// gaussian distribution with mean energy = 10.0 *MeV   
	// and sigma = 400.0 *keV
	G4double defaultMeanKineticEnergy = 30.0 * CLHEP::keV;
	meanKineticEnergy = defaultMeanKineticEnergy;

	G4double defaultsigmaEnergy = 0. * CLHEP::keV;
	sigmaEnergy = defaultsigmaEnergy;

	// Define the parameters of the initial position: 
	// the y, z coordinates have a gaussian distribution 

	G4double defaultX0 = -0.5 * CLHEP::mm;
	X0 = defaultX0;

	G4double defaultY0 = -0.5 * CLHEP::mm;
	Y0 = defaultY0;

	G4double defaultZ0 = -61.5 * CLHEP::mm;
	Z0 = defaultZ0;

	G4double defaultsigmaX = 0. * CLHEP::mm;
	sigmaX = defaultsigmaX;
	
	G4double defaultsigmaY = 0. * CLHEP::mm;
	sigmaY = defaultsigmaY;

	G4double defaultsigmaZ = 0. * CLHEP::mm;
	sigmaZ = defaultsigmaZ;

	// Define the parameters of the momentum of primary particles: 
	// The momentum along the y and z axis has a gaussian distribution

	G4double defaultMomentumX = 0.0;
	momentumX = defaultMomentumX;

	G4double defaultMomentumY = 0.0;
	momentumY = defaultMomentumY;

	G4double defaultMomentumZ = 1.0;
	momentumZ = defaultMomentumZ;


	G4double defaultsigmaMomentumX = 0.0;
	sigmaMomentumX = defaultsigmaMomentumX;

	G4double defaultsigmaMomentumY = 0.0;
	sigmaMomentumY = defaultsigmaMomentumY;

	G4double defaultsigmaMomentumZ = 0.0;
	sigmaMomentumZ = defaultsigmaMomentumZ;
  

	G4double defaultTheta = 0.0 * CLHEP::deg;
	Theta = defaultTheta;

}

void DicomPrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
	// ****************************************
	// Set the beam angular apread 
	// and spot size
	// beam spot size
	// ****************************************

	// Set the position of the primary particles
	G4double x = X0;
	G4double y = Y0;
	G4double z = Z0;

	if (sigmaX > 0.0)
	{
		x = X0 + G4RandGauss::shoot(0., sigmaX);
		//G4cout << "X PSigma" << sigmaX << G4endl;
	}

	if (sigmaY > 0.0)
	{
		y = Y0 + G4RandGauss::shoot(0., sigmaY);
		//G4cout << "X PSigma" << sigmaY << G4endl;
	}

	if (sigmaZ > 0.0)
	{
		z = Z0 + G4RandGauss::shoot(0., sigmaZ);
		//G4cout << "X PSigma" << sigmaZ << G4endl;
	}

	particleGun->SetParticlePosition(G4ThreeVector(x, y, z));

	// ********************************************
	// Set the beam energy and energy spread
	// ********************************************

	G4double kineticEnergy = G4RandGauss::shoot(meanKineticEnergy, sigmaEnergy);
	particleGun->SetParticleEnergy(kineticEnergy);

	// Set the direction and variance of the primary particles  
	G4double Mx = momentumX;
	G4double My = momentumY;
	G4double Mz = momentumZ;
	
	if (sigmaMomentumX > 0.0)
	{
		Mx += momentumX + G4RandGauss::shoot(0., sigmaMomentumX);
		//G4cout << "X MSigma " << sigmaMomentumX << G4endl;
	}
	if ( sigmaMomentumY  > 0.0 )
	  {
		My = momentumY + G4RandGauss::shoot( 0., sigmaMomentumY );
		//G4cout << "Y MSigma " << sigmaMomentumY << G4endl;
	  }
	if ( sigmaMomentumZ  > 0.0 )
	  {
		Mz = momentumZ + G4RandGauss::shoot( 0., sigmaMomentumZ );
		//G4cout << "Z MSigma " << sigmaMomentumZ << G4endl;
	  }

	particleGun -> SetParticleMomentumDirection( G4ThreeVector(Mx, My, Mz) );


	// Generate a primary particle
	particleGun->GeneratePrimaryVertex(anEvent);
}

void DicomPrimaryGeneratorAction::SetmeanKineticEnergy(G4double val)
{
	meanKineticEnergy = val;
	G4cout << "The mean Kinetic energy of the incident beam has been changed to (MeV):"
		<< meanKineticEnergy / MeV << G4endl;
}

void DicomPrimaryGeneratorAction::SetsigmaEnergy(G4double val)
{
	sigmaEnergy = val;
	G4cout << "The sigma of the kinetic energy of the incident beam has been changed to (MeV):"
		<< sigmaEnergy / MeV << G4endl;
}

void DicomPrimaryGeneratorAction::SetXposition(G4double val)
{
	X0 = val;
}

void DicomPrimaryGeneratorAction::SetYposition(G4double val)
{
	Y0 = val;
}

void DicomPrimaryGeneratorAction::SetZposition(G4double val)
{
	Z0 = val;
}

void DicomPrimaryGeneratorAction::SetsigmaX(G4double val)
{
	sigmaX = val;
}

void DicomPrimaryGeneratorAction::SetsigmaY(G4double val)
{
	sigmaY = val;
}

void DicomPrimaryGeneratorAction::SetsigmaZ(G4double val)
{
	sigmaZ = val;
}

void DicomPrimaryGeneratorAction::SetmomentumX(G4double val)
{
	momentumX = val;
}

void DicomPrimaryGeneratorAction::SetmomentumY(G4double val)
{
	momentumY = val;
}

void DicomPrimaryGeneratorAction::SetmomentumZ(G4double val)
{
	momentumZ = val;
}


void DicomPrimaryGeneratorAction::SetsigmaMomentumX(G4double val)
{
	sigmaMomentumX = val;
}

void DicomPrimaryGeneratorAction::SetsigmaMomentumY (G4double val )
{
	sigmaMomentumY = val;
}

void DicomPrimaryGeneratorAction::SetsigmaMomentumZ (G4double val )
{ 
	sigmaMomentumZ = val;
}


void DicomPrimaryGeneratorAction::SetTheta(G4double val)
{
	Theta = val;
}


G4double DicomPrimaryGeneratorAction::GetmeanKineticEnergy(void)
{
	return meanKineticEnergy;
}


