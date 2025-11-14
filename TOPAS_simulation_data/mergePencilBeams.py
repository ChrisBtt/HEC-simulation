import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from tqdm import tqdm

import sys
sys.path.append('../../TOPAS_analysis/')
from preprocessSimulation import Preprocessor


folder = '.'
path_dose = os.path.join(folder, 'DoseGlobal.csv')
path_current_elX = os.path.join(folder, 'angCurrElXGlob.csv')
path_current_elY = os.path.join(folder, 'angCurrElYGlob.csv')
path_current_elZ = os.path.join(folder, 'angCurrElZGlob.csv')

bin_x = 0.1  # cm / voxel
bin_y = 0.1  # cm / voxel
bin_z = 0.06  # cm / voxel

data = Preprocessor([path_dose, path_current_elX, path_current_elY, path_current_elZ], bin_x, bin_y, bin_z).data

spacing = 0.1  # cm
x_radius = 2.5  # cm
y_radius = 2.5  # cm

xs = np.arange(-x_radius, x_radius + 1e-6, spacing)
ys = np.arange(-y_radius, y_radius + 1e-6, spacing)
xx, yy = np.meshgrid(xs, ys)
mask = (xx / x_radius) ** 2 + (yy / y_radius) ** 2 <= 1.0

positions = np.column_stack([xx[mask], yy[mask]])
print(f"Number of pencil beam positions to merge: {len(positions)} resulting in total particles: {len(positions) * 1e6:g}")

# --- Prepare coordinate grid ---
x_unique = np.sort(data['x'].unique())
y_unique = np.sort(data['y'].unique())
z_unique = np.sort(data['z'].unique())
nx, ny, nz = len(x_unique), len(y_unique), len(z_unique)

# --- Columns to shift ---
value_cols = ['dose', 'jx', 'jy', 'jz', 'stdx', 'stdy', 'stdz', 'stdd',
              'histx', 'histy', 'histz', 'histd']

# --- Initialize empty grids for all quantities ---
grids = {col: data[col].values.reshape((nx, ny, nz)) for col in value_cols}
plan = {col: np.zeros_like(grids[col]) for col in value_cols}

# --- Function for shifting with zero padding ---
def shift_grid(arr, shift_x, shift_y):
    shifted = np.roll(arr, shift_x, axis=0)
    shifted = np.roll(shifted, shift_y, axis=1)
    # zero-out wrapped edges
    if shift_x > 0:
        shifted[:shift_x, :, :] = 0
    elif shift_x < 0:
        shifted[shift_x:, :, :] = 0
    if shift_y > 0:
        shifted[:, :shift_y, :] = 0
    elif shift_y < 0:
        shifted[:, shift_y:, :] = 0
    return shifted

# --- Sum over all shifted beams ---
print("\nCalculating full plan dose (superposition)...")
for pos in tqdm(positions):
    dx, dy = pos
    shift_x = int(round(dx / bin_x))
    shift_y = int(round(dy / bin_y))

    for col in value_cols:
        plan[col] += shift_grid(grids[col], shift_x, shift_y)

# --- Reassemble into a single DataFrame ---
xxg, yyg, zzg = np.meshgrid(x_unique, y_unique, z_unique, indexing='ij')
plan_df = pd.DataFrame({
    'x': xxg.ravel(),
    'y': yyg.ravel(),
    'z': zzg.ravel(),
})
for col in value_cols:
    plan_df[col] = plan[col].ravel()

# --- Save ---
plan_df.to_csv('mergedAngGlobal.csv', index=False)
print("\nFinal plan data saved as 'mergedAngGlobal.csv'")
print(plan_df.head())
