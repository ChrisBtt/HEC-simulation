from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_GEOMETRY_TYPES: set[str] = {"parametrized", "3dct", "4dct"}


@dataclass(slots=True)
class MaterialConfig:
    name: str = "water"
    hu: float = 0.0


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
    particleSourceFile: str = ""
    parametricGeometry: ParametricGeometry = field(default_factory=ParametricGeometry)
    placement: Placement = field(default_factory=Placement)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationConfig":
        # Parsing nested objects
        pg_data = data.get("parametricGeometry", {})
        mat_data = pg_data.get("material", {})
        placement_data = data.get("placement", {})

        return cls(
            seed=int(data.get("seed", 1)),
            physics=list(data.get("physics", []) or []),
            geometryType=str(data.get("geometryType", "parametrized")),
            outputDir=str(data.get("outputDir", "") or ""),
            dicomDirs=list(data.get("dicomDirs", []) or data.get("dicomDir", []) or []),
            transformSequence=list(data.get("transformSequence", []) or []),
            particleSourceFile=str(data.get("particleSourceFile", "") or ""),
            parametricGeometry=ParametricGeometry(
                size_mm=list(pg_data.get("size_mm", [100.0, 100.0, 100.0])),
                spacing_mm=list(pg_data.get("spacing_mm", [1.0, 1.0, 1.0])),
                material=MaterialConfig(
                    name=str(mat_data.get("name", "water")),
                    hu=float(mat_data.get("hu", 0.0))
                )
            ),
            placement=Placement(
                translation_mm=list(placement_data.get("translation_mm", [0.0, 0.0, 0.0])),
                rotation_deg=list(placement_data.get("rotation_deg", [0.0, 0.0, 0.0]))
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "physics": self.physics,
            "geometryType": self.geometryType,
            "outputDir": self.outputDir,
            "dicomDirs": self.dicomDirs,
            "transformSequence": self.transformSequence,
            "particleSourceFile": self.particleSourceFile,
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
            if not self.dicomDir.strip():
                errors.append("dicomDir is required when geometryType is 3dct or 4dct")

        # transformSequence: enforce “truth” format early
        if not isinstance(self.transformSequence, list):
            errors.append("transformSequence must be a list")
        else:
            for i, m in enumerate(self.transformSequence):
                if not (isinstance(m, list) and len(m) == 16 and all(isinstance(x, (int, float)) for x in m)):
                    errors.append(f"transformSequence[{i}] must be a list of 16 numbers (flattened 4x4 matrix)")

        if errors:
            raise ValueError("Invalid configuration:\n- " + "\n- ".join(errors))

    def write_topas_config(self, filepath: str, threadCount: int) -> None:
        """Generates a TOPAS parameter file pointing to the generated DICOMs."""
        out_path = Path(self.outputDir) if self.outputDir else Path("output")

        lines = [
            "# Generated by hecTool",
            f"i:Ph/Default/NumberOfThreads = {threadCount}",
            f"i:Ph/Default/Seed = {self.seed}",
            f"sv:Ph/Default/Modules = {len(self.physics)} " + " ".join([f'"{p}"' for p in self.physics]),
            f"includeFile: {self.particleSourceFile}",
            "",
            "# Geometry Setup",
            's:Ge/Patient/Type = "TsDicomPatient"',
            's:Ge/Patient/Parent = "World"',
        ]

        # Case A: It's a 4DCT (Multiple phases generated)
        if self.transformSequence:
            num_phases = len(self.transformSequence)
            lines.extend([
                f"i:Tf/NumberOfSequentialTimeSteps = {num_phases}",
                's:Tf/TimelineInterpolation = "Step"',
                's:Ge/Patient/DicomDirectory = Tf/PhaseMap/Value',
                f"sv:Tf/PhaseMap/Values = {num_phases} " +
                " ".join([f'"{out_path.absolute() / f"phase_{i}"}"' for i in range(num_phases)]),
            ])

        # Case B: It's a Static CT (Either user-provided or synthetic)
        else:
            # If it was parametrized, SimulationRunner put it here:
            if self.geometryType == "parametrized":
                dicom_path = out_path.absolute() / "synthetic_3dct"
            else:
                dicom_path = Path(self.dicomDirs[0]).absolute()

            lines.append(f's:Ge/Patient/DicomDirectory = "{dicom_path}"')

        with open(filepath, "w") as f:
            f.write("\n".join(lines))