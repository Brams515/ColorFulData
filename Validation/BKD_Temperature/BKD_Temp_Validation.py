import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.tri as tri

# Reading the data from the CSV file
file_path = "Validation/BKD_Temp.csv"
data = pd.read_csv(file_path)

# Filter the data
plot_data = data[data['Y'] <= 80]

triang = tri.Triangulation(plot_data['X'], plot_data['Y'])
analyzer = tri.TriAnalyzer(triang)
# Compute the mask 
# min_circle_ratio (e.g. between 0.01 en 0.2), masks triangles triangles with very large sides
mask = analyzer.get_flat_tri_mask(min_circle_ratio=0.15)
triang.set_mask(mask)

# Use the Object-Oriented API for cleaner state management
fig, ax = plt.subplots(figsize=(10, 6))

contour = ax.tricontourf(triang, plot_data['Value'], levels=43, cmap='jet')

ax.set(xlabel='X', ylabel='Y', title='Contour Plot (Reproduced from data)', aspect='equal')
fig.colorbar(contour, ax=ax, label='Value')

plt.show()

