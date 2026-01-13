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

    with open(filename, "w") as file:
        yaml.safe_dump(data, file, sort_keys=False)