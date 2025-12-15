from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True, slots=True)
class TransformParams:
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    shear: tuple[float, float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def params_to_flat_4x4(params: TransformParams) -> list[float]:
    tx, ty, tz = params.translation
    rx, ry, rz = params.rotation_deg
    sx, sy, sz = params.scale
    shxy, shyx, shxz, shzx, shyz, shzy = params.shear

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

    scale = np.array(
        [[sx, 0, 0, 0],
         [0, sy, 0, 0],
         [0, 0, sz, 0],
         [0, 0, 0, 1]],
        dtype=float,
    )

    shear = np.array(
        [[1, shxy, shxz, 0],
         [shyx, 1, shyz, 0],
         [shzx, shzy, 1, 0],
         [0, 0, 0, 1]],
        dtype=float,
    )

    matrix = trans @ rotz @ roty @ rotx @ scale @ shear
    return matrix.flatten().tolist()


def flat_4x4_to_params(matrix_flat: Iterable[float]) -> TransformParams:
    m = np.array(list(matrix_flat), dtype=float).reshape(4, 4)

    tx = float(m[0, 3])
    ty = float(m[1, 3])
    tz = float(m[2, 3])

    sx = float(np.sqrt(m[0, 0] ** 2 + m[0, 1] ** 2 + m[0, 2] ** 2))
    sy = float(np.sqrt(m[1, 0] ** 2 + m[1, 1] ** 2 + m[1, 2] ** 2))
    sz = float(np.sqrt(m[2, 0] ** 2 + m[2, 1] ** 2 + m[2, 2] ** 2))

    r = m[:3, :3].copy()
    if sx != 0:
        r[:, 0] /= sx
    if sy != 0:
        r[:, 1] /= sy
    if sz != 0:
        r[:, 2] /= sz

    ry = math.atan2(r[0, 2], math.sqrt(r[0, 0] ** 2 + r[0, 1] ** 2))
    rx = math.atan2(-r[1, 2], r[2, 2])
    rz = math.atan2(-r[0, 1], r[0, 0])

    rx, ry, rz = math.degrees(rx), math.degrees(ry), math.degrees(rz)

    shxy = float(m[0, 1] / sy) if sy != 0 else 0.0
    shxz = float(m[0, 2] / sz) if sz != 0 else 0.0
    shyx = float(m[1, 0] / sx) if sx != 0 else 0.0
    shyz = float(m[1, 2] / sz) if sz != 0 else 0.0
    shzx = float(m[2, 0] / sx) if sx != 0 else 0.0
    shzy = float(m[2, 1] / sy) if sy != 0 else 0.0

    return TransformParams(
        translation=(tx, ty, tz),
        rotation_deg=(rx, ry, rz),
        scale=(sx, sy, sz),
        shear=(shxy, shyx, shxz, shzx, shyz, shzy),
    )