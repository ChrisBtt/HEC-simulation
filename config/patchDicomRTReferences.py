from pathlib import Path
from collections import defaultdict
from datetime import datetime

import numpy as np
import pydicom
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid


# -----------------------------
# Configuration
# -----------------------------

dicom_folder = Path(r"E:\Christoph\EIT\CT\p107\MP1_ph0_masked")
output_folder = dicom_folder / "patched_for_weasis"
output_folder.mkdir(exist_ok=True)

# If your TOPAS/Eclipse dose is a full plan dose, set this to "PLAN".
# If it is really a single-beam dose, keep "BEAM".
DOSE_SUMMATION_TYPE = "BEAM"


# -----------------------------
# Helpers
# -----------------------------

def read_dicom_objects(folder: Path):
    objects = defaultdict(list)

    for f in folder.rglob("*"):
        if not f.is_file():
            continue

        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
            modality = getattr(ds, "Modality", "UNKNOWN")
            objects[modality].append((f, ds))
        except Exception:
            pass

    return objects


def get_ct_sorting_geometry(ct_items):
    """
    Sort CT slices by physical slice coordinate.
    Uses ImageOrientationPatient and ImagePositionPatient.
    """
    first_ct = ct_items[0][1]

    iop = np.array([float(x) for x in first_ct.ImageOrientationPatient])
    row_dir = iop[:3]
    col_dir = iop[3:]
    normal = np.cross(row_dir, col_dir)

    sorted_items = []

    for f, ds in ct_items:
        ipp = np.array([float(x) for x in ds.ImagePositionPatient])
        slice_coord = float(np.dot(ipp, normal))
        sorted_items.append((slice_coord, f, ds))

    sorted_items.sort(key=lambda x: x[0])
    return sorted_items, normal


def make_image_ref(ct_ds):
    ref = Dataset()
    ref.ReferencedSOPClassUID = ct_ds.SOPClassUID
    ref.ReferencedSOPInstanceUID = ct_ds.SOPInstanceUID
    return ref


def set_new_sop_instance_uid(ds):
    new_uid = generate_uid()
    ds.SOPInstanceUID = new_uid

    if hasattr(ds, "file_meta"):
        ds.file_meta.MediaStorageSOPInstanceUID = new_uid
        if hasattr(ds, "SOPClassUID"):
            ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID

    return new_uid


def set_common_patient_study_fields(ds, ct_ref):
    """
    Align basic patient/study metadata with the converted CT.
    """
    ds.PatientID = ct_ref.PatientID
    ds.StudyInstanceUID = ct_ref.StudyInstanceUID

    if hasattr(ct_ref, "PatientName"):
        ds.PatientName = ct_ref.PatientName

    if hasattr(ct_ref, "PatientBirthDate"):
        ds.PatientBirthDate = ct_ref.PatientBirthDate

    if hasattr(ct_ref, "PatientSex"):
        ds.PatientSex = ct_ref.PatientSex

    # Keep RT objects as separate series but within the same study.
    ds.SeriesInstanceUID = generate_uid()

    now = datetime.now()
    ds.InstanceCreationDate = now.strftime("%Y%m%d")
    ds.InstanceCreationTime = now.strftime("%H%M%S")


def find_nearest_ct_ref_for_contour(contour, sorted_ct_items, normal):
    """
    Map a contour to the nearest converted CT slice by physical plane coordinate.
    """
    if not hasattr(contour, "ContourData") or len(contour.ContourData) < 3:
        return None

    data = [float(x) for x in contour.ContourData]
    first_point = np.array(data[:3])
    contour_coord = float(np.dot(first_point, normal))

    nearest = min(
        sorted_ct_items,
        key=lambda item: abs(item[0] - contour_coord)
    )

    _, _, nearest_ct = nearest
    return make_image_ref(nearest_ct)


def copy_original_with_pixels(src_path, dst_path):
    """
    Re-read full DICOM including PixelData before saving.
    Useful for RTDOSE.
    """
    return pydicom.dcmread(src_path, force=True)


# -----------------------------
# Load files
# -----------------------------

objects = read_dicom_objects(dicom_folder)

ct_items = objects.get("CT", [])
rtstruct_items = objects.get("RTSTRUCT", [])
rtplan_items = objects.get("RTPLAN", [])
rtdose_items = objects.get("RTDOSE", [])

if len(ct_items) == 0:
    raise RuntimeError("No CT files found.")

if len(rtstruct_items) != 1:
    raise RuntimeError(f"Expected exactly one RTSTRUCT, found {len(rtstruct_items)}.")

if len(rtplan_items) != 1:
    raise RuntimeError(f"Expected exactly one RTPLAN, found {len(rtplan_items)}.")

if len(rtdose_items) != 1:
    raise RuntimeError(f"Expected exactly one RTDOSE, found {len(rtdose_items)}.")

sorted_ct_items, ct_normal = get_ct_sorting_geometry(ct_items)

ct_ref = sorted_ct_items[0][2]
ct_study_uid = ct_ref.StudyInstanceUID
ct_series_uid = ct_ref.SeriesInstanceUID
ct_frame_uid = ct_ref.FrameOfReferenceUID

all_ct_image_refs = Sequence([
    make_image_ref(ds) for _, _, ds in sorted_ct_items
])

print("Converted CT target:")
print("  PatientID:", ct_ref.PatientID)
print("  StudyInstanceUID:", ct_study_uid)
print("  SeriesInstanceUID:", ct_series_uid)
print("  FrameOfReferenceUID:", ct_frame_uid)
print("  Number of CT slices:", len(sorted_ct_items))


# -----------------------------
# Patch RTSTRUCT
# -----------------------------

rtstruct_path, _ = rtstruct_items[0]
rs = pydicom.dcmread(rtstruct_path, force=True)

set_common_patient_study_fields(rs, ct_ref)
new_rs_uid = set_new_sop_instance_uid(rs)

# Structure Set ROI frame references
if hasattr(rs, "StructureSetROISequence"):
    for roi in rs.StructureSetROISequence:
        roi.ReferencedFrameOfReferenceUID = ct_frame_uid

# Main RTSTRUCT reference tree:
# ReferencedFrameOfReferenceSequence
#   -> RTReferencedStudySequence
#      -> RTReferencedSeriesSequence
#         -> ContourImageSequence
rfor = Dataset()
rfor.FrameOfReferenceUID = ct_frame_uid

study_ref = Dataset()

# Many RTSTRUCTs use the old Detached Study Management SOP class here.
# We preserve the existing value if available; otherwise, use the common legacy value.
old_study_ref = None
if hasattr(rs, "ReferencedFrameOfReferenceSequence"):
    try:
        old_study_ref = rs.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0]
    except Exception:
        old_study_ref = None

if old_study_ref is not None and hasattr(old_study_ref, "ReferencedSOPClassUID"):
    study_ref.ReferencedSOPClassUID = old_study_ref.ReferencedSOPClassUID
else:
    study_ref.ReferencedSOPClassUID = "1.2.840.10008.3.1.2.3.1"

# In practice, this is often set to the StudyInstanceUID in RTSTRUCT exports.
study_ref.ReferencedSOPInstanceUID = ct_study_uid

series_ref = Dataset()
series_ref.SeriesInstanceUID = ct_series_uid
series_ref.ContourImageSequence = all_ct_image_refs

study_ref.RTReferencedSeriesSequence = Sequence([series_ref])
rfor.RTReferencedStudySequence = Sequence([study_ref])
rs.ReferencedFrameOfReferenceSequence = Sequence([rfor])

# Per-contour image references
if hasattr(rs, "ROIContourSequence"):
    for roi_contour in rs.ROIContourSequence:

        # Optional source series reference, if present
        if hasattr(roi_contour, "SourceSeriesSequence"):
            for src in roi_contour.SourceSeriesSequence:
                src.SeriesInstanceUID = ct_series_uid

        if not hasattr(roi_contour, "ContourSequence"):
            continue

        for contour in roi_contour.ContourSequence:
            nearest_ref = find_nearest_ct_ref_for_contour(
                contour,
                sorted_ct_items,
                ct_normal
            )

            if nearest_ref is not None:
                contour.ContourImageSequence = Sequence([nearest_ref])

rs.StructureSetLabel = getattr(rs, "StructureSetLabel", "PATCHED_RS")
rs.StructureSetName = getattr(rs, "StructureSetName", "PATCHED_RS")

patched_rs_path = output_folder / "RS_patched_to_converted_CT.dcm"
rs.save_as(patched_rs_path, write_like_original=False)

print("\nPatched RTSTRUCT:")
print("  New SOPInstanceUID:", new_rs_uid)
print("  Saved:", patched_rs_path)


# -----------------------------
# Patch RTPLAN
# -----------------------------

rtplan_path, _ = rtplan_items[0]
rp = pydicom.dcmread(rtplan_path, force=True)

set_common_patient_study_fields(rp, ct_ref)
new_rp_uid = set_new_sop_instance_uid(rp)

# Link RTPLAN to patched RTSTRUCT
ref_rs = Dataset()
ref_rs.ReferencedSOPClassUID = rs.SOPClassUID
ref_rs.ReferencedSOPInstanceUID = new_rs_uid
rp.ReferencedStructureSetSequence = Sequence([ref_rs])

patched_rp_path = output_folder / "RP_patched_to_converted_CT.dcm"
rp.save_as(patched_rp_path, write_like_original=False)

print("\nPatched RTPLAN:")
print("  New SOPInstanceUID:", new_rp_uid)
print("  References RTSTRUCT:", new_rs_uid)
print("  Saved:", patched_rp_path)


# -----------------------------
# Patch RTDOSE
# -----------------------------

rtdose_path, _ = rtdose_items[0]
rd = pydicom.dcmread(rtdose_path, force=True)

set_common_patient_study_fields(rd, ct_ref)
new_rd_uid = set_new_sop_instance_uid(rd)

rd.FrameOfReferenceUID = ct_frame_uid
rd.DoseSummationType = DOSE_SUMMATION_TYPE

# Link RTDOSE to patched RTPLAN
ref_rp = Dataset()
ref_rp.ReferencedSOPClassUID = rp.SOPClassUID
ref_rp.ReferencedSOPInstanceUID = new_rp_uid

# Preserve existing fraction/beam reference details if present.
old_rd = pydicom.dcmread(rtdose_path, stop_before_pixels=True, force=True)
if hasattr(old_rd, "ReferencedRTPlanSequence"):
    old_ref_plan = old_rd.ReferencedRTPlanSequence[0]

    if hasattr(old_ref_plan, "ReferencedFractionGroupSequence"):
        ref_rp.ReferencedFractionGroupSequence = old_ref_plan.ReferencedFractionGroupSequence

rd.ReferencedRTPlanSequence = Sequence([ref_rp])

patched_rd_path = output_folder / "RD_patched_to_converted_CT.dcm"
rd.save_as(patched_rd_path, write_like_original=False)

print("\nPatched RTDOSE:")
print("  New SOPInstanceUID:", new_rd_uid)
print("  References RTPLAN:", new_rp_uid)
print("  DoseSummationType:", rd.DoseSummationType)
print("  FrameOfReferenceUID:", rd.FrameOfReferenceUID)
print("  Saved:", patched_rd_path)


print("\nDone.")
print("Now import the converted CT slices plus the patched RS/RP/RD files into Weasis.")