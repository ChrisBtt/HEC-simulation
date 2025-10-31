#ifndef PRIMARYGENERATORMESSENGER_HH
#define PRIMARYGENERATORMESSENGER_HH

#include "G4UImessenger.hh"
#include "globals.hh"

class DicomPrimaryGeneratorAction;
class G4UIdirectory;
class G4UIcmdWith3Vector;
class G4UIcmdWithADouble;

class PrimaryGeneratorMessenger : public G4UImessenger
{
public:
    explicit PrimaryGeneratorMessenger(DicomPrimaryGeneratorAction*);
    ~PrimaryGeneratorMessenger() override;

    void SetNewValue(G4UIcommand*, G4String) override;

private:
    DicomPrimaryGeneratorAction* fAction = nullptr;

    G4UIcmdWith3Vector* fSetBeamOriginCmd = nullptr;
    G4UIcmdWith3Vector* fSetBeamDirectionCmd = nullptr;
    G4UIcmdWithADouble* fSetBeamRadiusCmd = nullptr;
};

#endif //PRIMARYGENERATORMESSENGER_HH
