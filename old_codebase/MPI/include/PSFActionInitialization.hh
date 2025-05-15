#pragma once

#include <memory>

#include "G4VUserActionInitialization.hh"
#include "globals.hh"

class PSFReader;

class PSFActionInitialization : public G4VUserActionInitialization
{
public:
    // Constructor and Destructor
    // Use this constructor for writing a PSF file
    PSFActionInitialization(const G4String&);
    // Use this one to read from a PSF
    PSFActionInitialization(const G4String&, 
                            std::shared_ptr<PSFReader>);

    PSFActionInitialization() = delete;
    virtual ~PSFActionInitialization();
    
public:
    virtual void BuildForMaster() const;
    virtual void Build() const;

private:
    // dose output file name
    G4String m_DoseFileName;

    std::shared_ptr<PSFReader> m_Reader;
};