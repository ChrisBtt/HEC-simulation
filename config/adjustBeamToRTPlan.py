import pydicom
from pathlib import Path

rtplan_path = Path("/Users/pb438/applications/hec-dose-distribution/data/p107/patched_rt/RP_patched_to_converted_CT.dcm")
ds = pydicom.dcmread(rtplan_path, stop_before_pixels=True, force=True)

print("PatientID:", ds.PatientID)
print("RTPlanLabel:", getattr(ds, "RTPlanLabel", None))
print("SOPInstanceUID:", ds.SOPInstanceUID)

beam_seq = getattr(ds, "BeamSequence", None)
ion_beam_seq = getattr(ds, "IonBeamSequence", None)

if beam_seq is not None:
    print("\nPhoton/electron RTPLAN beams:")
    for beam in beam_seq:
        print("\nBeamNumber:", beam.BeamNumber)
        print("BeamName:", getattr(beam, "BeamName", None))
        print("RadiationType:", getattr(beam, "RadiationType", None))
        print("TreatmentMachineName:", getattr(beam, "TreatmentMachineName", None))

        cps = beam.ControlPointSequence
        cp0 = cps[0]
        print("GantryAngle:", getattr(cp0, "GantryAngle", None))
        print("PatientSupportAngle:", getattr(cp0, "PatientSupportAngle", None))
        print("BeamLimitingDeviceAngle:", getattr(cp0, "BeamLimitingDeviceAngle", None))
        print("NominalBeamEnergy:", getattr(cp0, "NominalBeamEnergy", None))
        print("IsocenterPosition:", getattr(cp0, "IsocenterPosition", None))

elif ion_beam_seq is not None:
    print("\nIon RTPLAN beams:")
    for beam in ion_beam_seq:
        print("\nIon BeamNumber:", beam.IonBeamNumber)
        print("BeamName:", getattr(beam, "BeamName", None))
        print("RadiationType:", getattr(beam, "RadiationType", None))
        print("TreatmentMachineName:", getattr(beam, "TreatmentMachineName", None))

        cps = beam.IonControlPointSequence
        cp0 = cps[0]
        print("GantryAngle:", getattr(cp0, "GantryAngle", None))
        print("PatientSupportAngle:", getattr(cp0, "PatientSupportAngle", None))
        print("BeamLimitingDeviceAngle:", getattr(cp0, "BeamLimitingDeviceAngle", None))
        print("NominalBeamEnergy:", getattr(cp0, "NominalBeamEnergy", None))
        print("IsocenterPosition:", getattr(cp0, "IsocenterPosition", None))

else:
    print("No BeamSequence or IonBeamSequence found.")