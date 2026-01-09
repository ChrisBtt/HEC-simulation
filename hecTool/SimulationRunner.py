import os
import sys
import argparse

from hecTool.ConfigHandler import load_config
from hecTool.SyntheticCT import Synthetic3DCT, Synthetic4DCT


class SimulationRunner:
    def __init__(self):
        self.args = self.parse_arguments()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description="Simulation Runner")
        parser.add_argument("filename", help="Path to the YAML configuration file")
        parser.add_argument("--threadCount", type=int, default=-1, help="Number of threads to use")
        parser.add_argument("--perf", action="store_true", help="Enable performance monitoring")
        parser.add_argument("--interactive", action="store_true", help="Enable interactive config editor")
        return parser.parse_args()

    def run(self):
        cfg = load_config(self.args.filename)

        if self.args.threadCount > 0:
            print(f"Setting thread count to {self.args.threadCount}")

        if self.args.perf:
            print("Enabling performance monitoring")

        if self.args.interactive:
            try:
                from PyQt5.QtWidgets import QApplication
                from hecTool.ConfigEditor import ConfigGUI
            except ImportError as exc:
                raise SystemExit(
                    "PyQt5 is required for --interactive mode. "
                    "Install PyQt5 or run without --interactive."
                ) from exc

            app = QApplication(sys.argv)
            gui = ConfigGUI(cfg)
            gui.show()

            exit_code = app.exec_()
            if exit_code != 0:
                sys.exit(exit_code)

            if gui.saved_filename:
                print(f"Loading updated configuration from: {gui.saved_filename}")
                cfg = load_config(gui.saved_filename)
        else:
            print("Configuration parameters:")
            for key, value in cfg.to_dict().items():
                print(f"{key}: {value}")

        #self._handle_synthetic_ct(cfg)

    def _handle_synthetic_ct(self, cfg):
        """Processes synthetic CT generation based on config."""
        output_base = cfg.outputDir or "output"

        # 1. Generate/Locate Source 3DCT
        source_dir = cfg.dicomDir

        if cfg.geometryType == "parametrized":
            print("Generating parametrized 3DCT box...")
            # Example parameters - these could be added to ConfigModel later
            material = {"name": "water", "hu": 0}
            box = Synthetic3DCT(
                size_mm=(300.0, 300.0, 300.0),
                spacing_mm=(1.0, 1.0, 1.0),
                material=material
            )
            source_dir = os.path.join(output_base, "synthetic_3dct")
            box.write_dicom_series(source_dir)
            print(f"3DCT written to: {source_dir}")

        # 2. Apply Transform Sequence for 4DCT
        if cfg.transformSequence:
            print(f"Applying {len(cfg.transformSequence)} transforms to generate 4DCT...")
            generator = Synthetic4DCT(source_dir)

            phases = generator.generate_4dct(cfg.transformSequence)

            for i, phase_img in enumerate(phases):
                phase_dir = os.path.join(output_base, f"phase_{i}")
                generator.write_dicom_series(phase_img, phase_dir, phase_index=i)
            print(f"4DCT phases written to {output_base}")

        # 3. Write TOPAS configuration
        print("Writing TOPAS configuration...")
        cfg.write_topas_config(os.path.join(output_base, "simulation.txt"))


if __name__ == "__main__":
    runner = SimulationRunner()
    runner.run()