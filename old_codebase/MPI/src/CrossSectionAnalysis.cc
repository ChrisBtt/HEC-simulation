#include "CrossSectionAnalysis.hh"

#include <vector>
#include <map>
#include <utility>
#include <fstream>

#include "globals.hh"
#include "G4EmCalculator.hh"
#include "G4Material.hh"
#include "G4SystemOfUnits.hh"
#include "G4Gamma.hh"


CrossSectionAnalysis::CrossSectionAnalysis(const std::vector<G4Material*>* materials,
                                           G4double kinEnergy)
:m_Mats(materials), m_KinEnergy(kinEnergy)
{
}

XSMapping CrossSectionAnalysis::ComputeCrossSectionsPerVolumeForGamma()
{   
    G4EmCalculator emCalculator;
    //emCalculator.SetVerbose(1);

    // will store all data
    XSMapping data;
    data.reserve(m_Mats->size());

    // loop over materials
    for (const auto* mat : *m_Mats)
    {   
        // Material Info
        MaterialInfo matInfo;
        matInfo.name = mat->GetName();
        matInfo.dens = mat->GetDensity() / CLHEP::g * CLHEP::cm3;

        // holds xsection data for one material
        std::vector<XSData> dataVector;
        dataVector.reserve(3);

        // photoeffect
        XSData phot;
        phot.procName = "phot";
        phot.xSection = emCalculator.ComputeCrossSectionPerVolume(m_KinEnergy, 
                                                                  G4Gamma::Gamma(),
                                                                  "phot", mat);
        dataVector.push_back(phot);

        // compton
        XSData compt;
        compt.procName = "compt";
        compt.xSection = emCalculator.ComputeCrossSectionPerVolume(m_KinEnergy, 
                                                                  G4Gamma::Gamma(),
                                                                  "compt", mat);
        dataVector.push_back(compt);
        
        // rayleigh
        XSData rayl;
        rayl.procName = "rayl";
        rayl.xSection = emCalculator.ComputeCrossSectionPerVolume(m_KinEnergy, 
                                                                  G4Gamma::Gamma(),
                                                                  "Rayl", mat);
        dataVector.push_back(rayl);

        // add to the map
        data.emplace_back(std::make_pair<MaterialInfo, std::vector<XSData>>(std::move(matInfo),
                                                                            std::move(dataVector)));

        //G4cout << "DEDX " << emCalculator.ComputeTotalDEDX(m_KinEnergy, G4Electron::Electron(), mat) << G4endl;

    }

    return data;
}

void CrossSectionAnalysis::Dump(const XSMapping& data, const G4String& filename)
{   
    // open file for dumping
    std::ofstream outFile;
    outFile.open(filename + ".txt");

    // delimiter
    G4String tab = "    ";

    // print header
    outFile << "Material Index" << tab
            << "Material Name" << tab
            << "Density [g/cm^3]" << tab;

    // processes for header line
    auto entry = data[0];
    for (const auto& el : entry.second)
    {
        outFile << el.procName << " " << "[1/cm]" << tab;
    }
    outFile << "\n";

    // fill the file
    G4int idx = 0;
    for (const auto& [matInfo, xsData] : data)
    {
        outFile << idx++ << tab
                << matInfo.name << tab
                << matInfo.dens << tab;
        
        for (const auto& el : xsData)
        {
            outFile << el.xSection << tab;
        }

        outFile << "\n";
    }

    outFile.close();
}