import cv2
import numpy as np

def remove_background(image, target_color=(255, 255, 255), tolerance=10):
    """
    Masks out the background color based on a tolerance.
    image: OpenCV image (BGR)
    target_color: BGR tuple representing the background to remove
    """
    lower_bound = np.array([max(0, c - tolerance) for c in target_color])
    upper_bound = np.array([min(255, c + tolerance) for c in target_color])
    
    # Create mask: 255 where color is within bounds (background), 0 elsewhere
    mask = cv2.inRange(image, lower_bound, upper_bound)
    
    # Create an RGBA image with transparent background
    b, g, r = cv2.split(image)
    alpha = np.where(mask == 255, 0, 255).astype(np.uint8)
    image_rgba = cv2.merge((b, g, r, alpha))
    
    return image_rgba

def calculate_affine_transform(pixel_pts, real_pts):
    """
    Calculates the transformation matrix from pixel coordinates to real-world coordinates.
    pixel_pts: list of 3 (x,y) pixel tuples
    real_pts: list of 3 (X,Y) real-world tuples
    """
    pts1 = np.float32(pixel_pts)
    pts2 = np.float32(real_pts)
    matrix = cv2.getAffineTransform(pts1, pts2)
    return matrix

def generate_extraction_grid(bbox, nx, ny):
    """
    Generates a list of pixel coordinates inside the specified bounding box based on grid resolution.
    bbox: (x_min, y_min, x_max, y_max)
    """
    x_coords = np.linspace(bbox[0], bbox[2], nx)
    y_coords = np.linspace(bbox[1], bbox[3], ny)
    xx, yy = np.meshgrid(x_coords, y_coords)
    
    grid_points = np.vstack([xx.ravel(), yy.ravel()]).T
    return grid_points