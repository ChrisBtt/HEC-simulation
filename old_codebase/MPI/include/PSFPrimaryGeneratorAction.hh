#pragma once

#include <memory>

#include "globals.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

class PSFPrimaryGenerator;
class PSFReader;
class G4Event;

class PSFPrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction
{
public:
    PSFPrimaryGeneratorAction(std::shared_ptr<PSFReader>);
    ~PSFPrimaryGeneratorAction();
    PSFPrimaryGeneratorAction() = delete;

    inline auto* GetPrimaryGenerator() const { return m_PSFGenerator.get(); }

    void GeneratePrimaries(G4Event* evt);

private:
    std::unique_ptr<PSFPrimaryGenerator> m_PSFGenerator;
};