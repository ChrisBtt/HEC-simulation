"""
A script for creating depth-based visualization plots from HEC simulation data.
Processes multiple input files containing voxel data and generates plots
showing the cumulative values for each slice in the simulation volume.
"""

import argparse
import matplotlib.pyplot as plt
import numpy as np


def parse_args():
    """
    Parse command line arguments for the script.

    Returns:
        argparse.Namespace: Parsed command line arguments containing:
            - files: List of input files to process
            - x: X dimension size
            - y: Y dimension size
            - z: Z dimension size
            - output: Optional output file name
    """
    parser = argparse.ArgumentParser(description='Create depth plots from file data')
    parser.add_argument('files', nargs='+', help='Input files to process')
    parser.add_argument('x', type=int, help='X dimension')
    parser.add_argument('y', type=int, help='Y dimension')
    parser.add_argument('z', type=int, help='Z dimension')
    parser.add_argument('-o', '--output', help='Output file name')
    return parser.parse_args()


def read_data(filename):
    """
    Read voxel data from the input file.

    Args:
        filename (str): Path to the input file

    Returns:
        tuple: A pair containing:
            - str: Type of data (from first line of file)
            - dict: Dictionary mapping voxel indices to their values
    """
    data_type = None
    values = {}
    with open(filename, 'r') as f:
        data_type = f.readline().strip()
        for line in f:
            try:
                index, value = map(float, line.strip().split())
                values[int(index)] = value
            except ValueError:
                continue
    return data_type, values


def calculate_xy_sums(values, x_dim, y_dim, z_dim):
    """
    Calculate the sum of values for each Z-layer by aggregating XY plane values.

    Args:
        values (dict): Dictionary of voxel indices and their values
        x_dim (int): Size of X dimension
        y_dim (int): Size of Y dimension
        z_dim (int): Size of Z dimension

    Returns:
        numpy.ndarray: Array of length z_dim containing sums for each Z-layer
    """
    z_sums = np.zeros(z_dim)
    for index, value in values.items():
        z = (index // (x_dim * y_dim)) % z_dim
        # Inverse Z-index to match plot order
        z_sums[z_dim - 1 - z] += value
        # z_sums[z] += value
    return z_sums


if __name__ == "__main__":
    args = parse_args()

    plt.figure(figsize=(10, 6))

    for file in args.files:
        data_type, values = read_data(file)
        z_sums = calculate_xy_sums(values, args.x, args.y, args.z)
        plt.plot(range(args.z), z_sums, label=data_type)

    plt.xlabel('Z-Index (Depth in Voxels)')
    plt.ylabel('Cumulative Value')
    plt.title('Depth Plots')
    plt.grid(True)
    plt.legend()

    if args.output:
        plt.savefig(args.output)
    else:
        plt.show()
