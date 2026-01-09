import yaml

from hecTool.ConfigModel import SimulationConfig


def load_config(filename: str) -> SimulationConfig:
    with open(filename, "r") as file:
        raw = yaml.safe_load(file) or {}
    cfg = SimulationConfig.from_dict(raw)
    cfg.validate()
    return cfg


def save_config(cfg: SimulationConfig, filename: str) -> None:
    with open(filename, "w") as file:
        yaml.safe_dump(cfg.to_dict(), file, sort_keys=False)