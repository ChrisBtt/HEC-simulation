#include "GPSPrimaryGeneratorAction.hh"
#include "G4GeneralParticleSource.hh"

GPSPrimaryGeneratorAction::GPSPrimaryGeneratorAction()
{
    m_GPS.reset(new G4GeneralParticleSource);
}

GPSPrimaryGeneratorAction::~GPSPrimaryGeneratorAction()
{
}

void GPSPrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
    // Generate a primary particle
	m_GPS->GeneratePrimaryVertex(anEvent);
}