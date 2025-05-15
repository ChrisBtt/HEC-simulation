#pragma once

#include "G4StatAnalysis.hh"

// inherit from G4StatAnalysis to overwrite the PrintInfo method
class StatAnalysis : public G4StatAnalysis
{
    public:
        // overwritten
        void PrintInfo(std::ostream& os, const std::string& tab="   ") const;

        // overwritten
        friend std::ostream& operator<<(std::ostream& os, const StatAnalysis& obj)
        {
            obj.PrintInfo(os);
            return os;
        }
};