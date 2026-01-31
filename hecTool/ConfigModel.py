from __future__ import annotations

import os.path
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Dict, Set


VALID_GEOMETRY_TYPES: Set[str] = {"parametrized", "3dct", "4dct"}


@dataclass
class ParametricGeometry:
    size_mm: List[float] = field(default_factory=lambda: [100.0, 100.0, 100.0])
    spacing_mm: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    radiodensity_hu: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ParametricGeometry:
        return cls(
            size_mm=list(data.get("size_mm", [100.0, 100.0, 100.0]) or [100.0, 100.0, 100.0]),
            spacing_mm=list(data.get("spacing_mm", [1.0, 1.0, 1.0]) or [1.0, 1.0, 1.0]),
            radiodensity_hu=int(data.get("radiodensity_hu", 0) or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "size_mm": self.size_mm,
            "spacing_mm": self.spacing_mm,
            "radiodensity_hu": self.radiodensity_hu,
        }


@dataclass
class TransformStep:
    time_s: float
    translation_mm: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_deg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    shear: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransformStep:
        return cls(
            time_s=float(data.get("time_s", 0.0)),
            translation_mm=list(data.get("translation_mm", [0.0, 0.0, 0.0])),
            rotation_deg=list(data.get("rotation_deg", [0.0, 0.0, 0.0])),
            scale=list(data.get("scale", [1.0, 1.0, 1.0])),
            shear=list(data.get("shear", [0.0, 0.0, 0.0])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_s": self.time_s,
            "translation_mm": self.translation_mm,
            "rotation_deg": self.rotation_deg,
            "scale": self.scale,
            "shear": self.shear,
        }


@dataclass
class TumorConfig:
    topas_material: str = "water"
    translation_mm: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_deg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    radius_mm: List[float] = field(default_factory=lambda: [10.0, 10.0, 10.0])
    transform_sequence: List[TransformStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TumorConfig:
        return cls(
            topas_material=str(data.get("topas_material", "water")),
            translation_mm=list(data.get("translation_mm", [0.0, 0.0, 0.0])),
            rotation_deg=list(data.get("rotation_deg", [0.0, 0.0, 0.0])),
            radius_mm=list(data.get("radius_mm", [10.0, 10.0, 10.0])),
            transform_sequence=[TransformStep.from_dict(t) for t in data.get("transform_sequence", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "topas_material": self.topas_material,
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
        return cls(
            type=str(data.get("type", "parametrized") or "parametrized"),
            dicom_directories=list(data.get("dicom_directories", []) or []),
            parameters=ParametricGeometry.from_dict(data.get("parameters", {}) or {}),
            scoring_bins=list(data.get("scoring_bins", [25, 25, 25]) or [25, 25, 25]),
            translation_mm=list(data.get("translation_mm", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0]),
            rotation_deg=list(data.get("rotation_deg", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0]),
            use_center_as_transform_origin=bool(data.get("use_center_as_transform_origin", False) or False),
            transform_sequence=[TransformStep.from_dict(t) for t in data.get("transform_sequence", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
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
    seed: int = 1
    physics: List[str] = field(default_factory=list)
    interpolation_steps: int = 0
    include_files: List[str] = field(default_factory=list)
    patient: PatientConfig = field(default_factory=PatientConfig)
    tumors: List[TumorConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationConfig":
        topas_data = data.get("topas", {}) or {}
        general_data = data.get("general", {}) or {}
        patient_data = data.get("patient", {}) or {}
        tumors_data = data.get("tumors", []) or []

        return cls(
            seed=int(topas_data.get("seed", 1) or 1),
            physics=list(topas_data.get("physics", []) or []),
            interpolation_steps=int(general_data.get("interpolation_steps", 0) or 0),
            include_files=list(general_data.get("include_files", []) or []),
            patient=PatientConfig.from_dict(patient_data),
            tumors=[TumorConfig.from_dict(t) for t in tumors_data],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topas": {
                "seed": self.seed,
                "physics": self.physics,
            },
            "general": {
                "interpolation_steps": self.interpolation_steps,
                "include_files": self.include_files,
            },
            "patient": self.patient.to_dict(),
            "tumors": [t.to_dict() for t in self.tumors],
        }

    def validate(self) -> None:
        errors: List[str] = []

        # physics
        if not isinstance(self.physics, list) or not self.physics:
            errors.append("physics must be a non-empty list of strings")
        else:
            bad = [p for p in self.physics if not isinstance(p, str) or not p.strip()]
            if bad:
                errors.append("physics must contain only non-empty strings")

        # patient type
        if self.patient.type not in VALID_GEOMETRY_TYPES:
            errors.append(f"patient.type must be one of: {', '.join(sorted(VALID_GEOMETRY_TYPES))}")

        # dicom_directories required for CT types
        if self.patient.type in {"3dct", "4dct"}:
            if not isinstance(self.patient.dicom_directories, list) or not self.patient.dicom_directories:
                errors.append("patient.dicom_directories must be a non-empty list of strings for 3dct and 4dct geometry types")
            else:
                bad = [d for d in self.patient.dicom_directories if not isinstance(d, str) or not d.strip()]
                if bad:
                    errors.append("patient.dicom_directories must contain only non-empty strings")

        if errors:
            raise ValueError("Invalid configuration:\n- " + "\n- ".join(errors))

    def write_topas_config(self, output_dir: str, thread_count: int, timeline: List[float] = None) -> None:
        if output_dir:
            os.makedirs(os.path.join(output_dir, "results"), exist_ok=True)

        # Timeline setup
        if timeline is None:
            num_phases = 1
            duration = 1.0
            timeline = [0.0]
        else:
            num_phases = len(timeline)
            duration = timeline[-1] - timeline[0] if num_phases > 1 else 1.0

        # Main Topas config
        lines = [
            "# Generated by hecTool",
            f"i:Ts/NumberOfThreads = {thread_count}",
            f"i:Ph/Default/Seed = {self.seed}",
            f"sv:Ph/Default/Modules = {len(self.physics)} " + " ".join([f'"{p}"' for p in self.physics]),
        ]
        if self.tumors:
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
        if self.patient.type == "4dct" or (self.patient.transform_sequence and num_phases > 1):
            source_dirs = [os.path.join(output_dir, f"phase_{i}") for i in range(num_phases)]
            lines.extend([
                "s:Ge/Patient/DicomDirectory = Tf/PatientPhaseMap/Value",
                "s:Tf/PatientPhaseMap/Function = \"Step\"",
                f"dv:Tf/PatientPhaseMap/Times = {num_phases} " + " ".join([f"{t}" for t in timeline]) + " s",
                f"sv:Tf/PatientPhaseMap/Values = {num_phases} " + " ".join([f'"{Path(p).absolute()}"' for p in source_dirs]),
            ])
        else:
            dicom_dir = self.patient.dicom_directories[0] if self.patient.dicom_directories else os.path.join(output_dir, "synthetic_3dct")
            lines.append(f's:Ge/Patient/DicomDirectory = "{Path(dicom_dir).absolute()}"')

        # Add Tumors
        for i, tumor in enumerate(self.tumors):
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
                        f"dv:Tf/{name}_HL{axis}/Times = {num_phases} " + " ".join([f"{t}" for t in timeline]) + " s",
                        f"uv:Tf/{name}_HL{axis}/Values = {num_phases} " + " ".join(
                            [f"{p.scale[k]}" for p in interp_params])
                    ])
                    lines.extend([
                        f"d:Ge/{name}/Trans{axis} = {tumor.translation_mm[k]} mm + Tf/{name}_Trans{axis}/Value",
                        f"s:Tf/{name}_Trans{axis}/Function = \"Step\"",
                        f"dv:Tf/{name}_Trans{axis}/Times = {num_phases} " + " ".join([f"{t}" for t in timeline]) + " s",
                        f"dv:Tf/{name}_Trans{axis}/Values = {num_phases} " + " ".join(
                            [f"{p.translation[k]}" for p in interp_params]) + " mm"
                    ])
                    lines.extend([
                        f"d:Ge/{name}/Rot{axis} = {tumor.rotation_deg[k]} deg + Tf/{name}_Rot{axis}/Value",
                        f"s:Tf/{name}_Rot{axis}/Function = \"Step\"",
                        f"dv:Tf/{name}_Rot{axis}/Times = {num_phases} " + " ".join([f"{t}" for t in timeline]) + " s",
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
        def copy_include_files(file: str) -> None:
            shutil.copy(file, output_dir)
            with open(file, "r") as f:
                for line in f:
                    line_segments = [s.strip(' "\'') for s in line.strip().split("=")]
                    if len(line_segments) == 2 and line_segments[0] == "includeFile" and line_segments[1] != "hec_parameters.txt":
                        copy_include_files(os.path.join(os.path.dirname(file), line_segments[1]))

        for include_file in self.include_files:
            copy_include_files(include_file)
