from __future__ import annotations

import os.path
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Dict, Set


VALID_GEOMETRY_TYPES: Set[str] = {"parametrized", "3dct", "4dct"}


@dataclass
class ParametricGeometry:
    """Parametric box geometry for synthetic CT generation.

    Attributes
    ----------
    size_mm : list of float
        Physical size of the box in mm (X, Y, Z).
    spacing_mm : list of float
        Voxel spacing in mm (X, Y, Z).
    radiodensity_hu : int
        Radiodensity for the material in Hounsfield Units.
    """
    size_mm: List[float] = field(default_factory=lambda: [100.0, 100.0, 100.0])
    spacing_mm: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    radiodensity_hu: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ParametricGeometry:
        """Create a ParametricGeometry from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with ``size_mm``, ``spacing_mm``, and ``radiodensity_hu`` values.

        Returns
        -------
        ParametricGeometry
            Parsed parametric geometry configuration.
        """
        return cls(
            size_mm=list(data.get("size_mm", [100.0, 100.0, 100.0]) or [100.0, 100.0, 100.0]),
            spacing_mm=list(data.get("spacing_mm", [1.0, 1.0, 1.0]) or [1.0, 1.0, 1.0]),
            radiodensity_hu=int(data.get("radiodensity_hu", 0) or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the geometry to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the geometry.
        """
        return {
            "size_mm": self.size_mm,
            "spacing_mm": self.spacing_mm,
            "radiodensity_hu": self.radiodensity_hu,
        }


@dataclass
class TransformStep:
    """Single time-stamped transform step for motion sequences.

    Attributes
    ----------
    time_s : float
        Time in seconds.
    translation_mm : list of float
        Translation in mm (X, Y, Z).
    rotation_deg : list of float
        Euler rotation in degrees (X, Y, Z).
    scale : list of float
        Scale factors (X, Y, Z).
    shear : list of float
        Shear factors (XY, XZ, YZ).
    """
    time_s: float
    translation_mm: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_deg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    shear: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransformStep:
        """Create a TransformStep from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with transform values.

        Returns
        -------
        TransformStep
            Parsed transform step.
        """
        return cls(
            time_s=float(data.get("time_s", 0.0)),
            translation_mm=list(data.get("translation_mm", [0.0, 0.0, 0.0])),
            rotation_deg=list(data.get("rotation_deg", [0.0, 0.0, 0.0])),
            scale=list(data.get("scale", [1.0, 1.0, 1.0])),
            shear=list(data.get("shear", [0.0, 0.0, 0.0])),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the transform step to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the transform step.
        """
        return {
            "time_s": self.time_s,
            "translation_mm": self.translation_mm,
            "rotation_deg": self.rotation_deg,
            "scale": self.scale,
            "shear": self.shear,
        }


@dataclass
class TumorConfig:
    """Tumor configuration for geometry and motion.

    Attributes
    ----------
    topas_material : str
        TOPAS material name.
    radiodensity_hu : int
        Radiodensity in Hounsfield Units for DICOM embedding.
    embed_mode : str
        Embedding mode, e.g., "topas" or "dicom".
    translation_mm : list of float
        Translation in mm (X, Y, Z).
    rotation_deg : list of float
        Euler rotation in degrees (X, Y, Z).
    radius_mm : list of float
        Ellipsoid radii in mm (X, Y, Z).
    transform_sequence : list of TransformStep
        Time-dependent transform steps.
    """
    topas_material: str = "G4_WATER"
    radiodensity_hu: int = 0
    embed_mode: str = "topas"
    translation_mm: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_deg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    radius_mm: List[float] = field(default_factory=lambda: [10.0, 10.0, 10.0])
    transform_sequence: List[TransformStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TumorConfig:
        """Create a TumorConfig from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with tumor configuration values.

        Returns
        -------
        TumorConfig
            Parsed tumor configuration.
        """
        return cls(
            topas_material=str(data.get("topas_material", "G4_WATER")),
            radiodensity_hu=int(data.get("radiodensity_hu", 0) or 0),
            embed_mode=str(data.get("embed_mode", "topas") or "topas"),
            translation_mm=list(data.get("translation_mm", [0.0, 0.0, 0.0])),
            rotation_deg=list(data.get("rotation_deg", [0.0, 0.0, 0.0])),
            radius_mm=list(data.get("radius_mm", [10.0, 10.0, 10.0])),
            transform_sequence=[TransformStep.from_dict(t) for t in (data.get("transform_sequence", []) or [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the tumor configuration to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the tumor configuration.
        """
        data = {
            "topas_material": self.topas_material,
            "radiodensity_hu": self.radiodensity_hu,
            "embed_mode": self.embed_mode,
            "translation_mm": self.translation_mm,
            "rotation_deg": self.rotation_deg,
            "radius_mm": self.radius_mm,
            "transform_sequence": [],
        }
        for t in self.transform_sequence:
            t_dict = t.to_dict()
            if "shear" in t_dict:
                del t_dict["shear"]
            data["transform_sequence"].append(t_dict)
        return data


@dataclass
class PatientConfig:
    """Patient geometry and motion configuration.

    Attributes
    ----------
    type : str
        Geometry type: "parametrized", "3dct", or "4dct".
    dicom_directories : list of str
        Source DICOM directories for CT types.
    parameters : ParametricGeometry
        Parametrized geometry when type is "parametrized".
    scoring_bins : list of int
        Scoring grid bins (X, Y, Z).
    translation_mm : list of float
        Base translation in mm (X, Y, Z).
    rotation_deg : list of float
        Base rotation in degrees (X, Y, Z).
    use_center_as_transform_origin : bool
        If True, use image center as transform origin for motion.
    transform_sequence : list of TransformStep
        Time-dependent patient transforms.
    """
    type: str = "parametrized"
    dicom_directories: List[str] = field(default_factory=list)
    parameters: ParametricGeometry = field(default_factory=ParametricGeometry)
    scoring_bins: List[int] = field(default_factory=lambda: [25, 25, 25])
    translation_mm: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_deg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    use_center_as_transform_origin: bool = False
    transform_sequence: List[TransformStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PatientConfig:
        """Create a PatientConfig from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with patient configuration values.

        Returns
        -------
        PatientConfig
            Parsed patient configuration.
        """
        return cls(
            type=str(data.get("type", "parametrized") or "parametrized"),
            dicom_directories=list(data.get("dicom_directories", []) or []),
            parameters=ParametricGeometry.from_dict(data.get("parameters", {}) or {}),
            scoring_bins=list(data.get("scoring_bins", [25, 25, 25]) or [25, 25, 25]),
            translation_mm=list(data.get("translation_mm", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0]),
            rotation_deg=list(data.get("rotation_deg", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0]),
            use_center_as_transform_origin=bool(data.get("use_center_as_transform_origin", False) or False),
            transform_sequence=[TransformStep.from_dict(t) for t in (data.get("transform_sequence", []) or [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the patient configuration to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the patient configuration.
        """
        data = {
            "type": self.type,
            "scoring_bins": self.scoring_bins,
            "translation_mm": self.translation_mm,
            "rotation_deg": self.rotation_deg,
            "use_center_as_transform_origin": self.use_center_as_transform_origin,
            "transform_sequence": [t.to_dict() for t in self.transform_sequence],
        }
        if self.type == "parametrized":
            data["parameters"] = self.parameters.to_dict()
        else:
            data["dicom_directories"] = self.dicom_directories
        return data


@dataclass
class SimulationConfig:
    """Top-level simulation configuration model.

    Attributes
    ----------
    seed : int
        Random seed for TOPAS.
    physics : list of str
        Physics modules to enable.
    simulation_steps : int
        Number of simulation steps/phases.
    include_files : list of str
        Additional TOPAS include files.
    patient : PatientConfig
        Patient geometry and motion configuration.
    tumors : list of TumorConfig
        Tumor configurations.
    """
    seed: int = 1
    physics: List[str] = field(default_factory=list)
    simulation_steps: int = 0
    include_files: List[str] = field(default_factory=list)
    patient: PatientConfig = field(default_factory=PatientConfig)
    tumors: List[TumorConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationConfig":
        """Create a SimulationConfig from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with simulation configuration values.

        Returns
        -------
        SimulationConfig
            Parsed simulation configuration.
        """
        topas_data = data.get("topas", {}) or {}
        general_data = data.get("general", {}) or {}
        patient_data = data.get("patient", {}) or {}
        tumors_data = data.get("tumors", []) or []

        return cls(
            seed=int(topas_data.get("seed", 1) or 1),
            physics=list(topas_data.get("physics", []) or []),
            simulation_steps=int(general_data.get("simulation_steps", 0) or 0),
            include_files=list(general_data.get("include_files", []) or []),
            patient=PatientConfig.from_dict(patient_data),
            tumors=[TumorConfig.from_dict(t) for t in tumors_data],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the simulation configuration to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the simulation configuration.
        """
        return {
            "topas": {
                "seed": self.seed,
                "physics": self.physics,
            },
            "general": {
                "simulation_steps": self.simulation_steps,
                "include_files": self.include_files,
            },
            "patient": self.patient.to_dict(),
            "tumors": [t.to_dict() for t in self.tumors],
        }

    def validate(self):
        """Validate configuration consistency and required fields.

        Raises
        ------
        ValueError
            If the configuration is invalid.
        """
        errors: List[str] = []
        warnings: List[str] = []

        def warn(message: str):
            warnings.append(message)

        def is_number_like(value: Any) -> bool:
            try:
                float(value)
                return True
            except (TypeError, ValueError):
                return False

        def is_string_list(value: Any) -> bool:
            return isinstance(value, list) and all(isinstance(v, str) for v in value)

        # physics
        if not isinstance(self.physics, list) or not self.physics:
            errors.append("physics must be a non-empty list of strings")
        else:
            bad = [p for p in self.physics if not isinstance(p, str) or not p.strip()]
            if bad:
                errors.append("physics must contain only non-empty strings")
            elif len(self.physics) > 3 and all(isinstance(p, str) and len(p) == 1 for p in self.physics):
                warn("physics looks like a single string that was split into characters")

        # simulation_steps
        if not isinstance(self.simulation_steps, int):
            warn("general.simulation_steps is not an int; it was coerced by from_dict")
        if self.simulation_steps < 0:
            errors.append("general.simulation_steps must be >= 0")

        # patient type
        if self.patient.type not in VALID_GEOMETRY_TYPES:
            errors.append(f"patient.type must be one of: {', '.join(sorted(VALID_GEOMETRY_TYPES))}")

        # patient parameters ignored unless parametrized
        if self.patient.type != "parametrized":
            params = self.patient.parameters
            if params.size_mm != [100.0, 100.0, 100.0] or params.spacing_mm != [1.0, 1.0, 1.0] or params.radiodensity_hu != 0:
                warn("patient.parameters is ignored unless patient.type == 'parametrized'")
            if self.patient.dicom_directories:
                if not is_string_list(self.patient.dicom_directories):
                    errors.append("patient.dicom_directories must be a list of strings")
        else:
            if self.patient.dicom_directories:
                warn("patient.dicom_directories is ignored when patient.type == 'parametrized'")

        # vector sanity checks
        def check_vec(name: str, vec: Any, require_int: bool = False, strict: bool = True):
            if not isinstance(vec, list):
                if strict:
                    errors.append(f"{name} must be a list")
                else:
                    warn(f"{name} should be a list")
                return
            if len(vec) < 3:
                if strict:
                    errors.append(f"{name} must have at least 3 values")
                else:
                    warn(f"{name} should have at least 3 values")
                return
            if len(vec) > 3:
                warn(f"{name} has more than 3 values; extra values are ignored")
            for v in vec[:3]:
                if not is_number_like(v):
                    if strict:
                        errors.append(f"{name} values must be numeric")
                    else:
                        warn(f"{name} values should be numeric")
                    return
                if require_int and not isinstance(v, int):
                    warn(f"{name} values should be integers")

        check_vec("patient.scoring_bins", self.patient.scoring_bins, require_int=True)
        check_vec("patient.translation_mm", self.patient.translation_mm)
        check_vec("patient.rotation_deg", self.patient.rotation_deg)
        if self.patient.type == "parametrized":
            check_vec("patient.parameters.size_mm", self.patient.parameters.size_mm)
            check_vec("patient.parameters.spacing_mm", self.patient.parameters.spacing_mm)
        else:
            check_vec("patient.parameters.size_mm", self.patient.parameters.size_mm, strict=False)
            check_vec("patient.parameters.spacing_mm", self.patient.parameters.spacing_mm, strict=False)

        # dicom_directories required for CT types
        if self.patient.type in {"3dct", "4dct"}:
            if not isinstance(self.patient.dicom_directories, list) or not self.patient.dicom_directories:
                errors.append("patient.dicom_directories must be a non-empty list of strings for 3dct and 4dct geometry types")
            else:
                bad = [d for d in self.patient.dicom_directories if not isinstance(d, str) or not d.strip()]
                if bad:
                    errors.append("patient.dicom_directories must contain only non-empty strings")
                else:
                    if len(self.patient.dicom_directories) != 1:
                        errors.append("patient.dicom_directories must contain exactly one directory in the current pipeline")
                    elif self.patient.type == "4dct":
                        warn("patient.type is '4dct' but only one DICOM directory is supported; phases are generated from the single source")

        # include_files must exist when provided
        if self.include_files:
            if not is_string_list(self.include_files):
                errors.append("general.include_files must be a list of strings")
            else:
                if len(self.include_files) > 3 and all(isinstance(p, str) and len(p) == 1 for p in self.include_files):
                    warn("general.include_files looks like a single string that was split into characters")
                missing = [p for p in self.include_files if not p.strip() or not os.path.exists(p)]
                if missing:
                    errors.append("general.include_files must all exist on disk")
                else:
                    not_files = [p for p in self.include_files if not os.path.isfile(p)]
                    if not_files:
                        errors.append("general.include_files must reference files, not directories")

        # dicom_directories must exist on disk
        if self.patient.dicom_directories:
            missing = [p for p in self.patient.dicom_directories if not isinstance(p, str) or not p.strip() or not os.path.exists(p)]
            if missing:
                errors.append("patient.dicom_directories must all exist on disk")
            else:
                not_dirs = [p for p in self.patient.dicom_directories if not os.path.isdir(p)]
                if not_dirs:
                    errors.append("patient.dicom_directories must reference directories")

        # tumor checks
        for idx, tumor in enumerate(self.tumors):
            if tumor.embed_mode not in {"topas", "dicom"}:
                errors.append(f"tumors[{idx}].embed_mode must be 'topas' or 'dicom'")
            if not isinstance(tumor.topas_material, str) or not tumor.topas_material.strip():
                errors.append(f"tumors[{idx}].topas_material must be a non-empty string")
            check_vec(f"tumors[{idx}].translation_mm", tumor.translation_mm)
            check_vec(f"tumors[{idx}].rotation_deg", tumor.rotation_deg)
            check_vec(f"tumors[{idx}].radius_mm", tumor.radius_mm)
            if tumor.transform_sequence:
                times = [t.time_s for t in tumor.transform_sequence if isinstance(t, TransformStep)]
                if any(t < 0 for t in times):
                    warn(f"tumors[{idx}].transform_sequence contains negative time_s values")
                if len(times) != len(set(times)):
                    warn(f"tumors[{idx}].transform_sequence contains duplicate time_s values")
                if any(getattr(t, "shear", [0.0, 0.0, 0.0]) != [0.0, 0.0, 0.0] for t in tumor.transform_sequence):
                    warn(f"tumors[{idx}].transform_sequence.shear is ignored for tumors")

        # patient transform sequence checks
        if self.patient.transform_sequence:
            times = [t.time_s for t in self.patient.transform_sequence if isinstance(t, TransformStep)]
            if any(t < 0 for t in times):
                warn("patient.transform_sequence contains negative time_s values")
            if len(times) != len(set(times)):
                warn("patient.transform_sequence contains duplicate time_s values")
            if times and times != sorted(times):
                warn("patient.transform_sequence time_s values are not sorted")

        if errors:
            raise ValueError("Invalid configuration:\n- " + "\n- ".join(errors))
        for message in warnings:
            print(f"Warning: {message}", file=sys.stderr)

    def write_topas_config(self, output_dir: str, thread_count: int, timeline: List[float]):
        """Write TOPAS and HEC parameter files to the output directory.

        Parameters
        ----------
        output_dir : str
            Destination directory for generated files.
        thread_count : int
            Number of threads to configure in TOPAS.
        timeline : list of float
            Time points in seconds for the simulation phases.
        """
        if output_dir:
            os.makedirs(os.path.join(output_dir, "results"), exist_ok=True)

        # timeline contains exactly num_phases points.
        num_phases = len(timeline)
        # Duration in TOPAS usually defines the total time window.
        # If we have N steps, and each step is dt, total duration is N * dt.
        if num_phases > 1:
            dt = timeline[1] - timeline[0]
            duration = (timeline[-1] - timeline[0]) + dt
        else:
            duration = 1.0
        topas_timeline = timeline

        # Main Topas config
        lines = [
            "# Generated by hecTool",
            f"i:Ts/NumberOfThreads = {thread_count}",
            f"i:Ph/Default/Seed = {self.seed}",
            f"sv:Ph/Default/Modules = {len(self.physics)} " + " ".join([f'"{p}"' for p in self.physics]),
        ]
        if any([t.embed_mode == "topas" for t in self.tumors]):
            lines.append("sv:Ph/Default/LayeredMassGeometryWorlds = 1 \"TumorWorld\"")
        lines.extend([
            "",
            "# World Setup",
            "s:Ge/World/Material = \"Vacuum\"",
            "d:Ge/World/HLX = 1.0 m",
            "d:Ge/World/HLY = 1.0 m",
            "d:Ge/World/HLZ = 1.0 m",
            "",
            "d:Tf/TimelineStart = 0. s",
            f"d:Tf/TimelineEnd = {duration} s",
            f"i:Tf/NumberOfSequentialTimes = {num_phases}",
            "",
            "# Geometry Setup",
            "s:Ge/Patient/Type = \"TsDicomPatient\"",
            "s:Ge/Patient/Parent = \"World\"",
            "b:Ge/Patient/PreLoadAllMaterials = \"True\"",
            f"d:Ge/Patient/TransX = {self.patient.translation_mm[0]} mm",
            f"d:Ge/Patient/TransY = {self.patient.translation_mm[1]} mm",
            f"d:Ge/Patient/TransZ = {self.patient.translation_mm[2]} mm",
            f"d:Ge/Patient/RotX   = {self.patient.rotation_deg[0]} deg",
            f"d:Ge/Patient/RotY   = {self.patient.rotation_deg[1]} deg",
            f"d:Ge/Patient/RotZ   = {self.patient.rotation_deg[2]} deg",
        ])

        # Handle 4DCT/Time-dependent Patient DICOM
        if self.patient.type == "4dct" or num_phases > 1:#TODO: Fix 4DCT
            source_dirs = [os.path.join(output_dir, f"phase_{i}") for i in range(num_phases)]
            lines.extend([
                "s:Ge/Patient/DicomDirectory = Tf/PatientPhaseMap/Value",
                "s:Tf/PatientPhaseMap/Function = \"Step\"",
                f"dv:Tf/PatientPhaseMap/Times = {num_phases} " + " ".join([f"{t}" for t in topas_timeline]) + " s",
                f"sv:Tf/PatientPhaseMap/Values = {num_phases} " + " ".join([f'"{Path(p).absolute()}"' for p in source_dirs]),
            ])
        else:
            dicom_dir = self.patient.dicom_directories[0] if self.patient.type == "3dct" else os.path.join(output_dir, "phase_0")
            lines.append(f's:Ge/Patient/DicomDirectory = "{Path(dicom_dir).absolute()}"')

        # Add Tumors
        for i, tumor in enumerate(self.tumors):
            if tumor.embed_mode != "topas": continue

            name = f"Tumor_{i}"
            lines.extend([
                "",
                f"s:Ge/{name}/Type = \"G4Ellipsoid\"",
                f"s:Ge/{name}/Parent = \"Patient\"",
                f"s:Ge/{name}/Material = \"{tumor.topas_material}\"",
                f"b:Ge/{name}/IsParallel = \"True\"",
                f"s:Ge/{name}/ParallelWorldName = \"TumorWorld\"",
            ])

            # Apply tumor transformations
            if tumor.transform_sequence and num_phases > 1:
                from hecTool.TransformAffine import interpolate_transforms
                interp_params = interpolate_transforms(tumor.transform_sequence, timeline)

                for k, axis in enumerate(["X", "Y", "Z"]):
                    lines.extend([
                        f"d:Ge/{name}/HL{axis} = {tumor.radius_mm[k]} mm * Tf/{name}_HL{axis}/Value",
                        f"s:Tf/{name}_HL{axis}/Function = \"Step\"",
                        f"dv:Tf/{name}_HL{axis}/Times = {num_phases} " + " ".join([f"{t}" for t in topas_timeline]) + " s",
                        f"uv:Tf/{name}_HL{axis}/Values = {num_phases} " + " ".join(
                            [f"{p.scale[k]}" for p in interp_params])
                    ])
                    lines.extend([
                        f"d:Ge/{name}/Trans{axis} = {tumor.translation_mm[k]} mm + Tf/{name}_Trans{axis}/Value",
                        f"s:Tf/{name}_Trans{axis}/Function = \"Step\"",
                        f"dv:Tf/{name}_Trans{axis}/Times = {num_phases} " + " ".join([f"{t}" for t in topas_timeline]) + " s",
                        f"dv:Tf/{name}_Trans{axis}/Values = {num_phases} " + " ".join(
                            [f"{p.translation[k]}" for p in interp_params]) + " mm"
                    ])
                    lines.extend([
                        f"d:Ge/{name}/Rot{axis} = {tumor.rotation_deg[k]} deg + Tf/{name}_Rot{axis}/Value",
                        f"s:Tf/{name}_Rot{axis}/Function = \"Step\"",
                        f"dv:Tf/{name}_Rot{axis}/Times = {num_phases} " + " ".join([f"{t}" for t in topas_timeline]) + " s",
                        f"dv:Tf/{name}_Rot{axis}/Values = {num_phases} " + " ".join(
                            [f"{p.rotation_deg[k]}" for p in interp_params]) + " deg"
                    ])
            else:
                lines.extend([
                    f"d:Ge/{name}/HLX = {tumor.radius_mm[0]} mm",
                    f"d:Ge/{name}/HLY = {tumor.radius_mm[1]} mm",
                    f"d:Ge/{name}/HLZ = {tumor.radius_mm[2]} mm",
                    f"d:Ge/{name}/TransX = {tumor.translation_mm[0]} mm",
                    f"d:Ge/{name}/TransY = {tumor.translation_mm[1]} mm",
                    f"d:Ge/{name}/TransZ = {tumor.translation_mm[2]} mm",
                    f"d:Ge/{name}/RotX   = {tumor.rotation_deg[0]} deg",
                    f"d:Ge/{name}/RotY   = {tumor.rotation_deg[1]} deg",
                    f"d:Ge/{name}/RotZ   = {tumor.rotation_deg[2]} deg",
                ])

        lines.append("")
        lines.extend([f'includeFile = {os.path.basename(f)}' for f in self.include_files])

        with open(os.path.join(output_dir, "simulation.txt"), "w") as f:
            f.write("\n".join(lines))

        # HEC parameters
        lines = [
            f"s:Par/OutputDir = \"{Path(output_dir).absolute()}\"",
            "s:Par/ResultsDir = Par/OutputDir + \"/results\"",
            "",
            f"i:Par/ScoringGridXBins = {self.patient.scoring_bins[0]}",
            f"i:Par/ScoringGridYBins = {self.patient.scoring_bins[1]}",
            f"i:Par/ScoringGridZBins = {self.patient.scoring_bins[2]}"
        ]

        with open(os.path.join(output_dir, "hec_parameters.txt"), "w") as f:
            f.write("\n".join(lines))

        # Copy include files
        def copy_include_files(file: str):
            """Copy include files recursively, respecting nested includeFile lines."""
            shutil.copy(file, output_dir)
            with open(file, "r") as f:
                for line in f:
                    line_segments = [s.strip(' "\'') for s in line.strip().split("=")]
                    if len(line_segments) == 2 and line_segments[0] == "includeFile" and line_segments[1] != "hec_parameters.txt":
                        copy_include_files(os.path.join(os.path.dirname(file), line_segments[1]))

        for include_file in self.include_files:
            copy_include_files(include_file)
