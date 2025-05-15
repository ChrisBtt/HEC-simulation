#pragma once

#include "G4UserSteppingAction.hh"

class G4Step;

class PSFSteppingAction : public G4UserSteppingAction
{
public:
    PSFSteppingAction();
    ~PSFSteppingAction();

    void UserSteppingAction(const G4Step *aStep);
};
