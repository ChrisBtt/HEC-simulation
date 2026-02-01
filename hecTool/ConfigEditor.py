from PyQt5.QtWidgets import (QMainWindow, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QPushButton, QFileDialog, QHBoxLayout,
                             QLineEdit, QLabel, QGridLayout, QButtonGroup, QRadioButton,
                             QScrollArea, QFrame, QMessageBox, QCheckBox, QTabWidget, QListView,
                             QTreeView, QAbstractItemView)
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtCore import pyqtSignal

from hecTool.ConfigModel import SimulationConfig, TumorConfig, TransformStep
from hecTool.ConfigHandler import save_config


class TransformStepEditor(QWidget):
    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)

    def __init__(self, data: TransformStep = None, show_shear=True, parent=None):
        super().__init__(parent)
        self.show_shear = show_shear
        self.initUI()
        if data:
            self.set_value(data)

    def initUI(self):
        layout = QGridLayout(self)

        # Time
        layout.addWidget(QLabel("Time (s):"), 0, 0)
        self.time_s = QLineEdit("0.0")
        self.time_s.setValidator(QDoubleValidator())
        layout.addWidget(self.time_s, 0, 1)

        # Translation
        layout.addWidget(QLabel("Translation (mm):"), 1, 0)
        self.tx = QLineEdit("0.0")
        self.ty = QLineEdit("0.0")
        self.tz = QLineEdit("0.0")
        layout.addWidget(self.tx, 1, 1)
        layout.addWidget(self.ty, 1, 2)
        layout.addWidget(self.tz, 1, 3)

        # Rotation
        layout.addWidget(QLabel("Rotation (deg):"), 2, 0)
        self.rx = QLineEdit("0.0")
        self.ry = QLineEdit("0.0")
        self.rz = QLineEdit("0.0")
        layout.addWidget(self.rx, 2, 1)
        layout.addWidget(self.ry, 2, 2)
        layout.addWidget(self.rz, 2, 3)

        # Scale
        layout.addWidget(QLabel("Scale:"), 3, 0)
        self.sx = QLineEdit("1.0")
        self.sy = QLineEdit("1.0")
        self.sz = QLineEdit("1.0")
        layout.addWidget(self.sx, 3, 1)
        layout.addWidget(self.sy, 3, 2)
        layout.addWidget(self.sz, 3, 3)

        # Shear
        self.shear_label = QLabel("Shear:")
        self.shxy = QLineEdit("0.0")
        self.shxz = QLineEdit("0.0")
        self.shyz = QLineEdit("0.0")
        layout.addWidget(self.shear_label, 4, 0)
        layout.addWidget(self.shxy, 4, 1)
        layout.addWidget(self.shxz, 4, 2)
        layout.addWidget(self.shyz, 4, 3)

        if not self.show_shear:
            self.shear_label.hide()
            self.shxy.hide()
            self.shxz.hide()
            self.shyz.hide()

        btn_layout = QHBoxLayout()
        up_btn = QPushButton("↑")
        up_btn.clicked.connect(lambda: self.move_up_requested.emit(self))
        down_btn = QPushButton("↓")
        down_btn.clicked.connect(lambda: self.move_down_requested.emit(self))
        delete_btn = QPushButton("Delete Step")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout, 5, 0, 1, 4)

        for widget in [self.time_s, self.tx, self.ty, self.tz, self.rx, self.ry, self.rz,
                       self.sx, self.sy, self.sz, self.shxy, self.shxz, self.shyz]:
            widget.setValidator(QDoubleValidator())
            widget.textChanged.connect(self.changed.emit)

    def get_value(self) -> TransformStep:
        return TransformStep(
            time_s=float(self.time_s.text() or 0),
            translation_mm=[float(self.tx.text() or 0), float(self.ty.text() or 0), float(self.tz.text() or 0)],
            rotation_deg=[float(self.rx.text() or 0), float(self.ry.text() or 0), float(self.rz.text() or 0)],
            scale=[float(self.sx.text() or 1), float(self.sy.text() or 1), float(self.sz.text() or 1)],
            shear=[float(self.shxy.text() or 0), float(self.shxz.text() or 0), float(self.shyz.text() or 0)]
        )

    def set_value(self, data: TransformStep):
        self.time_s.setText(str(data.time_s))
        mapping = [
            (data.translation_mm, [self.tx, self.ty, self.tz]),
            (data.rotation_deg, [self.rx, self.ry, self.rz]),
            (data.scale, [self.sx, self.sy, self.sz]),
            (data.shear, [self.shxy, self.shxz, self.shyz])
        ]
        for values, widgets in mapping:
            for val, widget in zip(values, widgets):
                widget.setText(str(val))


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

    def set_value(self, values):
        for edit, val in zip(self.edits, values):
            edit.setText(str(val))


class StringItemEditor(QWidget):
    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)

    def __init__(self, value="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit(value)
        self.edit.textChanged.connect(self.changed.emit)
        
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedWidth(25)
        self.up_btn.clicked.connect(lambda: self.move_up_requested.emit(self))
        
        self.down_btn = QPushButton("↓")
        self.down_btn.setFixedWidth(25)
        self.down_btn.clicked.connect(lambda: self.move_down_requested.emit(self))

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedWidth(30)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        
        layout.addWidget(self.edit)
        layout.addWidget(self.up_btn)
        layout.addWidget(self.down_btn)
        layout.addWidget(self.del_btn)

    def get_value(self):
        return self.edit.text().strip()

    def set_value(self, value):
        self.edit.setText(value)


class CollectionEditor(QWidget):
    changed = pyqtSignal()

    def __init__(self, item_class, title="Items", parent=None):
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

    def add_item(self, data=None, **kwargs):
        editor = self.item_class(data, **kwargs)
        editor.changed.connect(self.changed.emit)
        editor.delete_requested.connect(self.remove_item)
        if hasattr(editor, "move_up_requested"):
            editor.move_up_requested.connect(self.move_item_up)
        if hasattr(editor, "move_down_requested"):
            editor.move_down_requested.connect(self.move_item_down)
        self.editors.append(editor)
        self.item_layout.insertWidget(self.item_layout.count() - 1, editor)
        self.changed.emit()

    def add_items(self, list_of_data, **kwargs):
        for data in list_of_data:
            self.add_item(data, **kwargs)

    def move_item_up(self, editor):
        idx = self.editors.index(editor)
        if idx > 0:
            self.editors[idx], self.editors[idx - 1] = self.editors[idx - 1], self.editors[idx]
            # Update UI layout
            self.item_layout.removeWidget(editor)
            self.item_layout.insertWidget(idx - 1, editor)
            self.changed.emit()

    def move_item_down(self, editor):
        idx = self.editors.index(editor)
        if idx < len(self.editors) - 1:
            self.editors[idx], self.editors[idx + 1] = self.editors[idx + 1], self.editors[idx]
            # Update UI layout
            self.item_layout.removeWidget(editor)
            self.item_layout.insertWidget(idx + 1, editor)
            self.changed.emit()

    def remove_item(self, editor):
        self.editors.remove(editor)
        editor.setParent(None)
        editor.deleteLater()
        self.changed.emit()

    def get_values(self):
        return [e.get_value() for e in self.editors if e.get_value() is not None]


class TumorEditor(QWidget):
    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)

    def __init__(self, data: TumorConfig = None, parent=None):
        super().__init__(parent)
        self.initUI()
        if data:
            self.set_value(data)

    def initUI(self):
        layout = QVBoxLayout(self)

        # Material
        mat_layout = QHBoxLayout()
        mat_layout.addWidget(QLabel("Material:"))
        self.material = QLineEdit("G4_WATER")
        self.material.textChanged.connect(self.changed.emit)
        mat_layout.addWidget(self.material)
        layout.addLayout(mat_layout)

        # Base Placement
        self.trans = VectorEditor(["Trans X:", "Y:", "Z:"], [0.0, 0.0, 0.0])
        self.rot = VectorEditor(["Rot X:", "Y:", "Z:"], [0.0, 0.0, 0.0])
        self.radius = VectorEditor(["Radius X:", "Y:", "Z:"], [10.0, 10.0, 10.0])
        self.trans.changed.connect(self.changed.emit)
        self.rot.changed.connect(self.changed.emit)
        self.radius.changed.connect(self.changed.emit)
        layout.addWidget(self.trans)
        layout.addWidget(self.rot)
        layout.addWidget(self.radius)

        # Transform Sequence
        layout.addWidget(QLabel("Transform Sequence:"))
        self.sequence_editor = CollectionEditor(TransformStepEditor, "Step")
        self.sequence_editor.add_btn.disconnect()
        self.sequence_editor.add_btn.clicked.connect(lambda: self.sequence_editor.add_item(show_shear=False))
        self.sequence_editor.changed.connect(self.changed.emit)
        layout.addWidget(self.sequence_editor)

        btn_layout = QHBoxLayout()
        up_btn = QPushButton("Move Up")
        up_btn.clicked.connect(lambda: self.move_up_requested.emit(self))
        down_btn = QPushButton("Move Down")
        down_btn.clicked.connect(lambda: self.move_down_requested.emit(self))
        del_btn = QPushButton("Remove Tumor")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

    def get_value(self) -> TumorConfig:
        return TumorConfig(
            topas_material=self.material.text(),
            translation_mm=self.trans.get_value(),
            rotation_deg=self.rot.get_value(),
            radius_mm=self.radius.get_value(),
            transform_sequence=self.sequence_editor.get_values()
        )

    def set_value(self, data: TumorConfig):
        self.material.setText(data.topas_material)
        self.trans.set_value(data.translation_mm)
        self.rot.set_value(data.rotation_deg)
        self.radius.set_value(data.radius_mm)
        # Clear and refill sequence
        for ed in list(self.sequence_editor.editors):
            self.sequence_editor.remove_item(ed)
        for step in data.transform_sequence:
            self.sequence_editor.add_item(step, show_shear=False)


class ConfigGUI(QMainWindow):
    def __init__(self, cfg: SimulationConfig):
        super().__init__()
        self._loading = True
        self.cfg = cfg
        self.saved_filename = None
        self.initUI()
        self.load_config_to_ui()
        self._loading = False
        self.on_changed()

    def initUI(self):
        self.setWindowTitle('TOPAS Simulation Config Editor')
        self.setGeometry(100, 100, 1000, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side: Editor
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_container = QWidget()
        self.editor_layout = QVBoxLayout(editor_container)
        editor_scroll.setWidget(editor_container)
        main_layout.addWidget(editor_scroll, stretch=2)

        # Right side: Tree View
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel('Configuration Preview')
        tree_layout.addWidget(self.tree)

        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_to_file)
        tree_layout.addWidget(save_btn)
        main_layout.addWidget(tree_container, stretch=1)

        self.setup_editors()

    def setup_editors(self):
        # General Settings
        gen_group = QFrame()
        gen_group.setFrameStyle(QFrame.StyledPanel)
        gen_layout = QGridLayout(gen_group)
        gen_layout.addWidget(QLabel("<b>General Settings</b>"), 0, 0, 1, 2)

        gen_layout.addWidget(QLabel("Interpolation Steps:"), 1, 0)
        self.interp_steps = QLineEdit()
        self.interp_steps.setValidator(QIntValidator(0, 1000))
        self.interp_steps.textChanged.connect(self.on_changed)
        gen_layout.addWidget(self.interp_steps, 1, 1)

        gen_layout.addWidget(QLabel("Random Seed:"), 2, 0)
        self.seed = QLineEdit()
        self.seed.setValidator(QIntValidator())
        self.seed.textChanged.connect(self.on_changed)
        gen_layout.addWidget(self.seed, 2, 1)

        self.editor_layout.addWidget(gen_group)

        # Physics and Includes
        col_layout = QHBoxLayout()
        self.physics_editor = CollectionEditor(StringItemEditor,  "Physics Module")
        self.physics_editor.changed.connect(self.on_changed)
        
        self.includes_editor = CollectionEditor(StringItemEditor, "Include File")
        self.includes_editor.changed.connect(self.on_changed)
        self.browse_includes_btn = QPushButton("Browse Files")
        self.browse_includes_btn.clicked.connect(self.browse_includes)
        self.includes_editor.layout().addWidget(self.browse_includes_btn)

        col_layout.addWidget(QLabel("Physics:"))
        col_layout.addWidget(self.physics_editor)
        col_layout.addWidget(QLabel("Includes:"))
        col_layout.addWidget(self.includes_editor)
        self.editor_layout.addLayout(col_layout)

        # Tabs for Patient and Tumors
        self.tabs = QTabWidget()
        self.editor_layout.addWidget(self.tabs)

        # Patient Tab
        self.patient_widget = QWidget()
        self.patient_layout = QVBoxLayout(self.patient_widget)

        # Patient Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.patient_type = QRadioButton("parametrized")
        self.patient_type_3dct = QRadioButton("3dct")
        self.patient_type_4dct = QRadioButton("4dct")
        self.patient_type_group = QButtonGroup()
        self.patient_type_group.addButton(self.patient_type)
        self.patient_type_group.addButton(self.patient_type_3dct)
        self.patient_type_group.addButton(self.patient_type_4dct)
        self.patient_type.toggled.connect(self.on_changed)
        self.patient_type_3dct.toggled.connect(self.on_changed)
        self.patient_type_4dct.toggled.connect(self.on_changed)
        type_layout.addWidget(self.patient_type)
        type_layout.addWidget(self.patient_type_3dct)
        type_layout.addWidget(self.patient_type_4dct)
        self.patient_layout.addLayout(type_layout)

        # Parametrized specific
        self.param_group = QFrame()
        param_layout = QGridLayout(self.param_group)
        self.param_size = VectorEditor(["Size X:", "Y:", "Z:"], [100.0, 100.0, 100.0])
        self.param_spacing = VectorEditor(["Spacing X:", "Y:", "Z:"], [1.0, 1.0, 1.0])
        self.param_hu = QLineEdit("0")
        self.param_hu.setValidator(QDoubleValidator())
        self.param_size.changed.connect(self.on_changed)
        self.param_spacing.changed.connect(self.on_changed)
        self.param_hu.textChanged.connect(self.on_changed)
        param_layout.addWidget(QLabel("Size (mm):"), 0, 0)
        param_layout.addWidget(self.param_size, 0, 1)
        param_layout.addWidget(QLabel("Spacing (mm):"), 1, 0)
        param_layout.addWidget(self.param_spacing, 1, 1)
        param_layout.addWidget(QLabel("Density (HU):"), 2, 0)
        param_layout.addWidget(self.param_hu, 2, 1)
        self.patient_layout.addWidget(self.param_group)

        # DICOM specific
        self.dicom_label = QLabel("DICOM Directories:")
        self.dicom_editor = CollectionEditor(StringItemEditor, "DICOM Directory")
        self.dicom_editor.changed.connect(self.on_changed)
        self.browse_dicom_btn = QPushButton("Browse Folders")
        self.browse_dicom_btn.clicked.connect(self.browse_dicoms)
        self.dicom_editor.layout().addWidget(self.browse_dicom_btn)
        
        self.patient_layout.addWidget(self.dicom_label)
        self.patient_layout.addWidget(self.dicom_editor)

        # Common patient settings
        self.scoring_bins = VectorEditor(["Bins X:", "Y:", "Z:"], [25, 25, 25])
        self.patient_trans = VectorEditor(["Trans X:", "Y:", "Z:"], [0.0, 0.0, 0.0])
        self.patient_rot = VectorEditor(["Rot X:", "Y:", "Z:"], [0.0, 0.0, 0.0])
        self.use_center = QCheckBox("Use Center as Transform Origin")
        self.scoring_bins.changed.connect(self.on_changed)
        self.patient_trans.changed.connect(self.on_changed)
        self.patient_rot.changed.connect(self.on_changed)
        self.use_center.stateChanged.connect(self.on_changed)

        self.patient_layout.addWidget(QLabel("Scoring Bins:"))
        self.patient_layout.addWidget(self.scoring_bins)
        self.patient_layout.addWidget(QLabel("Base Placement:"))
        self.patient_layout.addWidget(self.patient_trans)
        self.patient_layout.addWidget(self.patient_rot)
        self.patient_layout.addWidget(self.use_center)

        self.patient_seq = CollectionEditor(TransformStepEditor, "Step")
        self.patient_seq.changed.connect(self.on_changed)
        self.patient_layout.addWidget(QLabel("Transform Sequence:"))
        self.patient_layout.addWidget(self.patient_seq)

        self.tabs.addTab(self.patient_widget, "Patient")

        # Tumors Tab
        self.tumors_widget = QWidget()
        self.tumors_layout = QVBoxLayout(self.tumors_widget)
        self.tumors_collection = CollectionEditor(TumorEditor, "Tumor")
        self.tumors_collection.changed.connect(self.on_changed)
        self.tumors_layout.addWidget(self.tumors_collection)
        self.tabs.addTab(self.tumors_widget, "Tumors")

    def load_config_to_ui(self):
        self.interp_steps.setText(str(self.cfg.interpolation_steps))
        self.seed.setText(str(self.cfg.seed))

        for p in self.cfg.physics: self.physics_editor.add_item(p)
        for i in self.cfg.include_files: self.includes_editor.add_item(i)

        p = self.cfg.patient
        if p.type == "parametrized": self.patient_type.setChecked(True)
        elif p.type == "3dct": self.patient_type_3dct.setChecked(True)
        elif p.type == "4dct": self.patient_type_4dct.setChecked(True)

        patient_params = p.parameters
        self.param_size.set_value(patient_params.size_mm)
        self.param_spacing.set_value(patient_params.spacing_mm)
        self.param_hu.setText(str(patient_params.radiodensity_hu))

        for d in p.dicom_directories: self.dicom_editor.add_item(d)
        self.scoring_bins.set_value(p.scoring_bins)
        self.patient_trans.set_value(p.translation_mm)
        self.patient_rot.set_value(p.rotation_deg)
        self.use_center.setChecked(p.use_center_as_transform_origin)
        for step in p.transform_sequence: self.patient_seq.add_item(step)

        for tumor in self.cfg.tumors: self.tumors_collection.add_item(tumor)

    def browse_includes(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Include Files", "", "TOPAS Files (*.txt);;All Files (*)")
        if files:
            self.includes_editor.add_items(files)

    def browse_dicoms(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        
        # Enable multiple selection in QFileDialog for directories
        # By default, Directory mode only allows selecting one directory.
        # We find the internal view and set it to ExtendedSelection.
        file_view = dialog.findChild(QListView, "listView")
        if file_view:
            file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tree_view = dialog.findChild(QTreeView)
        if tree_view:
            tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        if dialog.exec_():
            paths = dialog.selectedFiles()
            if paths:
                self.dicom_editor.add_items(paths)

    def on_changed(self):
        if self._loading: return

        # Update model from UI
        self.cfg.interpolation_steps = int(self.interp_steps.text() or 0)
        self.cfg.seed = int(self.seed.text() or 1)
        self.cfg.physics = self.physics_editor.get_values()
        self.cfg.include_files = self.includes_editor.get_values()

        p = self.cfg.patient
        is_parametrized = self.patient_type.isChecked()
        is_4dct = self.patient_type_4dct.isChecked()

        if is_parametrized:
            p.type = "parametrized"
        elif self.patient_type_3dct.isChecked():
            p.type = "3dct"
        elif is_4dct:
            p.type = "4dct"

        # Enable/Disable fields based on type
        self.param_group.setEnabled(is_parametrized)
        self.dicom_editor.setEnabled(not is_parametrized)
        self.dicom_label.setEnabled(not is_parametrized)
        self.patient_seq.setEnabled(not is_4dct)

        # Clear data for disabled fields and update enabled fields
        if is_parametrized:
            p.parameters.size_mm = self.param_size.get_value()
            p.parameters.spacing_mm = self.param_spacing.get_value()
            p.parameters.radiodensity_hu = int(self.param_hu.text() or 0)
            p.dicom_directories = []
        else:
            p.parameters.size_mm = [100.0, 100.0, 100.0]
            p.parameters.spacing_mm = [1.0, 1.0, 1.0]
            p.parameters.radiodensity_hu = 0
            p.dicom_directories = self.dicom_editor.get_values()

        p.scoring_bins = [int(v) for v in self.scoring_bins.get_value()]
        p.translation_mm = self.patient_trans.get_value()
        p.rotation_deg = self.patient_rot.get_value()
        p.use_center_as_transform_origin = self.use_center.isChecked()

        if is_4dct:
            p.transform_sequence = []
        else:
            p.transform_sequence = self.patient_seq.get_values()

        self.cfg.tumors = self.tumors_collection.get_values()

        self.refresh_tree()

    def refresh_tree(self):
        self.tree.clear()
        self.populate_tree(self.tree, self.cfg.to_dict())
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)

    def populate_tree(self, tree, data, parent=None):
        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem(parent or tree)
                item.setText(0, str(key))
                self.populate_tree(tree, value, item)
        elif isinstance(data, list):
            # Check if it's a "vector" (list of numbers)
            if all(isinstance(x, (int, float)) for x in data) and len(data) > 0:
                item = QTreeWidgetItem(parent)
                item.setText(0, str(data))
            else:
                for idx, value in enumerate(data):
                    item = QTreeWidgetItem(parent)
                    item.setText(0, f"[{idx}]")
                    self.populate_tree(tree, value, item)
        else:
            item = QTreeWidgetItem(parent)
            item.setText(0, str(data))

    def save_to_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Configuration", "", "YAML Files (*.yaml)")
        if filename:
            try:
                save_config(self.cfg, filename)
                self.saved_filename = filename
                QMessageBox.information(self, "Success", f"Configuration saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save configuration: {e}")


def main():
    import sys
    import argparse
    from hecTool.ConfigHandler import load_config
    from PyQt5.QtWidgets import QApplication

    parser = argparse.ArgumentParser(description="TOPAS Configuration Editor")
    parser.add_argument("filename", nargs="?", help="Path to an existing YAML configuration file")
    args = parser.parse_args()

    if args.filename:
        try:
            cfg = load_config(args.filename)
        except Exception as e:
            print(f"Error loading config: {e}")
            return
    else:
        cfg = SimulationConfig()

    app = QApplication(sys.argv)
    gui = ConfigGUI(cfg)
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
