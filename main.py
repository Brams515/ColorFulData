"""
ColorFulData: Main script
============================================
Created on 31/08/2026
Author: Bram SAMYN
============================================
Script Description:
The Main script is the main executable for the application, and couples
the GUI with the underlying logic stored in other scripts.
============================================
"""
#===PyQt6 Imports===
import os

from PyQt6.QtWidgets import QApplication, QFileDialog , QInputDialog
from PyQt6.QtGui import QImage, QPixmap
import sys
import cv2
#===Math Imports===
import numpy as np
#===Local Script Imports===
from gui import CFDGur, ColormapMatchDialog, QIcon
import manipulation
import ColorDetection
import export

class CFDController:
    def __init__(self, ui):
        self.ui = ui
        self.cv2_image = None
        self.extracted_data = []
        self.connect_signals()

    def connect_signals(self):
        # Connects the UI buttons to their respective functions
        self.ui.btn_load.clicked.connect(self.load_image)
        #self.ui.btn_bg_remove.clicked.connect(self.remove_background)
        self.ui.btn_set_axes.clicked.connect(self.ui.view.start_setting_axes)
        self.ui.btn_select_cbar.clicked.connect(self.ui.view.start_colorbar_selection)
        self.ui.btn_extract.clicked.connect(self.extract_data) # Uses the code from previous step
        self.ui.btn_export.clicked.connect(self.export_data)
        
        # ===top bar connections===
        # menu connections
        self.ui.menu_import.triggered.connect(self.load_image) #menu action for loading image
        self.ui.menu_save.triggered.connect(self.save_project) #menu action for saving project
        self.ui.menu_save_as.triggered.connect(self.save_project_as) #menu action for saving project as
        self.ui.menu_load.triggered.connect(self.load_project) #menu action for loading project
        self.ui.menu_export_csv.triggered.connect(self.export_data) #menu action for exporting CSV
        self.ui.menu_export_as.triggered.connect(self.export_as) #menu action for exporting as
        # edit connections
        self.ui.edit_mask_area.triggered.connect(self.mask_area) #menu action for masking area
        self.ui.edit_post_processing.triggered.connect(self.post_processing) #menu action for opening post-processing window
        # view connections
    
        # Connect canvas signals directly to the controller
        self.ui.view.colorbar_selected.connect(self.process_colorbar_selection)

    def process_colorbar_selection(self, rect):
        """Triggered when the user finishes drawing the rubber band box."""
        if self.cv2_image is None:
            self.ui.show_message("Error", "Please load an image first.")
            return

        # Safely extract coordinates and clamp to image bounds
        img_h, img_w, _ = self.cv2_image.shape
        x, y = max(0, int(rect.x())), max(0, int(rect.y()))
        w, h = min(int(rect.width()), img_w - x), min(int(rect.height()), img_h - y)

        if w <= 0 or h <= 0:
            return

        # Crop the image and convert BGR (OpenCV) to RGB (Scikit/PyQt)
        cropped_bgr = self.cv2_image[y:y+h, x:x+w]
        cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)

        # Run the Similarity Analysis
        best_match, score, raw_profile = ColorDetection.analyze_colorbar_similarity(cropped_rgb)

        # Convert cropped RGB numpy array to QPixmap for the dialog preview
        # QImage requires the data buffer, width, height, bytes per line, and format
        bytes_per_line = 3 * w
        qimg = QImage(cropped_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        # Launch the Dialog
        dialog = ColormapMatchDialog(pixmap, best_match, score, self.ui)
        if dialog.exec():
            results = dialog.get_results()
            results['raw_profile'] = raw_profile # Save the extracted raw colors!
            
            self.ui.colorbar_settings = results
            self.ui.colorbar_bbox = (x, y, w, h)
            
            mode_text = "Raw Linear Colors" if results.get('use_raw', False) else results['colormap']
            self.ui.show_message("Settings Saved", 
                                 f"Using {mode_text} mapped from {results['min_val']} to {results['max_val']}.")
        else:
            if self.ui.view.colorbar_rect_item:
                self.ui.scene.removeItem(self.ui.view.colorbar_rect_item)
                self.ui.view.colorbar_rect_item = None
            self.ui.colorbar_bbox = None

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self.ui, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
        if file_name:
            self.ui.current_image_path = file_name
            import cv2
            self.cv2_image = cv2.imread(file_name)
            self.ui.display_image(file_name)

    def remove_background(self):
        if self.cv2_image is not None:
            # Passes to manipulation module
            rgba_img = manipulation.remove_background(self.cv2_image, target_color=(255, 255, 255), tolerance=15)
            self.ui.show_message("Success", "Background masking applied (Preview update pending in baseline).")

    def select_colorbar(self):
        # In full implementation, this triggers a rubber band selection on QGraphicsView
        # Here we simulate the pipeline
        best_match, score = ColorDetection.analyze_colorbar_similarity(None)
        self.ui.show_message("Colormap Detected", f"Best Match: {best_match} ({score}% similarity)")

    def extract_data(self):
        # Validation Checks
        if self.cv2_image is None:
            self.ui.show_message("Error", "Please load an image first.")
            return
        if len(self.ui.view.reference_points) < 3:
            self.ui.show_message("Error", "Please define all 3 reference points first.")
            return
        if not hasattr(self.ui, 'colorbar_settings') or not self.ui.colorbar_settings:
            self.ui.show_message("Error", "Please select a colorbar and confirm its settings first.")
            return

        # Get Grid Resolution (Step 6)
        nx, ok_x = QInputDialog.getInt(self.ui, "Grid Resolution", "Number of points in X direction:", 100, 10, 2000)
        if not ok_x: return
        ny, ok_y = QInputDialog.getInt(self.ui, "Grid Resolution", "Number of points in Y direction:", 100, 10, 2000)
        if not ok_y: return

        # Calculate Affine Transform Matrix (Pixel to Physical)
        # Extract pixel points from canvas and physical points from UI
        pixel_pts = [(p.x(), p.y()) for p in self.ui.view.reference_points]
        phys_dict = self.ui.get_physical_coordinates()
        real_pts = [phys_dict["origin"], phys_dict["x_axis"], phys_dict["y_axis"]]
        
        matrix = manipulation.calculate_affine_transform(pixel_pts, real_pts)

        # Generate Pixel Grid over the entire image extent
        h, w, _ = self.cv2_image.shape
        bbox = (0, 0, w, h)
        pixel_grid = manipulation.generate_extraction_grid(bbox, nx, ny)

        # Ensure grid coordinates fall safely inside image bounds
        valid_pixels = np.array([
            (int(pt[0]), int(pt[1])) for pt in pixel_grid 
            if 0 <= int(pt[0]) < w and 0 <= int(pt[1]) < h
        ])
        
        if len(valid_pixels) == 0:
            return

        # Extract Colors (Vectorized for performance)
        px_indices = valid_pixels[:, 0]
        py_indices = valid_pixels[:, 1]
        colors_bgr = self.cv2_image[py_indices, px_indices]
        
        # Convert BGR (OpenCV format) to RGB (Scikit-image / Matplotlib format)
        colors_rgb = colors_bgr[:, ::-1]

        # Masking / Background Removal
        # Drop pixels that are nearly pure white (or transparent if RGBA was used)
        # Assuming background is white (R>245, G>245, B>245)
        is_not_background = np.any(colors_rgb < 245, axis=1)
        
        filtered_pixels = valid_pixels[is_not_background]
        filtered_colors_rgb = colors_rgb[is_not_background]

        if len(filtered_colors_rgb) == 0:
            self.ui.show_message("Error", "No colored data found. Adjust background tolerance.")
            return

        # 7. Map Colors to Values using KD-Tree
        settings = self.ui.colorbar_settings
        
        # Check if the user opted to use the raw colors
        raw_prof = settings['raw_profile'] if settings.get('use_raw') else None

        mapped_values = ColorDetection.map_colors_to_values(
            filtered_colors_rgb, 
            settings['colormap'], 
            settings['min_val'], 
            settings['max_val'],
            raw_cmap_profile=raw_prof # Pass it here!
        )

        # Transform Pixel Coordinates to Real-World Physical Coordinates
        # OpenCV requires shape (N, 1, 2) for transform arrays
        pts_to_transform = np.array(filtered_pixels, dtype=np.float32).reshape(-1, 1, 2)
        physical_coords = cv2.transform(pts_to_transform, matrix).reshape(-1, 2)

        # Assemble and Store Final Data
        self.extracted_data = []
        for i in range(len(physical_coords)):
            self.extracted_data.append({
                'X': physical_coords[i, 0],
                'Y': physical_coords[i, 1],
                'Value': mapped_values[i]
            })
        # Update the UI Table Preview
        self.ui.update_data_preview(self.extracted_data)

        self.ui.show_message("Extraction Complete", 
                             f"Successfully extracted {len(self.extracted_data)} points.\n"
                             "You can now export to CSV.")

    def mask_area(self):
        if self.cv2_image is None:
            self.ui.show_message("Error", "Please load an image first.")
            return

        self.ui.show_message("Error", "This function is not implemented yet.")

    def post_processing(self):
        if not self.extracted_data:
            self.ui.show_message("Error", "No data to process. Please extract data first.")
            return

        self.ui.show_message("Error", "This function is not implemented yet.")

    def export_data(self):
        if not self.extracted_data:
            self.ui.show_message("Error", "No data to export.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self.ui, "Save CSV", "", "CSV Files (*.csv)")
        if save_path:
            export.export_csv(self.extracted_data, save_path)

    def export_as(self):
        if not self.extracted_data:
            self.ui.show_message("Error", "No data to export.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self.ui, "Export As", "", "CSV Files (*.csv);;JSON Files (*.json)")
        if save_path:
            export.export_as(self.extracted_data, save_path)

    def save_project(self):
        if not self.extracted_data:
            self.ui.show_message("Error", "No data to save.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self.ui, "Save Project", "", "Project Files (*.cfdproj)")
        if save_path:
            export.save_project(self.cv2_image, self.ui.view.reference_points, self.ui.colorbar_settings, save_path)

    def save_project_as(self):
        if not self.extracted_data:
            self.ui.show_message("Error", "No data to save.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self.ui, "Save Project As", "", "Project Files (*.cfdproj)")
        if save_path:
            export.save_project(self.cv2_image, self.ui.view.reference_points, self.ui.colorbar_settings, save_path)

    def load_project(self):
        load_path, _ = QFileDialog.getOpenFileName(self.ui, "Load Project", "", "Project Files (*.cfdproj)")
        if load_path:
            image, ref_points, colorbar_settings = export.load_project(load_path)
            if image is not None:
                self.cv2_image = image
                self.ui.display_image_from_array(image)
                self.ui.view.reference_points = ref_points
                self.ui.colorbar_settings = colorbar_settings
                self.ui.show_message("Project Loaded", "Successfully loaded project settings and image.")
            else:
                self.ui.show_message("Error", "Failed to load project.")

    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CFDGur()
    controller = CFDController(window)
    window.show()
    sys.exit(app.exec())