#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

import numpy as np
import pydicom

DEFAULT_SIMULATION_MACRO = Path(
    "/Users/pb438/applications/hec-dose-distribution/TOPAS_macros/dicom_input/simulation.txt"
)
DEFAULT_PARTICLE_SOURCES = Path(
    "/Users/pb438/applications/hec-dose-distribution/TOPAS_macros/dicom_input/particle_sources.txt"
)
DEFAULT_RTSTRUCT = Path(
    "/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RS_patched_to_converted_CT.dcm"
)
PTV_NAME_PATTERNS = ["PTV", "ptv"]


def parse_simulation_macro(simulation_macro_path):
    values = {
        "DicomDirectory": None,
        "TransX": 0.0,
        "TransY": 0.0,
        "TransZ": 0.0,
        "RotX": 0.0,
        "RotY": 0.0,
        "RotZ": 0.0,
    }

    for line in simulation_macro_path.read_text().splitlines():
        if ":Ge/Patient/DicomDirectory" in line:
            m = re.search(r"Ge/Patient/DicomDirectory\s*=\s*\"(.+?)\"", line)
            if m:
                values["DicomDirectory"] = Path(m.group(1))
        else:
            m = re.match(r"^[isdubv]:Ge/Patient/Trans([XYZ])\s*=\s*([-+0-9.eE]+)", line)
            if m:
                values[f"Trans{m.group(1)}"] = float(m.group(2))
            m = re.match(r"^[isdubv]:Ge/Patient/Rot([XYZ])\s*=\s*([-+0-9.eE]+)", line)
            if m:
                values[f"Rot{m.group(1)}"] = float(m.group(2))

    return values


def parse_particle_sources(particle_sources_path):
    data = {
        "BeamPos/TransX": None,
        "BeamPos/TransY": None,
        "BeamPos/TransZ": None,
        "BeamPos/RotX": 0.0,
        "BeamPos/RotY": 0.0,
        "BeamPos/RotZ": 0.0,
        "BeamPositionSpreadX": None,
        "BeamPositionSpreadY": None,
        "BeamPositionCutoffX": None,
        "BeamPositionCutoffY": None,
        "BeamPositionCutoffShape": None,
    }

    for line in particle_sources_path.read_text().splitlines():
        m = re.match(r"^[isdbuv]:(Ge/BeamPos/Trans[XYZ])\s*=\s*([-+0-9.eE]+)", line)
        if m:
            data[m.group(1).split("Ge/BeamPos/")[1]] = float(m.group(2))
            continue
        m = re.match(r"^[isdbuv]:(Ge/BeamPos/Rot[XYZ])\s*=\s*([-+0-9.eE]+)", line)
        if m:
            data[m.group(1).split("Ge/BeamPos/")[1]] = float(m.group(2))
            continue
        m = re.match(r"^[isdbuv]:(So/Beam/BeamPositionSpread[XY])\s*=\s*([-+0-9.eE]+)\s*cm", line)
        if m:
            data[m.group(1).split("So/Beam/")[1]] = float(m.group(2))
            continue
        m = re.match(r"^[isdbuv]:(So/Beam/BeamPositionCutoff[XY])\s*=\s*([-+0-9.eE]+)\s*cm", line)
        if m:
            data[m.group(1).split("So/Beam/")[1]] = float(m.group(2))
            continue
        m = re.match(r"^[isdbuv]:(So/Beam/BeamPositionCutoffShape)\s*=\s*\"(.+?)\"", line)
        if m:
            data["BeamPositionCutoffShape"] = m.group(2)

    return data


def load_ptv_bbox(rtstruct_path):
    ds = pydicom.dcmread(rtstruct_path, stop_before_pixels=True, force=True)
    roi_name_by_number = {}
    for roi in getattr(ds, "StructureSetROISequence", []):
        roi_number = getattr(roi, "ROINumber", None)
        if roi_number is None:
            continue
        roi_name_by_number[int(roi_number)] = getattr(roi, "ROIName", "")

    def is_ptv_name(name):
        return any(pattern in name for pattern in PTV_NAME_PATTERNS)

    points = []
    for roi_contour in getattr(ds, "ROIContourSequence", []):
        roi_number = getattr(roi_contour, "ReferencedROINumber", None)
        roi_name = roi_name_by_number.get(int(roi_number), "") if roi_number is not None else ""
        if not is_ptv_name(roi_name):
            continue

        for contour in getattr(roi_contour, "ContourSequence", []):
            coords = [float(x) for x in contour.ContourData]
            if len(coords) % 3 != 0:
                continue
            pts = np.array(coords, dtype=float).reshape(-1, 3)
            points.append(pts)

    if not points:
        return None

    all_points = np.vstack(points)
    return {
        "points": all_points,
        "bbox_min": all_points.min(axis=0),
        "bbox_max": all_points.max(axis=0),
        "center": 0.5 * (all_points.min(axis=0) + all_points.max(axis=0)),
    }


def rx(angle_deg):
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(angle_deg):
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(angle_deg):
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rotation_matrix_xyz(rot_deg):
    return rz(rot_deg[2]) @ ry(rot_deg[1]) @ rx(rot_deg[0])


def load_ct_slices(ct_dir):
    items = []
    for path in sorted(ct_dir.iterdir()):
        if not path.is_file():
            continue
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True, force=True)
            if getattr(ds, "Modality", None) == "CT":
                items.append((path, ds))
        except Exception:
            pass
    if not items:
        raise RuntimeError(f"No CT slices found in {ct_dir}")
    return items


def ct_corners(ds):
    ipp = np.array([float(x) for x in ds.ImagePositionPatient], dtype=float)
    iop = np.array([float(x) for x in ds.ImageOrientationPatient], dtype=float)
    row_dir = iop[:3]
    col_dir = iop[3:]
    rows = int(ds.Rows)
    cols = int(ds.Columns)
    row_spacing = float(ds.PixelSpacing[0])
    col_spacing = float(ds.PixelSpacing[1])
    corners = []
    for r in [0, rows - 1]:
        for c in [0, cols - 1]:
            corners.append(ipp + row_dir * c * col_spacing + col_dir * r * row_spacing)
    return np.array(corners)


def ray_intersects_aabb(origin, direction, box_min, box_max):
    direction = direction / np.linalg.norm(direction)
    inv = np.empty_like(direction)
    eps = 1e-12
    for i in range(3):
        inv[i] = np.inf if abs(direction[i]) < eps else 1.0 / direction[i]
    t1 = (box_min - origin) * inv
    t2 = (box_max - origin) * inv
    tmin = np.maximum.reduce(np.minimum(t1, t2))
    tmax = np.minimum.reduce(np.maximum(t1, t2))
    hit = tmax >= max(tmin, 0.0)
    return hit, tmin, tmax


def point_to_ray_distance(point, origin, direction):
    direction = direction / np.linalg.norm(direction)
    v = point - origin
    proj = np.dot(v, direction)
    closest = origin + proj * direction
    return np.linalg.norm(point - closest)


def main():
    parser = argparse.ArgumentParser(description="Check TOPAS beam geometry against synthetic CT and RTSTRUCT PTV.")
    parser.add_argument("--simulation-macro", default=DEFAULT_SIMULATION_MACRO, type=Path)
    parser.add_argument("--particle-sources", default=DEFAULT_PARTICLE_SOURCES, type=Path)
    parser.add_argument("--rtstruct", default=DEFAULT_RTSTRUCT, type=Path)
    parser.add_argument("--beam-component-axis", default="+Z", choices=["+Z", "-Z", "+X", "-X", "+Y", "-Y"], help="Local component axis used by the TOPAS beam component.")
    args = parser.parse_args()

    sim = parse_simulation_macro(args.simulation_macro)
    ps = parse_particle_sources(args.particle_sources)

    ct_dir = sim["DicomDirectory"] or Path(
        "/Users/pb438/applications/hec-dose-distribution/TOPAS_simulation_data/dataset_3dct/phase_0"
    )
    ct_items = load_ct_slices(ct_dir)
    all_corners = np.vstack([ct_corners(ds) for _, ds in ct_items])
    ct_min = all_corners.min(axis=0)
    ct_max = all_corners.max(axis=0)
    ct_center = 0.5 * (ct_min + ct_max)

    patient_translation = np.array([sim["TransX"], sim["TransY"], sim["TransZ"]], dtype=float)
    patient_rotation = np.array([sim["RotX"], sim["RotY"], sim["RotZ"]], dtype=float)
    R_patient = rotation_matrix_xyz(patient_rotation)
    ct_world = (R_patient @ all_corners.T).T + patient_translation
    ct_world_min = ct_world.min(axis=0)
    ct_world_max = ct_world.max(axis=0)
    ct_world_center = 0.5 * (ct_world_min + ct_world_max)

    source_origin = np.array([ps["TransX"], ps["TransY"], ps["TransZ"]], dtype=float)
    source_rotation = np.array([ps["RotX"], ps["RotY"], ps["RotZ"]], dtype=float)
    R_beam = rotation_matrix_xyz(source_rotation)
    local_axis = {
        "+Z": np.array([0.0, 0.0, 1.0]),
        "-Z": np.array([0.0, 0.0, -1.0]),
        "+X": np.array([1.0, 0.0, 0.0]),
        "-X": np.array([-1.0, 0.0, 0.0]),
        "+Y": np.array([0.0, 1.0, 0.0]),
        "-Y": np.array([0.0, -1.0, 0.0]),
    }[args.beam_component_axis]
    source_direction = R_beam @ local_axis

    print("Simulation macro:")
    print("  DicomDirectory:", ct_dir)
    print("  Patient Trans:", patient_translation.tolist())
    print("  Patient Rot:", patient_rotation.tolist())

    print("\nParticle sources:")
    print("  Beam anchor:", source_origin.tolist())
    print("  Beam rotation:", source_rotation.tolist())
    print("  Beam direction:", source_direction.tolist())
    print("  BeamPositionSpreadX:", ps["BeamPositionSpreadX"], "cm")
    print("  BeamPositionSpreadY:", ps["BeamPositionSpreadY"], "cm")
    print("  BeamPositionCutoffShape:", ps["BeamPositionCutoffShape"])
    print("  BeamPositionCutoffX:", ps["BeamPositionCutoffX"], "cm")
    print("  BeamPositionCutoffY:", ps["BeamPositionCutoffY"], "cm")

    hit_ct, t_enter_ct, t_exit_ct = ray_intersects_aabb(source_origin, source_direction, ct_world_min, ct_world_max)
    print("\nCT world bounds [mm]:")
    print("  min:", ct_world_min.tolist())
    print("  max:", ct_world_max.tolist())
    print("  center:", ct_world_center.tolist())
    print("\nBeam ray test:")
    print("  Intersects CT bounding box:", hit_ct)
    print("  t_enter:", t_enter_ct)
    print("  t_exit:", t_exit_ct)
    print("  Distance from CT center to beam axis [mm]:", point_to_ray_distance(ct_world_center, source_origin, source_direction))

    if args.rtstruct.exists():
        ptv = load_ptv_bbox(args.rtstruct)
        if ptv is None:
            print("\nWARNING: No PTV contours found in RTSTRUCT.")
        else:
            ptv_world_min = (R_patient @ ptv["bbox_min"]) + patient_translation
            ptv_world_max = (R_patient @ ptv["bbox_max"]) + patient_translation
            ptv_world_center = (R_patient @ ptv["center"]) + patient_translation
            hit_ptv, tenter_ptv, texit_ptv = ray_intersects_aabb(
                source_origin, source_direction, ptv_world_min, ptv_world_max
            )

            print("\nPTV bounding box [mm]:")
            print("  min:", ptv_world_min.tolist())
            print("  max:", ptv_world_max.tolist())
            print("  center:", ptv_world_center.tolist())
            print("  size:", (ptv_world_max - ptv_world_min).tolist())
            print("\nBeam/PTV test:")
            print("  Intersects PTV bounding box:", hit_ptv)
            print("  t_enter:", tenter_ptv)
            print("  t_exit:", texit_ptv)
            print("  Distance from PTV center to beam axis [mm]:", point_to_ray_distance(ptv_world_center, source_origin, source_direction))
            if hit_ptv:
                print("  Result: beam axis passes through the PTV bounding box.")
            else:
                print("  Result: beam axis misses the PTV bounding box.")
    else:
        print("\nNo RTSTRUCT file found; only CT geometry was tested.")

    if not hit_ct:
        print("\nDIAGNOSIS: The beam axis does not intersect the CT geometry. Check the beam anchor and/or patient transform.")
    print("\nDone.")


if __name__ == "__main__":
    main()
