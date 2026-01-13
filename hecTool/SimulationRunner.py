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
        parser.add_argument("--profiling", action="store_true", help="Enable performance monitoring")
        parser.add_argument("--interactive", action="store_true", help="Enable interactive config editor")
        return parser.parse_args()

    def run(self):
        cfg = load_config(self.args.filename)

        if self.args.threadCount > 0:
            print(f"Setting thread count to {self.args.threadCount}")

        if self.args.profiling:
            print("Enabling performance monitoring (Not yet supported)")

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
        #else:
        #    print("Configuration parameters:")
        #    for key, value in cfg.to_dict().items():
        #        print(f"{key}: {value}")

        self._handle_synthetic_ct(cfg)

    def _handle_synthetic_ct(self, cfg):
        source_dirs = cfg.dicomDirs

        # Generate synthetic 3DCT
        if cfg.geometryType == "parametrized":
            print("Generating parametrized 3DCT box...")
            box = Synthetic3DCT(
                cfg.parametricGeometry.size_mm,
                cfg.parametricGeometry.spacing_mm,
                cfg.parametricGeometry.material.to_dict(),
            )
            source_dirs = [os.path.join(cfg.outputDir, "synthetic_3dct")]
            box.write_dicom_series(source_dirs[0])
            print(f"3DCT written to: {source_dirs[0]}")

        # Apply Transform Sequence for 4DCT
        if cfg.transformSequence and len(source_dirs) == 1:
            print(f"Applying {len(cfg.transformSequence)} transforms to generate 4DCT...")
            generator = Synthetic4DCT(source_dirs[0])

            phases = generator.generate_4dct(cfg.transformSequence, cfg.useCenterAsTransformOrigin)

            for i, phase_img in enumerate(phases):
                phase_dir = os.path.join(cfg.outputDir, f"phase_{i}")
                generator.write_dicom_series(phase_img, phase_dir, phase_index=i)
            print(f"4DCT phases written to {cfg.outputDir}")

        # Write TOPAS configuration
        print("Writing TOPAS configuration...")
        cfg.write_topas_config(self.args.threadCount)
        print(f"TOPAS configuration written to : {cfg.outputDir}")

if __name__ == "__main__":
    runner = SimulationRunner()
    runner.run()