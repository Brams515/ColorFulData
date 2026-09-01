"""
ColorFulData: Utils script
============================================
Created on 01/09/2026
Author: Bram SAMYN
============================================
Script Description:
This script contains utility functions that are used across the ColorFulData application.
============================================
"""

import sys
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    """ Get the absolute path to a resource, working for both development and PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        # Running normally from the project directory
        base_path = Path(__file__).parent.resolve()

    return base_path / relative_path