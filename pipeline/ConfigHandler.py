import yaml
from PyQt5.QtWidgets import (QMainWindow, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QPushButton, QFileDialog, QHBoxLayout,
                             QLineEdit, QLabel, QGridLayout, QButtonGroup, QRadioButton)
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp

class ConfigHandler:
    def __init__(self, filename):
        self.filename = filename
        self.valid_geometry_types = ['parametrized', '3dct', '4dct']

    def read_config(self):
        with open(self.filename, 'r') as file:
            config = yaml.safe_load(file)
            self.validate_config(config)
            return config

    def print_parameters(self):
        config = self.read_config()
        print("Configuration parameters:")
        for key, value in config.items():
            print(f"{key}: {value}")

    def validate_physics(self, config):
        physics = config.get('physics')
        if not physics or not isinstance(physics, list):
            raise ValueError("Physics parameter must be a list of strings")
        if not physics:
            raise ValueError("Physics parameter cannot be empty")
        if not all(isinstance(p, str) and p.strip() for p in physics):
            raise ValueError("All physics parameters must be non-empty strings")

    def validate_particle_count(self, config):
        count = config.get('particleCount')
        if not count or not isinstance(count, int):
            raise ValueError("Particle count must be a positive integer")
        if count <= 0:
            raise ValueError("Particle count must be greater than zero")

    def validate_geometry_type(self, config):
        geometry_type = config.get('geometryType')
        if not geometry_type:
            raise ValueError("Geometry type must be specified")
        if geometry_type not in self.valid_geometry_types:
            raise ValueError(f"Invalid geometry type. Must be one of: {', '.join(self.valid_geometry_types)}")

    def validate_output_dir(self, config):
        import os
        output_dir = config.get('outputDir')
        if not output_dir:
            raise ValueError("Output directory must be specified")
        if not os.path.exists(output_dir):
            raise ValueError(f"Output directory {output_dir} does not exist")
        if not os.access(output_dir, os.W_OK):
            raise ValueError(f"Output directory {output_dir} is not writable")

    def validate_config(self, config):
        #self.validate_output_dir(config)
        self.validate_particle_count(config)
        self.validate_geometry_type(config)
        self.validate_physics(config)


class ConfigGUI(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.initUI()
        self.setup_parameter_editors()

    def initUI(self):
        self.setWindowTitle('Edit Configuration')
        self.setGeometry(100, 100, 600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        editor_layout = QGridLayout()
        layout.addLayout(editor_layout)

        tree = QTreeWidget()
        tree.setHeaderLabel('Configuration')
        self.populate_tree(tree, self.config)
        layout.addWidget(tree)

        button_layout = QHBoxLayout()
        save_button = QPushButton('Save As...')
        save_button.clicked.connect(self.save_to_file)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

    def populate_tree(self, tree, config, parent=None):
        for key, value in config.items():
            if parent is None:
                item = QTreeWidgetItem(tree)
            else:
                item = QTreeWidgetItem(parent)

            if isinstance(value, dict):
                item.setText(0, str(key))
                self.populate_tree(tree, value, item)
            else:
                item.setText(0, f"{key}: {value}")

    def setup_parameter_editors(self):
        editor_layout = self.centralWidget().layout().itemAt(0).layout()

        # Physics Parameter
        physics_label = QLabel("Modular Physics List:")
        physics_value = ', '.join(self.config.get('physics', []))
        self.physics_edit = QLineEdit(physics_value)
        self.physics_edit.textChanged.connect(self.update_physics)
        editor_layout.addWidget(physics_label, 0, 0)
        editor_layout.addWidget(self.physics_edit, 0, 1)

        # Particle Count
        particle_label = QLabel("Particle Count:")
        self.particle_edit = QLineEdit(str(self.config.get('particleCount', '1000')))
        self.particle_edit.setValidator(QRegExpValidator(QRegExp(r'[0-9]+')))
        self.particle_edit.textChanged.connect(self.update_particle_count)
        editor_layout.addWidget(particle_label, 1, 0)
        editor_layout.addWidget(self.particle_edit, 1, 1)

        # Geometry Type
        geometry_label = QLabel("Geometry Type:")
        editor_layout.addWidget(geometry_label, 2, 0)

        geometry_group = QButtonGroup(self)
        geometry_layout = QHBoxLayout()

        parametrized_radio = QRadioButton("Parametrized")
        threedct_radio = QRadioButton("3DCT")
        fourdct_radio = QRadioButton("4DCT")

        geometry_group.addButton(parametrized_radio)
        geometry_group.addButton(threedct_radio)
        geometry_group.addButton(fourdct_radio)

        geometry_layout.addWidget(parametrized_radio)
        geometry_layout.addWidget(threedct_radio)
        geometry_layout.addWidget(fourdct_radio)

        current_geometry = self.config.get('geometryType', 'parametrized')
        if current_geometry == 'parametrized':
            parametrized_radio.setChecked(True)
        elif current_geometry == '3dct':
            threedct_radio.setChecked(True)
        elif current_geometry == '4dct':
            fourdct_radio.setChecked(True)

        geometry_group.buttonClicked.connect(self.update_geometry_type)
        editor_layout.addLayout(geometry_layout, 2, 1)

        # Output Directory
        output_label = QLabel("Output Directory:")
        self.output_edit = QLineEdit(self.config.get('outputDir', ''))
        self.output_edit.textChanged.connect(self.update_output_dir)
        editor_layout.addWidget(output_label, 3, 0)
        editor_layout.addWidget(self.output_edit, 3, 1)

        # DICOM Directory
        dicom_label = QLabel("DICOM Directory:")
        self.dicom_edit = QLineEdit(self.config.get('dicomDir', ''))
        self.dicom_edit.textChanged.connect(self.update_dicom_dir)
        editor_layout.addWidget(dicom_label, 4, 0)
        editor_layout.addWidget(self.dicom_edit, 4, 1)
        if current_geometry == 'parametrized':
            self.dicom_edit.setEnabled(False)

    def update_output_dir(self, value):
        self.config['outputDir'] = value

    def update_particle_count(self, value):
        if value:
            self.config['particleCount'] = int(value)

    def update_geometry_type(self, button):
        self.config['geometryType'] = button.text().lower()
        self.dicom_edit.setEnabled(False if self.config['geometryType'] == 'parametrized' else True)

    def update_physics(self, value):
        self.config['physics'] = [p.strip() for p in value.split(',') if p.strip()]

    def update_dicom_dir(self, value):
        self.config['dicomDir'] = value

    def save_to_file(self): # Maybe preserve input format
        filename, _ = QFileDialog.getSaveFileName(self, 'Save Configuration',
                                                  None,
                                                  'YAML files (*.yaml);;All Files (*)')
        if filename:
            with open(filename, 'w') as file:
                yaml.dump(self.config, file)