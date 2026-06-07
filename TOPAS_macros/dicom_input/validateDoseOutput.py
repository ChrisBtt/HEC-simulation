from pathlib import Path
import numpy as np
import pydicom

DOSE_DIR = Path("/Users/pb438/applications/hec-dose-distribution/TOPAS_simulation_data/dicom_input")
DOSE_PATTERN = "DoseGrid_Run_*.dcm"


def find_latest_dose_file(folder: Path):
    files = sorted(folder.glob(DOSE_PATTERN), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No dose files matching {DOSE_PATTERN} found in {folder}")
    return files[-1]


dose_path = find_latest_dose_file(DOSE_DIR)
print("Using dose file:", dose_path)

ds = pydicom.dcmread(dose_path, force=True)

print("Modality:", getattr(ds, "Modality", None))
print("SOPClassUID:", getattr(ds, "SOPClassUID", None))
print("SOPInstanceUID:", getattr(ds, "SOPInstanceUID", None))
print("PatientID:", getattr(ds, "PatientID", None))
print("StudyInstanceUID:", getattr(ds, "StudyInstanceUID", None))
print("SeriesInstanceUID:", getattr(ds, "SeriesInstanceUID", None))
print("FrameOfReferenceUID:", getattr(ds, "FrameOfReferenceUID", None))

print("\nDose tags:")
for key in [
    "DoseUnits",
    "DoseType",
    "DoseSummationType",
    "DoseGridScaling",
    "Rows",
    "Columns",
    "NumberOfFrames",
    "PixelSpacing",
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "GridFrameOffsetVector",
    "FrameIncrementPointer",
    "BitsAllocated",
    "BitsStored",
    "HighBit",
    "PixelRepresentation",
    "SamplesPerPixel",
    "PhotometricInterpretation",
]:
    print(f"{key}: {getattr(ds, key, 'MISSING')}")

print("\nPixel data:")
print("Has PixelData:", hasattr(ds, "PixelData"))
print("PixelData bytes:", len(getattr(ds, "PixelData", b"")))

arr = ds.pixel_array.astype(np.float64)
scaling = float(ds.DoseGridScaling)
dose = arr * scaling

print("\nStored pixel values:")
print("shape:", arr.shape)
print("min:", arr.min())
print("max:", arr.max())
print("nonzero voxels:", np.count_nonzero(arr), "/", arr.size)

print("\nDose values:")
print("unit:", getattr(ds, "DoseUnits", "UNKNOWN"))
print("min:", dose.min())
print("max:", dose.max())
print("mean nonzero:", dose[dose > 0].mean() if np.any(dose > 0) else 0)
print("nonzero dose voxels:", np.count_nonzero(dose), "/", dose.size)

for p in [50, 90, 95, 99, 99.9, 100]:
    print(f"Dose percentile {p}%:", np.percentile(dose, p))