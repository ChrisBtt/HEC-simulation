import os
from typing import List, Tuple
import numpy as np
import itk


"""
Synthetic homogeneous 3DCT box generator using ITK

This module:
- Creates a 3D CT volume of a rectangular box
- Uses a material description (HU, density, or name)
- Preserves physical spacing, origin, and direction
- Can be written to a DICOM series
"""
class Synthetic3DCT:
    def __init__(
        self,
        size_mm: Tuple[float, float, float],
        spacing_mm: Tuple[float, float, float],
        radiodensity_hu: int,
        origin_mm: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        patient_name: str = "ANONYMOUS",
        patient_id: str = "0000000",
    ):
        """
        Parameters
        ----------
        size_mm : (float, float, float)
            Physical size of the box in mm (X, Y, Z)
        spacing_mm : (float, float, float)
            Voxel spacing in mm
        radiodensity_hu : dict
            Material description, e.g.
            {"name": "water", "hu": 0}
            {"name": "lung", "hu": -750}
            {"name": "bone", "hu": 1000}
        origin_mm : (float, float, float), optional
            Image origin in physical space
        patient_name : str, optional
            Patient name for DICOM metadata
        patient_id : str, optional
            Patient ID for DICOM metadata
        """
        self.size_mm = size_mm
        self.spacing_mm = spacing_mm
        self.radiodensity_hu = radiodensity_hu
        self.origin_mm = origin_mm

        self.metadata_dict = {
            "0010|0010": patient_name,
            "0010|0020": patient_id,
            "0008|1030": "Synthetic Study"  # Study Description
        }
        self.image = self._create_image()

    def _create_image(self):
        """Create a homogeneous ITK 3D image."""
        pixel_type = itk.SS  # signed short for CT
        image_type = itk.Image[pixel_type, 3]

        size_voxels = [
            int(np.round(self.size_mm[i] / self.spacing_mm[i]))
            for i in range(3)
        ]

        region = itk.ImageRegion[3]()
        region.SetSize(size_voxels)

        image = image_type.New()
        image.SetRegions(region)
        image.SetSpacing(self.spacing_mm)
        image.SetOrigin(self.origin_mm)
        direction = itk.GetMatrixFromArray(np.eye(3, dtype=np.float64))
        image.SetDirection(direction)
        image.Allocate()

        image.FillBuffer(self.radiodensity_hu)

        return image

    def get_image(self):
        """Return the ITK image."""
        return self.image

    def write_dicom_series(self, output_dir: str):
        """Write the synthetic CT to a DICOM series."""
        os.makedirs(output_dir, exist_ok=True)

        pixel_type = itk.SS
        image_type = itk.Image[pixel_type, 3]

        writer = itk.ImageSeriesWriter[image_type, itk.Image[pixel_type, 2]].New()
        writer.SetInput(self.image)

        gdcm_io = itk.GDCMImageIO.New()
        metadata_dict = itk.MetaDataDictionary()
        for key, value in self.metadata_dict.items():
            metadata_dict[key] = value

        metadata_dict["0008|103e"] = "3DCT"  # Series Description
        metadata_dict["0008|0060"] = "CT"  # Modality

        gdcm_io.SetMetaDataDictionary(metadata_dict)

        writer.SetImageIO(gdcm_io)

        names = itk.NumericSeriesFileNames.New()
        names.SetSeriesFormat(os.path.join(output_dir, "slice_%03d.dcm"))
        names.SetStartIndex(0)
        names.SetEndIndex(self.image.GetLargestPossibleRegion().GetSize()[2] - 1)
        names.SetIncrementIndex(1)

        writer.SetFileNames(names.GetFileNames())
        writer.Update()


"""
Synthetic 4DCT generation from a 3DCT DICOM directory using ITK

This module:
- Reads a 3DCT from a DICOM directory
- Applies a series of affine transforms (e.g. respiratory phases)
- Writes each phase as a DICOM series (4DCT)
"""
class Synthetic4DCT:
    def __init__(self, dicom_dir: str):
        """
        Parameters
        ----------
        dicom_dir : str
            Path to the input 3DCT DICOM directory
        """
        self.dicom_dir = dicom_dir
        self.metadata_dict = {
            "0010|0010": "ANONYMOUS",  # Patient's Name
            "0010|0020": "00000",  # Patient ID
            "0008|1030": "Synthetic Study"  # Study Description
        }
        self.image = self._read_dicom()

    def _read_dicom(self):
        """Read a DICOM series into an ITK image."""
        pixel_type = itk.SS
        image_type = itk.Image[pixel_type, 3]

        names = itk.GDCMSeriesFileNames.New()
        names.SetUseSeriesDetails(True)
        names.SetDirectory(self.dicom_dir)

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

        for tag in ["0010|0010", "0010|0020", "0008|1030"]:
            if tag in metadata:
                self.metadata_dict[tag] = metadata[tag]

        return reader.GetOutput()

    def _apply_affine(self, affine: itk.AffineTransform, output_origin=None, output_size=None):
        """Apply affine transform with fixed geometry."""
        image_type = type(self.image)

        # If no specific geometry is provided, default to original (clipping occurs)
        # If provided, all phases will align to this common frame
        origin = output_origin if output_origin is not None else self.image.GetOrigin()
        size = output_size if output_size is not None else self.image.GetLargestPossibleRegion().GetSize()

        inverse = itk.AffineTransform[itk.D, 3].New()
        affine.GetInverse(inverse)

        resampler = itk.ResampleImageFilter[image_type, image_type].New()
        resampler.SetInput(self.image)
        resampler.SetTransform(inverse)

        resampler.SetOutputOrigin(origin)
        resampler.SetSize(size)
        resampler.SetOutputSpacing(self.image.GetSpacing())
        resampler.SetOutputDirection(self.image.GetDirection())

        resampler.SetInterpolator(itk.LinearInterpolateImageFunction.New(self.image))
        resampler.SetDefaultPixelValue(-1024)
        resampler.Update()
        return resampler.GetOutput()

    def generate_4dct(self, affines: List[itk.AffineTransform], use_center_as_origin: bool = False):
        """Generate transformed phases using a global common bounding box."""
        origin = self.image.GetOrigin()
        spacing = self.image.GetSpacing()
        original_size = self.image.GetLargestPossibleRegion().GetSize()

        converted_affines = [
            transform if not isinstance(transform, list) else self._matrix_to_itk_affine(transform)
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
        corners_phys = [self.image.TransformIndexToPhysicalPoint(c) for c in corners]

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
            phase_img = self._apply_affine(affine, output_origin=global_min, output_size=global_size)
            phases.append(phase_img)
        return phases

    @staticmethod
    def _matrix_to_itk_affine(matrix_flat: List[float]) -> itk.AffineTransform:
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

    def write_dicom_series(self, image, output_dir, phase_index=0):
        """Write a 3D image as a DICOM series."""
        print(f"Writing phase {phase_index}...")
        os.makedirs(output_dir, exist_ok=True)

        pixel_type = itk.SS
        image_type = itk.Image[pixel_type, 3]

        writer = itk.ImageSeriesWriter[image_type, itk.Image[pixel_type, 2]].New()
        writer.SetInput(image)

        gdcm_io = itk.GDCMImageIO.New()
        metadata_dict = itk.MetaDataDictionary()
        for key, value in self.metadata_dict.items():
            metadata_dict[key] = value

        # Add phase-specific metadata
        #metadata_dict["0020|000e"] = f"1.2.3.4.5.6.7.8.9.{phase_index}"  # Series Instance UID
        metadata_dict["0008|103e"] = f"4DCT Phase {phase_index}"  # Series Description
        metadata_dict["0008|0060"] = "CT"  # Modality

        gdcm_io.SetMetaDataDictionary(metadata_dict)
        writer.SetImageIO(gdcm_io)

        names = itk.NumericSeriesFileNames.New()
        names.SetSeriesFormat(os.path.join(output_dir, f"phase{phase_index}_%03d.dcm"))
        names.SetStartIndex(0)
        names.SetEndIndex(image.GetLargestPossibleRegion().GetSize()[2] - 1)
        names.SetIncrementIndex(1)

        writer.SetFileNames(names.GetFileNames())
        writer.Update()


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
    box = Synthetic3DCT(
        size_mm=(300.0, 300.0, 300.0),
        spacing_mm=(1.0, 1.0, 1.0),
        radiodensity_hu=0,
    )

    box.write_dicom_series("output/synthetic_water_box")


    ct = Synthetic4DCT(dicom_dir="output/synthetic_water_box")

    # Create example affine transforms (e.g. breathing motion)
    affines = []
    for scale_z in np.linspace(0.1, 1.0, 10):
        affine = itk.AffineTransform[itk.D, 3].New()
        affine.SetIdentity()
        scale = [1.0, 1.0, scale_z]  # Z-axis scaling
        affine.Scale(scale)
        affines.append(affine)

    phases = ct.generate_4dct(affines)

    for i, img in enumerate(phases):
        ct.write_dicom_series(img, f"output/phase_{i}", phase_index=i)

if __name__ == "__main__":
    main()
