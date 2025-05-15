#include "PSFWriter.hh"

#include <mutex>
#include <shared_mutex>
#include <memory>
#include <atomic>

#include "globals.hh"
#include "G4SystemOfUnits.hh"
#include "G4MPImanager.hh"
#include "G4Threading.hh"
#include "G4Run.hh"
#include "G4TrackStatus.hh"
#include "G4Step.hh"
#include "G4VSensitiveDetector.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4ProductionCutsTable.hh"

#include "iaea_phsp.h"

std::unique_ptr<PSFWriter> PSFWriter::s_Instance = nullptr;
std::once_flag PSFWriter::s_initOnce;


PSFWriter* PSFWriter::GetInstance()
{
    // one time global init
    std::call_once(s_initOnce, []() {
        s_Instance.reset(new PSFWriter);
    });

    return s_Instance.get();
}

PSFWriter::PSFWriter()
{
    // standard file name
    m_FileName = "PSF";
    m_CutEnergy = 0.0 * CLHEP::keV;
}

PSFWriter::~PSFWriter()
{
}

void PSFWriter::SetFileName(const G4String &name, bool nameIsOutPath)
{   
    std::unique_lock<std::shared_mutex> lock(m_rwMtx);
    std::call_once(m_fileOnce, [&]() 
    {
        if (nameIsOutPath)
        {
            // create the template for the naming scheme
            G4String out_folder = "output_cubes";
            auto pos_out_cubes = name.find("output_cubes");
            auto cube_id_end = name.find(".out");
            auto fileNameTempl = name.substr(
                0, cube_id_end
            ).insert(pos_out_cubes + out_folder.length()+1, "PSF_");

            // set member
            m_FileName = static_cast<G4String>(fileNameTempl);
        }
        else
        {
            m_FileName = name;
        }
        
#ifdef G4VERBOSE
        G4cout << "Thread " << G4Threading::G4GetThreadId()
               << " of Rank " << G4MPImanager::GetManager()->GetRank()
               << " -> PSFWriter::SetFileName set file name to "
               << m_FileName << G4endl;
#endif
    });
}

void PSFWriter::SetCutEnergy(G4double cutEnergy)
{
    std::unique_lock<std::shared_mutex> lock(m_rwMtx);

    std::call_once(m_energyOnce, [&]() 
    {
        m_CutEnergy = cutEnergy;
#ifdef G4VERBOSE
        G4cout << "Thread " << G4Threading::G4GetThreadId()
               << " of Rank " << G4MPImanager::GetManager()->GetRank()
               << " -> PSFWriter::SetCutEnergy set Energy to "
               << cutEnergy / CLHEP::keV << " keV." << G4endl;
#endif
    });

}

G4String PSFWriter::GetFileName() const 
{
    std::shared_lock<std::shared_mutex> lock(m_rwMtx);
    return m_FileName;
}

G4double PSFWriter::GetCutEnergy() const 
{
    std::shared_lock<std::shared_mutex> lock(m_rwMtx);
    return m_CutEnergy;
}

void PSFWriter::SetWriteASCII()
{
    writeASCII = true;
}

bool PSFWriter::GetWriteASCII()
{
    return writeASCII;
}

void PSFWriter::BeginOfRunAction(const G4Run* aRun)
{
#ifdef G4VERBOSE
    G4cout << "PSFWriter::BeginOfRunAction() called by Rank:Thread"
           << G4MPImanager::GetManager()->GetRank() 
           << " : " << G4Threading::G4GetThreadId() << G4endl;
#endif

    // check if cut energy is set
    if (GetCutEnergy() == 0.0)
    {
        G4Exception("PSFWriter::BeginOfRunAction()",
                    "", RunMustBeAborted,
                    "Please set a cut Energy > 0 before invoking " \
                    "PSFWriter::BeginOfRunAction().");
    }

    // MPI Rank
    const auto rank = static_cast<IAEA_I32>(G4MPImanager::GetManager()->GetRank());

    auto fullName = m_FileName + "_" + std::to_string(rank);

    if (writeASCII == true)
    {
        // set the file name
        auto fileNameASCII = fullName + ".txt";

        //create ascii file
        outdata.open(fileNameASCII);
        if (!outdata) {
            G4Exception("PSFWriter::StoreIAEAParticleToASCII()",
                        "IAEAwriter005", JustWarning,
                        "Ascii file could not be opened");
        }
    }
    else
    {
        // set the file name
        auto* fileName = const_cast<char *>(fullName.data());

        // Open a file to store the phase space following the IAEA format
        const auto accessWrite = static_cast<const IAEA_I32>(s_theAccessWrite);

        // number of events processed by the specific MPI Rank
        auto nEvts = static_cast<IAEA_I64>(aRun->GetNumberOfEventToBeProcessed());

        // create file
        IAEA_I32 result;
        IAEA_I32 id = 0;
        iaea_new_source(&id, fileName, &accessWrite, &result, fullName.size()+1);

        // Number of original histories
        iaea_set_total_original_particles(&id, &nEvts);
    }

}

void PSFWriter::EndOfRunAction(const G4Run* aRun)
{
    // get unique lock
    std::unique_lock<std::shared_mutex> lock(m_rwMtx);
#ifdef G4VERBOSE
    G4cout << "PSFWriter::EndOfRunAction() called by Rank:Thread"
           << G4MPImanager::GetManager()->GetRank() 
           << " : " << G4Threading::G4GetThreadId() << G4endl;
#endif

    if (writeASCII == true)
    {
        //close ascii file
        outdata.close();
    }
    else
    {
        // close PSF
        const IAEA_I32 sourceID = 0;
        IAEA_I32 result;

#ifdef G4VERBOSE
        iaea_print_header(&sourceID, &result);
        if (result < 0)
        {
            G4Exception("PSFWriter::EndOfRunAction()",
                        "IAEAwriter003", JustWarning,
                        "IAEA phsp source not found");
        }
#endif

        iaea_destroy_source(&sourceID, &result);
        if (result > 0)
        {
            const auto rank = G4MPImanager::GetManager()->GetRank();
#ifdef G4VERBOSE
            G4cout << "Phase-space file of MPI Rank " << rank
                   << " closed successfully!"
                   << G4endl;
#endif
        }
        else
        {
            G4Exception("PSFWriter::EndOfRunAction()",
                        "IAEAwriter004", JustWarning,
                        "IAEA file not closed properly");
        }
    }

}

bool PSFWriter::CheckWriteCriterion(const G4Step* aStep)
{   
    // post step holds relevant info
    auto postStep = aStep->GetPostStepPoint();

    // check if particle is inside the scoring volume
    auto SD = postStep->GetSensitiveDetector();
    if (SD == nullptr) return false;

    // check if material is air
    auto mat = postStep->GetMaterial();
    if (mat->GetName().find("G4_AIR") != -1) return false;

    // check manual upper bound cut energy
    auto postStepEkin = postStep->GetKineticEnergy();
    auto manualCutCrit = (postStepEkin <= GetCutEnergy());

    // get lower cut energy given by material and range of the 
    // particle in that medium
    auto partDef = aStep->GetTrack()->GetParticleDefinition();
    auto rangeCuts = postStep->GetMaterialCutsCouple()->GetProductionCuts();
    auto partRangeCut = rangeCuts->GetProductionCut(partDef->GetParticleName());

    // convert range to energy and check if criterion is met
    auto table = G4ProductionCutsTable::GetProductionCutsTable();
    auto prodCutEnergy = table->ConvertRangeToEnergy(partDef, mat, partRangeCut);
    auto prodCutCrit = (prodCutEnergy < postStepEkin);

    return (manualCutCrit && prodCutCrit);
}

void PSFWriter::UserSteppingAction(const G4Step* aStep)
{
    if ( CheckWriteCriterion(aStep) )
    {
        // acquire lock, so no simultaneous writing to one
        // file takes place
        std::unique_lock<std::shared_mutex> lock(m_rwMtx);

        // store particle
        if (writeASCII == true)
        {
            StoreIAEAParticleToASCII(aStep);
        }
        else
        {
            StoreIAEAParticle(aStep);
        }
        m_TotalParticles++;

        // kill track and all secondaries
        aStep->GetTrack()->SetTrackStatus(G4TrackStatus::fKillTrackAndSecondaries);
    }
}

void PSFWriter::StoreIAEAParticle(const G4Step* aStep)
{
    IAEA_I32 srcID = 0;

    // Get particle information
    const auto theTrack = aStep->GetTrack();
    const auto PDGCode = theTrack->GetDefinition()->GetPDGEncoding();
    const auto postE = aStep->GetPostStepPoint()->GetKineticEnergy();

    // kinetic energy pre step in MeV, value to be saved in PSF
    auto kinEnergyMeV = static_cast<IAEA_Float>(postE / CLHEP::MeV);

    // set particle typ
    IAEA_I32 partType;
    switch (PDGCode)
    {
    case 22:
        partType = 1; // gamma
        break;
    case 11:
        partType = 2; // electron
        break;
    case -11:
        partType = 3; // positron
        break;
    case 2112:
        partType = 4; // neutron
        break;
    case 2212:
        partType = 5; // proton
        break;
    default:
        G4String pname = theTrack->GetDefinition()->GetParticleName();
        G4String errmsg = "'" + pname + "' is not supported by IAEA phsp format and will not be recorded.";
        G4Exception("G4IAEAphspWriter::StoreIAEAParticle()",
                    "IAEAwriter002", JustWarning, errmsg.c_str());
    }

    // Track weight
    auto wt = static_cast<IAEA_Float>(theTrack->GetWeight());

    // position !WORLD COORDS!
    const auto pos = aStep->GetPostStepPoint()->GetPosition();
    auto x = static_cast<IAEA_Float>(pos.x());
    auto y = static_cast<IAEA_Float>(pos.y());
    auto z = static_cast<IAEA_Float>(pos.z());

    // Momentum direction
    auto momDir = aStep->GetPostStepPoint()->GetMomentumDirection();
    auto u = static_cast<IAEA_Float>(momDir.x());
    auto v = static_cast<IAEA_Float>(momDir.y());
    auto w = static_cast<IAEA_Float>(momDir.z());

    // Extra variables
    IAEA_Float extraFloat = -1; // no extra floats stored
    IAEA_I32 extraInt = -1; // no extra ints stored

    // nStat = 0 for secondaries, > 0 for primaries
    IAEA_I32 nStat = theTrack->GetParentID() > 0 ? 0 : 1;

    iaea_write_particle(&srcID, &nStat, &partType,
                        &kinEnergyMeV, &wt, &x, &y, &z,
                        &u, &v, &w, &extraFloat, &extraInt);
}

void PSFWriter::StoreIAEAParticleToASCII(const G4Step* aStep)
{
    // Get particle information
    const auto theTrack = aStep->GetTrack();
    const auto PDGCode = theTrack->GetDefinition()->GetPDGEncoding();
    const auto postE = aStep->GetPostStepPoint()->GetKineticEnergy();

    // kinetic energy pre step in MeV
    auto kinEnergyMeV = postE / CLHEP::MeV;

    int partType;
    switch (PDGCode)
    {
        case 22:
            partType = 1; // gamma
            break;
        case 11:
            partType = 2; // electron
            break;
        case -11:
            partType = 3; // positron
            break;
        case 2112:
            partType = 4; // neutron
            break;
        case 2212:
            partType = 5; // proton
            break;
        default:
            G4String pname = theTrack->GetDefinition()->GetParticleName();
            G4String errmsg = "'" + pname + "' is not supported by IAEA phsp format and will not be recorded.";
            G4Exception("G4IAEAphspWriter::StoreIAEAParticle()",
                        "IAEAwriter002", JustWarning, errmsg.c_str());
    }

    // position !WORLD COORDS!
    const auto pos = aStep->GetPostStepPoint()->GetPosition();
    auto x = pos.x();
    auto y = pos.y();
    auto z = pos.z();

    // Momentum direction
    auto momDir = aStep->GetPostStepPoint()->GetMomentumDirection();
    auto u = momDir.x();
    auto v = momDir.y();
    auto w = momDir.z();

    // write particle data in file:
    // particle type, position x, position y, position z, momentum u, momentum v, momentum w, kinetic energy
    outdata << partType << std::setw(15) << x << std::setw(15) << y << std::setw(15) << z << std::setw(15) << u
            << std::setw(15) << v << std::setw(15) << w << std::setw(15) << kinEnergyMeV << std::endl;

}