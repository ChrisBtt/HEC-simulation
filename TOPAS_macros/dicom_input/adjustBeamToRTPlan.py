#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

import numpy as np
import pydicom

DEFAULT_RTPLAN = Path(
    "/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RP_patched_to_converted_CT.dcm"
)
DEFAULT_RTSTRUCT = Path(
    "/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RS_patched_to_converted_CT.dcm"
)
DEFAULT_PARTICLE_SOURCES = Path(
    "/Users/pb438/applications/hec-dose-distribution/TOPAS_macros/dicom_input/particle_sources.txt"
)
DEFAULT_SIMULATION_MACRO = Path(
    "/Users/pb438/applications/hec-dose-distribution/TOPAS_macros/dicom_input/simulation.txt"
)
PTV_NAME_PATTERNS = ["PTV", "ptv"]


def parse_float(value):
    value = value.split("#", 1)[0].strip()
    value = value.replace("mm", "").replace("deg", "").strip()
    return float(value)


def parse_simulation_patient_translation(simulation_macro_path):
    translation = np.zeros(3, dtype=float)
    if not simulation_macro_path.exists():
        return translation

    for line in simulation_macro_path.read_text().splitlines():
        match = re.match(r"^[isdubv]:Ge/Patient/Trans([XYZ])\s*=\s*([0-9.+\-eE]+).*$", line)
        if not match:
            continue
        axis = match.group(1)
        value = float(match.group(2))
        translation["XYZ".index(axis)] = value

    return translation


def load_rtplan_beam(rtplan_path, beam_number=1):
    ds = pydicom.dcmread(rtplan_path, stop_before_pixels=True, force=True)
    beam_seq = getattr(ds, "BeamSequence", None) or getattr(ds, "IonBeamSequence", None)
    if beam_seq is None:
        raise ValueError("No BeamSequence or IonBeamSequence found in RTPLAN.")

    selected_beam = None
    id_field = "BeamNumber" if hasattr(beam_seq[0], "BeamNumber") else "IonBeamNumber"
    for beam in beam_seq:
        if getattr(beam, id_field) == beam_number:
            selected_beam = beam
            break
    if selected_beam is None:
        selected_beam = beam_seq[0]

    cps = getattr(selected_beam, "ControlPointSequence", None) or getattr(
        selected_beam, "IonControlPointSequence", None
    )
    if cps is None or len(cps) == 0:
        raise ValueError("RTPLAN beam has no control points.")

    cp0 = cps[0]
    params = {
        "BeamNumber": getattr(selected_beam, id_field, None),
        "BeamName": getattr(selected_beam, "BeamName", None),
        "RadiationType": getattr(selected_beam, "RadiationType", None),
        "GantryAngle": getattr(cp0, "GantryAngle", None),
        "PatientSupportAngle": getattr(cp0, "PatientSupportAngle", None),
        "BeamLimitingDeviceAngle": getattr(cp0, "BeamLimitingDeviceAngle", None),
        "NominalBeamEnergy": getattr(cp0, "NominalBeamEnergy", None),
        "IsocenterPosition": getattr(cp0, "IsocenterPosition", None),
        "JawFieldSizeX": None,
        "JawFieldSizeY": None,
    }

    for device in getattr(cp0, "BeamLimitingDevicePositionSequence", []):
        device_type = getattr(device, "RTBeamLimitingDeviceType", None) or getattr(
            device, "BeamLimitingDeviceType", None
        )
        if not device_type or not hasattr(device, "BeamLimitingDevicePosition"):
            continue

        positions = [float(x) for x in device.BeamLimitingDevicePosition]
        device_type = str(device_type).upper()

        if "X" in device_type and len(positions) >= 2:
            params["JawFieldSizeX"] = abs(positions[1] - positions[0])
        elif "Y" in device_type and len(positions) >= 2:
            params["JawFieldSizeY"] = abs(positions[1] - positions[0])
        elif len(positions) == 4:
            params["JawFieldSizeX"] = abs(positions[1] - positions[0])
            params["JawFieldSizeY"] = abs(positions[3] - positions[2])

    return params


def load_ptv_from_rtstruct(rtstruct_path):
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
        roi_name = roi_name_by_number.get(roi_number, "")
        if not is_ptv_name(roi_name):
            continue

        for contour in getattr(roi_contour, "ContourSequence", []):
            contour_data = [float(x) for x in contour.ContourData]
            contour_points = np.array(contour_data, dtype=float).reshape(-1, 3)
            points.append(contour_points)

    if not points:
        return None

    all_points = np.vstack(points)
    return {
        "points": all_points,
        "bbox_min": all_points.min(axis=0),
        "bbox_max": all_points.max(axis=0),
    }


def parse_particle_sources_file(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        m = re.match(r"^[isdbuv]:(?P<key>[^\s=]+)\s*=\s*(?P<value>.*)$", line)
        if not m:
            continue
        values[m.group("key")] = m.group("value").strip()
    return values


def format_numeric(value, unit=None):
    if unit:
        return f"{value:.6f} {unit}"
    return f"{value:.6f}"


def update_particle_sources_file(path, updates):
    lines = Path(path).read_text().splitlines()
    updated = []
    changed = set()
    pattern = re.compile(r"^[isdbuv]:(?P<key>[^\s=]+)\s*=.*$")
    for line in lines:
        m = pattern.match(line)
        if m and m.group("key") in updates:
            updated.append(updates[m.group("key")])
            changed.add(m.group("key"))
        else:
            updated.append(line)

    missing = [key for key in updates if key not in changed]
    if missing:
        anchor = next(
            (i for i, line in enumerate(updated) if line.strip().startswith("# --- Photon beam")),
            len(updated),
        )
        for offset, key in enumerate(missing):
            updated.insert(anchor + offset, updates[key])

    Path(path).write_text("\n".join(updated) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract RTPLAN beam parameters and write a TOPAS particle_sources.txt update."
    )
    parser.add_argument("--rtplan", default=DEFAULT_RTPLAN, type=Path)
    parser.add_argument("--rtstruct", default=DEFAULT_RTSTRUCT, type=Path)
    parser.add_argument("--particle-sources", default=DEFAULT_PARTICLE_SOURCES, type=Path)
    parser.add_argument("--simulation-macro", default=DEFAULT_SIMULATION_MACRO, type=Path)
    parser.add_argument("--beam-number", default=1, type=int)
    args = parser.parse_args()

    beam = load_rtplan_beam(args.rtplan, beam_number=args.beam_number)
    patient_translation = parse_simulation_patient_translation(args.simulation_macro)

    isocenter = np.array(beam["IsocenterPosition"], dtype=float)
    world_iso = isocenter + patient_translation

    print("RTPLAN beam extracted:")
    print(f"  BeamNumber:                 {beam['BeamNumber']}")
    print(f"  BeamName:                   {beam['BeamName']}")
    print(f"  RadiationType:              {beam['RadiationType']}")
    print(f"  GantryAngle:                {beam['GantryAngle']}")
    print(f"  PatientSupportAngle:        {beam['PatientSupportAngle']}")
    print(f"  BeamLimitingDeviceAngle:    {beam['BeamLimitingDeviceAngle']}")
    print(f"  NominalBeamEnergy:          {beam['NominalBeamEnergy']}")
    print(f"  IsocenterPosition (DICOM):  {isocenter.tolist()} mm")
    print(f"  Patient translation:        {patient_translation.tolist()} mm")
    print(f"  Beam anchor (TOPAS world):  {world_iso.tolist()} mm")

    updates = {
        "Ge/BeamPos/TransX": f"d:Ge/BeamPos/TransX   = {format_numeric(world_iso[0], 'mm')}",
        "Ge/BeamPos/TransY": f"d:Ge/BeamPos/TransY   = {format_numeric(world_iso[1], 'mm')}",
        "Ge/BeamPos/TransZ": f"d:Ge/BeamPos/TransZ   = {format_numeric(world_iso[2], 'mm')}",
    }

    if beam["RadiationType"] is not None:
        particle = {
            "PHOTON": '"gamma"',
            "ELECTRON": '"e-"',
            "PROTON": '"proton"',
            "ION": '"ion"',
        }.get(str(beam["RadiationType"]).upper(), None)
        if particle is not None:
            updates["So/Beam/BeamParticle"] = (
                f"s:So/Beam/BeamParticle               = {particle}"
            )

    if beam["JawFieldSizeX"] is not None:
        spread_x = beam["JawFieldSizeX"] / 10.0
        updates["So/Beam/BeamPositionSpreadX"] = (
            f"d:So/Beam/BeamPositionSpreadX        = {format_numeric(spread_x, 'cm')}"
        )
        updates["So/Beam/BeamPositionCutoffX"] = (
            f"d:So/Beam/BeamPositionCutoffX        = {format_numeric(spread_x, 'cm')}"
        )

    if beam["JawFieldSizeY"] is not None:
        spread_y = beam["JawFieldSizeY"] / 10.0
        updates["So/Beam/BeamPositionSpreadY"] = (
            f"d:So/Beam/BeamPositionSpreadY        = {format_numeric(spread_y, 'cm')}"
        )
        updates["So/Beam/BeamPositionCutoffY"] = (
            f"d:So/Beam/BeamPositionCutoffY        = {format_numeric(spread_y, 'cm')}"
        )

    update_particle_sources_file(args.particle_sources, updates)
    print(f"\nUpdated: {args.particle_sources}")

    if args.rtstruct.exists():
        ptv = load_ptv_from_rtstruct(args.rtstruct)
        if ptv is None:
            print("\nWARNING: No PTV contours found in RTSTRUCT.")
        else:
            center = 0.5 * (ptv["bbox_min"] + ptv["bbox_max"])
            print("\nPTV geometry from RTSTRUCT:")
            print(f"  PTV contour points: {ptv['points'].shape[0]}")
            print(f"  PTV bounding box min: {ptv['bbox_min'].tolist()}")
            print(f"  PTV bounding box max: {ptv['bbox_max'].tolist()}")
            print(f"  PTV center: {center.tolist()} mm")
            print(f"  PTV size: {(ptv['bbox_max'] - ptv['bbox_min']).tolist()} mm")

    print("\nDone.")


if __name__ == "__main__":
    main()
