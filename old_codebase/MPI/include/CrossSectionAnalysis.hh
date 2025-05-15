#pragma once

#include <vector>
#include <memory>
#include <utility>
#include "globals.hh"

class G4Material;

struct XSData
{
    G4String procName;
    G4double xSection;
};

struct MaterialInfo
{
    G4String name;
    G4double dens;
};

typedef std::vector<std::pair<MaterialInfo, std::vector<XSData>>> XSMapping;

class CrossSectionAnalysis
{
public:
    CrossSectionAnalysis(const std::vector<G4Material*>* materials,
                         G4double kinEnergy);

    void SetKineticEnergy(G4double val) { m_KinEnergy = val; }

    // compute xs for every material in m_Mats for
    // gamma particles w/ energy m_KinEnergy
    XSMapping ComputeCrossSectionsPerVolumeForGamma();

    // save xs data to a ASCII .txt file
    static void Dump(const XSMapping& data, const G4String& filename);

private:

    G4double m_KinEnergy;
    const std::vector<G4Material*>* m_Mats;
};