import os
from typing import List, Tuple, Dict
import numpy as np
import itk

from pathlib import Path
from datetime import datetime

import pydicom
from pydicom.dataset import FileMetaDataset
from pydicom.uid import (
    CTImageStorage,
    ImplicitVRLittleEndian,
    generate_uid,
)
from hecTool.TransformAffine import interpolate_transforms, euler_deg_to_matrix
from hecTool.ProcessCT import read_dicom_series, audit_dicom_series


def get_default_image_metadata(metadata=None) -> Dict:
    """Return a DICOM metadata dictionary containing only basic patient and study tags.

    Parameters
    ----------
    metadata : dict, optional
        Existing metadata values keyed by DICOM tag strings (e.g., "0010|0010").
        Any provided values override the defaults.

    Returns
    -------
    dict
        Metadata dictionary containing required keys for a CT series.
    """
    metadata = metadata or {}
    return {
        "0010|0010": metadata.get("0010|0010", "ANONYMOUS"),       # Patient Name
        "0010|0020": metadata.get("0010|0020", "00000"),           # Patient ID
        "0008|1030": metadata.get("0008|1030", "Synthetic Study"), # Study Description
        "0008|103e": metadata.get("0008|103e", "3DCT"),            # Series Description
        "0008|0060": metadata.get("0008|0060", "CT")               # Modality
    }


def clone_itk_image(img):
    """Deep-copy an ITK image and detach it from the pipeline.

    Parameters
    ----------
    img : itk.Image
        Source ITK image to duplicate.

    Returns
    -------
    itk.Image
        Independent image copy with a disconnected pipeline.
    """
    duplicator = itk.ImageDuplicator[type(img)].New()
    duplicator.SetInputImage(img)
    duplicator.Update()
    out = duplicator.GetOutput()
    out.DisconnectPipeline()
    return out


def clean_dicom_output_dir(output_dir: str):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for p in output_dir.iterdir():
        if p.is_file() and (
            p.suffix.lower() in [".dcm", ".dicom", ""]
            or p.name.startswith("slice_")
        ):
            p.unlink()


def get_image_center_mm(image):
    """Compute the physical-space center of an ITK image in millimeters.

    Parameters
    ----------
    image : itk.Image
        Input image.

    Returns
    -------
    numpy.ndarray
        Center point in physical coordinates (mm), shape (3,).
    """
    origin = np.array(image.GetOrigin(), dtype=float)
    spacing = np.array(image.GetSpacing(), dtype=float)
    direction = np.array(image.GetDirection(), dtype=float)
    size = np.array(image.GetLargestPossibleRegion().GetSize(), dtype=float)

    return origin + direction @ ((size - 1) * spacing / 2.0)


def generate_synthetic_3dct(
        size_mm: Tuple[float, float, float],
        spacing_mm: Tuple[float, float, float],
        radiodensity_hu: int,
        origin_mm: Tuple[float, float, float] = (0.0, 0.0, 0.0)
) -> itk.Image:
    """Create a 3D CT volume filled with a constant HU value.

    Parameters
    ----------
    size_mm : tuple of float
        Physical size of the volume in mm (X, Y, Z).
    spacing_mm : tuple of float
        Voxel spacing in mm (X, Y, Z).
    radiodensity_hu : int
        Radiodensity to fill the volume with, in Hounsfield Units.
    origin_mm : tuple of float, optional
        Image origin in physical space (mm).

    Returns
    -------
    itk.Image
        ITK image containing the synthetic 3D CT volume.
    """
    pixel_type = itk.SS  # signed short for CT
    image_type = itk.Image[pixel_type, 3]

    size_voxels = [
        int(np.round(size_mm[i] / spacing_mm[i]))
        for i in range(3)
    ]

    region = itk.ImageRegion[3]()
    region.SetSize(size_voxels)

    image = image_type.New()
    image.SetRegions(region)
    image.SetSpacing(spacing_mm)
    image.SetOrigin(origin_mm)
    direction = itk.GetMatrixFromArray(np.eye(3, dtype=np.float64))
    image.SetDirection(direction)
    image.Allocate()

    image.FillBuffer(radiodensity_hu)

    return image


def _format_ds(value: float) -> str:
    """Format a DICOM DS value safely."""
    return f"{float(value):.12g}"


def _format_multi_ds(values) -> list[str]:
    """Format a DICOM multi-value DS field."""
    return [_format_ds(v) for v in values]


def _itk_direction_to_numpy(image: itk.Image) -> np.ndarray:
    """Convert ITK 3D direction matrix to a NumPy 3x3 array."""
    direction = image.GetDirection()

    try:
        arr = np.asarray(direction, dtype=float)
        if arr.shape == (3, 3):
            return arr
    except Exception:
        pass

    try:
        return itk.array_from_matrix(direction).astype(float)
    except Exception:
        pass

    try:
        return np.array(
            [[float(direction[i, j]) for j in range(3)] for i in range(3)],
            dtype=float,
        )
    except Exception:
        pass

    try:
        vnl = direction.GetVnlMatrix()
        return np.array(
            [[float(vnl.get(i, j)) for j in range(3)] for i in range(3)],
            dtype=float,
        )
    except Exception as exc:
        raise RuntimeError("Could not convert ITK image direction to NumPy.") from exc


def _metadata_get(metadata: dict, keyword: str, tag: str, default=None):
    """Read metadata either by DICOM keyword or ITK/GDCM tag string."""
    if metadata is None:
        return default

    candidates = [
        keyword,
        tag,
        tag.lower(),
        tag.upper(),
        tag.replace("|", ","),
        tag.replace("|", ",").upper(),
    ]

    for key in candidates:
        if key in metadata and metadata[key] not in [None, ""]:
            return metadata[key]

    return default


def _set_file_meta(ds: pydicom.Dataset):
    """Ensure file meta information exists and is internally consistent."""
    if not hasattr(ds, "file_meta") or ds.file_meta is None:
        ds.file_meta = FileMetaDataset()

    ds.file_meta.MediaStorageSOPClassUID = CTImageStorage
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    if "TransferSyntaxUID" not in ds.file_meta:
        ds.file_meta.TransferSyntaxUID = ImplicitVRLittleEndian

    ds.file_meta.ImplementationClassUID = generate_uid()


def write_dicom_series(image: itk.Image, output_dir: str, metadata: dict = None, expected_slices: int | None = None, clean_output: bool = True, debug: bool = True):
    """Write an ITK image to a DICOM CT series on disk.

    Missing CT geometry and DICOM series metadata are derived from the 3D ITK
    image and patched into each slice after ITK/GDCM writing.

    Parameters
    ----------
    image : itk.Image
        3D ITK image to write.
    output_dir : str
        Destination directory for the DICOM slices.
    metadata : dict, optional
        DICOM metadata dictionary. May use ITK/GDCM tag keys such as
        "0008|0060" or DICOM keywords such as "Modality".
    """
    metadata = metadata or get_default_image_metadata()

    output_dir = Path(output_dir)
    if clean_output:
        clean_dicom_output_dir(output_dir)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Basic image geometry extracted from the ITK image
    # -------------------------------------------------------------------------

    region = image.GetLargestPossibleRegion()
    size = tuple(int(v) for v in region.GetSize())

    if len(size) != 3:
        raise ValueError(f"Expected a 3D image, got image size: {size}")

    spacing = np.asarray(image.GetSpacing(), dtype=float)
    origin = np.asarray(image.GetOrigin(), dtype=float)
    direction = _itk_direction_to_numpy(image)

    rows = size[1]
    columns = size[0]
    number_of_slices = size[2]

    # ITK index axis 0 corresponds to DICOM image row direction,
    # ITK index axis 1 corresponds to DICOM image column direction.
    row_direction = direction[:, 0]
    column_direction = direction[:, 1]
    slice_direction = direction[:, 2]

    image_orientation_patient = np.concatenate(
        [row_direction, column_direction]
    )

    # DICOM PixelSpacing is row spacing first, column spacing second.
    pixel_spacing = [spacing[1], spacing[0]]

    slice_spacing = abs(float(spacing[2]))

    # -------------------------------------------------------------------------
    # Fill global metadata before ITK/GDCM writing
    # -------------------------------------------------------------------------

    now = datetime.now()

    study_instance_uid = _metadata_get(
        metadata,
        "StudyInstanceUID",
        "0020|000d",
        generate_uid(),
    )
    series_instance_uid = _metadata_get(
        metadata,
        "SeriesInstanceUID",
        "0020|000e",
        generate_uid(),
    )
    frame_of_reference_uid = _metadata_get(
        metadata,
        "FrameOfReferenceUID",
        "0020|0052",
        generate_uid(),
    )

    metadata.setdefault("0008|0008", "DERIVED\\SECONDARY")
    metadata.setdefault("0008|0016", str(CTImageStorage))
    metadata.setdefault("0008|0020", now.strftime("%Y%m%d"))
    metadata.setdefault("0008|0030", now.strftime("%H%M%S"))
    metadata.setdefault("0008|0060", "CT")
    metadata.setdefault("0008|103e", "Synthetic CT")

    metadata.setdefault("0018|0050", _format_ds(slice_spacing))
    metadata.setdefault("0018|0088", _format_ds(slice_spacing))

    metadata.setdefault("0020|000d", str(study_instance_uid))
    metadata.setdefault("0020|000e", str(series_instance_uid))
    metadata.setdefault("0020|0052", str(frame_of_reference_uid))
    metadata.setdefault("0020|0011", "1")

    metadata.setdefault("0028|0002", "1")
    metadata.setdefault("0028|0004", "MONOCHROME2")
    metadata.setdefault("0028|0010", str(rows))
    metadata.setdefault("0028|0011", str(columns))
    metadata.setdefault("0028|0030", "\\".join(_format_multi_ds(pixel_spacing)))
    metadata.setdefault("0028|0100", "16")
    metadata.setdefault("0028|0101", "16")
    metadata.setdefault("0028|0102", "15")
    metadata.setdefault("0028|0103", "1")
    metadata.setdefault("0028|1052", "0")
    metadata.setdefault("0028|1053", "1")
    metadata.setdefault("0028|1054", "HU")

    # -------------------------------------------------------------------------
    # ITK/GDCM write
    # -------------------------------------------------------------------------

    pixel_type = itk.SS
    image_type = itk.Image[pixel_type, 3]
    slice_type = itk.Image[pixel_type, 2]

    writer = itk.ImageSeriesWriter[image_type, slice_type].New()
    writer.SetInput(image)

    gdcm_io = itk.GDCMImageIO.New()
    metadata_dict = itk.MetaDataDictionary()

    for key, value in metadata.items():
        metadata_dict[str(key)] = str(value)

    gdcm_io.SetMetaDataDictionary(metadata_dict)
    writer.SetImageIO(gdcm_io)

    names = itk.NumericSeriesFileNames.New()
    names.SetSeriesFormat(str(output_dir / "slice_%03d.dcm"))
    names.SetStartIndex(0)
    names.SetEndIndex(number_of_slices - 1)
    names.SetIncrementIndex(1)

    file_names = list(names.GetFileNames())
    writer.SetFileNames(file_names)
    writer.Update()

    # -------------------------------------------------------------------------
    # Robust post-patching with pydicom
    # -------------------------------------------------------------------------
    # This is important because InstanceNumber, ImagePositionPatient and
    # SOPInstanceUID must be slice-specific.

    for k, file_name in enumerate(file_names):
        ds = pydicom.dcmread(file_name, force=True)

        sop_instance_uid = generate_uid()

        # Identification
        ds.SOPClassUID = CTImageStorage
        ds.SOPInstanceUID = sop_instance_uid
        ds.Modality = "CT"
        ds.ImageType = ["DERIVED", "SECONDARY"]

        ds.StudyInstanceUID = str(study_instance_uid)
        ds.SeriesInstanceUID = str(series_instance_uid)
        ds.FrameOfReferenceUID = str(frame_of_reference_uid)

        ds.SeriesNumber = str(
            _metadata_get(metadata, "SeriesNumber", "0020|0011", "1")
        )
        ds.InstanceNumber = str(k + 1)

        # Geometry
        image_position_patient = origin + k * spacing[2] * slice_direction

        ds.ImagePositionPatient = _format_multi_ds(image_position_patient)
        ds.ImageOrientationPatient = _format_multi_ds(image_orientation_patient)

        ds.PixelSpacing = _format_multi_ds(pixel_spacing)
        ds.SliceThickness = _format_ds(slice_spacing)
        ds.SpacingBetweenSlices = _format_ds(slice_spacing)

        # Pixel module
        ds.Rows = int(rows)
        ds.Columns = int(columns)
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1

        # CT HU semantics
        ds.RescaleIntercept = "0"
        ds.RescaleSlope = "1"
        ds.RescaleType = "HU"

        # Optional but often helpful
        if not getattr(ds, "StudyDate", None):
            ds.StudyDate = now.strftime("%Y%m%d")
        if not getattr(ds, "StudyTime", None):
            ds.StudyTime = now.strftime("%H%M%S")
        if not getattr(ds, "SeriesDescription", None):
            ds.SeriesDescription = "Synthetic CT"

        _set_file_meta(ds)

        ds.is_little_endian = True
        ds.is_implicit_VR = True

        ds.save_as(file_name, write_like_original=False)
    
    if debug:
        audit_dicom_series(
            str(output_dir),
            title="After DICOM writing",
            expected_slices=expected_slices,
            strict=True,
        )

        
def apply_affine(image, affine: itk.AffineTransform, output_origin=None, output_size=None):
    """Resample an image with an affine transform into a fixed geometry.

    Parameters
    ----------
    image : itk.Image
        Input image to resample.
    affine : itk.AffineTransform
        Affine transform mapping output physical points to input points.
    output_origin : sequence of float, optional
        Physical origin of the output image. Defaults to the input origin.
    output_size : sequence of int, optional
        Size of the output image in voxels. Defaults to the input size.

    Returns
    -------
    itk.Image
        Resampled image in the specified output geometry.
    """
    image_type = type(image)

    # If no specific geometry is provided, default to original (clipping occurs)
    # If provided, all phases will align to this common frame
    origin = output_origin if output_origin is not None else image.GetOrigin()
    size = output_size if output_size is not None else image.GetLargestPossibleRegion().GetSize()

    inverse = itk.AffineTransform[itk.D, 3].New()
    affine.GetInverse(inverse)

    resampler = itk.ResampleImageFilter[image_type, image_type].New()
    resampler.SetInput(image)
    resampler.SetTransform(inverse)

    resampler.SetOutputOrigin(origin)
    resampler.SetSize(size)
    resampler.SetOutputSpacing(image.GetSpacing())
    resampler.SetOutputDirection(image.GetDirection())

    resampler.SetInterpolator(itk.LinearInterpolateImageFunction.New(image))
    resampler.SetDefaultPixelValue(-1024)
    resampler.Update()
    return resampler.GetOutput()


def generate_4dct(image, affines: List[itk.AffineTransform], tumors=None, timeline=None,
                  use_center_as_origin: bool = False):
    """Generate transformed 4DCT phases in a shared global bounding box.

    Parameters
    ----------
    image : itk.Image
        Source 3D CT image.
    affines : list of itk.AffineTransform or list of list
        Per-phase transforms. A flattened 4x4 matrix list is accepted and
        converted to an ITK affine.
    tumors : list, optional
        Tumor objects to embed.
    timeline : list of float, optional
        Time points in seconds aligned with ``affines`` for time-dependent
        tumor transforms.
    use_center_as_origin : bool, optional
        If True, set each affine's center to the image center.

    Returns
    -------
    list of itk.Image
        List of phase images aligned to a common bounding box.
    """
    spacing = np.array(image.GetSpacing(), dtype=float)
    original_size = image.GetLargestPossibleRegion().GetSize()

    converted_affines = [
        transform if not isinstance(transform, list) else matrix_to_itk_affine(transform)
        for transform in affines
    ]

    if use_center_as_origin:
        center = get_image_center_mm(image)

        for affine in converted_affines:
            affine.SetCenter(center)

    # Calculate the bounding box for all transforms combined
    corners = [
        [0, 0, 0], [original_size[0]-1, 0, 0], [0, original_size[1]-1, 0], [original_size[0]-1, original_size[1]-1, 0],
        [0, 0, original_size[2]-1], [original_size[0]-1, 0, original_size[2]-1], [0, original_size[1]-1, original_size[2]-1],
        [original_size[0]-1, original_size[1]-1, original_size[2]-1]
    ]
    corners_phys = [image.TransformIndexToPhysicalPoint(c) for c in corners]

    all_transformed_points = []
    for affine in converted_affines:
        all_transformed_points.extend([affine.TransformPoint(p) for p in corners_phys])

    # Find the global min/max across all phases
    global_min = np.min(all_transformed_points, axis=0)
    global_max = np.max(all_transformed_points, axis=0)

    eps = 1e-6
    snapped_min = np.floor(global_min / spacing + eps) * spacing
    snapped_max = np.ceil(global_max / spacing - eps) * spacing

    global_min = snapped_min
    global_size = (((snapped_max - snapped_min) / spacing).astype(int) + 1)

    # Generate each phase using this global frame
    phases = []
    for i, affine in enumerate(converted_affines):
        phase_src = image
        if tumors is not None and timeline is not None:
            phase_src = clone_itk_image(image)
            embed_tumors_in_image(phase_src, tumors, time_s=timeline[i])
        phase_img = apply_affine(phase_src, affine, output_origin=global_min, output_size=global_size.tolist())
        phases.append(phase_img)
    return phases


def stamp_ellipsoid_hu(
    image: itk.Image,
    center_mm,
    radii_mm,
    rotation_deg=(0.0, 0.0, 0.0),
    hu=0,
):
    """Stamp an oriented ellipsoid into an ITK image by writing HU in-place.

    Parameters
    ----------
    image : itk.Image
        Image to modify in-place.
    center_mm : sequence of float
        Ellipsoid center in physical coordinates (mm).
    radii_mm : sequence of float
        Ellipsoid radii in mm (X, Y, Z).
    rotation_deg : sequence of float, optional
        Euler rotations in degrees (X, Y, Z).
    hu : int, optional
        Hounsfield Unit value to write inside the ellipsoid.
    """
    # Convert to numpy view for in-place write
    arr = itk.array_view_from_image(image)

    origin = np.array(image.GetOrigin(), dtype=float)
    spacing = np.array(image.GetSpacing(), dtype=float)
    direction = np.array(image.GetDirection(), dtype=float)

    center = np.array(center_mm, dtype=float)
    radii = np.array(radii_mm, dtype=float)

    rot = euler_deg_to_matrix(rotation_deg)

    # Precompute inverse rotation for point transform
    inv_rot = rot.T

    # Compute index bounds for a conservative box (sphere with max radius)
    max_r = float(np.max(radii))
    # Convert center in physical -> index space (approx)
    center_idx = np.linalg.inv(direction) @ (center - origin) / spacing
    center_idx = center_idx.astype(int)

    # Index bounds (clamp to image size)
    size = np.array(image.GetLargestPossibleRegion().GetSize())
    min_idx = np.maximum(center_idx - int(np.ceil(max_r / spacing.min())) - 1, 0)
    max_idx = np.minimum(center_idx + int(np.ceil(max_r / spacing.min())) + 1, size - 1)

    # Iterate bounding box
    for k in range(min_idx[2], max_idx[2] + 1):
        for j in range(min_idx[1], max_idx[1] + 1):
            for i in range(min_idx[0], max_idx[0] + 1):
                idx = np.array([i, j, k], dtype=float)

                # index -> physical
                phys = origin + direction @ (idx * spacing)

                # ellipsoid local frame
                local = inv_rot @ (phys - center)

                # inside ellipsoid?
                if np.sum((local / radii) ** 2) <= 1.0:
                    arr[k, j, i] = int(hu)


def embed_tumors_in_image(image, tumors, time_s=None):
    """Embed tumors into an image in-place using DICOM HU rules.

    Parameters
    ----------
    image : itk.Image
        Target image to modify.
    tumors : list
        Tumor objects with attributes: ``embed_mode``, ``translation_mm``,
        ``rotation_deg``, ``radius_mm``, ``radiodensity_hu``, and optionally
        ``transform_sequence``.
    time_s : float, optional
        Time in seconds used for interpolating tumor transforms.
    """
    for tumor in tumors:
        if tumor.embed_mode != "dicom": continue

        # Base params
        translation = np.array(tumor.translation_mm, dtype=float)
        rotation = np.array(tumor.rotation_deg, dtype=float)
        scale = np.array([1.0, 1.0, 1.0], dtype=float)

        # Apply time-dependent transform if present
        if time_s is not None and tumor.transform_sequence:
            interp = interpolate_transforms(tumor.transform_sequence, [time_s])[0]
            translation = translation + np.array(interp.translation)
            rotation = rotation + np.array(interp.rotation_deg)
            scale = scale * np.array(interp.scale)

        radii = np.array(tumor.radius_mm, dtype=float) * scale

        stamp_ellipsoid_hu(
            image=image,
            center_mm=get_image_center_mm(image) + translation,
            radii_mm=radii,
            rotation_deg=rotation,
            hu=tumor.radiodensity_hu,
        )


def matrix_to_itk_affine(matrix_flat: List[float]) -> itk.AffineTransform:
    """Convert a flattened 4x4 matrix to an ITK AffineTransform.

    Parameters
    ----------
    matrix_flat : list of float
        Flattened 4x4 affine matrix in row-major order.

    Returns
    -------
    itk.AffineTransform
        ITK affine transform containing the 3x3 matrix and offset.
    """
    matrix_np = np.array(matrix_flat).reshape(4, 4)

    # Extract 3x3 rotation/scale part and 3x1 translation part
    matrix_3x3 = matrix_np[:3, :3].astype(np.float64)
    translation = matrix_np[:3, 3].astype(np.float64)

    affine = itk.AffineTransform[itk.D, 3].New()

    itk_matrix = itk.GetMatrixFromArray(matrix_3x3)
    affine.SetMatrix(itk_matrix)

    affine.SetOffset(translation.tolist())

    return affine


# ---------------- Example usage ----------------
def main():
    """Run a basic synthetic 3DCT/4DCT generation demo."""
    print("Generating synthetic 3DCT...")
    synthetic_3dct = generate_synthetic_3dct(
        size_mm=(300.0, 300.0, 300.0),
        spacing_mm=(1.0, 1.0, 1.0),
        radiodensity_hu=0,
    )

    print("Writing synthetic 3DCT...")
    write_dicom_series(synthetic_3dct, "output/synthetic_water_box")

    print("Generating synthetic 4DCT...")
    ct, metadata, files = read_dicom_series("output/synthetic_water_box")

    # Create example affine transforms (e.g. breathing motion)
    affines = []
    for scale_z in np.linspace(0.1, 1.0, 10):
        affine = itk.AffineTransform[itk.D, 3].New()
        affine.SetIdentity()
        scale = [1.0, 1.0, scale_z]  # Z-axis scaling
        affine.Scale(scale)
        affines.append(affine)

    phases = generate_4dct(ct, affines)

    print("Writing synthetic 4DCT...")
    for i, img in enumerate(phases):
        phase_data = get_default_image_metadata(metadata)
        phase_data["0008|103e"] = f"4DCT Phase {i}"
        write_dicom_series(img, f"output/phase_{i}", phase_data)


if __name__ == "__main__":
    main()
