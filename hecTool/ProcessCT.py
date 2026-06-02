import itk
import pydicom
import numpy as np

from pathlib import Path
from collections import Counter, defaultdict


def _as_float_array(value):
    return np.asarray([float(v) for v in value], dtype=float)


def _slice_position_from_ds(ds):
    """Return geometric slice coordinate = dot(IPP, normal)."""
    ipp = _as_float_array(ds.ImagePositionPatient)
    iop = _as_float_array(ds.ImageOrientationPatient)

    row = iop[:3]
    col = iop[3:]
    normal = np.cross(row, col)

    return float(np.dot(ipp, normal))


def audit_dicom_series(
    dicom_dir: str,
    title: str = "DICOM audit",
    expected_slices: int | None = None,
    strict: bool = False,
):
    dicom_dir = Path(dicom_dir)

    records = []
    unreadable = []

    for p in sorted(dicom_dir.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith(".") or p.name.startswith("._"):
            continue

        try:
            ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=False)
        except Exception as e:
            unreadable.append((p, repr(e)))
            continue

        modality = getattr(ds, "Modality", "MISSING")
        series_uid = getattr(ds, "SeriesInstanceUID", "MISSING")
        sop_uid = getattr(ds, "SOPInstanceUID", "MISSING")
        instance_number = getattr(ds, "InstanceNumber", None)

        has_geom = hasattr(ds, "ImagePositionPatient") and hasattr(ds, "ImageOrientationPatient")
        pos = _slice_position_from_ds(ds) if has_geom else None

        records.append(
            {
                "path": p,
                "ds": ds,
                "modality": modality,
                "series_uid": str(series_uid),
                "sop_uid": str(sop_uid),
                "instance_number": None if instance_number is None else int(instance_number),
                "position": pos,
            }
        )

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print(f"Directory: {dicom_dir}")
    print(f"Readable DICOM files: {len(records)}")
    print(f"Unreadable/non-DICOM files: {len(unreadable)}")

    if unreadable:
        print("\nUnreadable files:")
        for p, err in unreadable[:20]:
            print(f"  {p.name}: {err}")

    modality_counts = Counter(r["modality"] for r in records)
    print("\nModalities:")
    for k, v in modality_counts.items():
        print(f"  {k}: {v}")

    series_counts = Counter(r["series_uid"] for r in records)
    print("\nSeriesInstanceUIDs:")
    for uid, n in series_counts.items():
        print(f"  {uid}: {n}")

    sop_counts = Counter(r["sop_uid"] for r in records)
    duplicate_sops = [uid for uid, n in sop_counts.items() if n > 1]
    print(f"\nUnique SOPInstanceUIDs: {len(sop_counts)} / {len(records)}")
    if duplicate_sops:
        print("Duplicate SOPInstanceUIDs found:")
        for uid in duplicate_sops[:10]:
            print(f"  {uid}")

    ct_records = [r for r in records if r["modality"] == "CT"]
    print(f"\nCT files: {len(ct_records)}")

    if expected_slices is not None and len(ct_records) != expected_slices:
        print(f"WARNING: expected {expected_slices} CT slices, found {len(ct_records)}")

    by_series = defaultdict(list)
    for r in ct_records:
        by_series[r["series_uid"]].append(r)

    for series_uid, items in by_series.items():
        print("\n" + "-" * 80)
        print(f"CT Series: {series_uid}")
        print(f"Slices in this series: {len(items)}")

        with_positions = [r for r in items if r["position"] is not None]
        if len(with_positions) != len(items):
            print("WARNING: Some slices have no ImagePositionPatient/ImageOrientationPatient.")
            continue

        sorted_items = sorted(with_positions, key=lambda r: r["position"])
        positions = np.asarray([r["position"] for r in sorted_items], dtype=float)
        diffs = np.diff(positions)

        print(f"Position min/max: {positions[0]:.6f} / {positions[-1]:.6f}")

        if len(diffs) > 0:
            print(f"Position spacing median: {np.median(np.abs(diffs)):.6f}")
            print(f"Position spacing min/max abs: {np.min(np.abs(diffs)):.6f} / {np.max(np.abs(diffs)):.6f}")

            zero_diffs = np.where(np.isclose(diffs, 0.0, atol=1e-5))[0]
            if len(zero_diffs) > 0:
                print(f"WARNING: duplicate geometric slice positions at sorted indices: {zero_diffs[:20]}")

            irregular = np.where(
                ~np.isclose(np.abs(diffs), np.median(np.abs(diffs)), rtol=1e-3, atol=1e-3)
            )[0]
            if len(irregular) > 0:
                print(f"WARNING: irregular geometric spacing at sorted indices: {irregular[:20]}")

        instance_numbers = [r["instance_number"] for r in sorted_items]
        if all(v is not None for v in instance_numbers):
            expected = list(range(1, len(instance_numbers) + 1))
            if instance_numbers != expected:
                print("WARNING: InstanceNumber does not follow geometric order.")
                print("First 20 geometrically sorted InstanceNumbers:")
                print("  ", instance_numbers[:20])
            else:
                print("InstanceNumber follows geometric order.")
        else:
            print("WARNING: Some InstanceNumber values are missing.")

        # Check file meta consistency.
        mismatches = []
        for r in sorted_items:
            ds = r["ds"]
            if hasattr(ds, "file_meta") and hasattr(ds.file_meta, "MediaStorageSOPInstanceUID"):
                if str(ds.file_meta.MediaStorageSOPInstanceUID) != str(ds.SOPInstanceUID):
                    mismatches.append(r["path"].name)

        if mismatches:
            print("WARNING: file_meta.MediaStorageSOPInstanceUID != SOPInstanceUID in:")
            for name in mismatches[:20]:
                print(f"  {name}")

        print("\nFirst 5 slices in geometric order:")
        for r in sorted_items[:5]:
            print(
                f"  {r['path'].name}: "
                f"InstanceNumber={r['instance_number']}, "
                f"position={r['position']:.6f}"
            )

        print("\nLast 5 slices in geometric order:")
        for r in sorted_items[-5:]:
            print(
                f"  {r['path'].name}: "
                f"InstanceNumber={r['instance_number']}, "
                f"position={r['position']:.6f}"
            )

    if strict:
        if unreadable:
            raise RuntimeError("Unreadable files detected.")
        if expected_slices is not None and len(ct_records) != expected_slices:
            raise RuntimeError(f"Expected {expected_slices} CT slices, found {len(ct_records)}.")
        if len(by_series) != 1:
            raise RuntimeError(f"Expected exactly one CT SeriesInstanceUID, found {len(by_series)}.")

    return records


def read_dicom_series(
    dicom_dir: str,
    expected_slices: int | None = None,
    series_uid: str | None = None,
    debug: bool = True,
):
    """Read a DICOM CT series into an ITK image with metadata.

    Returns
    -------
    tuple
        image, metadata_dict, filenames
    """
    pixel_type = itk.SS
    image_type = itk.Image[pixel_type, 3]

    if debug:
        audit_dicom_series(
            dicom_dir,
            title="Before ITK loading",
            expected_slices=expected_slices,
            strict=False,
        )

    names = itk.GDCMSeriesFileNames.New()
    names.SetUseSeriesDetails(True)
    names.SetDirectory(dicom_dir)

    series_uids = list(names.GetSeriesUIDs())
    if len(series_uids) == 0:
        raise RuntimeError("No DICOM series found")

    print("\nITK/GDCM detected series:")
    candidates = []

    for uid in series_uids:
        uid_files = list(names.GetFileNames(uid))

        # Count modalities for this ITK/GDCM series.
        modalities = []
        for f in uid_files:
            try:
                ds = pydicom.dcmread(f, stop_before_pixels=True, force=False)
                modalities.append(getattr(ds, "Modality", "MISSING"))
            except Exception:
                modalities.append("UNREADABLE")

        modality_counts = Counter(modalities)
        candidates.append((uid, uid_files, modality_counts))

        print(f"  UID: {uid}")
        print(f"    files: {len(uid_files)}")
        print(f"    modalities: {dict(modality_counts)}")

    if series_uid is not None:
        selected_uid = series_uid
        if selected_uid not in series_uids:
            raise RuntimeError(f"Requested SeriesInstanceUID not found: {selected_uid}")
    else:
        # Prefer a CT series with the expected number of slices.
        ct_candidates = []
        for uid, uid_files, modality_counts in candidates:
            if modality_counts.get("CT", 0) == len(uid_files):
                ct_candidates.append((uid, uid_files))

        if expected_slices is not None:
            exact = [(uid, files) for uid, files in ct_candidates if len(files) == expected_slices]
            if len(exact) == 1:
                selected_uid = exact[0][0]
            elif len(exact) > 1:
                raise RuntimeError(
                    f"Multiple CT series with {expected_slices} slices found. "
                    f"Pass series_uid explicitly."
                )
            else:
                raise RuntimeError(
                    f"No CT series with expected_slices={expected_slices} found."
                )
        else:
            if not ct_candidates:
                raise RuntimeError("No pure CT series found.")
            selected_uid = max(ct_candidates, key=lambda x: len(x[1]))[0]

    filenames = list(names.GetFileNames(selected_uid))

    print(f"\nSelected SeriesInstanceUID: {selected_uid}")
    print(f"Selected file count: {len(filenames)}")

    if expected_slices is not None and len(filenames) != expected_slices:
        raise RuntimeError(
            f"Selected series has {len(filenames)} files, expected {expected_slices}."
        )

    print("\nFirst 5 ITK/GDCM filenames:")
    for f in filenames[:5]:
        print("  ", f)

    print("\nLast 5 ITK/GDCM filenames:")
    for f in filenames[-5:]:
        print("  ", f)

    reader = itk.ImageSeriesReader[image_type].New()
    dicom_io = itk.GDCMImageIO.New()
    reader.SetImageIO(dicom_io)
    reader.SetFileNames(filenames)
    reader.Update()

    # Store metadata from first selected slice.
    dicom_io.SetFileName(filenames[0])
    dicom_io.ReadImageInformation()
    metadata = dicom_io.GetMetaDataDictionary()
    metadata_dict = {k: metadata[k] for k in metadata.GetKeys()}

    image = reader.GetOutput()

    print("\nLoaded ITK image:")
    print("  size:     ", tuple(image.GetLargestPossibleRegion().GetSize()))
    print("  spacing:  ", tuple(image.GetSpacing()))
    print("  origin:   ", tuple(image.GetOrigin()))
    print("  direction:", image.GetDirection())

    return image, metadata_dict, filenames