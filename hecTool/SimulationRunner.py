import sys
import argparse

from hecTool.ConfigHandler import ConfigHandler


class SimulationRunner:
    def __init__(self):
        self.args = self.parse_arguments()
        self.config_handler = ConfigHandler(self.args.filename)

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description="Simulation Runner")
        parser.add_argument("filename", help="Path to the YAML configuration file")
        parser.add_argument("--threadCount", type=int, default=0, help="Number of threads to use")
        parser.add_argument("--perf", action="store_true", help="Enable performance monitoring")
        parser.add_argument("--interactive", action="store_true", help="Enable interactive config editor")
        parser.add_argument("--gui", action="store_true", help="Enable GUI mode")
        return parser.parse_args()

    def run(self):
        cfg = self.config_handler.load()

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
        else:
            print("Configuration parameters:")
            for key, value in cfg.to_dict().items():
                print(f"{key}: {value}")


if __name__ == "__main__":
    runner = SimulationRunner()
    runner.run()