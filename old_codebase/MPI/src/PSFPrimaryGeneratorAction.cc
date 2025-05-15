#include "PSFPrimaryGeneratorAction.hh"

#include <memory>

#include "globals.hh"
#include "PSFPrimaryGenerator.hh"

PSFPrimaryGeneratorAction::PSFPrimaryGeneratorAction(std::shared_ptr<PSFReader> theReader)
{
    // pass the shared ptr to the generator
    // primary generator now part owner of the reader
    m_PSFGenerator.reset(new PSFPrimaryGenerator(theReader));
    // optional
    //m_PSFGenerator->SetNumRecycle(100);
}

PSFPrimaryGeneratorAction::~PSFPrimaryGeneratorAction() {}

void PSFPrimaryGeneratorAction::GeneratePrimaries(G4Event* evt)
{
    m_PSFGenerator->GeneratePrimaryVertex(evt);
}

