#ifndef DicomPrimaryGeneratorAction_h
#define DicomPrimaryGeneratorAction_h 1

#include "G4VUserPrimaryGeneratorAction.hh"
#include "globals.hh"

class G4ParticleGun;
class G4Event;

class DicomPrimaryGeneratorMessenger;
class DicomPrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction
{
public:
	DicomPrimaryGeneratorAction();
	~DicomPrimaryGeneratorAction();

public:
	// Methods to change the parameters of primary particle generation 
	// interactively
	void SetsigmaEnergy(G4double);
	void SetmeanKineticEnergy(G4double);
	void GeneratePrimaries(G4Event*);
	void SetXposition(G4double);
	void SetYposition(G4double);
	void SetZposition(G4double);
	void SetsigmaX(G4double);
	void SetsigmaY(G4double);
	void SetsigmaZ(G4double);
	void SetmomentumX(G4double);
	void SetmomentumY(G4double);
	void SetmomentumZ(G4double);
	void SetsigmaMomentumX(G4double);
	void SetsigmaMomentumY(G4double);
	void SetsigmaMomentumZ(G4double);
	void SetTheta(G4double); // aggiunto
	G4double GetmeanKineticEnergy(void);
	G4ParticleGun* GetParticleGun(void) { return particleGun; }

private:
	void SetDefaultPrimaryParticle();
	G4double meanKineticEnergy;
	G4double sigmaEnergy;
	G4double X0;
	G4double Y0;
	G4double Z0;
	G4double sigmaX;
	G4double sigmaY;
	G4double sigmaZ;
	G4double momentumX;
	G4double momentumY;
	G4double momentumZ;
	G4double sigmaMomentumX;
	G4double sigmaMomentumY;
	G4double sigmaMomentumZ;
	G4double Theta;  // aggiunto

private:
	G4ParticleGun* particleGun;
	DicomPrimaryGeneratorMessenger* gunMessenger;
};

#endif


