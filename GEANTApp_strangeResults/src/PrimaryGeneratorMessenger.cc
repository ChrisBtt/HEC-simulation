#include "PrimaryGeneratorMessenger.hh"

#include "DicomPrimaryGeneratorAction.hh"

#include "G4UIcmdWith3Vector.hh"
#include "G4UIcmdWithADouble.hh"

PrimaryGeneratorMessenger::PrimaryGeneratorMessenger(DicomPrimaryGeneratorAction* Gun) : fAction(Gun)
{
    fSetBeamOriginCmd = new G4UIcmdWith3Vector("/particleGun/setPosition", this);
    fSetBeamOriginCmd->SetGuidance("Set particle beam origin");
    fSetBeamOriginCmd->SetParameterName("posX", "posY", "posZ", false);

    fSetBeamDirectionCmd = new G4UIcmdWith3Vector("/particleGun/setDirection", this);
    fSetBeamDirectionCmd->SetGuidance("Set particle beam direction");
    fSetBeamDirectionCmd->SetParameterName("dirX", "dirY", "dirZ", false);

    fSetBeamRadiusCmd = new G4UIcmdWithADouble("/particleGun/setRadius", this);
    fSetBeamRadiusCmd->SetGuidance("Set particle beam radius");
    fSetBeamRadiusCmd->SetParameterName("radius", false);
}

PrimaryGeneratorMessenger::~PrimaryGeneratorMessenger()
{
    delete fSetBeamOriginCmd;
    delete fSetBeamDirectionCmd;
    delete fSetBeamRadiusCmd;
}

void PrimaryGeneratorMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
    if (command == fSetBeamOriginCmd)
        fAction->setBeamOrigin(G4UIcmdWith3Vector::GetNew3VectorValue(newValue));
    else if (command == fSetBeamDirectionCmd)
        fAction->setBeamDirection(G4UIcmdWith3Vector::GetNew3VectorValue(newValue));
    else if (command == fSetBeamRadiusCmd)
        fAction->setBeamRadius(G4UIcmdWithADouble::GetNewDoubleValue(newValue));
}