#include "PSFActionInitialization.hh"
#include "DicomRunActionMaster.hh"
#include "DicomRunAction.hh"
#include "DicomEventAction.hh"
#include "PSFPrimaryGeneratorAction.hh"
#include "PSFSteppingAction.hh"
//#include "DicomPrimaryGeneratorAction.hh"
#include "GPSPrimaryGeneratorAction.hh"
#include "PSFReader.hh"


PSFActionInitialization::PSFActionInitialization(const G4String& filename)
: G4VUserActionInitialization(), m_DoseFileName(filename), m_Reader(nullptr)
{
}

PSFActionInitialization::PSFActionInitialization(const G4String& filename,
                                                 std::shared_ptr<PSFReader> theReader)
: G4VUserActionInitialization(), m_DoseFileName(filename), m_Reader(theReader)
{
}

PSFActionInitialization::~PSFActionInitialization() {}

void PSFActionInitialization::BuildForMaster() const
{
    SetUserAction(new DicomRunActionMaster(m_DoseFileName));
}

void PSFActionInitialization::Build() const
{
#ifdef PSF_WRITE
    SetUserAction(new PSFSteppingAction);
    SetUserAction(new GPSPrimaryGeneratorAction);
#elif PSF_READ
    SetUserAction(new PSFPrimaryGeneratorAction(m_Reader));
#endif 
    SetUserAction(new DicomRunAction(m_DoseFileName));
    SetUserAction(new DicomEventAction);
}