from PyQt5.QtWidgets import (QMainWindow, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QPushButton, QFileDialog, QHBoxLayout,
                             QLineEdit, QLabel, QGridLayout, QButtonGroup, QRadioButton,
                             QScrollArea, QFrame, QMessageBox, QListWidgetItem)
from PyQt5.QtGui import QRegExpValidator, QDoubleValidator, QIntValidator
from PyQt5.QtCore import pyqtSignal, QRegExp

from hecTool.ConfigModel import SimulationConfig
from hecTool.ConfigHandler import save_config
from hecTool.TransformAffine import TransformParams, params_to_flat_4x4, flat_4x4_to_params


class TransformEditor(QWidget):
    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, transform_data=None, parent=None):
        super().__init__(parent)
        self.initUI()
        if transform_data:
            self.set_value(transform_data)

    def initUI(self):
        layout = QGridLayout(self)

        # Translation
        layout.addWidget(QLabel("Translation (mm):"), 0, 0)
        self.tx = QLineEdit("0")
        self.ty = QLineEdit("0")
        self.tz = QLineEdit("0")
        layout.addWidget(self.tx, 0, 1)
        layout.addWidget(self.ty, 0, 2)
        layout.addWidget(self.tz, 0, 3)

        # Rotation
        layout.addWidget(QLabel("Rotation (deg):"), 1, 0)
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
            widget.setValidator(QDoubleValidator())
            widget.textChanged.connect(self.on_change)

    def on_change(self):
        self.changed.emit()

    def get_value(self):
        try:
            params = TransformParams(
                translation=(float(self.tx.text()), float(self.ty.text()), float(self.tz.text())),
                rotation_deg=(float(self.rx.text()), float(self.ry.text()), float(self.rz.text())),
                scale=(float(self.sx.text()), float(self.sy.text()), float(self.sz.text())),
                shear=(
                    float(self.shxy.text()), float(self.shyx.text()),
                    float(self.shxz.text()), float(self.shzx.text()),
                    float(self.shyz.text()), float(self.shzy.text()),
                ),
            )
            return params_to_flat_4x4(params)
        except ValueError:
            return None

    def set_value(self, data):
        if isinstance(data, list) and len(data) == 16:
            p = flat_4x4_to_params(data)
            params = {
                "translation": list(p.translation), "rotation": list(p.rotation_deg),
                "scale": list(p.scale), "shear": list(p.shear),
            }
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


class VectorEditor(QWidget):
    changed = pyqtSignal()

    def __init__(self, labels, values, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edits = []
        for label, val in zip(labels, values):
            layout.addWidget(QLabel(label))
            edit = QLineEdit(str(val))
            edit.setValidator(QDoubleValidator())
            edit.textChanged.connect(self.changed.emit)
            layout.addWidget(edit)
            self.edits.append(edit)

    def get_value(self):
        return [float(e.text() or 0) for e in self.edits]


class StringItemEditor(QWidget):
    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, value="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit(value)
        self.edit.textChanged.connect(self.changed.emit)
        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedWidth(30)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        layout.addWidget(self.edit)
        layout.addWidget(self.del_btn)

    def get_value(self):
        return self.edit.text().strip()

    def set_value(self, value):
        self.edit.setText(value)

class CollectionEditor(QWidget):
    changed = pyqtSignal()

    def __init__(self, item_class, initial_data=None, title="Items", parent=None):
        super().__init__(parent)
        self.item_class = item_class
        layout = QVBoxLayout(self)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        self.item_layout = QVBoxLayout(container)
        self.item_layout.addStretch()
        self.scroll.setWidget(container)
        layout.addWidget(self.scroll)

        self.add_btn = QPushButton(f"Add {title}")
        self.add_btn.clicked.connect(lambda: self.add_item())
        layout.addWidget(self.add_btn)

        self.editors = []
        if initial_data:
            for data in initial_data:
                self.add_item(data)

    def add_item(self, data=None):
        editor = self.item_class(data)
        editor.changed.connect(self.changed.emit)
        editor.delete_requested.connect(self.remove_item)
        self.editors.append(editor)
        # Insert before the stretch
        self.item_layout.insertWidget(self.item_layout.count() - 1, editor)
        self.changed.emit()

    def remove_item(self, editor):
        self.editors.remove(editor)
        editor.setParent(None)
        editor.deleteLater()
        self.changed.emit()

    def get_values(self):
        return [e.get_value() for e in self.editors if e.get_value() is not None]

class ConfigGUI(QMainWindow):
    def __init__(self, cfg: SimulationConfig):
        super().__init__()
        self.cfg = cfg
        self.saved_filename = None

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
            elif isinstance(value, list):
                # Represent lists as expandable nodes so long values (e.g., matrices) don't get forced into one line.
                item.setText(0, str(key))

                for idx, elem in enumerate(value):
                    child = QTreeWidgetItem(item)
                    child.setText(0, f"{idx}: {elem}")
            else:
                item.setText(0, f"{key}: {value}")

    def setup_parameter_editors(self):
        editor_layout = self.centralWidget().layout().itemAt(0).layout()

        # Physics
        editor_layout.addWidget(QLabel("Physics:"), 0, 0)
        self.physics_editor = CollectionEditor(StringItemEditor, self.cfg.physics, "Physics")
        self.physics_editor.changed.connect(self.update_physics)
        editor_layout.addWidget(self.physics_editor, 0, 1)

        # Random Seed
        seed_label = QLabel("Random Seed:")
        self.seed_edit = QLineEdit(str(self.cfg.seed))
        self.seed_edit.setValidator(QIntValidator())
        self.seed_edit.textChanged.connect(self.update_seed)
        editor_layout.addWidget(seed_label, 1, 0)
        editor_layout.addWidget(self.seed_edit, 1, 1)

        # Include Files
        editor_layout.addWidget(QLabel("Include Files:"), 2, 0)
        self.include_files_editor = CollectionEditor(StringItemEditor, self.cfg.includeFiles, "File")
        self.include_files_editor.changed.connect(self.update_include_files)
        editor_layout.addWidget(self.include_files_editor, 2, 1)

        # Geometry
        geometry_label = QLabel("Geometry Type:")
        editor_layout.addWidget(geometry_label, 3, 0)

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
        editor_layout.addLayout(geometry_layout, 3, 1)

        # Parametric Geometry (Visible only if parametrized)
        self.pg_label = QLabel("Parametric Geometry:")
        self.pg_widget = QWidget()
        pg_vbox = QVBoxLayout(self.pg_widget)

        self.pg_size = VectorEditor(["X:", "Y:", "Z:"], self.cfg.parametricGeometry.size_mm)
        self.pg_size.changed.connect(self.update_parametrized_geometry)
        pg_vbox.addWidget(QLabel("Size (mm):"))
        pg_vbox.addWidget(self.pg_size)

        self.pg_spacing = VectorEditor(["X:", "Y:", "Z:"], self.cfg.parametricGeometry.spacing_mm)
        self.pg_spacing.changed.connect(self.update_parametrized_geometry)
        pg_vbox.addWidget(QLabel("Spacing (mm):"))
        pg_vbox.addWidget(self.pg_spacing)

        mat_layout = QHBoxLayout()
        self.mat_name = QLineEdit(self.cfg.parametricGeometry.material.name)
        self.mat_hu = QLineEdit(str(self.cfg.parametricGeometry.material.hu))
        self.mat_hu.setValidator(QDoubleValidator())
        self.mat_name.textChanged.connect(self.update_parametrized_geometry)
        self.mat_hu.textChanged.connect(self.update_parametrized_geometry)
        mat_layout.addWidget(QLabel("Material Name:"))
        mat_layout.addWidget(self.mat_name)
        mat_layout.addWidget(QLabel("Density (HU):"))
        mat_layout.addWidget(self.mat_hu)
        pg_vbox.addLayout(mat_layout)

        editor_layout.addWidget(self.pg_label, 4, 0)
        editor_layout.addWidget(self.pg_widget, 4, 1)

        # Output Dir
        output_label = QLabel("Output Directory:")
        self.output_edit = QLineEdit(self.cfg.outputDir)
        self.output_edit.textChanged.connect(self.update_output_dir)
        editor_layout.addWidget(output_label, 5, 0)
        editor_layout.addWidget(self.output_edit, 5, 1)

        # DICOM Dirs
        self.dicom_label = QLabel("DICOM Directories:")
        self.dicom_editor = CollectionEditor(StringItemEditor, self.cfg.dicomDirs, "Directory")
        self.dicom_editor.changed.connect(self.update_dicom_dirs)
        editor_layout.addWidget(self.dicom_label, 6, 0)
        editor_layout.addWidget(self.dicom_editor, 6, 1)

        # Transforms
        self.transform_label = QLabel("Transforms:")
        self.transform_editor = CollectionEditor(TransformEditor, self.cfg.transformSequence, "Transform")
        self.transform_editor.changed.connect(self.update_transform_sequence)
        editor_layout.addWidget(self.transform_label, 7, 0)
        editor_layout.addWidget(self.transform_editor, 7, 1)

        # Placement
        editor_layout.addWidget(QLabel("Placement:"), 8, 0)
        self.placement_widget = QWidget()
        pl_vbox = QVBoxLayout(self.placement_widget)

        self.pl_trans = VectorEditor(["X:", "Y:", "Z:"], self.cfg.placement.translation_mm)
        self.pl_rot = VectorEditor(["X:", "Y:", "Z:"], self.cfg.placement.rotation_deg)
        self.pl_trans.changed.connect(self.update_placement)
        self.pl_rot.changed.connect(self.update_placement)

        pl_vbox.addWidget(QLabel("Translation (mm):"))
        pl_vbox.addWidget(self.pl_trans)
        pl_vbox.addWidget(QLabel("Rotation (deg):"))
        pl_vbox.addWidget(self.pl_rot)
        editor_layout.addWidget(self.placement_widget, 8, 1)

        self.toggle_geometry_fields()

    def toggle_geometry_fields(self):
        is_param = self.cfg.geometryType == "parametrized"
        is_4dct = self.cfg.geometryType == "4dct"

        self.pg_label.setVisible(is_param)
        self.pg_widget.setVisible(is_param)
        self.dicom_label.setVisible(not is_param)
        self.dicom_editor.setVisible(not is_param)
        self.transform_label.setVisible(not is_4dct)
        self.transform_editor.setVisible(not is_4dct)

    def update_output_dir(self, value):
        self.cfg.outputDir = value
        self.refresh_tree()

    def update_physics(self):
        self.cfg.physics = self.physics_editor.get_values()
        self.refresh_tree()

    def update_seed(self, value):
        if value:
            self.cfg.seed = int(value)
            self.refresh_tree()

    def update_include_files(self):
        self.cfg.includeFiles = self.include_files_editor.get_values()
        self.refresh_tree()

    def update_geometry_type(self, button):
        self.cfg.geometryType = button.text().lower()
        self.toggle_geometry_fields()
        self.refresh_tree()

    def update_parametrized_geometry(self):
        self.cfg.parametricGeometry.size_mm = self.pg_size.get_value()
        self.cfg.parametricGeometry.spacing_mm = self.pg_spacing.get_value()
        self.cfg.parametricGeometry.material.name = self.mat_name.text()
        try:
            self.cfg.parametricGeometry.material.hu = float(self.mat_hu.text() or 0)
        except ValueError:
            pass
        self.refresh_tree()

    def update_dicom_dirs(self):
        self.cfg.dicomDirs = self.dicom_editor.get_values()
        self.refresh_tree()

    def update_transform_sequence(self):
        self.cfg.transformSequence = self.transform_editor.get_values()
        self.refresh_tree()

    def update_placement(self):
        self.cfg.placement.translation_mm = self.pl_trans.get_value()
        self.cfg.placement.rotation_deg = self.pl_rot.get_value()
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

        save_config(self.cfg, filename)
        self.saved_filename = filename