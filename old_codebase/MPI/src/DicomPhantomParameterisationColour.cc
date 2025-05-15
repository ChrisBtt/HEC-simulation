

#include "DicomPhantomParameterisationColour.hh"
#include "DicomHandler.hh"

#include "globals.hh"
#include "G4VisAttributes.hh"
#include "G4Material.hh"
#include "G4VPhysicalVolume.hh"
#include "G4LogicalVolume.hh"

#include "G4VisAttributes.hh"
#include "G4VVisManager.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4String DicomPhantomParameterisationColour::defaultColorFile =
        DicomHandler::GetDicomDataPath() + "/ColourMap.dat";

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
DicomPhantomParameterisationColour::DicomPhantomParameterisationColour( G4String colourFile)
: G4PhantomParameterisation()
{
	G4cout << "Loaded Color Map Data: " << colourFile << G4endl;
    ReadColourData(colourFile);
    SetSkipEqualMaterials(false);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
DicomPhantomParameterisationColour::~DicomPhantomParameterisationColour()
{
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
void DicomPhantomParameterisationColour::ReadColourData(G4String colourFile)
{
    //----- Add a G4VisAttributes for materials not defined in file;
    G4VisAttributes* blankAtt = new G4VisAttributes;
    blankAtt->SetVisibility( FALSE );
    fColours["Default"] = blankAtt;

    //----- Read file
   std::ifstream fin(colourFile.c_str());
    G4int nMate;
    G4String mateName;
    G4double cred, cgreen, cblue, copacity;
    fin >> nMate;
    for( G4int ii = 0; ii < nMate; ii++ )
    {
		fin >> mateName;
#ifdef G4VERBOSE
		G4cout << "Material Name: " << mateName << G4endl;
#endif
        if(fin.eof())
            break;
        fin >> cred >> cgreen >> cblue >> copacity;
#ifdef G4VERBOSE
		G4cout << "Material Color: " << cred << cgreen << cblue << copacity << G4endl;
#endif

		// OPACITY IS AUTOMATICALY SET TO 1, G4COLOR SEEMS TO NOT WORK WITH OPACITY

        G4Colour colour( cred, cgreen, cblue, copacity );
        G4VisAttributes* visAtt = new G4VisAttributes( colour );
        visAtt->SetVisibility(true);
        fColours[mateName] = visAtt;
        mColours[ii] = new G4VisAttributes(*visAtt);
    }

}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
G4Material* DicomPhantomParameterisationColour::
ComputeMaterial(const G4int copyNo, G4VPhysicalVolume * physVol, const G4VTouchable *)
{
	// 
    G4Material* mate = G4PhantomParameterisation::ComputeMaterial( copyNo, physVol, 0 );

    if(G4VVisManager::GetConcreteInstance() && physVol)
    {
        G4String mateName = mate->GetName();
		        std::string::size_type iuu = mateName.find("__");
        if( iuu != std::string::npos )
            mateName = mateName.substr( 0, iuu );

		if (0 < fColours.count(mateName))
		{
			physVol->GetLogicalVolume()->SetVisAttributes(fColours.find(mateName)->second);
		}

		
        else
        {
            bool found = false;
            for(const auto& itr : fColours)
            {
                G4String mat_color = itr.first;
                auto len = mat_color.length();
                if(mateName.find(mat_color) == 0 &&
                   mateName.length() > len && mateName[len] == '_')
                {	
                    physVol->GetLogicalVolume()->SetVisAttributes(
                        fColours.find(mat_color)->second);


                    found = true;
                }
                if(found)
                    break;
            }
            if(!found)
            {
                G4int matIndex = GetMaterialIndex(copyNo);
                static uintmax_t n = 0;
                if(n++ < 100)
                    G4cout << "Unknown material name " << mateName
                           << " for index " << matIndex << G4endl;
                if(mColours.find(matIndex) != mColours.end())
                    physVol->GetLogicalVolume()->SetVisAttributes(
                        mColours.find(matIndex)->second);
                else
                    physVol->GetLogicalVolume()->SetVisAttributes(
                        fColours.begin()->second);
            }
        }
    }

    return mate;
}
