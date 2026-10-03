# Simulating an Eclipse 3D CT Plan with TOPAS

This workflow uses an Eclipse-exported CT image set, RT Structure Set (RTSTRUCT), RT Plan (RTPLAN), and RT Dose (RTDOSE) with TOPAS. TOPAS scores a new dose distribution as DICOM; `replace_rtdose.py` then places that dose into a copy of the Eclipse RTDOSE while retaining the Eclipse plan references.

The beam geometry is not automatically derived from the Eclipse RT Plan in this workflow. Set and verify the source position and direction manually so that the beam enters from outside the patient and its central axis intersects the PTV. Dose normalization and geometry choices also require review before interpreting the output.

## 1. Prepare the Eclipse DICOM data

Export the 3D CT image series and its matching RTSTRUCT, RTPLAN, and RTDOSE from Eclipse. Keep the files from the same plan and image frame of reference together. For the example commands below, the files are in:

```text
data/p107_20260910/new_DICOM/
```

Use the RTDOSE belonging to the RTPLAN that you will pass to the conversion script. The script reports Frame of Reference UID and RTDOSE-to-RTPLAN reference mismatches; resolve unexpected mismatches before using its output.

## 2. Configure the 3D CT simulation

The TOPAS macro set for this workflow is in `TOPAS_macros/dicom_input/`. `simulation.txt` is the top-level macro and includes the beam source, scorer, and HU-to-material files. The checked-in macros may contain machine-specific absolute paths, so update paths for the local installation and the generated TOPAS patient data before running.

The repository also has `config/dataset_3dct.yaml` for generating the TOPAS dataset with `hecTool`. Check its `patient.dicom_directories`, output directory, and settings. If using `hecTool` to prepare or regenerate the simulation directory, run it from the project root, for example:

```bash
python -m hecTool config/dataset_3dct.yaml --threadcount 24
```

Review the generated `simulation.txt` and included files after generation. Ensure the `Ge/Patient/DicomDirectory` points to the prepared 3D CT data and that the includes resolve to the intended `particle_sources.txt`, `scoring_dose.txt` (or the desired scoring macro), `HUtoMaterialSchneider.txt`, and `hec_parameters.txt`. When running the macros in `TOPAS_macros/dicom_input` directly, check their configured paths and includes rather than assuming the generated `config/` macros are being used.

The dose scorer in `scoring_dose.txt` is configured for DICOM output. It writes the dose grid using the configured output directory and a `DoseGrid` file stem; TOPAS may append an index such as `_Run_0000_50.dcm`. Confirm the actual output path and that the result is a readable RTDOSE before conversion.

## 3. Set and verify the beam manually

Edit `TOPAS_macros/dicom_input/particle_sources.txt` (or the copy included by the active simulation macro). Adjust `Ge/BeamPos/TransX`, `TransY`, and `TransZ` to put the source outside the body. Adjust `Ge/BeamPos/RotX`, `RotY`, and `RotZ` so the source emits toward the PTV. The TOPAS beam emits along the local `+Z` axis of `BeamPos`; its rotation determines the world-space beam direction.

The default source direction is head-to-toe. For a front-to-back anteroposterior beam, rotate that direction about the X axis by 90 degrees, choosing `+90 deg` or `-90 deg` according to the coordinate convention and desired direction of travel. A 180-degree reversal changes which side the beam enters from. Do not assume an angle alone makes the beam hit the PTV: the source's lateral coordinates and the central-axis line must also pass through the target.

Use the CT/RTSTRUCT and TOPAS geometry to determine the PTV center, body surface, patient orientation, and coordinate mapping. Place the source beyond the body surface along the reverse beam direction. Verify the resulting line from source through the PTV in patient/world coordinates (and, where available, a geometry or dose visualization). RTSTRUCT BODY restriction and cloning the RTDOSE grid can help with geometry/scoring, but neither determines the correct beam aim.

Beam positioning is intentionally a manual step. The sample beam values in a macro may be experimental and are not a validated treatment setup. Do not rely on the previous beam position or angle without checking it against the current CT and PTV.

## 4. Run TOPAS

Run from the macro directory (or otherwise ensure all relative `includeFile` paths resolve). The primary simulation command is:

```bash
cd TOPAS_macros/dicom_input
topas simulation.txt
```

The visualization settings in `simulation.txt` can be left disabled. Visualization is optional and may not work in some TOPAS installations; it is not required for dose scoring. After the run, check the TOPAS log for errors and locate the DICOM dose output configured by the scorer. The example below expects:

```text
TOPAS_simulation_data/dicom_input/DoseGrid_Run_0000_50.dcm
```

Change `--topas-dose` if the actual output filename or directory differs. Review the scored dose grid and its coordinates before proceeding.

### Optional body or dose-grid restriction

Scoring can optionally be restricted to an RTSTRUCT region such as `BODY` (the commented `OnlyIncludeIfInRTStructure` setting in `scoring_dose.txt`) or configured to use the patient's cloned RTDOSE grid (`Patient/RTDoseGrid`, with `CloneRTDoseGridFrom` in the patient macro). These are optional scoring/grid choices, not beam-aiming controls. Confirm that the active TOPAS version and macro support the selected option and that the output grid covers the region of interest.

If the TOPAS dose grid does not match the Eclipse grid, the conversion script normally resamples TOPAS dose onto the Eclipse RTDOSE grid in physical patient coordinates. Use `--keep-geometry-from-topas` only when intentionally retaining the TOPAS grid and its geometry in the output. It does not align, shift, or correct a wrongly positioned dose grid.

## 5. Convert TOPAS dose into a matching RTDOSE

Run the conversion from the repository root. Replace paths if your input or output files differ:

```bash
python3 TOPAS_macros/dicom_input/replace_rtdose.py \
  --eclipse-dose "data/p107_20260910/new_DICOM/RD.1.2.246.352.71.7.859390668362.14023170.20260910084532.dcm" \
  --topas-dose "TOPAS_simulation_data/dicom_input/DoseGrid_Run_0000_50.dcm" \
  --rtplan "data/p107_20260910/new_DICOM/RP.1.2.246.352.71.5.859390668362.5112380.20260910084529.dcm" \
  --rtstruct "data/p107_20260910/new_DICOM/RS.1.2.246.352.205.5224313503680033237.5100524843594716820.dcm" \
  --output "TOPAS_simulation_data/dataset_3dct/phase_0/RTDOSE.dcm" \
  --overwrite \
  --plot-3d-interactive \
  --plot-histogram \
  --norm-method percentile \
  --keep-geometry-from-topas
```

The script copies the Eclipse RTDOSE metadata/references and substitutes the normalized TOPAS dose pixels. It checks the supplied RTDOSE, RTPLAN, and RTSTRUCT references, compares the dose grids, reports dose centroids and normalization information, and writes the requested plots next to the output unless plot paths are explicitly supplied.

Important options in this command:

- `--norm-method percentile` scales TOPAS dose so its selected percentile matches the same percentile of the Eclipse dose. The default is P99.9; set `--norm-percentile` explicitly if another percentile is intended. The scale factor is analytical normalization, not absolute TOPAS calibration.
- `--keep-geometry-from-topas` retains the TOPAS dose grid and geometry rather than resampling to the Eclipse dose grid. Omit this flag to resample to the Eclipse grid. Confirm that retaining the TOPAS geometry is intentional and supported by the target viewer/workflow.
- `--plot-histogram` writes a dose histogram image. `--plot-3d-interactive` writes an interactive HTML dose plot. By default these use the output stem, for example `RTDOSE_dose_histogram.png` and `RTDOSE_3d.html` in the output directory.
- `--overwrite` permits replacing the output file if it already exists. Choose a separate output path if you need to preserve a previous result.

The script requires Python packages `numpy`, `pydicom`, and `scipy`. Histogram plotting also requires `matplotlib`; interactive plotting requires `plotly`. Install missing packages in the Python environment used to run the script.

## 6. Review the result

Before using the output, confirm that the script completed without errors and inspect its warnings and diagnostic values. Open the generated RTDOSE and plots in a DICOM viewer, checking dose location, grid orientation/spacing, target coverage, and agreement with the intended geometry. Pay particular attention to Frame of Reference UID warnings, RT Plan reference warnings, all-zero/resampled dose warnings, dose saturation warnings, and the normalization factor.

The workflow produces a derived research/simulation dose associated with Eclipse plan metadata; matching metadata does not make the TOPAS dose clinically approved or equivalent to the Eclipse calculation. Validate coordinates, beam angle, dose scoring, normalization, and the final DICOM in the intended downstream system. Do not use it for patient treatment without the appropriate independent clinical and physics validation.
