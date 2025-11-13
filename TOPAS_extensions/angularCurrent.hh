#ifndef angularCurrent_hh
#define angularCurrent_hh

#include "TsVBinnedScorer.hh"
#include "G4ios.hh"


class angularCurrent : public TsVBinnedScorer
{
public:
	angularCurrent(TsParameterManager* pM, TsMaterialManager* mM, TsGeometryManager* gM, TsScoringManager* scM, TsExtensionManager* eM,
						  G4String scorerName, G4String quantity, G4String outFileName, G4bool isSubScorer);

	virtual ~angularCurrent();

	G4bool ProcessHits(G4Step*,G4TouchableHistory*);
	G4int SingleBoundary = 0;
	G4int DoubleBoundary =0;

private:
	char dirAxis_ = 'z';
};
#endif