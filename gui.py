"""
ColorFulData: GUI script
====================================================================================
Created on 31/08/2026
Author: Bram SAMYN
====================================================================================
Script Description:
This  script handles the frontend of the ColorFulData
application, which is built using PyQt6. Allowing for a user-friendly way to load
and extract data from color mapped images.
====================================================================================
"""
#===PyQt6 Imports===
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QGraphicsView, QGraphicsScene, 
                             QMessageBox, QGraphicsEllipseItem, QGraphicsTextItem,
                             QLabel, QLineEdit, QFormLayout, QGroupBox, QGraphicsRectItem, 
                             QDialog, QDialogButtonBox, QComboBox, QFormLayout, QLabel, 
                             QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView)

from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QDoubleValidator, QImage, QAction, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF

#===Plotting Imports===
import matplotlib as mpl 
#===Other Imports===
import numpy as np


class ImageCanvas(QGraphicsView):
    # Signals
    point_added = pyqtSignal(int)
    points_complete = pyqtSignal(list)
    colorbar_selected = pyqtSignal(QRectF)  # NEW: Emits the bounding box

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        # Axis setting state
        self.is_setting_axes = False
        self.reference_points = []
        self.markers = []
        
        # Colorbar selection state
        self.is_selecting_colorbar = False
        self.colorbar_rect_item = None  # Stores the visual bounding box

    def start_setting_axes(self):
        self.is_setting_axes = True
        self.is_selecting_colorbar = False
        self.reference_points.clear()
        
        for item in self.markers:
            if item.scene() == self.scene():
                self.scene().removeItem(item)
        self.markers.clear()
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def start_colorbar_selection(self):
        """Activates the rubber band drag for selecting the colorbar."""
        self.is_setting_axes = False
        self.is_selecting_colorbar = True
        
        # Enable the native rubber band selection tool
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event):
        if self.is_setting_axes and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.reference_points.append(scene_pos)
            point_index = len(self.reference_points)
            
            self._draw_marker(scene_pos, point_index)
            self.point_added.emit(point_index)
            
            if point_index == 3:
                self.is_setting_axes = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.points_complete.emit(self.reference_points)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Capture the rubber band rectangle BEFORE the super class processes the release
        rubber_rect = self.rubberBandRect()
        
        super().mouseReleaseEvent(event)
        
        # If we were selecting a colorbar and the user actually drew a box
        if self.is_selecting_colorbar and not rubber_rect.isNull() and not rubber_rect.isEmpty():
            # Map the UI viewport rectangle to the actual image/scene coordinates
            scene_polygon = self.mapToScene(rubber_rect)
            scene_rect = scene_polygon.boundingRect()
            
            # Remove the old box if it exists
            if self.colorbar_rect_item and self.colorbar_rect_item.scene() == self.scene():
                self.scene().removeItem(self.colorbar_rect_item)
                
            # Draw a permanent blue, semi-transparent rectangle
            self.colorbar_rect_item = QGraphicsRectItem(scene_rect)
            pen = QPen(QColor(0, 150, 255))
            pen.setWidth(2)
            self.colorbar_rect_item.setPen(pen)
            self.colorbar_rect_item.setBrush(QBrush(QColor(0, 150, 255, 50)))
            self.scene().addItem(self.colorbar_rect_item)
            
            # Reset UI states
            self.is_selecting_colorbar = False
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
            # Send the coordinates back to the main window
            self.colorbar_selected.emit(scene_rect)

    def _draw_marker(self, pos, index):
        radius = 4
        ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2)
        ellipse.setPen(QPen(QColor("red")))
        ellipse.setBrush(QBrush(QColor("red")))
        self.scene().addItem(ellipse)
        
        labels = ["Origin", "X-Axis", "Y-Axis"]
        text = QGraphicsTextItem(f"{index}. {labels[index - 1]}")
        text.setDefaultTextColor(QColor("red"))
        text.setPos(pos.x() + 5, pos.y() + 5)
        self.scene().addItem(text)
        self.markers.extend([ellipse, text])

class CFDGur(QMainWindow):
    def __init__(self):
        super().__init__()
        version_nr = "v1.0.0"
        self.setWindowTitle(f"ColorFulData - {version_nr}")
        self.setWindowIcon(QIcon("Images/Logo/ColorFulData_Logo.png"))
        self.setGeometry(100, 100, 1000, 700)
        
        self.current_image_path = None
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Toolbar (Left Panel)
        toolbar_layout = QVBoxLayout()
        
        self.btn_load = QPushButton(QIcon("Images/Icons/image--plus.png"), "1. Load Image")
        #self.btn_bg_remove = QPushButton("2. Remove Background") #will be moved to edit menu
        self.btn_set_axes = QPushButton(QIcon("Images/Icons/pin.png"),"2. Set Reference Points (0/3)")
        
        # Coordinate Input Panel
        self.coord_group = QGroupBox("Physical Coordinates")
        coord_layout = QFormLayout()
        
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        
        # Point 1 (Origin)
        self.pt1_x = QLineEdit("0.0"); self.pt1_x.setValidator(validator)
        self.pt1_y = QLineEdit("0.0"); self.pt1_y.setValidator(validator)
        pt1_layout = QHBoxLayout()
        pt1_layout.addWidget(QLabel("X:")); pt1_layout.addWidget(self.pt1_x)
        pt1_layout.addWidget(QLabel("Y:")); pt1_layout.addWidget(self.pt1_y)
        coord_layout.addRow("1 (Origin):", pt1_layout)
        
        # Point 2 (X-Axis)
        self.pt2_x = QLineEdit("1.0"); self.pt2_x.setValidator(validator)
        self.pt2_y = QLineEdit("0.0"); self.pt2_y.setValidator(validator)
        pt2_layout = QHBoxLayout()
        pt2_layout.addWidget(QLabel("X:")); pt2_layout.addWidget(self.pt2_x)
        pt2_layout.addWidget(QLabel("Y:")); pt2_layout.addWidget(self.pt2_y)
        coord_layout.addRow("2 (X-Axis):", pt2_layout)
        
        # Point 3 (Y-Axis)
        self.pt3_x = QLineEdit("0.0"); self.pt3_x.setValidator(validator)
        self.pt3_y = QLineEdit("1.0"); self.pt3_y.setValidator(validator)
        pt3_layout = QHBoxLayout()
        pt3_layout.addWidget(QLabel("X:")); pt3_layout.addWidget(self.pt3_x)
        pt3_layout.addWidget(QLabel("Y:")); pt3_layout.addWidget(self.pt3_y)
        coord_layout.addRow("3 (Y-Axis):", pt3_layout)
        
        self.coord_group.setLayout(coord_layout)
        self.coord_group.setVisible(False) # Hidden until points are clicked
        

        self.btn_select_cbar = QPushButton(QIcon("Images/Icons/color.png"),"3. Select Colorbar")
        self.btn_extract = QPushButton(QIcon("Images/Icons/compile.png"),"4. Extract Data")
        self.btn_export = QPushButton(QIcon("Images/Icons/table-export.png"),"5. Export to CSV")
        self.btn_save_cfd = QPushButton(QIcon("Images/Icons/disk.png"),"Save .CFD Project")

        # Data preview panel
        self.data_preview_group = QGroupBox("Data Preview:")
        self.data_preview_layout = QVBoxLayout()
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(["X", "Y", "Value"])
        
        # Stretch columns to fit the box, but allow horizontal scrolling if it gets too narrow
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Lock the height to roughly show the header + 10 rows (approx 320px)
        self.data_table.setMinimumHeight(200)
        self.data_table.setMaximumHeight(320)
        
        self.data_preview_layout.addWidget(self.data_table)
        self.data_preview_group.setLayout(self.data_preview_layout)
        
        # Build Toolbar
        toolbar_layout.addWidget(self.btn_load)
        #toolbar_layout.addWidget(self.btn_bg_remove)
        toolbar_layout.addWidget(self.btn_set_axes)
        toolbar_layout.addWidget(self.coord_group) # Add the panel under the button
        toolbar_layout.addWidget(self.btn_select_cbar)
        toolbar_layout.addWidget(self.btn_extract)
        toolbar_layout.addWidget(self.btn_export)
        toolbar_layout.addWidget(self.data_preview_group)
        toolbar_layout.addStretch() # Pushes the save button to the bottom
        toolbar_layout.addWidget(self.btn_save_cfd)

        self.logo_label = QLabel()
        logo_path = "Images/Logo/ColorFulData_Logo.png"
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(
                200, 100, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(scaled_logo)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.logo_label.setText("ColorFulData") # Fallback text if image missing
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        toolbar_layout.addWidget(self.logo_label)

        self.toggle_terminal = QAction("Toggle Terminal", self)
        self.toggle_terminal.setCheckable(True)
        self.toggle_terminal.setChecked(False) #default state

        # Building the top menu bar
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        edit_menu = menu.addMenu("&Edit")
        view_menu = menu.addMenu("&View")
        # Add actions to the File menu
        self.menu_import = file_menu.addAction(QIcon("Images/Icons/image--plus.png"),"Import Image")
        self.menu_save = file_menu.addAction(QIcon("Images/Icons/disk.png"),"Save Project")
        self.menu_save_as =file_menu.addAction(QIcon("Images/Icons/disk--plus.png"),"Save Project As")
        self.menu_load = file_menu.addAction(QIcon("Images/Icons/folder--arrow.png"),"Load Project")
        self.menu_export_csv = file_menu.addAction(QIcon("Images/Icons/table-export.png"),"Export CSV")
        self.menu_export_as = file_menu.addAction(QIcon("Images/Icons/blue-folder-export.png"),"Export As")
        # Add actions to the Edit menu
        self.edit_mask_area =edit_menu.addAction("Mask Area")
        self.edit_post_processing = edit_menu.addAction("Post-Processing")
        edit_menu.addAction("Preferences")
        # Add actions to the View menu
        self.view_reset = view_menu.addAction("Reset View")
        self.view_toggle_terminal = view_menu.addAction(self.toggle_terminal)
        # ===Menu Shortcuts===
        self.menu_load.setShortcut("Ctrl+o")
        self.menu_import.setShortcut("Ctrl+i") 
        self.menu_save.setShortcut("Ctrl+s")
        self.menu_save_as.setShortcut("Ctrl+Shift+s")
        self.menu_export_csv.setShortcut("Ctrl+e")
        self.menu_export_as.setShortcut("Ctrl+Shift+e")
        self.edit_mask_area.setShortcut("Ctrl+m")
        self.edit_post_processing.setShortcut("Ctrl+Shift+p")
        # Canvas (Right Panel)
        self.scene = QGraphicsScene()
        self.view = ImageCanvas(self.scene)
        
        # Connect canvas signals
        self.view.point_added.connect(self.update_axes_button)
        self.view.points_complete.connect(self.axes_completed)


        main_layout.addLayout(toolbar_layout, 1)
        main_layout.addWidget(self.view, 4)


    def display_image(self, filepath):
        self.scene.clear()
        self.view.markers.clear()
        self.coord_group.setVisible(False) # Hide coordinates if a new image is loaded
        pixmap = QPixmap(filepath)
        self.scene.addPixmap(pixmap)
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def update_axes_button(self, count):
        self.btn_set_axes.setText(f"2. Set Reference Points ({count}/3)")

    def axes_completed(self, points):
        self.btn_set_axes.setText("2. Set Reference Points (Done)")
        self.coord_group.setVisible(True) # Reveal the coordinate inputs
        
    def get_physical_coordinates(self):
        """Helper method for main.py to fetch the user-defined physical values."""
        return {
            "origin": (float(self.pt1_x.text()), float(self.pt1_y.text())),
            "x_axis": (float(self.pt2_x.text()), float(self.pt2_y.text())),
            "y_axis": (float(self.pt3_x.text()), float(self.pt3_y.text()))
        }

    def update_data_preview(self, data_list):
        """Populates the table widget with extracted data, capped at 500 rows for performance."""
        self.data_table.setRowCount(0) # Clear existing data
        
        if not data_list:
            return
            
        # Cap the preview to keep the GUI snappy
        preview_limit = min(len(data_list), 100)
        self.data_table.setRowCount(preview_limit)
        
        for row in range(preview_limit):
            item = data_list[row]
            # Format numbers to 4 decimal places for clean UI
            self.data_table.setItem(row, 0, QTableWidgetItem(f"{item['X']:.4f}"))
            self.data_table.setItem(row, 1, QTableWidgetItem(f"{item['Y']:.4f}"))
            self.data_table.setItem(row, 2, QTableWidgetItem(f"{item['Value']:.4f}"))
            
        if len(data_list) > preview_limit:
            self.data_preview_group.setTitle(f"Data Preview (Showing {preview_limit} of {len(data_list)} points):")
        else:
            self.data_preview_group.setTitle(f"Data Preview ({len(data_list)} points):")

    def show_message(self, title, message):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

class ColormapMatchDialog(QDialog):
    def __init__(self, cropped_pixmap, best_match, match_score, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Colormap Detected")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        self.preview_width = 300
        
        # Display Analysis Results
        result_label = QLabel(f"<b>Match:</b> {best_match} ({match_score:.1f}%)")
        result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(result_label)
        
        # Original User Selection Preview
        layout.addWidget(QLabel("<b>Your Selection:</b>"))
        self.original_cbar_label = QLabel()
        self.original_cbar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        scaled_crop = cropped_pixmap.scaled(
            self.preview_width, 60, 
            Qt.AspectRatioMode.IgnoreAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.original_cbar_label.setPixmap(scaled_crop)
        layout.addWidget(self.original_cbar_label)
        
        # 3. Standard Colormap Preview
        layout.addWidget(QLabel("<b>Mapped Colormap:</b>"))
        self.std_cbar_label = QLabel()
        self.std_cbar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.std_cbar_label)
        
        # 4. Form Layout for Inputs
        form_layout = QFormLayout()

        self.use_raw_checkbox = QCheckBox("Use raw colors from selection linearly")
        self.use_raw_checkbox.stateChanged.connect(self.on_checkbox_toggle)
        form_layout.addRow(self.use_raw_checkbox)
        
        self.cmap_dropdown = QComboBox()
        common_cmaps = ["viridis", "plasma", "inferno", "magma", "cividis", 
                        "jet", "coolwarm", "bwr", "seismic", "turbo",
                        "Greys", "Blues", "Reds", "YlGnBu"]
        self.cmap_dropdown.addItems(common_cmaps)
        
        if best_match not in common_cmaps:
            self.cmap_dropdown.addItem(best_match)
        self.cmap_dropdown.setCurrentText(best_match)
        self.cmap_dropdown.currentTextChanged.connect(self.update_cmap_preview)
        
        form_layout.addRow("Colormap:", self.cmap_dropdown)
        
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        
        self.val_min = QLineEdit("0.0")
        self.val_min.setValidator(validator)
        form_layout.addRow("Colorbar Min Value:", self.val_min)
        
        self.val_max = QLineEdit("1.0")
        self.val_max.setValidator(validator)
        form_layout.addRow("Colorbar Max Value:", self.val_max)
        
        layout.addLayout(form_layout)
        
        # 5. Dialog Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        self.update_cmap_preview(self.cmap_dropdown.currentText())

    def on_checkbox_toggle(self, state):
        """Disables the dropdown if the user checks the raw color box."""
        if state == 2:  # Qt.CheckState.Checked
            self.cmap_dropdown.setEnabled(False)
        else:
            self.cmap_dropdown.setEnabled(True)

    def update_cmap_preview(self, cmap_name):
        """Generates a QPixmap of the standard colormap dynamically using matplotlib."""
        try:
            # FIX: Use colormaps dictionary
            cmap = mpl.colormaps[cmap_name]
        except KeyError:
            cmap = mpl.colormaps["viridis"]
            
        height = 30 # Fixed pixel height for standard preview
        
        # Generate a 1D gradient from 0 to 1
        gradient = np.linspace(0, 1, self.preview_width)
        # Stack it vertically to create a 2D image block
        gradient_2d = np.vstack([gradient] * height)
        
        # Get RGBA colors (matplotlib returns 0.0 - 1.0 ranges)
        rgba_colors = cmap(gradient_2d)
        
        # Convert to 8-bit RGBA for PyQt6
        rgba_8bit = (rgba_colors * 255).astype(np.uint8)
        
        h, w, ch = rgba_8bit.shape
        bytes_per_line = ch * w
        
        # Load into QImage, then set to QLabel
        qimg = QImage(rgba_8bit.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        self.std_cbar_label.setPixmap(QPixmap.fromImage(qimg))

    def get_results(self):
        """Returns the user-confirmed colormap and value range."""
        return {
            "colormap": self.cmap_dropdown.currentText(),
            "min_val": float(self.val_min.text()),
            "max_val": float(self.val_max.text()),
            "use_raw": self.use_raw_checkbox.isChecked() # <--- This prevents the KeyError
        }


if __name__ == "__main__":
    #Testing section for the GUI code. (without the backend)
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = CFDGur()
    window.show()
    sys.exit(app.exec()) 