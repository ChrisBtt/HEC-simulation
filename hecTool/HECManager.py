import os
import sys
import argparse
import numpy as np
import multiprocessing as mp

from hecTool.ConfigHandler import load_config
from hecTool.SyntheticCT import (generate_synthetic_3dct, write_dicom_series, read_dicom_series, generate_4dct,
                                 get_default_image_metadata, embed_tumors_in_image, clone_itk_image)
from hecTool.TransformAffine import interpolate_transforms, params_to_flat_4x4


class HECManager:
    def __init__(self):
        self.args = self.parse_arguments()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description="Simulation Runner")
        parser.add_argument("filename", help="Path to the YAML configuration file")
        parser.add_argument("--output_dir", help="Where all generated files and DICOMs are saved")
        parser.add_argument("--threadcount", type=int, default=-1, help="Number of threads to use")
        parser.add_argument("--profiling", action="store_true", help="Enable performance monitoring")
        parser.add_argument("--interactive", action="store_true", help="Enable interactive config editor")
        return parser.parse_args()

    def run(self):
        try:
            cfg = load_config(self.args.filename)
        except Exception as e:
            print(f"Error loading config: {e}")
            return

        # Determine output directory
        output_dir = self.args.output_dir
        if not output_dir:
            config_name = os.path.splitext(os.path.basename(self.args.filename))[0]
            output_dir = os.path.join("TOPAS_simulation_data", config_name)

        if os.path.exists(output_dir) and os.listdir(output_dir):
            confirm = input(f"Warning: Output directory '{output_dir}' is not empty. Overwrite existing files? (y/n): ")
            if confirm.lower() != 'y':
                print("Simulation aborted by user.")
                return

        if self.args.threadcount > 0:
            print(f"Setting thread count to {self.args.threadcount}")

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

        timeline = self._get_shared_timeline(cfg)
        self._handle_synthetic_ct(cfg, timeline, output_dir)

        # Write TOPAS configuration
        print("Writing TOPAS configuration...")
        cfg.write_topas_config(output_dir, self.args.threadcount, timeline)
        print(f"TOPAS configuration written to: {output_dir}")

    def _get_shared_timeline(self, cfg):
        time_points = set()
        if cfg.patient.transform_sequence:
            for t in cfg.patient.transform_sequence:
                time_points.add(t.time_s)
        for tumor in cfg.tumors:
            for t in tumor.transform_sequence:
                time_points.add(t.time_s)

        if not time_points:
            return [0.0]

        if cfg.simulation_steps < len(time_points):
            return list(time_points)

        return np.linspace(min(time_points), max(time_points), cfg.simulation_steps).tolist()

    def _handle_synthetic_ct(self, cfg, timeline, output_dir):
        source_dirs = cfg.patient.dicom_directories

        # Generate synthetic 3DCT
        if cfg.patient.type == "parametrized":
            print("Generating parametrized 3DCT box...")
            params = cfg.patient.parameters

            synthetic_3dct = generate_synthetic_3dct(params.size_mm, params.spacing_mm, params.radiodensity_hu)
            source_dirs = [os.path.join(output_dir, "synthetic_3dct")]
            write_dicom_series(synthetic_3dct, source_dirs[0])
            print(f"3DCT written to: {source_dirs[0]}")

        if len(source_dirs) != 1:
            return

        source_3dct, metadata = read_dicom_series(source_dirs[0])

        has_patient_motion = bool(cfg.patient.transform_sequence)
        has_tumor_motion = any(t.embed_mode == "dicom" and t.transform_sequence for t in cfg.tumors)

        if has_patient_motion:
            print(f"Applying transforms to generate 4DCT with {len(timeline)} phases...")
            patient_transforms_interpolated = interpolate_transforms(cfg.patient.transform_sequence, timeline)
            flat_matrices = [params_to_flat_4x4(p) for p in patient_transforms_interpolated]
            phases = generate_4dct(source_3dct, flat_matrices, cfg.tumors, timeline,
                                   cfg.patient.use_center_as_transform_origin)
        elif has_tumor_motion:
            print(f"Generating tumor-motion 4DCT with {len(timeline)} phases...")
            phases = [clone_itk_image(source_3dct) for _ in timeline]
            for phase, t in zip(phases, timeline):
                embed_tumors_in_image(phase, cfg.tumors, t)
        else:
            phases = [source_3dct]
            phase_times = [timeline[0]]
            embed_tumors_in_image(phases[0], cfg.tumors, phase_times[0])

        pool = mp.Pool()
        for i, phase_img in enumerate(phases):
            phase_dir = os.path.join(output_dir, f"phase_{i}")
            phase_data = get_default_image_metadata(metadata)
            phase_data["0008|103e"] = f"4DCT Phase {i}"
            pool.apply_async(write_dicom_series, args=(phase_img, phase_dir, phase_data))
        print(f"4DCT phases written to: {output_dir}")
        pool.close()
        pool.join()


def main():
    hec_manager = HECManager()
    hec_manager.run()


if __name__ == "__main__":
    main()
