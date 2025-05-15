/*
 * Copyright (C) 2009 International Atomic Energy Agency
 * -----------------------------------------------------------------------------
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is furnished
 * to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 *-----------------------------------------------------------------------------
 *
 *   AUTHORS:
 *
 *   Miguel Antonio Cortes Giraldo
 *   e-mail: miancortes -at- us.es
 *   University of Seville, Spain
 *   Dep. Fisica Atomica, Molecular y Nuclear
 *   Ap. 1065, E-41080 Seville, SPAIN
 *   Phone: +34-954550928; Fax: +34-954554445
 *
 *   Jose Manuel Quesada Molina, PhD
 *   e-mail: quesada -at- us.es
 *   University of Seville, Spain
 *   Dep. Fisica Atomica, Molecular y Nuclear
 *   Ap. 1065, E-41080 Seville, SPAIN
 *   Phone: +34-954559508; Fax: +34-954554445
 *
 *   Roberto Capote Noy, PhD
 *   e-mail: R.CapoteNoy -at- iaea.org (rcapotenoy -at- yahoo.com)
 *   International Atomic Energy Agency
 *   Nuclear Data Section, P.O.Box 100
 *   Wagramerstrasse 5, Vienna A-1400, AUSTRIA
 *   Phone: +431-260021713; Fax: +431-26007
 *
 **********************************************************************************
 * For documentation
 * see http://www-nds.iaea.org/phsp
 *
 * - 07/12/2009: public version 1.0
 *
 **********************************************************************************/

/* Special purpose PSFWriter class, stopping particles below a certain energy threshold
 * and writing them into a PSF file in IAEA format. 
 * Based on G4IAEAphspWriter, i.e. Singleton design but also works in conjunction with 
 * Multithreading and MPI -> Thread safe and a single PSF for every MPI Process, 
 */

#pragma once

#include <memory>
#include <atomic>
#include <shared_mutex>
#include <iostream>
#include <fstream>

#include "globals.hh"

class G4Event;
class G4Run;
class G4Step;

class PSFWriter
{
private:
    // singleton design
    static std::unique_ptr<PSFWriter> s_Instance;
    static std::once_flag s_initOnce;
    std::ofstream outdata;

    PSFWriter();
    PSFWriter(const PSFWriter&) = delete;
    PSFWriter &operator=(const PSFWriter&) = delete;

public:
    ~PSFWriter();
    static PSFWriter* GetInstance();

    void BeginOfRunAction(const G4Run*);
    void EndOfRunAction(const G4Run*);
    //void BeginOfEventAction(const G4Event*);
    void UserSteppingAction(const G4Step*);

private:
    void StoreIAEAParticle(const G4Step*);
    void StoreIAEAParticleToASCII(const G4Step*);
    bool CheckWriteCriterion(const G4Step*);

public:
    // These should be called only once (by master thread)
    void SetFileName(const G4String&, bool nameIsOutPath = false);
    void SetCutEnergy(G4double);

    // Getters
    G4String GetFileName() const;
    G4double GetCutEnergy() const;

    void SetWriteASCII();
    bool GetWriteASCII();

private:
    // Keeps track of the total number of particles written to a IAEA
    // file.
    std::atomic<int> m_TotalParticles = 0;

    // Cut Energy. Particles with E < E_cut are stopped and written
    // to the PSF.
    G4double m_CutEnergy;
    std::once_flag m_energyOnce;

    /* Naming scheme [...]/PSF_PATIENT-UUID_CUBE-ID_MPI-RANK.IAEAphsp
     * if path of output cube is passed to SetFileName and bool is set to 
     * True. Default name is PSF_MPI-RANK.IAEAphsp or in general 
     * NAME-PASSED_MPI-RANK.IAEA.phsp
     */
    G4String m_FileName;
    std::once_flag m_fileOnce;

    // read/write mutex
    mutable std::shared_mutex m_rwMtx;

    // Value needed in the IAEA routines to open a source for writing.
    static const G4int s_theAccessWrite = 2;

    bool writeASCII = false;
};