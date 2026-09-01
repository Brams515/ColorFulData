import numpy as np
import matplotlib as mpl 
import cv2
from scipy.spatial import cKDTree
from skimage.color import rgb2lab
from scipy.interpolate import interp1d

def analyze_colorbar_similarity(cropped_colorbar_img_rgb):
    if cropped_colorbar_img_rgb is None or cropped_colorbar_img_rgb.size == 0:
        return "Unknown", 0.0, None # Added None for raw profile

    h, w, _ = cropped_colorbar_img_rgb.shape

    if h > w:
        profile = np.median(cropped_colorbar_img_rgb, axis=1)
    else:
        profile = np.median(cropped_colorbar_img_rgb, axis=0)

    profile_reshaped = profile.reshape(1, -1, 3).astype(np.float32)
    profile_256 = cv2.resize(profile_reshaped, (256, 1), interpolation=cv2.INTER_LINEAR).reshape(256, 3)

    profile_rgb_norm = profile_256 / 255.0
    profile_lab = rgb2lab(profile_rgb_norm.reshape(1, 256, 3)).reshape(256, 3)

    common_cmaps = [
        "viridis", "plasma", "inferno", "magma", "cividis", 
        "jet", "coolwarm", "bwr", "seismic", "turbo",
        "rainbow", "terrain", "ocean", "gist_earth", "hot"
    ]

    best_match = None
    min_error = float('inf')

    for cmap_name in common_cmaps:
        try:
            cmap = mpl.colormaps[cmap_name]
        except KeyError:
            continue
            
        std_colors_rgba = cmap(np.linspace(0, 1, 256))
        std_colors_rgb = std_colors_rgba[:, :3]
        std_lab = rgb2lab(std_colors_rgb.reshape(1, 256, 3)).reshape(256, 3)

        error_fwd = np.mean(np.linalg.norm(profile_lab - std_lab, axis=1))
        error_bwd = np.mean(np.linalg.norm(profile_lab[::-1] - std_lab, axis=1))

        best_local_error = min(error_fwd, error_bwd)

        if best_local_error < min_error:
            min_error = best_local_error
            best_match = cmap_name

    max_expected_error = 80.0 
    confidence = max(0.0, 100.0 - (min_error / max_expected_error) * 100.0)
    confidence = min(100.0, confidence) 

    # Return the best match, the confidence percentage and the raw profile
    return best_match, confidence, profile_256


def map_colors_to_values(pixel_colors_rgb, colormap_name, min_val, max_val, resolution=1024, raw_cmap_profile=None):
    pixel_colors_rgb = np.asarray(pixel_colors_rgb)
    if pixel_colors_rgb.size == 0:
        return np.array([])

    if raw_cmap_profile is not None:
        # User checked the box: Use the raw pixels extracted from the image
        raw_norm = raw_cmap_profile / 255.0  # Normalize 0-255 to 0.0-1.0
        x_old = np.linspace(0, 1, len(raw_norm))
        x_new = np.linspace(0, 1, resolution)
        
        # Interpolate the raw 256-profile up to the specified KD-Tree resolution
        f = interp1d(x_old, raw_norm, axis=0)
        standard_colors_rgb = f(x_new)
        standard_values_normalized = x_new
    else:
        # Standard flow: use Matplotlib
        try:
            cmap = mpl.colormaps[colormap_name]
        except KeyError:
            cmap = mpl.colormaps["viridis"]
            
        standard_values_normalized = np.linspace(0, 1, resolution)
        standard_colors_rgba = cmap(standard_values_normalized)
        standard_colors_rgb = standard_colors_rgba[:, :3]
    
    # 2. Convert standard colormap to LAB color space
    std_rgb_reshaped = standard_colors_rgb.reshape(1, -1, 3)
    std_lab = rgb2lab(std_rgb_reshaped).reshape(-1, 3)
    
    # 3. Build KD-Tree
    tree = cKDTree(std_lab)
    
    # 4. Query KD-Tree with user colors
    user_rgb_normalized = pixel_colors_rgb / 255.0
    user_lab = rgb2lab(user_rgb_normalized.reshape(1, -1, 3)).reshape(-1, 3)
    
    distances, indices = tree.query(user_lab, k=1)
    
    # 5. Map matched indices back to the physical value range
    mapped_normalized = standard_values_normalized[indices]
    mapped_values = min_val + (mapped_normalized * (max_val - min_val))
    
    return mapped_values