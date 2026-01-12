from __future__ import annotations

import os.path
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_GEOMETRY_TYPES: set[str] = {"parametrized", "3dct", "4dct"}


@dataclass(slots=True)
class MaterialConfig:
    name: str = "water"
    hu: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "hu": self.hu
        }


@dataclass(slots=True)
class ParametricGeometry:
    size_mm: list[float] = field(default_factory=lambda: [100.0, 100.0, 100.0])
    spacing_mm: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    material: MaterialConfig = field(default_factory=MaterialConfig)


@dataclass(slots=True)
class Placement:
    translation_mm: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_deg: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass(slots=True)
class SimulationConfig:
    seed: int = 1
    physics: list[str] = field(default_factory=list)
    geometryType: str = "parametrized"
    outputDir: str = ""
    dicomDirs: list[str] = field(default_factory=list)
    transformSequence: list[list[float]] = field(default_factory=list)  # list of 4x4 flattened matrices (len 16)
    includeFiles: list[str] = field(default_factory=list)
    scoringBins: list[int] = field(default_factory=list)
    parametricGeometry: ParametricGeometry = field(default_factory=ParametricGeometry)
    placement: Placement = field(default_factory=Placement)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationConfig":
        # Parsing nested objects
        pg_data = data.get("parametricGeometry", {})
        mat_data = pg_data.get("material", {})
        placement_data = data.get("placement", {})

        return cls(
            seed=int(data.get("seed", 1) or 1),
            physics=list(data.get("physics", []) or []),
            geometryType=str(data.get("geometryType", "parametrized") or "parametrized"),
            outputDir=str(data.get("outputDirectory", "output") or "output"),
            dicomDirs=list(data.get("dicomDirectories", []) or []),
            transformSequence=list(data.get("transformSequence", []) or []),
            includeFiles=list(data.get("includeFiles", []) or []),
            scoringBins=list(data.get("scoringBins", [10, 10, 10]) or [10, 10, 10]),
            parametricGeometry=ParametricGeometry(
                size_mm=list(pg_data.get("size_mm", [100.0, 100.0, 100.0]) or [100.0, 100.0, 100.0]),
                spacing_mm=list(pg_data.get("spacing_mm", [1.0, 1.0, 1.0]) or [1.0, 1.0, 1.0]),
                material=MaterialConfig(
                    name=str(mat_data.get("name", "water") or "water"),
                    hu=float(mat_data.get("hu", 0.0) or 0.0)
                )
            ),
            placement=Placement(
                translation_mm=list(placement_data.get("translation_mm", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0]),
                rotation_deg=list(placement_data.get("rotation_deg", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0])
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "physics": self.physics,
            "geometryType": self.geometryType,
            "outputDirectory": self.outputDir,
            "dicomDirectories": self.dicomDirs,
            "transformSequence": self.transformSequence,
            "includeFiles": self.includeFiles,
            "scoringBins": self.scoringBins,
            "parametricGeometry": {
                "size_mm": self.parametricGeometry.size_mm,
                "spacing_mm": self.parametricGeometry.spacing_mm,
                "material": {
                    "name": self.parametricGeometry.material.name,
                    "hu": self.parametricGeometry.material.hu
                }
            },
            "placement": {
                "translation_mm": self.placement.translation_mm,
                "rotation_deg": self.placement.rotation_deg
            }
        }

    def validate(self) -> None:
        errors: list[str] = []

        # physics
        if not isinstance(self.physics, list) or not self.physics:
            errors.append("physics must be a non-empty list of strings")
        else:
            bad = [p for p in self.physics if not isinstance(p, str) or not p.strip()]
            if bad:
                errors.append("physics must contain only non-empty strings")

        # geometryType
        if self.geometryType not in VALID_GEOMETRY_TYPES:
            errors.append(f"geometryType must be one of: {', '.join(sorted(VALID_GEOMETRY_TYPES))}")

        # outputDir (optional strictness: require existence)
        if self.outputDir:
            p = Path(self.outputDir)
            if not p.exists():
                errors.append(f"outputDir does not exist: {self.outputDir}")
            elif not p.is_dir():
                errors.append(f"outputDir is not a directory: {self.outputDir}")

        # dicomDir required for CT types
        if self.geometryType in {"3dct", "4dct"}:
            if not isinstance(self.dicomDirs, list) or not self.dicomDirs:
                errors.append("dicomDirectories must be a non-empty list of strings for 3dct and 4dct geometry types")
            else:
                bad = [d for d in self.dicomDirs if not isinstance(d, str) or not d.strip()]
                if bad:
                    errors.append("dicomDirectories must contain only non-empty strings")

        # transformSequence: enforce “truth” format early
        if not isinstance(self.transformSequence, list):
            errors.append("transformSequence must be a list")
        else:
            for i, m in enumerate(self.transformSequence):
                if not (isinstance(m, list) and len(m) == 16 and all(isinstance(x, (int, float)) for x in m)):
                    errors.append(f"transformSequence[{i}] must be a list of 16 numbers (flattened 4x4 matrix)")

        if errors:
            raise ValueError("Invalid configuration:\n- " + "\n- ".join(errors))

    def write_topas_config(self, thread_count: int) -> None:
        # Main Topas config
        lines = [
            "# Generated by hecTool",
            f"i:Ph/Default/NumberOfThreads = {thread_count}",
            f"i:Ph/Default/Seed = {self.seed}",
            f"sv:Ph/Default/Modules = {len(self.physics)} " + " ".join([f'"{p}"' for p in self.physics]),
            "",
            "# World Setup", #TODO: Dynamically calculate required world size based on geometry
            's:Ge/World/Material = "Vacuum"',
            "d:Ge/World/HLX = 15.0 m",
            "d:Ge/World/HLY = 15.0 m",
            "d:Ge/World/HLZ = 15.0 m",
            "",
            "# Geometry Setup",
            's:Ge/Patient/Type = "TsDicomPatient"',
            's:Ge/Patient/Parent = "World"',
            'b:Ge/Patient/PreLoadAllMaterials = "True"',
            f"d:Ge/Patient/TransX = {self.placement.translation_mm[0]} mm",
            f"d:Ge/Patient/TransY = {self.placement.translation_mm[1]} mm",
            f"d:Ge/Patient/TransZ = {self.placement.translation_mm[2]} mm",
            f"d:Ge/Patient/RotX   = {self.placement.rotation_deg[0]} deg",
            f"d:Ge/Patient/RotY   = {self.placement.rotation_deg[1]} deg",
            f"d:Ge/Patient/RotZ   = {self.placement.rotation_deg[2]} deg"
        ]

        if self.transformSequence or self.geometryType == "4dct":
            source_dirs = self.dicomDirs
            if self.transformSequence:
                source_dirs = [os.path.join(self.outputDir, f"phase_{i}") for i in range(len(self.transformSequence))]
            num_phases = len(source_dirs)
            lines.extend([
                "d:Tf/TimelineStart = 0. s",
                f"d:Tf/TimelineEnd = {num_phases - 1} s",
                f"i:Tf/NumberOfSequentialTimes = {num_phases}",
                's:Ge/Patient/DicomDirectory = Tf/PhaseMap/Value',
                's:Tf/PhaseMap/Function = "Step"',
                f"dv:Tf/PhaseMap/Times = {num_phases} " +
                " ".join([f"{i}" for i in range(num_phases)]) + " s",
                f"sv:Tf/PhaseMap/Values = {num_phases} " +
                " ".join([f'"{Path(p).absolute()}"' for p in source_dirs]),
                ""
            ])
        else:
            dicom_dir = self.dicomDirs[0] if self.dicomDirs else os.path.join(self.outputDir, "synthetic_3dct")
            lines.append(f's:Ge/Patient/DicomDirectory = "{Path(dicom_dir).absolute()}"\n')

        lines.extend([f'includeFile = {os.path.basename(f)}' for f in self.includeFiles])

        with open(os.path.join(self.outputDir, "simulation.txt"), "w") as f:
            f.write("\n".join(lines))

        # HEC parameters
        lines = [
            f's:Par/OutputDir = "{Path(self.outputDir).absolute()}"',
            "",
            f"i:Par/ScoringGridXBins = {self.scoringBins[0]}",
            f"i:Par/ScoringGridYBins = {self.scoringBins[1]}",
            f"i:Par/ScoringGridZBins = {self.scoringBins[2]}"
        ]

        with open(os.path.join(self.outputDir, "hec_parameters.txt"), "w") as f:
            f.write("\n".join(lines))

        # Copy include files
        def copy_include_files(file: str) -> None:
            shutil.copy(file, self.outputDir)
            with open(file, "r") as f:
                for line in f:
                    line_segments = [s.strip(' "\'') for s in line.strip().split("=")]
                    if len(line_segments) == 2 and line_segments[0] == "includeFile" and line_segments[1] != "hec_parameters.txt":
                        copy_include_files(os.path.join(os.path.dirname(file), line_segments[1]))

        for include_file in self.includeFiles:
            copy_include_files(include_file)
