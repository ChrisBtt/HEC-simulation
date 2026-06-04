from pathlib import Path
from collections import defaultdict
from datetime import datetime
import shutil

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid, ExplicitVRLittleEndian


# =============================================================================
# Configuration
# =============================================================================

SYNTHETIC_CT_DIR = Path("/Users/pb438/applications/hec-dose-distribution/TOPAS_simulation_data/dataset_3dct/phase_0")
OLD_RTSTRUCT_PATH = Path("/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RS_patched_to_converted_CT.dcm")
OLD_RTPLAN_PATH = Path("/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RP_patched_to_converted_CT.dcm")
CORRECTED_RTDose_PATH = Path("/Users/pb438/applications/hec-dose-distribution/TOPAS_simulation_data/dicom_input/DoseGrid_Run_0000.dcm")

OUTPUT_DIR = SYNTHETIC_CT_DIR
DOSE_SUMMATION_TYPE = "BEAM"

# If BEAM dose: set the beam number from the Eclipse RTPLAN.
# If unknown, inspect the RTPLAN first with the helper printout below.
REFERENCED_BEAM_NUMBER = 1


# =============================================================================
# Helper functions
# =============================================================================

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


def ensure_file_meta(ds):
    if not hasattr(ds, "file_meta") or ds.file_meta is None:
        ds.file_meta = FileMetaDataset()

    if not hasattr(ds.file_meta, "TransferSyntaxUID"):
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    if hasattr(ds, "SOPClassUID"):
        ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID

    if hasattr(ds, "SOPInstanceUID"):
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    ds.is_little_endian = True
    ds.is_implicit_VR = False


def set_new_sop_instance_uid(ds):
    new_uid = generate_uid()
    ds.SOPInstanceUID = new_uid
    ensure_file_meta(ds)
    ds.file_meta.MediaStorageSOPInstanceUID = new_uid
    return new_uid


def set_common_patient_study_fields(ds, ct_ref):
    """
    Align RT object metadata to the synthetic CT study.
    The RT objects get new SeriesInstanceUIDs but remain in the CT StudyInstanceUID.
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
        elif hasattr(ds, keyword):
            delattr(ds, keyword)

    ds.StudyInstanceUID = ct_ref.StudyInstanceUID
    ds.SeriesInstanceUID = generate_uid()

    now = datetime.now()
    ds.InstanceCreationDate = now.strftime("%Y%m%d")
    ds.InstanceCreationTime = now.strftime("%H%M%S")

    ensure_file_meta(ds)


def get_ct_sorting_geometry(ct_items):
    """
    Sort CT slices along the physical slice normal.
    """
    first_ct = ct_items[0][1]

    if not hasattr(first_ct, "ImageOrientationPatient"):
        raise RuntimeError("CT slices have no ImageOrientationPatient.")

    if not hasattr(first_ct, "ImagePositionPatient"):
        raise RuntimeError("CT slices have no ImagePositionPatient.")

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


def find_nearest_ct_ref_for_contour(contour, sorted_ct_items, normal):
    """
    Retarget a contour to the nearest synthetic CT slice based on physical contour
    coordinates. This assumes the synthetic CT has the same physical geometry as
    the original CT.
    """
    if not hasattr(contour, "ContourData") or len(contour.ContourData) < 3:
        return None

    data = [float(x) for x in contour.ContourData]
    first_point = np.array(data[:3])
    contour_coord = float(np.dot(first_point, normal))

    nearest = min(
        sorted_ct_items,
        key=lambda item: abs(item[0] - contour_coord),
    )

    _, _, nearest_ct = nearest
    return make_image_ref(nearest_ct)


def build_referenced_frame_of_reference_sequence(rs, ct_ref, sorted_ct_items):
    """
    Build the RTSTRUCT reference tree:

    ReferencedFrameOfReferenceSequence
      -> RTReferencedStudySequence
         -> RTReferencedSeriesSequence
            -> ContourImageSequence
    """
    ct_frame_uid = ct_ref.FrameOfReferenceUID
    ct_study_uid = ct_ref.StudyInstanceUID
    ct_series_uid = ct_ref.SeriesInstanceUID

    all_ct_image_refs = Sequence([
        make_image_ref(ds) for _, _, ds in sorted_ct_items
    ])

    rfor = Dataset()
    rfor.FrameOfReferenceUID = ct_frame_uid

    study_ref = Dataset()

    # Preserve existing study reference SOP class if possible.
    old_study_ref = None
    try:
        old_study_ref = rs.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0]
    except Exception:
        pass

    if old_study_ref is not None and hasattr(old_study_ref, "ReferencedSOPClassUID"):
        study_ref.ReferencedSOPClassUID = old_study_ref.ReferencedSOPClassUID
    else:
        # Legacy Detached Study Management SOP Class UID, often seen in RTSTRUCTs.
        study_ref.ReferencedSOPClassUID = "1.2.840.10008.3.1.2.3.1"

    study_ref.ReferencedSOPInstanceUID = ct_study_uid

    series_ref = Dataset()
    series_ref.SeriesInstanceUID = ct_series_uid
    series_ref.ContourImageSequence = all_ct_image_refs

    study_ref.RTReferencedSeriesSequence = Sequence([series_ref])
    rfor.RTReferencedStudySequence = Sequence([study_ref])

    return Sequence([rfor])


def patch_rtstruct_to_synthetic_ct(
    old_rtstruct_path: Path,
    output_path: Path,
    ct_ref,
    sorted_ct_items,
    ct_normal,
):
    rs = pydicom.dcmread(old_rtstruct_path, force=True)

    if getattr(rs, "Modality", None) != "RTSTRUCT":
        raise ValueError(f"Expected RTSTRUCT, found {getattr(rs, 'Modality', None)}")

    set_common_patient_study_fields(rs, ct_ref)
    new_rs_uid = set_new_sop_instance_uid(rs)

    # RTSTRUCT-level reference tree.
    rs.ReferencedFrameOfReferenceSequence = build_referenced_frame_of_reference_sequence(
        rs=rs,
        ct_ref=ct_ref,
        sorted_ct_items=sorted_ct_items,
    )

    # ROI-level frame reference.
    if hasattr(rs, "StructureSetROISequence"):
        for roi in rs.StructureSetROISequence:
            roi.ReferencedFrameOfReferenceUID = ct_ref.FrameOfReferenceUID

    # Per-contour reference to the nearest synthetic CT slice.
    if hasattr(rs, "ROIContourSequence"):
        for roi_contour in rs.ROIContourSequence:

            # Source series reference, if present.
            if hasattr(roi_contour, "SourceSeriesSequence"):
                for src in roi_contour.SourceSeriesSequence:
                    src.SeriesInstanceUID = ct_ref.SeriesInstanceUID

            if not hasattr(roi_contour, "ContourSequence"):
                continue

            for contour in roi_contour.ContourSequence:
                nearest_ref = find_nearest_ct_ref_for_contour(
                    contour=contour,
                    sorted_ct_items=sorted_ct_items,
                    normal=ct_normal,
                )

                if nearest_ref is not None:
                    contour.ContourImageSequence = Sequence([nearest_ref])

    rs.StructureSetLabel = getattr(rs, "StructureSetLabel", "PATCHED_RS")
    rs.StructureSetName = getattr(rs, "StructureSetName", "PATCHED_RS")

    ensure_file_meta(rs)
    rs.save_as(output_path, write_like_original=False)

    return new_rs_uid, output_path


def patch_rtplan_to_patched_rtstruct(
    old_rtplan_path: Path,
    output_path: Path,
    ct_ref,
    patched_rs_sop_instance_uid,
    patched_rs_sop_class_uid,
):
    rp = pydicom.dcmread(old_rtplan_path, force=True)

    if getattr(rp, "Modality", None) != "RTPLAN":
        raise ValueError(f"Expected RTPLAN, found {getattr(rp, 'Modality', None)}")

    set_common_patient_study_fields(rp, ct_ref)
    new_rp_uid = set_new_sop_instance_uid(rp)

    ref_rs = Dataset()
    ref_rs.ReferencedSOPClassUID = patched_rs_sop_class_uid
    ref_rs.ReferencedSOPInstanceUID = patched_rs_sop_instance_uid
    rp.ReferencedStructureSetSequence = Sequence([ref_rs])

    ensure_file_meta(rp)
    rp.save_as(output_path, write_like_original=False)

    return new_rp_uid, output_path


def patch_rtdose_to_synthetic_ct_and_plan(
    corrected_rtdose_path: Path,
    output_path: Path,
    ct_ref,
    patched_rp_sop_instance_uid,
    patched_rp_sop_class_uid,
    patched_rtplan_path: Path,
):
    rd = pydicom.dcmread(corrected_rtdose_path, force=True)

    if getattr(rd, "Modality", None) != "RTDOSE":
        raise ValueError(f"Expected RTDOSE, found {getattr(rd, 'Modality', None)}")

    rp = pydicom.dcmread(patched_rtplan_path, stop_before_pixels=True, force=True)

    set_common_patient_study_fields(rd, ct_ref)
    rd.FrameOfReferenceUID = ct_ref.FrameOfReferenceUID
    rd.DoseSummationType = DOSE_SUMMATION_TYPE

    new_rd_uid = set_new_sop_instance_uid(rd)

    ref_plan = Dataset()
    ref_plan.ReferencedSOPClassUID = patched_rp_sop_class_uid
    ref_plan.ReferencedSOPInstanceUID = patched_rp_sop_instance_uid

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

    elif DOSE_SUMMATION_TYPE.upper() == "PLAN":
        # For PLAN dose, only the RTPLAN reference is usually needed.
        pass

    else:
        print(
            f"Warning: DOSE_SUMMATION_TYPE={DOSE_SUMMATION_TYPE} is not explicitly handled. "
            "Only ReferencedRTPlanSequence will be written."
        )

    rd.ReferencedRTPlanSequence = Sequence([ref_plan])

    ensure_file_meta(rd)
    rd.save_as(output_path, write_like_original=False)

    return new_rd_uid, output_path


def print_ct_summary(ct_ref, sorted_ct_items):
    print("\nSynthetic CT target:")
    print("  PatientID:           ", getattr(ct_ref, "PatientID", None))
    print("  PatientName:         ", getattr(ct_ref, "PatientName", None))
    print("  StudyInstanceUID:    ", getattr(ct_ref, "StudyInstanceUID", None))
    print("  SeriesInstanceUID:   ", getattr(ct_ref, "SeriesInstanceUID", None))
    print("  FrameOfReferenceUID: ", getattr(ct_ref, "FrameOfReferenceUID", None))
    print("  Number of CT slices: ", len(sorted_ct_items))


def print_rtplan_beams(rtplan_path):
    rp = pydicom.dcmread(rtplan_path, stop_before_pixels=True, force=True)

    print("\nRTPLAN beams:")
    if hasattr(rp, "BeamSequence"):
        for beam in rp.BeamSequence:
            print(
                "  BeamNumber:",
                getattr(beam, "BeamNumber", None),
                "BeamName:",
                getattr(beam, "BeamName", None),
            )

    if hasattr(rp, "IonBeamSequence"):
        for beam in rp.IonBeamSequence:
            print(
                "  IonBeamNumber:",
                getattr(beam, "IonBeamNumber", None),
                "BeamName:",
                getattr(beam, "BeamName", None),
            )


def validate_patched_folder(folder: Path):
    """
    Minimal validation equivalent to your previous diagnostic script.
    """
    objects = read_dicom_objects(folder)

    ct_items = objects.get("CT", [])
    rs_items = objects.get("RTSTRUCT", [])
    rp_items = objects.get("RTPLAN", [])
    rd_items = objects.get("RTDOSE", [])

    print("\nValidation summary:")
    print("  CT:       ", len(ct_items))
    print("  RTSTRUCT: ", len(rs_items))
    print("  RTPLAN:   ", len(rp_items))
    print("  RTDOSE:   ", len(rd_items))

    if not ct_items:
        print("  No CT found for validation.")
        return

    sorted_ct_items, _ = get_ct_sorting_geometry(ct_items)
    ct_ref = sorted_ct_items[0][2]

    ct_sops = {getattr(ds, "SOPInstanceUID", None) for _, _, ds in sorted_ct_items}

    print("\nCT reference:")
    print("  PatientID:           ", getattr(ct_ref, "PatientID", None))
    print("  StudyInstanceUID:    ", getattr(ct_ref, "StudyInstanceUID", None))
    print("  SeriesInstanceUID:   ", getattr(ct_ref, "SeriesInstanceUID", None))
    print("  FrameOfReferenceUID: ", getattr(ct_ref, "FrameOfReferenceUID", None))

    for _, rs in rs_items:
        referenced_series = set()
        referenced_frames = set()
        referenced_images = set()

        for rfor in getattr(rs, "ReferencedFrameOfReferenceSequence", []):
            referenced_frames.add(getattr(rfor, "FrameOfReferenceUID", None))
            for study in getattr(rfor, "RTReferencedStudySequence", []):
                for series in getattr(study, "RTReferencedSeriesSequence", []):
                    referenced_series.add(getattr(series, "SeriesInstanceUID", None))
                    for img in getattr(series, "ContourImageSequence", []):
                        referenced_images.add(getattr(img, "ReferencedSOPInstanceUID", None))

        print("\nRTSTRUCT:")
        print("  SOPInstanceUID:                ", getattr(rs, "SOPInstanceUID", None))
        print("  PatientID:                     ", getattr(rs, "PatientID", None))
        print("  StudyInstanceUID:              ", getattr(rs, "StudyInstanceUID", None))
        print("  FrameOfReferenceUID matches CT:", ct_ref.FrameOfReferenceUID in referenced_frames)
        print("  SeriesInstanceUID matches CT:  ", ct_ref.SeriesInstanceUID in referenced_series)
        print(
            "  Referenced CT images found:    ",
            len(referenced_images & ct_sops),
            "/",
            len(referenced_images),
        )

    rs_sops = {getattr(ds, "SOPInstanceUID", None) for _, ds in rs_items}
    rp_sops = {getattr(ds, "SOPInstanceUID", None) for _, ds in rp_items}

    for _, rp in rp_items:
        print("\nRTPLAN:")
        print("  SOPInstanceUID:   ", getattr(rp, "SOPInstanceUID", None))
        print("  PatientID:        ", getattr(rp, "PatientID", None))
        print("  StudyInstanceUID: ", getattr(rp, "StudyInstanceUID", None))

        for ref in getattr(rp, "ReferencedStructureSetSequence", []):
            ref_uid = getattr(ref, "ReferencedSOPInstanceUID", None)
            print("  References patched RTSTRUCT:", ref_uid in rs_sops, ref_uid)

    for _, rd in rd_items:
        print("\nRTDOSE:")
        print("  SOPInstanceUID:       ", getattr(rd, "SOPInstanceUID", None))
        print("  PatientID:            ", getattr(rd, "PatientID", None))
        print("  StudyInstanceUID:     ", getattr(rd, "StudyInstanceUID", None))
        print("  FrameOfReferenceUID:  ", getattr(rd, "FrameOfReferenceUID", None))
        print("  Matches CT FoR:       ", getattr(rd, "FrameOfReferenceUID", None) == ct_ref.FrameOfReferenceUID)
        print("  DoseSummationType:    ", getattr(rd, "DoseSummationType", None))
        print("  DoseGridScaling:      ", getattr(rd, "DoseGridScaling", None))

        for ref in getattr(rd, "ReferencedRTPlanSequence", []):
            ref_uid = getattr(ref, "ReferencedSOPInstanceUID", None)
            print("  References patched RTPLAN:", ref_uid in rp_sops, ref_uid)


# =============================================================================
# Main execution
# =============================================================================

def main():
    if not SYNTHETIC_CT_DIR.exists():
        raise FileNotFoundError(f"Synthetic CT directory does not exist: {SYNTHETIC_CT_DIR}")

    for p in [OLD_RTSTRUCT_PATH, OLD_RTPLAN_PATH, CORRECTED_RTDose_PATH]:
        if not p.exists():
            raise FileNotFoundError(f"Input file does not exist: {p}")

    objects = read_dicom_objects(SYNTHETIC_CT_DIR)
    ct_items = objects.get("CT", [])

    if len(ct_items) == 0:
        raise RuntimeError(f"No CT files found in synthetic CT directory: {SYNTHETIC_CT_DIR}")

    sorted_ct_items, ct_normal = get_ct_sorting_geometry(ct_items)
    ct_ref = sorted_ct_items[0][2]

    if not hasattr(ct_ref, "FrameOfReferenceUID"):
        raise RuntimeError("Synthetic CT has no FrameOfReferenceUID.")

    print_ct_summary(ct_ref, sorted_ct_items)
    print_rtplan_beams(OLD_RTPLAN_PATH)

    # Output filenames inside the synthetic CT folder.
    patched_rs_path = OUTPUT_DIR / "RS_patched_to_synthetic_CT.dcm"
    patched_rp_path = OUTPUT_DIR / "RP_patched_to_synthetic_CT.dcm"
    patched_rd_path = OUTPUT_DIR / "RD_patched_to_synthetic_CT.dcm"

    # Patch RTSTRUCT.
    rs_uid, rs_out = patch_rtstruct_to_synthetic_ct(
        old_rtstruct_path=OLD_RTSTRUCT_PATH,
        output_path=patched_rs_path,
        ct_ref=ct_ref,
        sorted_ct_items=sorted_ct_items,
        ct_normal=ct_normal,
    )

    patched_rs = pydicom.dcmread(rs_out, stop_before_pixels=True, force=True)

    print("\nPatched RTSTRUCT written:")
    print("  ", rs_out)
    print("  New SOPInstanceUID:", rs_uid)

    # Patch RTPLAN.
    rp_uid, rp_out = patch_rtplan_to_patched_rtstruct(
        old_rtplan_path=OLD_RTPLAN_PATH,
        output_path=patched_rp_path,
        ct_ref=ct_ref,
        patched_rs_sop_instance_uid=rs_uid,
        patched_rs_sop_class_uid=patched_rs.SOPClassUID,
    )

    patched_rp = pydicom.dcmread(rp_out, stop_before_pixels=True, force=True)

    print("\nPatched RTPLAN written:")
    print("  ", rp_out)
    print("  New SOPInstanceUID:", rp_uid)
    print("  References RTSTRUCT:", rs_uid)

    # Patch RTDOSE.
    rd_uid, rd_out = patch_rtdose_to_synthetic_ct_and_plan(
        corrected_rtdose_path=CORRECTED_RTDose_PATH,
        output_path=patched_rd_path,
        ct_ref=ct_ref,
        patched_rp_sop_instance_uid=rp_uid,
        patched_rp_sop_class_uid=patched_rp.SOPClassUID,
        patched_rtplan_path=rp_out,
    )

    print("\nPatched RTDOSE written:")
    print("  ", rd_out)
    print("  New SOPInstanceUID:", rd_uid)
    print("  References RTPLAN:", rp_uid)
    print("  DoseSummationType:", DOSE_SUMMATION_TYPE)

    validate_patched_folder(SYNTHETIC_CT_DIR)

    print("\nDone.")
    print("Open/import this folder in Weasis:")
    print(" ", SYNTHETIC_CT_DIR)


if __name__ == "__main__":
    main()