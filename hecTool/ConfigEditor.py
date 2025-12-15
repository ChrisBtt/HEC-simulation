from PyQt5.QtWidgets import (QMainWindow, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QPushButton, QFileDialog, QHBoxLayout,
                             QLineEdit, QLabel, QGridLayout, QButtonGroup, QRadioButton,
                             QScrollArea, QFrame, QMessageBox)
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp

from hecTool.ConfigModel import SimulationConfig
from hecTool.ConfigHandler import ConfigHandler
from hecTool.TransformAffine import TransformParams, params_to_flat_4x4, flat_4x4_to_params


class TransformEditor(QWidget):
    from PyQt5.QtCore import pyqtSignal

    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, transform_data=None, parent=None):
        super().__init__(parent)
        self.initUI()
        if transform_data:
            self.set_values(transform_data)

    def initUI(self):
        layout = QGridLayout(self)

        # Translation
        layout.addWidget(QLabel("Translation:"), 0, 0)
        self.tx = QLineEdit("0")
        self.ty = QLineEdit("0")
        self.tz = QLineEdit("0")
        layout.addWidget(self.tx, 0, 1)
        layout.addWidget(self.ty, 0, 2)
        layout.addWidget(self.tz, 0, 3)

        # Rotation
        layout.addWidget(QLabel("Rotation:"), 1, 0)
        self.rx = QLineEdit("0")
        self.ry = QLineEdit("0")
        self.rz = QLineEdit("0")
        layout.addWidget(self.rx, 1, 1)
        layout.addWidget(self.ry, 1, 2)
        layout.addWidget(self.rz, 1, 3)

        # Scale
        layout.addWidget(QLabel("Scale:"), 2, 0)
        self.sx = QLineEdit("1")
        self.sy = QLineEdit("1")
        self.sz = QLineEdit("1")
        layout.addWidget(self.sx, 2, 1)
        layout.addWidget(self.sy, 2, 2)
        layout.addWidget(self.sz, 2, 3)

        # Shear
        layout.addWidget(QLabel("Shear XY/YX:"), 3, 0)
        self.shxy = QLineEdit("0")
        self.shyx = QLineEdit("0")
        layout.addWidget(self.shxy, 3, 1)
        layout.addWidget(self.shyx, 3, 2)

        layout.addWidget(QLabel("Shear XZ/ZX:"), 4, 0)
        self.shxz = QLineEdit("0")
        self.shzx = QLineEdit("0")
        layout.addWidget(self.shxz, 4, 1)
        layout.addWidget(self.shzx, 4, 2)

        layout.addWidget(QLabel("Shear YZ/ZY:"), 5, 0)
        self.shyz = QLineEdit("0")
        self.shzy = QLineEdit("0")
        layout.addWidget(self.shyz, 5, 1)
        layout.addWidget(self.shzy, 5, 2)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        layout.addWidget(delete_btn, 6, 0)

        for widget in [self.tx, self.ty, self.tz, self.rx, self.ry, self.rz,
                       self.sx, self.sy, self.sz, self.shxy, self.shyx, self.shxz,
                       self.shzx, self.shyz, self.shzy]:
            widget.setValidator(QRegExpValidator(QRegExp(r'-?\d*\.?\d*'))) # or QDoubleValidator()
            widget.textChanged.connect(self.on_change)

    def on_change(self):
        self.changed.emit()

    def params_to_matrix(self):
        params = TransformParams(
            translation=(float(self.tx.text()), float(self.ty.text()), float(self.tz.text())),
            rotation_deg=(float(self.rx.text()), float(self.ry.text()), float(self.rz.text())),
            scale=(float(self.sx.text()), float(self.sy.text()), float(self.sz.text())),
            shear=(
                float(self.shxy.text()),
                float(self.shyx.text()),
                float(self.shxz.text()),
                float(self.shzx.text()),
                float(self.shyz.text()),
                float(self.shzy.text()),
            ),
        )
        return params_to_flat_4x4(params)

    def matrix_to_params(self, matrix):
        p = flat_4x4_to_params(matrix)
        return {
            "translation": list(p.translation),
            "rotation": list(p.rotation_deg),
            "scale": list(p.scale),
            "shear": list(p.shear),
        }

    def get_matrix(self):
        try:
            return self.params_to_matrix()
        except ValueError:
            return None

    def set_values(self, data):
        if isinstance(data, list) and len(data) == 16:
            params = self.matrix_to_params(data)
        else:
            params = data

        t = params.get('translation', [0, 0, 0])
        r = params.get('rotation', [0, 0, 0])
        s = params.get('scale', [1, 1, 1])
        sh = params.get('shear', [0, 0, 0, 0, 0, 0])

        self.tx.setText(str(t[0]))
        self.ty.setText(str(t[1]))
        self.tz.setText(str(t[2]))
        self.rx.setText(str(r[0]))
        self.ry.setText(str(r[1]))
        self.rz.setText(str(r[2]))
        self.sx.setText(str(s[0]))
        self.sy.setText(str(s[1]))
        self.sz.setText(str(s[2]))
        self.shxy.setText(str(sh[0]))
        self.shyx.setText(str(sh[1]))
        self.shxz.setText(str(sh[2]))
        self.shzx.setText(str(sh[3]))
        self.shyz.setText(str(sh[4]))
        self.shzy.setText(str(sh[5]))


class ConfigGUI(QMainWindow):
    def __init__(self, cfg: SimulationConfig):
        super().__init__()
        self.cfg = cfg
        self.initUI()
        self.setup_parameter_editors()
        self.refresh_tree()

    def initUI(self):
        self.setWindowTitle('Edit Configuration')
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        editor_layout = QGridLayout()
        layout.addLayout(editor_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel('Configuration')
        layout.addWidget(self.tree)

        button_layout = QHBoxLayout()
        save_button = QPushButton('Save As...')
        save_button.clicked.connect(self.save_to_file)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

    def refresh_tree(self):
        self.tree.clear()
        self.populate_tree(self.tree, self.cfg.to_dict())

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

        physics_label = QLabel("Modular Physics List:")
        self.physics_edit = QLineEdit(", ".join(self.cfg.physics))
        self.physics_edit.textChanged.connect(self.update_physics)
        editor_layout.addWidget(physics_label, 0, 0)
        editor_layout.addWidget(self.physics_edit, 0, 1)

        particle_label = QLabel("Particle Count:")
        self.particle_edit = QLineEdit(str(self.cfg.particleCount))
        self.particle_edit.setValidator(QRegExpValidator(QRegExp(r'[0-9]+')))
        self.particle_edit.textChanged.connect(self.update_particle_count)
        editor_layout.addWidget(particle_label, 1, 0)
        editor_layout.addWidget(self.particle_edit, 1, 1)

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

        current_geometry = self.cfg.geometryType
        if current_geometry == "parametrized":
            parametrized_radio.setChecked(True)
        elif current_geometry == "3dct":
            threedct_radio.setChecked(True)
        elif current_geometry == "4dct":
            fourdct_radio.setChecked(True)

        geometry_group.buttonClicked.connect(self.update_geometry_type)
        editor_layout.addLayout(geometry_layout, 2, 1)

        output_label = QLabel("Output Directory:")
        self.output_edit = QLineEdit(self.cfg.outputDir)
        self.output_edit.textChanged.connect(self.update_output_dir)
        editor_layout.addWidget(output_label, 3, 0)
        editor_layout.addWidget(self.output_edit, 3, 1)

        dicom_label = QLabel("DICOM Directory:")
        self.dicom_edit = QLineEdit(self.cfg.dicomDir)
        self.dicom_edit.textChanged.connect(self.update_dicom_dir)
        editor_layout.addWidget(dicom_label, 4, 0)
        editor_layout.addWidget(self.dicom_edit, 4, 1)
        self.dicom_edit.setEnabled(False if self.cfg.geometryType == "parametrized" else True)

        transform_label = QLabel("Transform Sequence:")
        editor_layout.addWidget(transform_label, 5, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        transform_container = QWidget()
        self.transform_layout = QVBoxLayout(transform_container)

        self.transforms = []
        for transform in self.cfg.transformSequence:
            self.add_transform_editor(transform)

        scroll.setWidget(transform_container)
        editor_layout.addWidget(scroll, 5, 1, 1, 2)

        add_transform_btn = QPushButton("Add Transform")
        add_transform_btn.clicked.connect(self.add_transform_editor)
        editor_layout.addWidget(add_transform_btn, 6, 1)

    def add_transform_editor(self, transform_data=None):
        transform = TransformEditor(transform_data)
        transform.changed.connect(self.update_transform_sequence)
        transform.delete_requested.connect(self.remove_transform)
        self.transforms.append(transform)
        self.transform_layout.addWidget(transform)
        self.update_transform_sequence()

    def remove_transform(self, transform):
        self.transforms.remove(transform)
        transform.setParent(None)
        transform.deleteLater()
        self.update_transform_sequence()

    def update_output_dir(self, value):
        self.cfg.outputDir = value
        self.refresh_tree()

    def update_particle_count(self, value):
        if value:
            self.cfg.particleCount = int(value)
            self.refresh_tree()

    def update_geometry_type(self, button):
        self.cfg.geometryType = button.text().lower()
        self.dicom_edit.setEnabled(False if self.cfg.geometryType == "parametrized" else True)
        self.refresh_tree()

    def update_physics(self, value):
        self.cfg.physics = [p.strip() for p in value.split(",") if p.strip()]
        self.refresh_tree()

    def update_dicom_dir(self, value):
        self.cfg.dicomDir = value
        self.refresh_tree()

    def update_transform_sequence(self):
        sequence = []
        for transform in self.transforms:
            matrix = transform.get_matrix()
            if matrix is not None:
                sequence.append(matrix)
        self.cfg.transformSequence = sequence
        self.refresh_tree()

    def save_to_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            None,
            "YAML files (*.yaml);;All Files (*)",
        )
        if not filename:
            return

        try:
            self.cfg.validate()
        except ValueError as exc:
            QMessageBox.critical(self, "Invalid configuration", str(exc), QMessageBox.Ok)
            return

        ConfigHandler.save(self.cfg, filename)