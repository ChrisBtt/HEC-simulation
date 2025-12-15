import yaml

from hecTool.ConfigModel import SimulationConfig


class ConfigHandler:
    def __init__(self, filename: str):
        self.filename = filename

    def load(self) -> SimulationConfig:
        with open(self.filename, "r") as file:
            raw = yaml.safe_load(file) or {}
        cfg = SimulationConfig.from_dict(raw)
        cfg.validate()
        return cfg

    @staticmethod
    def save(cfg: SimulationConfig, filename: str) -> None:
        with open(filename, "w") as file:
            yaml.safe_dump(cfg.to_dict(), file, sort_keys=False)