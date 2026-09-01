"""
ColorFulData: PostProcessing script
====================================================================================
Created on 01/09/2026
Author: Bram SAMYN
====================================================================================
Script Description:
This  script handles the functions for post-processing through the GUI,
making it more user-friendly and accessible for users who may not be familiar with 
programming or command-line interfaces (widening the user base).
====================================================================================
"""

# ===Import Libraries===
# ===Math and Data Processing===
import numpy as np
import pandas as pd
# ===Plotting===
import matplotlib.pyplot as plt

def contour_plot(data, x_coords, y_coords, levels:int=10, cmap:str ='viridis', mask:bool = False, mask_data:np.ndarray = None):
    pass

def extract_along_line(data, start_point:tuple = None, end_point:tuple = None)-> np.ndarray:
    pass

def find_and_replace(data, target_value, replace_value):
    pass

