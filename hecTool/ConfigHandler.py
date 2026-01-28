import yaml

from hecTool.ConfigModel import SimulationConfig


class FlowList(list):
    """Wrapper to force PyYAML to use flow style for specific lists."""
    pass


def flow_list_representer(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)


yaml.add_representer(FlowList, flow_list_representer)
yaml.add_representer(FlowList, flow_list_representer, Dumper=yaml.SafeDumper)


def load_config(filename: str) -> SimulationConfig:
    with open(filename, "r") as file:
        raw = yaml.safe_load(file) or {}
    cfg = SimulationConfig.from_dict(raw)
    cfg.validate()
    return cfg


def save_config(cfg: SimulationConfig, filename: str) -> None:
    data = cfg.to_dict()

    # Wrap transform sequences to force flow style
    if "transformSequence" in data:
        data["transformSequence"] = [FlowList(m) for m in data["transformSequence"]]

    # Wrap scoringBins to force flow style
    if "scoringBins" in data:
        data["scoringBins"] = FlowList(data["scoringBins"])

    # Wrap placement components to force flow style
    if "placement" in data:
        if "translation_mm" in data["placement"]:
            data["placement"]["translation_mm"] = FlowList(data["placement"]["translation_mm"])
        if "rotation_deg" in data["placement"]:
            data["placement"]["rotation_deg"] = FlowList(data["placement"]["rotation_deg"])

    # Wrap parametric geometry components to force flow style
    if "parametricGeometry" in data:
        if "size_mm" in data["parametricGeometry"]:
            data["parametricGeometry"]["size_mm"] = FlowList(data["parametricGeometry"]["size_mm"])
        if "spacing_mm" in data["parametricGeometry"]:
            data["parametricGeometry"]["spacing_mm"] = FlowList(data["parametricGeometry"]["spacing_mm"])

    with open(filename, "w") as file:
        yaml.safe_dump(data, file, sort_keys=False, version=(1, 2))