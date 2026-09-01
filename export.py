import json
import pandas as pd

def export_csv(data_points, filepath):
    """
    Exports extracted data to a CSV.
    data_points: list of dictionaries or tuples, e.g., [{'x': 1.0, 'y': 2.0, 'value': 0.5}, ...]
    """
    df = pd.DataFrame(data_points)
    df.to_csv(filepath, index=False)
    print(f"Data successfully exported to {filepath}")

def save_cfd_project(setup_dict, filepath):
    """
    Saves the current tool state (coordinates, bounding boxes, grid res) to a .CFD (JSON) file.
    """
    with open(filepath, 'w') as f:
        json.dump(setup_dict, f, indent=4)
    print(f"Project saved to {filepath}")

def load_cfd_project(filepath):
    """
    Loads a .CFD configuration file.
    """
    with open(filepath, 'r') as f:
        setup_dict = json.load(f)
    return setup_dict