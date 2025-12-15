from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_GEOMETRY_TYPES: set[str] = {"parametrized", "3dct", "4dct"}


@dataclass(slots=True)
class SimulationConfig:
    physics: list[str] = field(default_factory=list)
    particleCount: int = 1000
    geometryType: str = "parametrized"
    outputDir: str = ""
    dicomDir: str = ""
    transformSequence: list[list[float]] = field(default_factory=list)  # list of 4x4 flattened matrices (len 16)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationConfig":
        # Keep permissive parsing here; strictness lives in validate()
        return cls(
            physics=list(data.get("physics", []) or []),
            particleCount=int(data.get("particleCount", 1000)),
            geometryType=str(data.get("geometryType", "parametrized")),
            outputDir=str(data.get("outputDir", "") or ""),
            dicomDir=str(data.get("dicomDir", "") or ""),
            transformSequence=list(data.get("transformSequence", []) or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "physics": self.physics,
            "particleCount": self.particleCount,
            "geometryType": self.geometryType,
            "outputDir": self.outputDir,
            "dicomDir": self.dicomDir,
            "transformSequence": self.transformSequence,
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

        # particleCount
        if not isinstance(self.particleCount, int) or self.particleCount <= 0:
            errors.append("particleCount must be a positive integer")

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