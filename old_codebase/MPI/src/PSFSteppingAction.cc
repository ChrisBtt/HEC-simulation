#include "PSFSteppingAction.hh"

#include "G4Step.hh"
#include "PSFWriter.hh"

PSFSteppingAction::PSFSteppingAction()
{
}

PSFSteppingAction::~PSFSteppingAction()
{
}

void PSFSteppingAction::UserSteppingAction(const G4Step *aStep)
{
    PSFWriter::GetInstance()->UserSteppingAction(aStep);
}
