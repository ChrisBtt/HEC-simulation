# TOPAS DICOM Input Workflow

This folder contains helper scripts for adjusting an RTPlan-based TOPAS DICOM simulation, validating the geometry and dose output, and patching the resulting RTDOSE into the synthesized DICOM dataset.

## Recommended workflow

1. Adjust the TOPAS beam setup from the Eclipse RTPlan:
   ```bash
   python3 TOPAS_macros/dicom_input/adjustBeamToRTPlan.py
   ```
   This updates `TOPAS_macros/dicom_input/particle_sources.txt` using the RTPlan and optionally reports the PTV bounding box from RTStruct.

2. Check the updated beam geometry against the synthetic CT and PTV:
   ```bash
   python3 TOPAS_macros/dicom_input/checkTOPASGeometry.py
   ```
   This verifies whether the TOPAS beam axis intersects the CT and the RTStruct-derived PTV.

3. Run the TOPAS simulation in the `TOPAS_macros/dicom_input` directory:
   ```bash
   cd TOPAS_macros/dicom_input
   /Users/pb438/shellScripts/topas simulation.txt
   ```

4. Validate the produced dose file:
   ```bash
   python3 TOPAS_macros/dicom_input/validateDoseOutput.py
   ```
   This selects the latest `DoseGrid_Run_*.dcm` and prints dose statistics.

5. Patch the generated RTDOSE into the synthetic CT dataset for Weasis import:
   ```bash
   python3 TOPAS_macros/dicom_input/correctOutputToDicomReq.py
   ```
   This writes patched RTSTRUCT, RTPLAN, and RTDOSE files into `TOPAS_simulation_data`.

## File purposes

- `adjustBeamToRTPlan.py`: load RTPlan, extract beam geometry, and update `particle_sources.txt`.
- `checkTOPASGeometry.py`: verify that the TOPAS beam origin/direction hits the CT and PTV.
- `validateDoseOutput.py`: inspect the newest TOPAS RTDOSE output for nonzero dose.
- `correctOutputToDicomReq.py`: patch RTSTRUCT/RTPLAN/RTDOSE so the resulting dataset is consistent for viewer import.

## Notes

- The scripts use hard-coded default paths to the current workspace DICOM and TOPAS folders.
- If your RTPlan or RTStruct file locations change, update the paths inside the scripts or invoke with custom arguments where supported.
- Ensure `topas` is available at `/Users/pb438/shellScripts/topas` or update the command to your local TOPAS executable.
