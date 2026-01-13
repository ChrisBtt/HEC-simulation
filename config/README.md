To initialize an OpenTOPAS simulation with `hecTool`, you use a YAML configuration to define the geometry and physics. The tool generates the synthetic CT data and the required TOPAS `.txt` files.

### 1. How to Run
Execute the tool from the project root:
```shell script
python -m hecTool config/your_config.yaml [options]
```

*   `--interactive`: Opens a GUI to edit parameters before starting.
*   `--threadCount N`: Sets the number of CPU threads for TOPAS.
*   `--profiling`: Enables performance profiling. (Not yet supported)

---

### 2. YAML Configuration Parameters

| Parameter                        | Description                                                                    |
|:---------------------------------|:-------------------------------------------------------------------------------|
| **`seed`**                       | Integer for simulation reproducibility.                                        |
| **`physics`**                    | List of Geant4 modules (e.g., `[g4em-standard_opt0]`).                         |
| **`geometryType`**               | `parametrized` (creates a box), `3dct`, or `4dct`.                             |
| **`outputDirectory`**            | Where all generated files and DICOMs are saved.                                |
| **`dicomDirectories`**           | Paths to input DICOMs (required for `3dct` or `4dct`).                         |
| **`parametricGeometry`**         | Defines `size_mm`, `spacing_mm`, and `material` (name/HU) for a synthetic box. |
| **`placement`**                  | `translation_mm` and `rotation_deg` of the patient in the World.               |
| **`scoringBins`**                | `[X, Y, Z]` resolution for dose/fluence grids.                                 |
| **`includeFiles`**               | Paths to external TOPAS macros (sources, scorers, etc.).                       |
| **`transformSequence`**          | List of $4 \times 4$ matrices to create motion phases (4DCT).                  |
| **`useCenterAsTransformOrigin`** | Change origin of transformations from corner to model center                   |

---

### 3. The `hec_parameters.txt` File
`hecTool` automatically generates a special file named `hec_parameters.txt` in the output folder. It contains dynamic values that your custom macros can reference:

*   **`s:Par/OutputDir`**: Absolute path to the output folder.
*   **`s:Par/ResultsDir`**: Absolute path to the `results` folder.
*   **`i:Par/ScoringGridXBins` (Y/Z)**: Bin counts from your YAML `scoringBins`.

**How to use it:**
In your custom macros (like `scoring_dose.txt`), include this file to access the variables:
```
includeFile = hec_parameters.txt
i:Sc/MyScorer/XBins = Par/ScoringGridXBins
```

*Note: `hecTool` recursively copies all `includeFiles` and their dependencies to the output folder, but it manages `hec_parameters.txt` automatically—you do not need to list it in the YAML.*

---

### 4. Next Steps
After initialization, navigate to your `outputDirectory` and run the simulation:
```shell script
topas simulation.txt
```
