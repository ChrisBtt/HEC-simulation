#ifndef trackLength_hh
#define trackLength_hh

#include "TsVBinnedScorer.hh"
#include "G4ios.hh"


class trackLength : public TsVBinnedScorer
{
public:
	trackLength(TsParameterManager* pM, TsMaterialManager* mM, TsGeometryManager* gM, TsScoringManager* scM, TsExtensionManager* eM,
						  G4String scorerName, G4String quantity, G4String outFileName, G4bool isSubScorer);

	virtual ~trackLength();

	G4bool ProcessHits(G4Step*,G4TouchableHistory*);
	G4int SingleBoundary = 0;
	G4int DoubleBoundary = 0;

private:
	char dirAxis_ = 'z';
};
#endif