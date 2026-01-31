To initialize an OpenTOPAS simulation with `hecTool`, you use a YAML configuration to define the geometry and physics. The tool generates the synthetic CT data and the required TOPAS `.txt` files.

### 1. How to Run
Execute the tool from the project root:
```shell script
python -m hecTool config/your_config.yaml [options]
```

*   `--interactive`: Opens a GUI to edit parameters before starting.
*   `--output_dir PATH`: Where all generated files and DICOMs are saved. (Defaults to `TOPAS_simulation_data/{config_name}/`)
*   `--threadcount N`: Sets the number of CPU threads for TOPAS.
*   `--profiling`: Enables performance profiling. (Not yet supported)

Alternatively, you can run the configuration editor standalone to create or modify a config file:
```shell script
python -m hecTool.ConfigEditor [your_config.yaml]
```
The config directory contains an example configuration file (`config/example.yaml`) that can be used as a starting point.

---

### 2. YAML Configuration Parameters

The configuration is divided into four main sections: `topas`, `general`, `patient`, and `tumors`.

#### 2.1 `topas`
| Parameter                  | Description                                            |
|:---------------------------|:-------------------------------------------------------|
| **`seed`**                 | Integer for simulation reproducibility.                |
| **`physics`**              | List of Geant4 modules (e.g., `[g4em-standard_opt0]`). |

#### 2.2 `general`
| Parameter                 | Description                                                              |
|:--------------------------|:-------------------------------------------------------------------------|
| **`interpolation_steps`** | Number of time points to interpolate between keyframes (0 = no interp).  |
| **`include_files`**       | Paths to external TOPAS macros (sources, scorers, etc.).                 |

#### 2.3 `patient`
| Parameter                            | Description                                                                    |
|:-------------------------------------|:-------------------------------------------------------------------------------|
| **`type`**                           | `parametrized` (creates a box), `3dct`, or `4dct`.                             |
| **`dicom_directories`**              | List of paths to input DICOMs (required for `3dct` or `4dct`).                 |
| **`parameters`**                     | Map defining `size_mm`, `spacing_mm`, and `radiodensity_hu` for synthetic box. |
| **`scoring_bins`**                   | `[X, Y, Z]` resolution for dose/fluence grids.                                 |
| **`translation_mm`**                 | Base translation `[X, Y, Z]` of the patient in the World.                      |
| **`rotation_deg`**                   | Base rotation `[X, Y, Z]` of the patient in the World.                         |
| **`use_center_as_transform_origin`** | Boolean to change origin of transformations from corner to model center.       |
| **`transform_sequence`**             | List of keyframe `TransformStep` objects for patient motion.                   |

#### 2.4 `tumors`
A list of tumor objects, each with:

| Parameter                | Description                                                |
|:-------------------------|:-----------------------------------------------------------|
| **`topas_material`**     | Material name from TOPAS/Geant4 (e.g., `G4_WATER`).        |
| **`translation_mm`**     | Base translation `[X, Y, Z]` relative to the patient.      |
| **`rotation_deg`**       | Base rotation `[X, Y, Z]` relative to the patient.         |
| **`radius_mm`**          | Half-lengths `[X, Y, Z]` of the `TsEllipsoid`.             |
| **`transform_sequence`** | List of keyframe `TransformStep` objects for tumor motion. |

#### 2.5 `TransformStep`
Used in `transform_sequence` for both patient and tumors:

| Parameter            | Description                                        |
|:---------------------|:---------------------------------------------------|
| **`time_s`**         | Time point for this keyframe in seconds.           |
| **`translation_mm`** | `[X, Y, Z]` translation relative to base position. |
| **`rotation_deg`**   | `[X, Y, Z]` rotation relative to base position.    |
| **`scale`**          | `[X, Y, Z]` scaling factors (default `[1, 1, 1]`). |
| **`shear`**          | `[XY, XZ, YZ]` shear factors (patient only).      |

---

### 3. The `hec_parameters.txt` File
`hecTool` automatically generates a special file named `hec_parameters.txt` in the output folder. It contains dynamic values that your custom macros can reference:

*   **`s:Par/OutputDir`**: Absolute path to the output folder.
*   **`s:Par/ResultsDir`**: Absolute path to the `results` folder.
*   **`i:Par/ScoringGridXBins` (Y/Z)**: Bin counts from your YAML `scoring_bins`.

**How to use it:**
In your custom macros (like `scoring_dose.txt`), include this file to access the variables:
```
includeFile = hec_parameters.txt
i:Sc/MyScorer/XBins = Par/ScoringGridXBins
```

*Note: `hecTool` recursively copies all `include_files` and their dependencies to the output folder, but it manages `hec_parameters.txt` automatically—you do not need to list it in the YAML.*

---

### 5. Next Steps
After initialization, navigate to your `output_directory` and run the simulation:
```shell script
topas simulation.txt
```
