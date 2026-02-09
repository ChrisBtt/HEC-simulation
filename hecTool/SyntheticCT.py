import os
from typing import List, Tuple, Dict
import numpy as np
import itk


def get_default_image_metadata(metadata=None) -> Dict:
    metadata = metadata or {}
    return {
        "0010|0010": metadata.get("0010|0010", "ANONYMOUS"),       # Patient Name
        "0010|0020": metadata.get("0010|0020", "00000"),           # Patient ID
        "0008|1030": metadata.get("0008|1030", "Synthetic Study"), # Study Description
        "0008|103e": metadata.get("0008|103e", "3DCT"),            # Series Description
        "0008|0060": metadata.get("0008|0060", "CT")               # Modality
    }


def generate_synthetic_3dct(
        size_mm: Tuple[float, float, float],
        spacing_mm: Tuple[float, float, float],
        radiodensity_hu: int,
        origin_mm: Tuple[float, float, float] = (0.0, 0.0, 0.0)
) -> itk.Image:
    """
    Parameters
    ----------
    size_mm : (float, float, float)
        Physical size of the box in mm (X, Y, Z)
    spacing_mm : (float, float, float)
        Voxel spacing in mm
    radiodensity_hu : int
        Radiodensity of material in Hounsfield Units
    origin_mm : (float, float, float), optional
        Image origin in physical space

    Returns
    -------
    itk.Image
        itk Image containing 3D CT volume
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


def read_dicom_series(dicom_dir: str):
    """Read a DICOM series into an ITK image and its associated metadata."""
    pixel_type = itk.SS
    image_type = itk.Image[pixel_type, 3]

    names = itk.GDCMSeriesFileNames.New()
    names.SetUseSeriesDetails(True)
    names.SetDirectory(dicom_dir)

    series_uids = names.GetSeriesUIDs()
    if len(series_uids) == 0:
        raise RuntimeError("No DICOM series found")

    reader = itk.ImageSeriesReader[image_type].New()
    dicom_io = itk.GDCMImageIO.New()
    reader.SetImageIO(dicom_io)
    filenames = names.GetFileNames(series_uids[0])
    reader.SetFileNames(filenames)
    reader.Update()

    # Store essential metadata from first slice
    dicom_io.SetFileName(filenames[0])
    dicom_io.ReadImageInformation()
    metadata = dicom_io.GetMetaDataDictionary()

    metadata_dict = {k: metadata[k] for k in metadata.GetKeys()}

    return reader.GetOutput(), metadata_dict


def write_dicom_series(image: itk.Image, output_dir: str, metadata: dict = None):
    """Write an ITK image to a DICOM series."""
    metadata = metadata or get_default_image_metadata()

    os.makedirs(output_dir, exist_ok=True)

    pixel_type = itk.SS
    image_type = itk.Image[pixel_type, 3]

    writer = itk.ImageSeriesWriter[image_type, itk.Image[pixel_type, 2]].New()
    writer.SetInput(image)

    gdcm_io = itk.GDCMImageIO.New()
    metadata_dict = itk.MetaDataDictionary()
    for key, value in metadata.items():
        metadata_dict[key] = value

    gdcm_io.SetMetaDataDictionary(metadata_dict)
    writer.SetImageIO(gdcm_io)

    names = itk.NumericSeriesFileNames.New()
    names.SetSeriesFormat(os.path.join(output_dir, "slice_%03d.dcm"))
    names.SetStartIndex(0)
    names.SetEndIndex(image.GetLargestPossibleRegion().GetSize()[2] - 1)
    names.SetIncrementIndex(1)

    writer.SetFileNames(names.GetFileNames())
    writer.Update()


def apply_affine(image, affine: itk.AffineTransform, output_origin=None, output_size=None):
    """Apply affine transform with fixed geometry."""
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

def generate_4dct(image, affines: List[itk.AffineTransform], use_center_as_origin: bool = False):
    """Generate transformed phases using a global common bounding box."""
    origin = image.GetOrigin()
    spacing = image.GetSpacing()
    original_size = image.GetLargestPossibleRegion().GetSize()

    converted_affines = [
        transform if not isinstance(transform, list) else matrix_to_itk_affine(transform)
        for transform in affines
    ]

    if use_center_as_origin:
        center = [
            origin[i] + (original_size[i] * spacing[i]) / 2.0
            for i in range(3)
        ]

        for affine in converted_affines:
            affine.SetCenter(center)

    # Calculate the bounding box for all transforms combined
    corners = [
        [0, 0, 0], [original_size[0], 0, 0], [0, original_size[1], 0], [original_size[0], original_size[1], 0],
        [0, 0, original_size[2]], [original_size[0], 0, original_size[2]], [0, original_size[1], original_size[2]],
        [original_size[0], original_size[1], original_size[2]]
    ]
    corners_phys = [image.TransformIndexToPhysicalPoint(c) for c in corners]

    all_transformed_points = []
    for affine in converted_affines:
        all_transformed_points.extend([affine.TransformPoint(p) for p in corners_phys])

    # Find the global min/max across all phases
    global_min = np.min(all_transformed_points, axis=0)
    global_max = np.max(all_transformed_points, axis=0)

    # 2. Add Padding (e.g., 2 voxels on each side)
    padding_voxels = 2
    padding_mm = spacing * padding_voxels

    # Expand the physical bounds
    global_min -= padding_mm
    global_max += padding_mm

    global_size = [
        int(np.ceil((global_max[i] - global_min[i]) / spacing[i]))
        for i in range(3)
    ]

    # Generate each phase using this global frame
    phases = []
    for affine in converted_affines:
        # Pass the same origin and size to every phase
        phase_img = apply_affine(image, affine, output_origin=global_min, output_size=global_size)
        phases.append(phase_img)
    return phases


def matrix_to_itk_affine(matrix_flat: List[float]) -> itk.AffineTransform:
    """Convert a flattened 4x4 matrix to an ITK AffineTransform."""
    matrix_np = np.array(matrix_flat).reshape(4, 4)

    # Extract 3x3 rotation/scale part and 3x1 translation part
    matrix_3x3 = matrix_np[:3, :3].astype(np.float64)
    translation = matrix_np[:3, 3].astype(np.float64)

    affine = itk.AffineTransform[itk.D, 3].New()

    itk_matrix = itk.GetMatrixFromArray(matrix_3x3)
    affine.SetMatrix(itk_matrix)

    affine.SetOffset(translation.tolist())

    return affine


def get_dicom_extent(dicom_dir):
    # 1. Read the DICOM series
    pixel_type = itk.SS
    image_type = itk.Image[pixel_type, 3]

    names_generator = itk.GDCMSeriesFileNames.New()
    names_generator.SetUseSeriesDetails(True)
    names_generator.SetDirectory(dicom_dir)

    series_uids = names_generator.GetSeriesUIDs()
    if not series_uids:
        raise RuntimeError("No DICOM series found in directory")

    file_names = names_generator.GetFileNames(series_uids[0])
    reader = itk.ImageSeriesReader[image_type].New()
    reader.SetFileNames(file_names)
    reader.Update()

    image = reader.GetOutput()

    # 2. Extract Geometry Information
    origin = np.array(image.GetOrigin())
    spacing = np.array(image.GetSpacing())
    size = np.array(image.GetLargestPossibleRegion().GetSize())

    # 3. Calculate Extent
    # The extent is the physical range from the first voxel center to the last voxel center
    # Note: If you want the outer boundary of the voxels, use 'size' instead of 'size - 1'
    min_physical = origin
    max_physical = origin + (spacing * (size - 1))

    return min_physical, max_physical


# ---------------- Example usage ----------------
def main():
    print("Generating synthetic 3DCT...")
    synthetic_3dct = generate_synthetic_3dct(
        size_mm=(300.0, 300.0, 300.0),
        spacing_mm=(1.0, 1.0, 1.0),
        radiodensity_hu=0,
    )

    print("Writing synthetic 3DCT...")
    write_dicom_series(synthetic_3dct, "output/synthetic_water_box")

    print("Generating synthetic 4DCT...")
    ct, metadata = read_dicom_series("output/synthetic_water_box")

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
