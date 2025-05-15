#include "StatAnalysis.hh"

void StatAnalysis::PrintInfo(std::ostream& os, const std::string& tab) const
{
    G4int _hits     = this->GetHits();
    G4double _sum   = this->GetSum();
    G4double _mean = this->GetMean();
    G4double _sigma = this->GetStdDev();
    G4double _coeff = this->GetCoeffVariation();
    G4double _error = this->GetRelativeError();
    G4double _eff   = this->GetEfficiency();
    G4double _fom   = this->GetFOM();
    G4double _r2int = this->GetR2Int();
    G4double _r2eff = this->GetR2Eff();

    using std::setprecision;
    using std::setw;
    using std::scientific;
    using std::fixed;
    using std::left;
    using std::right;
    using std::ios;

    std::stringstream ss;
    ss << tab << _sum 
    << tab << _mean
    << tab << _sigma
    << tab << _error
    //<< tab << _coeff
    //<< tab << _eff
    //<< tab << _fom
    //<< tab << _r2int
    //<< tab << _r2eff
    << tab << _hits;

    os << ss.str();
}