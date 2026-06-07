from pathlib import Path
from collections import defaultdict
from datetime import datetime
import shutil

import numpy as np
import pydicom
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid


# =============================================================================
# Configuration
# =============================================================================

SYNTHETIC_CT_DIR = Path("/Users/pb438/applications/hec-dose-distribution/TOPAS_simulation_data/dataset_3dct/phase_0")

# Adjust these three paths.
SOURCE_RTSTRUCT = Path("/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RS_patched_to_converted_CT.dcm")
SOURCE_RTPLAN = Path("/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RP_patched_to_converted_CT.dcm")
SOURCE_RTDose_DIR = Path("/Users/pb438/applications/hec-dose-distribution/TOPAS_simulation_data/dicom_input")
SOURCE_RTDose = max(
    SOURCE_RTDose_DIR.glob("DoseGrid_Run_*.dcm"),
    key=lambda p: p.stat().st_mtime,
)

OUTPUT_DIR = Path("/Users/pb438/applications/hec-dose-distribution/TOPAS_simulation_data")

OUT_RTSTRUCT = OUTPUT_DIR / "RS_linked_to_synthetic_CT.dcm"
OUT_RTPLAN = OUTPUT_DIR / "RP_linked_to_synthetic_CT.dcm"
OUT_RTDose = OUTPUT_DIR / "RD_linked_to_synthetic_CT.dcm"

# Safer for Weasis/Eclipse if originals may also be imported somewhere.
REGENERATE_RT_OBJECT_UIDS = True

# Use "PLAN" if the dose is the complete plan dose.
# Use "BEAM" if the dose is one beam only.
DOSE_SUMMATION_TYPE = "BEAM"

# Only used when DOSE_SUMMATION_TYPE == "BEAM".
REFERENCED_BEAM_NUMBER = 1


# =============================================================================
# Basic helpers
# =============================================================================

def read_full_dicom(path: Path):
    """
    Important: no stop_before_pixels here.
    Especially RTDOSE must be read with PixelData preserved.
    """
    return pydicom.dcmread(path, force=False)


def read_dicom_objects(folder: Path):
    objects = defaultdict(list)

    for f in folder.rglob("*"):
        if not f.is_file():
            continue

        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
            objects[getattr(ds, "Modality", "UNKNOWN")].append((f, ds))
        except Exception:
            pass

    return objects


def save_preserving(ds, out_path: Path):
    """
    Preserve original DICOM content as much as possible.

    write_like_original=False makes pydicom write a valid Part-10 file.
    This should not remove dataset tags. It only normalizes file writing.
    """
    if hasattr(ds, "file_meta"):
        if hasattr(ds, "SOPClassUID"):
            ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
        if hasattr(ds, "SOPInstanceUID"):
            ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    ds.save_as(out_path, write_like_original=False)


def regenerate_sop_uid_if_requested(ds):
    if not REGENERATE_RT_OBJECT_UIDS:
        return ds.SOPInstanceUID

    new_uid = generate_uid()
    ds.SOPInstanceUID = new_uid

    if hasattr(ds, "file_meta"):
        ds.file_meta.MediaStorageSOPInstanceUID = new_uid

    return new_uid


def copy_patient_study_identity_from_ct(ds, ct_ref):
    """
    Minimal identity patch. Do not delete other fields.
    """
    for keyword in [
        "PatientName",
        "PatientID",
        "PatientBirthDate",
        "PatientSex",
        "PatientAge",
        "PatientWeight",
    ]:
        if hasattr(ct_ref, keyword):
            setattr(ds, keyword, getattr(ct_ref, keyword))

    ds.StudyInstanceUID = ct_ref.StudyInstanceUID

    # Put copied RT objects into the synthetic CT study.
    # Keep their original SeriesDescription etc.
    # New SeriesInstanceUID avoids clashes with prior RT series.
    if REGENERATE_RT_OBJECT_UIDS:
        ds.SeriesInstanceUID = generate_uid()

    now = datetime.now()
    ds.InstanceCreationDate = now.strftime("%Y%m%d")
    ds.InstanceCreationTime = now.strftime("%H%M%S")


def get_sorted_ct(ct_dir: Path):
    objects = read_dicom_objects(ct_dir)
    ct_items = objects.get("CT", [])

    if not ct_items:
        raise RuntimeError(f"No CT files found in {ct_dir}")

    first_ct = ct_items[0][1]

    iop = np.array([float(x) for x in first_ct.ImageOrientationPatient])
    row_dir = iop[:3]
    col_dir = iop[3:]
    normal = np.cross(row_dir, col_dir)

    sorted_ct = []

    for f, ds in ct_items:
        ipp = np.array([float(x) for x in ds.ImagePositionPatient])
        coord = float(np.dot(ipp, normal))
        sorted_ct.append((coord, f, ds))

    sorted_ct.sort(key=lambda x: x[0])
    return sorted_ct, normal


def make_ct_ref(ct_ds):
    ref = Dataset()
    ref.ReferencedSOPClassUID = ct_ds.SOPClassUID
    ref.ReferencedSOPInstanceUID = ct_ds.SOPInstanceUID
    return ref


def nearest_ct_ref_from_contour(contour, sorted_ct, normal):
    if not hasattr(contour, "ContourData") or len(contour.ContourData) < 3:
        return None

    coords = [float(x) for x in contour.ContourData]
    p = np.array(coords[:3])
    contour_coord = float(np.dot(p, normal))

    _, _, nearest_ct = min(
        sorted_ct,
        key=lambda item: abs(item[0] - contour_coord),
    )

    return make_ct_ref(nearest_ct)


def print_file_size(label, path):
    print(f"{label}: {path}")
    print(f"  size: {path.stat().st_size / 1024:.1f} KiB")


# =============================================================================
# Minimal RTSTRUCT patch
# =============================================================================

def patch_rtstruct_minimal(source_rs: Path, out_rs: Path, ct_ref, sorted_ct, normal):
    rs = read_full_dicom(source_rs)

    if getattr(rs, "Modality", None) != "RTSTRUCT":
        raise ValueError(f"Expected RTSTRUCT, found {getattr(rs, 'Modality', None)}")

    copy_patient_study_identity_from_ct(rs, ct_ref)
    new_rs_uid = regenerate_sop_uid_if_requested(rs)

    ct_frame_uid = ct_ref.FrameOfReferenceUID
    ct_series_uid = ct_ref.SeriesInstanceUID
    ct_study_uid = ct_ref.StudyInstanceUID

    all_ct_refs = Sequence([make_ct_ref(ds) for _, _, ds in sorted_ct])

    # 1) Patch ROI frame references.
    if hasattr(rs, "StructureSetROISequence"):
        for roi in rs.StructureSetROISequence:
            if hasattr(roi, "ReferencedFrameOfReferenceUID"):
                roi.ReferencedFrameOfReferenceUID = ct_frame_uid

    # 2) Patch existing ReferencedFrameOfReferenceSequence if present.
    # Do not rebuild the whole thing unless missing.
    if hasattr(rs, "ReferencedFrameOfReferenceSequence") and len(rs.ReferencedFrameOfReferenceSequence) > 0:
        for rfor in rs.ReferencedFrameOfReferenceSequence:
            if hasattr(rfor, "FrameOfReferenceUID"):
                rfor.FrameOfReferenceUID = ct_frame_uid

            for study in getattr(rfor, "RTReferencedStudySequence", []):
                if hasattr(study, "ReferencedSOPInstanceUID"):
                    study.ReferencedSOPInstanceUID = ct_study_uid

                for series in getattr(study, "RTReferencedSeriesSequence", []):
                    if hasattr(series, "SeriesInstanceUID"):
                        series.SeriesInstanceUID = ct_series_uid

                    # Replace only the CT image reference list.
                    # Preserve the enclosing sequence object and other tags.
                    series.ContourImageSequence = all_ct_refs

    else:
        # Only if the reference tree is missing, create a minimal one.
        rfor = Dataset()
        rfor.FrameOfReferenceUID = ct_frame_uid

        study = Dataset()
        study.ReferencedSOPClassUID = "1.2.840.10008.3.1.2.3.1"
        study.ReferencedSOPInstanceUID = ct_study_uid

        series = Dataset()
        series.SeriesInstanceUID = ct_series_uid
        series.ContourImageSequence = all_ct_refs

        study.RTReferencedSeriesSequence = Sequence([series])
        rfor.RTReferencedStudySequence = Sequence([study])
        rs.ReferencedFrameOfReferenceSequence = Sequence([rfor])

    # 3) Patch per-contour references to nearest synthetic CT slice.
    if hasattr(rs, "ROIContourSequence"):
        for roi_contour in rs.ROIContourSequence:
            for src in getattr(roi_contour, "SourceSeriesSequence", []):
                if hasattr(src, "SeriesInstanceUID"):
                    src.SeriesInstanceUID = ct_series_uid

            for contour in getattr(roi_contour, "ContourSequence", []):
                nearest_ref = nearest_ct_ref_from_contour(contour, sorted_ct, normal)
                if nearest_ref is not None:
                    contour.ContourImageSequence = Sequence([nearest_ref])

    save_preserving(rs, out_rs)
    return new_rs_uid


# =============================================================================
# Minimal RTPLAN patch
# =============================================================================

def patch_rtplan_minimal(source_rp: Path, out_rp: Path, ct_ref, rs_uid, rs_sop_class_uid):
    rp = read_full_dicom(source_rp)

    if getattr(rp, "Modality", None) != "RTPLAN":
        raise ValueError(f"Expected RTPLAN, found {getattr(rp, 'Modality', None)}")

    copy_patient_study_identity_from_ct(rp, ct_ref)
    new_rp_uid = regenerate_sop_uid_if_requested(rp)

    # Patch existing RTSTRUCT reference, or create it if missing.
    ref_rs = Dataset()
    ref_rs.ReferencedSOPClassUID = rs_sop_class_uid
    ref_rs.ReferencedSOPInstanceUID = rs_uid

    rp.ReferencedStructureSetSequence = Sequence([ref_rs])

    save_preserving(rp, out_rp)
    return new_rp_uid


# =============================================================================
# Minimal RTDOSE patch
# =============================================================================

def patch_rtdose_minimal(
    source_rd: Path,
    out_rd: Path,
    ct_ref,
    rp_uid,
    rp_sop_class_uid,
    patched_rp_path: Path,
):
    rd = read_full_dicom(source_rd)

    if getattr(rd, "Modality", None) != "RTDOSE":
        raise ValueError(f"Expected RTDOSE, found {getattr(rd, 'Modality', None)}")

    # Make sure PixelData is really present before saving.
    if not hasattr(rd, "PixelData"):
        raise RuntimeError(
            "RTDOSE has no PixelData after reading. "
            "Do not read RTDOSE with stop_before_pixels=True."
        )

    rp = pydicom.dcmread(patched_rp_path, stop_before_pixels=True, force=False)

    copy_patient_study_identity_from_ct(rd, ct_ref)
    rd.FrameOfReferenceUID = ct_ref.FrameOfReferenceUID
    rd.DoseType = getattr(rd, "DoseType", None) or "PHYSICAL"
    rd.DoseSummationType = DOSE_SUMMATION_TYPE

    new_rd_uid = regenerate_sop_uid_if_requested(rd)

    ref_plan = Dataset()
    ref_plan.ReferencedSOPClassUID = rp_sop_class_uid
    ref_plan.ReferencedSOPInstanceUID = rp_uid

    if DOSE_SUMMATION_TYPE.upper() == "BEAM":
        ref_fg = Dataset()

        if hasattr(rp, "FractionGroupSequence") and len(rp.FractionGroupSequence) > 0:
            ref_fg.ReferencedFractionGroupNumber = int(
                rp.FractionGroupSequence[0].FractionGroupNumber
            )
        else:
            ref_fg.ReferencedFractionGroupNumber = 1

        ref_beam = Dataset()
        ref_beam.ReferencedBeamNumber = int(REFERENCED_BEAM_NUMBER)

        ref_fg.ReferencedBeamSequence = Sequence([ref_beam])
        ref_plan.ReferencedFractionGroupSequence = Sequence([ref_fg])

    rd.ReferencedRTPlanSequence = Sequence([ref_plan])

    save_preserving(rd, out_rd)
    return new_rd_uid


# =============================================================================
# Validation
# =============================================================================

def validate_folder(folder: Path):
    objects = read_dicom_objects(folder)

    # Also inspect parent folders so RT objects written next to the CT folder are included.
    for extra in [folder.parent, folder.parent.parent]:
        if extra.exists():
            extra_objects = read_dicom_objects(extra)
            for modality, items in extra_objects.items():
                objects[modality].extend(items)

    ct_items = objects.get("CT", [])
    rs_items = objects.get("RTSTRUCT", [])
    rp_items = objects.get("RTPLAN", [])
    rd_items = objects.get("RTDOSE", [])

    print("\nValidation:")
    print("  CT:       ", len(ct_items))
    print("  RTSTRUCT: ", len(rs_items))
    print("  RTPLAN:   ", len(rp_items))
    print("  RTDOSE:   ", len(rd_items))

    sorted_ct, _ = get_sorted_ct(folder)
    ct_ref = sorted_ct[0][2]
    ct_sops = {ds.SOPInstanceUID for _, _, ds in sorted_ct}

    print("\nSynthetic CT:")
    print("  PatientID:          ", getattr(ct_ref, "PatientID", None))
    print("  StudyInstanceUID:   ", getattr(ct_ref, "StudyInstanceUID", None))
    print("  SeriesInstanceUID:  ", getattr(ct_ref, "SeriesInstanceUID", None))
    print("  FrameOfReferenceUID:", getattr(ct_ref, "FrameOfReferenceUID", None))

    rs_sops = {getattr(ds, "SOPInstanceUID", None) for _, ds in rs_items}
    rp_sops = {getattr(ds, "SOPInstanceUID", None) for _, ds in rp_items}

    for _, rs in rs_items:
        ref_frames = set()
        ref_series = set()
        ref_images = set()

        for rfor in getattr(rs, "ReferencedFrameOfReferenceSequence", []):
            ref_frames.add(getattr(rfor, "FrameOfReferenceUID", None))

            for study in getattr(rfor, "RTReferencedStudySequence", []):
                for series in getattr(study, "RTReferencedSeriesSequence", []):
                    ref_series.add(getattr(series, "SeriesInstanceUID", None))
                    for img in getattr(series, "ContourImageSequence", []):
                        ref_images.add(getattr(img, "ReferencedSOPInstanceUID", None))

        print("\nRTSTRUCT:")
        print("  SOPInstanceUID:        ", getattr(rs, "SOPInstanceUID", None))
        print("  FoR matches CT:        ", ct_ref.FrameOfReferenceUID in ref_frames)
        print("  Series matches CT:     ", ct_ref.SeriesInstanceUID in ref_series)
        print("  CT image refs matched: ", len(ref_images & ct_sops), "/", len(ref_images))

    for _, rp in rp_items:
        print("\nRTPLAN:")
        print("  SOPInstanceUID:", getattr(rp, "SOPInstanceUID", None))

        for ref in getattr(rp, "ReferencedStructureSetSequence", []):
            uid = getattr(ref, "ReferencedSOPInstanceUID", None)
            print("  References RTSTRUCT:", uid in rs_sops, uid)

    for rd_path, rd_meta in rd_items:
        rd = pydicom.dcmread(rd_path, force=True)

        print("\nRTDOSE:")
        print("  File:                ", rd_path)
        print("  SOPInstanceUID:      ", getattr(rd, "SOPInstanceUID", None))
        print("  FrameOfReferenceUID: ", getattr(rd, "FrameOfReferenceUID", None))
        print("  FoR matches CT:      ", getattr(rd, "FrameOfReferenceUID", None) == ct_ref.FrameOfReferenceUID)
        print("  DoseSummationType:   ", getattr(rd, "DoseSummationType", None))
        print("  Has PixelData:       ", hasattr(rd, "PixelData"))
        print("  PixelData length:    ", len(getattr(rd, "PixelData", b"")) if hasattr(rd, "PixelData") else 0)

        for ref in getattr(rd, "ReferencedRTPlanSequence", []):
            uid = getattr(ref, "ReferencedSOPInstanceUID", None)
            print("  References RTPLAN:   ", uid in rp_sops, uid)


# =============================================================================
# Main
# =============================================================================

def main():
    for path in [SYNTHETIC_CT_DIR, SOURCE_RTSTRUCT, SOURCE_RTPLAN, SOURCE_RTDose]:
        if not path.exists():
            raise FileNotFoundError(path)

    sorted_ct, normal = get_sorted_ct(SYNTHETIC_CT_DIR)
    ct_ref = sorted_ct[0][2]

    print("Synthetic CT target:")
    print("  PatientID:          ", getattr(ct_ref, "PatientID", None))
    print("  StudyInstanceUID:   ", getattr(ct_ref, "StudyInstanceUID", None))
    print("  SeriesInstanceUID:  ", getattr(ct_ref, "SeriesInstanceUID", None))
    print("  FrameOfReferenceUID:", getattr(ct_ref, "FrameOfReferenceUID", None))
    print("  CT slices:          ", len(sorted_ct))

    print("\nInput file sizes:")
    print_file_size("  Source RTSTRUCT", SOURCE_RTSTRUCT)
    print_file_size("  Source RTPLAN  ", SOURCE_RTPLAN)
    print_file_size("  Source RTDOSE  ", SOURCE_RTDose)

    rs_uid = patch_rtstruct_minimal(
        source_rs=SOURCE_RTSTRUCT,
        out_rs=OUT_RTSTRUCT,
        ct_ref=ct_ref,
        sorted_ct=sorted_ct,
        normal=normal,
    )

    patched_rs = pydicom.dcmread(OUT_RTSTRUCT, stop_before_pixels=True, force=False)

    rp_uid = patch_rtplan_minimal(
        source_rp=SOURCE_RTPLAN,
        out_rp=OUT_RTPLAN,
        ct_ref=ct_ref,
        rs_uid=rs_uid,
        rs_sop_class_uid=patched_rs.SOPClassUID,
    )

    patched_rp = pydicom.dcmread(OUT_RTPLAN, stop_before_pixels=True, force=False)

    rd_uid = patch_rtdose_minimal(
        source_rd=SOURCE_RTDose,
        out_rd=OUT_RTDose,
        ct_ref=ct_ref,
        rp_uid=rp_uid,
        rp_sop_class_uid=patched_rp.SOPClassUID,
        patched_rp_path=OUT_RTPLAN,
    )

    print("\nOutput file sizes:")
    print_file_size("  Patched RTSTRUCT", OUT_RTSTRUCT)
    print_file_size("  Patched RTPLAN  ", OUT_RTPLAN)
    print_file_size("  Patched RTDOSE  ", OUT_RTDose)

    print("\nNew UIDs:")
    print("  RTSTRUCT:", rs_uid)
    print("  RTPLAN:  ", rp_uid)
    print("  RTDOSE:  ", rd_uid)

    validate_folder(SYNTHETIC_CT_DIR)

    print("\nDone. Import this folder into Weasis:")
    print(" ", SYNTHETIC_CT_DIR)


if __name__ == "__main__":
    main()