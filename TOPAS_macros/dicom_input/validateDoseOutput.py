from pathlib import Path
from datetime import datetime

import numpy as np
import pydicom
from pydicom.uid import generate_uid, ExplicitVRLittleEndian
from pydicom.dataset import FileMetaDataset

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

arr = ds.pixel_array.astype(np.float64)
old_scaling = float(ds.DoseGridScaling)
dose = arr * old_scaling

max_dose = float(dose.max())
if max_dose <= 0:
    raise ValueError("Cannot normalize dose: maximum dose is zero.")

normalized_dose = dose / max_dose * 1000.0

print("\nOriginal dose:")
print("min:", dose.min())
print("max:", dose.max())
print("nonzero:", np.count_nonzero(dose), "/", dose.size)

print("\nNormalized dose:")
print("min:", normalized_dose.min())
print("max:", normalized_dose.max())
print("mean nonzero:", normalized_dose[normalized_dose > 0].mean() if np.any(normalized_dose > 0) else 0)
print("nonzero:", np.count_nonzero(normalized_dose), "/", normalized_dose.size)

for p in [50, 90, 95, 99, 99.9, 100]:
    print(f"Normalized dose percentile {p}%:", np.percentile(normalized_dose, p))


# ---------------------------------------------------------------------
# Write normalized dose back into a new RTDOSE DICOM
# ---------------------------------------------------------------------

out_path = dose_path.with_name(dose_path.stem + "_normalized_1000.dcm")

# Encode normalized dose as uint32 with DoseGridScaling
stored_max = np.iinfo(np.uint32).max
new_scaling = 1000.0 / stored_max

stored = np.rint(normalized_dose / new_scaling)
stored = np.clip(stored, 0, stored_max).astype(np.uint32)
stored = stored.astype("<u4", copy=False)

ds.PixelData = stored.tobytes()
ds.DoseGridScaling = new_scaling

ds.BitsAllocated = 32
ds.BitsStored = 32
ds.HighBit = 31
ds.PixelRepresentation = 0
ds.SamplesPerPixel = 1
ds.PhotometricInterpretation = "MONOCHROME2"

# Since this is now a relative, normalized dose, not a physical Gy dose
ds.DoseUnits = "RELATIVE"
ds.DoseType = getattr(ds, "DoseType", "PHYSICAL")
ds.DoseSummationType = getattr(ds, "DoseSummationType", "PLAN")

# Create new identifiers for the derived DICOM object
ds.SOPInstanceUID = generate_uid()
ds.SeriesInstanceUID = generate_uid()

now = datetime.now()
ds.InstanceCreationDate = now.strftime("%Y%m%d")
ds.InstanceCreationTime = now.strftime("%H%M%S")

ds.SeriesDescription = "Normalized 32-bit RTDOSE scaled to 1000"
ds.DoseComment = f"Original max dose {max_dose:.12g}; normalized to max=1000; uint32 encoding"

# Ensure file meta exists and is consistent
if not hasattr(ds, "file_meta") or ds.file_meta is None:
    ds.file_meta = FileMetaDataset()

ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
ds.is_little_endian = True
ds.is_implicit_VR = False

ds.save_as(out_path, write_like_original=False)

print("\nSaved normalized 32-bit RTDOSE:")
print(out_path)


# ---------------------------------------------------------------------
# Verify written file
# ---------------------------------------------------------------------

check = pydicom.dcmread(out_path)
check_arr = check.pixel_array.astype(np.float64)
check_dose = check_arr * float(check.DoseGridScaling)

print("\nVerification:")
print("DoseUnits:", check.DoseUnits)
print("DoseGridScaling:", check.DoseGridScaling)
print("stored min:", check_arr.min())
print("stored max:", check_arr.max())
print("dose min:", check_dose.min())
print("dose max:", check_dose.max())
print("nonzero:", np.count_nonzero(check_dose), "/", check_dose.size)