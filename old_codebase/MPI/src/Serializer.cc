#include "Serializer.hh"
#include "DicomRun.hh"


Serializer::Serializer()
{
    arrSum1.fill(0.0);
    arrSum2.fill(0.0);
    arrHits.fill(0);
    arrZeros.fill(0);
    needsUnpacking = false;
}

Serializer::~Serializer()
{
}

void Serializer::Pack(const DicomRun::StatVector* statVec)
{
    if(statVec) 
    {
        for(auto itr = statVec->begin(); itr != statVec->end(); itr++) 
        {
            // get voxel idx and corresponding stats of the voxel
            auto _idx = statVec->GetIndex(itr);
            auto _stat = statVec->GetObject(itr);
            //G4cout << *_stat << G4endl;

            // add stats to members
            if(_stat && _stat->GetHits() > 0)
            {
                arrSum1[_idx] = _stat->GetSum1();
                arrSum2[_idx] = _stat->GetSum2();
                arrHits[_idx] = _stat->GetHits();
                arrZeros[_idx] = _stat->GetNumZero();
            }
        }
    }
}

DicomRun::StatVector* Serializer::Unpack() const
{
    auto unpackedStatVec = new DicomRun::StatVector("phantomSD", "DoseDeposit");

    for (int _idx = 0; _idx < GetBufferSize(); _idx++)
    {   
        // only add entry if voxel experienced any hits
        if (arrHits[_idx] != 0)
        {
            StatAnalysis currVoxel;
            currVoxel.SetSum1(arrSum1[_idx]);
            currVoxel.SetSum2(arrSum2[_idx]);
            currVoxel.SetHits(arrHits[_idx]);
            currVoxel.SetZero(arrZeros[_idx]);

            unpackedStatVec->add(_idx, currVoxel);
        }
    }

    return unpackedStatVec;
}

