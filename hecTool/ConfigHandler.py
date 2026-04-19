import yaml

from hecTool.ConfigModel import SimulationConfig


class FlowList(list):
    """Wrapper to force PyYAML to use flow style for specific lists."""
    pass


def flow_list_representer(dumper, data):
    """Represent FlowList values in YAML using flow style.

    Parameters
    ----------
    dumper : yaml.Dumper
        YAML dumper instance.
    data : FlowList
        FlowList to serialize.

    Returns
    -------
    yaml.nodes.SequenceNode
        YAML sequence node with flow style enabled.
    """
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)


def load_config(filename: str) -> SimulationConfig:
    """Load, validate, and return a SimulationConfig from a YAML file.

    Parameters
    ----------
    filename : str
        Path to the YAML configuration file.

    Returns
    -------
    SimulationConfig
        Parsed and validated configuration model.
    """
    with open(filename, "r") as file:
        raw = yaml.safe_load(file) or {}
    cfg = SimulationConfig.from_dict(raw)
    cfg.validate()
    return cfg


def save_config(cfg: SimulationConfig, filename: str):
    """Serialize a SimulationConfig to YAML with preferred flow-style lists.

    Parameters
    ----------
    cfg : SimulationConfig
        Configuration model to serialize.
    filename : str
        Destination path for the YAML file.
    """
    yaml.add_representer(FlowList, flow_list_representer)
    yaml.add_representer(FlowList, flow_list_representer, Dumper=yaml.SafeDumper)

    data = cfg.to_dict()

    # Apply flow style to patient components
    patient = data.get("patient", {})
    if "transform_sequence" in patient:
        for t in patient["transform_sequence"]:
            for key in ["translation_mm", "rotation_deg", "scale", "shear"]:
                if key in t:
                    t[key] = FlowList(t[key])
    if "scoring_bins" in patient:
        patient["scoring_bins"] = FlowList(patient["scoring_bins"])
    if "translation_mm" in patient:
        patient["translation_mm"] = FlowList(patient["translation_mm"])
    if "rotation_deg" in patient:
        patient["rotation_deg"] = FlowList(patient["rotation_deg"])

    # Apply flow style to parametric geometry components
    patient_params = patient.get("parameters", {})
    if "size_mm" in patient_params:
        patient_params["size_mm"] = FlowList(patient_params["size_mm"])
    if "spacing_mm" in patient_params:
        patient_params["spacing_mm"] = FlowList(patient_params["spacing_mm"])

    # Apply flow style to tumor transforms
    for tumor in data.get("tumors", []):
        if "transform_sequence" in tumor:
            for t in tumor["transform_sequence"]:
                for key in ["translation_mm", "rotation_deg", "scale"]:
                    if key in t:
                        t[key] = FlowList(t[key])
        for key in ["translation_mm", "rotation_deg", "radius_mm"]:
            if key in tumor:
                tumor[key] = FlowList(tumor[key])

    with open(filename, "w") as file:
        yaml.safe_dump(data, file, sort_keys=False, version=(1, 2))
