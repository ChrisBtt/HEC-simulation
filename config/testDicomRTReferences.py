from pathlib import Path
from collections import defaultdict
import pydicom

folder = Path("E:\\Christoph\\EIT\\CT\\p107\\MP1_ph0_masked")

objects = defaultdict(list)

for f in folder.rglob("*"):
    if f.is_file():
        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
            objects[getattr(ds, "Modality", "UNKNOWN")].append((f, ds))
        except Exception:
            pass

print("Modalities found:")
for modality, items in objects.items():
    print(f"{modality}: {len(items)}")

print("\nCT reference values:")
ct_items = objects.get("CT", [])
if ct_items:
    f, ct = ct_items[0]
    ct_series_uid = getattr(ct, "SeriesInstanceUID", None)
    ct_study_uid = getattr(ct, "StudyInstanceUID", None)
    ct_frame_uid = getattr(ct, "FrameOfReferenceUID", None)

    print("Example CT file:", f)
    print("PatientID:", getattr(ct, "PatientID", None))
    print("StudyInstanceUID:", ct_study_uid)
    print("SeriesInstanceUID:", ct_series_uid)
    print("FrameOfReferenceUID:", ct_frame_uid)

    ct_sop_uids = {getattr(ds, "SOPInstanceUID", None) for _, ds in ct_items}
    print("Number of CT SOPInstanceUIDs:", len(ct_sop_uids))
else:
    ct_series_uid = None
    ct_frame_uid = None
    ct_sop_uids = set()
    print("No CT files found.")

print("\nRTSTRUCT references:")
for f, ds in objects.get("RTSTRUCT", []):
    print("\nRTSTRUCT file:", f)
    print("SOPInstanceUID:", getattr(ds, "SOPInstanceUID", None))
    print("PatientID:", getattr(ds, "PatientID", None))
    print("StudyInstanceUID:", getattr(ds, "StudyInstanceUID", None))

    referenced_ct_series = set()
    referenced_ct_images = set()
    referenced_frame_uids = set()

    for rfor in getattr(ds, "ReferencedFrameOfReferenceSequence", []):
        referenced_frame_uids.add(getattr(rfor, "FrameOfReferenceUID", None))

        for study in getattr(rfor, "RTReferencedStudySequence", []):
            for series in getattr(study, "RTReferencedSeriesSequence", []):
                referenced_ct_series.add(getattr(series, "SeriesInstanceUID", None))

                for img in getattr(series, "ContourImageSequence", []):
                    referenced_ct_images.add(getattr(img, "ReferencedSOPInstanceUID", None))

    print("Referenced FrameOfReferenceUIDs:", referenced_frame_uids)
    print("Referenced CT SeriesInstanceUIDs:", referenced_ct_series)
    print("Number of referenced CT images:", len(referenced_ct_images))

    print("FrameOfReferenceUID matches CT:", ct_frame_uid in referenced_frame_uids)
    print("SeriesInstanceUID matches CT:", ct_series_uid in referenced_ct_series)

    if referenced_ct_images:
        overlap = len(referenced_ct_images & ct_sop_uids)
        print("Referenced CT SOPInstanceUIDs found in loaded CT:", overlap, "/", len(referenced_ct_images))

print("\nRTPLAN references:")
for f, ds in objects.get("RTPLAN", []):
    print("\nRTPLAN file:", f)
    print("SOPInstanceUID:", getattr(ds, "SOPInstanceUID", None))
    print("PatientID:", getattr(ds, "PatientID", None))
    print("StudyInstanceUID:", getattr(ds, "StudyInstanceUID", None))
    print("RTPlanLabel:", getattr(ds, "RTPlanLabel", None))

    for ref in getattr(ds, "ReferencedStructureSetSequence", []):
        print("Referenced RTSTRUCT SOPInstanceUID:", getattr(ref, "ReferencedSOPInstanceUID", None))

print("\nRTDOSE references:")
for f, ds in objects.get("RTDOSE", []):
    print("\nRTDOSE file:", f)
    print("SOPInstanceUID:", getattr(ds, "SOPInstanceUID", None))
    print("PatientID:", getattr(ds, "PatientID", None))
    print("StudyInstanceUID:", getattr(ds, "StudyInstanceUID", None))
    print("FrameOfReferenceUID:", getattr(ds, "FrameOfReferenceUID", None))
    print("DoseSummationType:", getattr(ds, "DoseSummationType", None))
    print("DoseGridScaling:", getattr(ds, "DoseGridScaling", None))

    for ref in getattr(ds, "ReferencedRTPlanSequence", []):
        print("Referenced RTPLAN SOPInstanceUID:", getattr(ref, "ReferencedSOPInstanceUID", None))