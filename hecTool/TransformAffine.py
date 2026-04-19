from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Tuple, List, TYPE_CHECKING

import numpy as np

# Avoids circular dependency
if TYPE_CHECKING:
    from hecTool.ConfigModel import TransformStep


@dataclass(frozen=True)
class TransformParams:
    translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    shear: Tuple[float, float, float] = (0.0, 0.0, 0.0)


def params_to_flat_4x4(params: TransformParams) -> List[float]:
    tx, ty, tz = params.translation
    rx, ry, rz = params.rotation_deg
    sx, sy, sz = params.scale
    shxy, shxz, shyz = params.shear

    rx, ry, rz = math.radians(rx), math.radians(ry), math.radians(rz)

    trans = np.array(
        [[1, 0, 0, tx],
         [0, 1, 0, ty],
         [0, 0, 1, tz],
         [0, 0, 0, 1]],
        dtype=float,
    )

    rotx = np.array(
        [[1, 0, 0, 0],
         [0, math.cos(rx), -math.sin(rx), 0],
         [0, math.sin(rx), math.cos(rx), 0],
         [0, 0, 0, 1]],
        dtype=float,
    )

    roty = np.array(
        [[math.cos(ry), 0, math.sin(ry), 0],
         [0, 1, 0, 0],
         [-math.sin(ry), 0, math.cos(ry), 0],
         [0, 0, 0, 1]],
        dtype=float,
    )

    rotz = np.array(
        [[math.cos(rz), -math.sin(rz), 0, 0],
         [math.sin(rz), math.cos(rz), 0, 0],
         [0, 0, 1, 0],
         [0, 0, 0, 1]],
        dtype=float,
    )

    shear = np.array(
        [[1, shxy, shxz, 0],
         [0, 1, shyz, 0],
         [0, 0, 1, 0],
         [0, 0, 0, 1]],
        dtype=float,
    )

    scale = np.array(
        [[sx, 0, 0, 0],
         [0, sy, 0, 0],
         [0, 0, sz, 0],
         [0, 0, 0, 1]],
        dtype=float,
    )

    matrix = trans @ rotz @ roty @ rotx @ shear @ scale
    return matrix.flatten().tolist()


def interpolate_transforms(sequence: List[TransformStep], target_times: Iterable[float]) -> List[TransformParams]:
    """Interpolate a transform sequence at target time points."""
    if not sequence:
        return [TransformParams() for _ in target_times]

    # Sort sequence by time
    sorted_seq = sorted(sequence, key=lambda x: x.time_s)
    times = [s.time_s for s in sorted_seq]

    results = []
    for t in target_times:
        if t <= times[0]:
            s = sorted_seq[0]
            results.append(TransformParams(
                tuple(s.translation_mm), tuple(s.rotation_deg), tuple(s.scale), tuple(s.shear)
            ))
        elif t >= times[-1]:
            s = sorted_seq[-1]
            results.append(TransformParams(
                tuple(s.translation_mm), tuple(s.rotation_deg), tuple(s.scale), tuple(s.shear)
            ))
        else:
            # Linear interpolation
            idx = next(i for i, time in enumerate(times) if time > t)
            t0, t1 = times[idx - 1], times[idx]
            s0, s1 = sorted_seq[idx - 1], sorted_seq[idx]
            f = (t - t0) / (t1 - t0)

            interp_trans = tuple(s0.translation_mm[i] + f * (s1.translation_mm[i] - s0.translation_mm[i]) for i in range(3))
            interp_rot = tuple(s0.rotation_deg[i] + f * (s1.rotation_deg[i] - s0.rotation_deg[i]) for i in range(3))
            interp_scale = tuple(s0.scale[i] + f * (s1.scale[i] - s0.scale[i]) for i in range(3))
            interp_shear = tuple(s0.shear[i] + f * (s1.shear[i] - s0.shear[i]) for i in range(len(s0.shear)))

            results.append(TransformParams(interp_trans, interp_rot, interp_scale, interp_shear))

    return results