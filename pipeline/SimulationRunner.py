import sys
import argparse
from PyQt5.QtWidgets import QApplication

from ConfigHandler import ConfigHandler, ConfigGUI
#import GeometryValidator
#import TransformValidator
#import SimulationDispatcher
#import ResultsProcessor

class SimulationRunner:
    def __init__(self):
        self.args = self.parse_arguments()
        self.config_handler = ConfigHandler(self.args.filename)

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description='Simulation Runner')
        parser.add_argument('filename', help='Path to the YAML configuration file')
        parser.add_argument('--threadCount', type=int, default=0, help='Number of threads to use')
        parser.add_argument('--perf', action='store_true', help='Enable performance monitoring')
        parser.add_argument('--interactive', action='store_true', help='Enable interactive config editor')
        parser.add_argument('--gui', action='store_true', help='Enable GUI mode')
        return parser.parse_args()

    def run(self):
        if self.args.interactive:
            app = QApplication(sys.argv)
            config = self.config_handler.read_config()
            gui = ConfigGUI(config)
            gui.show()
            sys.exit(app.exec_())
        else:
            self.config_handler.print_parameters()


if __name__ == '__main__':
    runner = SimulationRunner()
    runner.run()
