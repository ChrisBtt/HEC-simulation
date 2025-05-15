#include "PSFPrimaryGenerator.hh"

#include <memory>
#include <array>

#include "globals.hh"
#include "G4ThreeVector.hh"
#include "G4MPImanager.hh"
#include "G4Threading.hh"
#include "G4PrimaryVertex.hh"
#include "G4Event.hh"
#include "G4Gamma.hh"
#include "G4Electron.hh"
#include "G4Positron.hh"
#include "G4Neutron.hh"
#include "G4Proton.hh"
#include "G4RunManagerFactory.hh"
#include "PSFReader.hh"


struct IAEAParticle;

PSFPrimaryGenerator::PSFPrimaryGenerator(std::shared_ptr<PSFReader> theReader)
: m_Reader(theReader)
{
    // mpi info
    m_numRanks = G4MPImanager::GetManager()->GetTotalSize();
    m_Rank = G4MPImanager::GetManager()->GetRank();

    // threading info
    m_numThreads = G4RunManagerFactory::GetMTMasterRunManager()->GetNumberOfThreads();
    m_ThreadID = G4Threading::G4GetThreadId();
}

PSFPrimaryGenerator::~PSFPrimaryGenerator() {}

void PSFPrimaryGenerator::GeneratePrimaryVertex(G4Event *evt)
{ 
    // Get one particle from the reader
    const auto iaeaParticle = m_Reader->ReadNextParticle();

    // particle definition
    G4ParticleDefinition *partDef = 0;
    switch (iaeaParticle.type)
    {
    case 1:
        partDef = G4Gamma::Definition();
        break;
    case 2:
        partDef = G4Electron::Definition();
        break;
    case 3:
        partDef = G4Positron::Definition();
        break;
    case 4:
        partDef = G4Neutron::Definition();
        break;
    case 5:
        partDef = G4Proton::Definition();
    default:
#ifdef G4VERBOSE
        G4cout << "Exception occurred at event " << evt->GetEventID() << "\n"
                << "reading particle code " << iaeaParticle.type << "." << G4endl;
#endif
        G4Exception("PSFPrimaryGenerator::GeneratePrimaryParticles()",
                    "", EventMustBeAborted, "Unknown particle code in IAEA file");
    }

    // particle position, time and momentum
    // particle_position member of G4VPrimaryGenerator
    particle_position = iaeaParticle.position * CLHEP::mm;

    G4double mass = partDef->GetPDGMass();
    G4double energy = iaeaParticle.energy * CLHEP::MeV + mass;
    G4double momentum = std::sqrt(energy * energy - mass * mass);

    // stored momentum vector is just direction
    auto momentumVec = iaeaParticle.momentum * momentum;

    // loop to take care of recycling
    for (G4int n = 0; n <= m_numRecycle; n++)
    {
        // Create the new primary particle
        auto* particle = new G4PrimaryParticle(partDef, momentumVec.x(), 
                                               momentumVec.y(), momentumVec.z());

        particle->SetWeight(iaeaParticle.weight);

        // Create the new primary vertex and set the primary to it
        // particle_time member of G4VPrimaryGenerator
        auto* vertex = new G4PrimaryVertex(particle_position, particle_time);
        vertex->SetPrimary(particle);

        // And finally set the vertex to this event
        evt->AddPrimaryVertex(vertex);
    }
}