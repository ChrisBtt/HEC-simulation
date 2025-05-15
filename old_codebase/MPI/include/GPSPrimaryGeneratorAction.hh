#pragma once

#include "G4VUserPrimaryGeneratorAction.hh"
#include "globals.hh"

#include <memory>

class G4GeneralParticleSource;
class G4Event;

class GPSPrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction
{
public:
	GPSPrimaryGeneratorAction();
	~GPSPrimaryGeneratorAction();

    void GeneratePrimaries(G4Event*);

    G4GeneralParticleSource* GetGPS(void) { return m_GPS.get(); }

private:
    std::unique_ptr<G4GeneralParticleSource> m_GPS;
};