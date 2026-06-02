from pathlib import Path
import pydicom

infile = Path("E:\\Christoph\\EIT\\CT\\p107\\MP1_ph0_masked\\Simulation\\DoseGrid_Run_0000.dcm")
outfile = Path("E:\\Christoph\\EIT\\CT\\p107\\MP1_ph0_masked\\Simulation\\DoseGrid_Run_0000_patched.dcm")

ds = pydicom.dcmread(infile, force=True)

if getattr(ds, "Modality", None) != "RTDOSE":
    raise ValueError(f"Expected RTDOSE, found Modality={getattr(ds, 'Modality', None)}")

# Choose the correct value semantically.
# Use PLAN only if the dose represents the full RT plan dose.
ds.DoseSummationType = "PLAN"

ds.save_as(outfile, write_like_original=False)

print(f"Saved patched RTDOSE to: {outfile}")