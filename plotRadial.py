"""
A script for creating radial plots from HEC simulation output files.
Reads data files and generates plots showing the radial distribution
of values at a specified depth in the simulation volume.
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
            - x, y, z: Dimensions of the simulation volume
            - d: Specific depth to plot
            - rings: Number of rings for radial averaging
            - output: Output file name (optional)
    """
    parser = argparse.ArgumentParser(description='Create depth plots from file data')
    parser.add_argument('files', nargs='+', help='Input files to process')
    parser.add_argument('x', type=int, help='X dimension')
    parser.add_argument('y', type=int, help='Y dimension')
    parser.add_argument('z', type=int, help='Z dimension')
    parser.add_argument('d', type=int, help='Specific depth to plot')
    parser.add_argument('-r', '--rings', type=int, default=70, help='Number of rings for radial averaging')
    parser.add_argument('-o', '--output', help='Output file name')
    return parser.parse_args()


def read_data(filename):
    """
    Read data from an input file.

    Args:
        filename (str): Path to the input file

    Returns:
        tuple: (data_type, values) where:
            - data_type (str): Type of data contained in the file
            - values (dict): Dictionary mapping indices to values
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


def index_to_xyz(index, x_dim, y_dim, z_dim):
    """
    Convert a linear index to XYZ coordinates.

    Args:
        index (int): Linear index in the volume
        x_dim (int): X dimension size
        y_dim (int): Y dimension size
        z_dim (int): Z dimension size

    Returns:
        tuple: (x, y, z) coordinates in the volume
    """
    xy_size = x_dim * y_dim
    z = (index // xy_size) % z_dim
    remainder = index % xy_size
    y = remainder // x_dim
    x = remainder % x_dim
    return x, y, (z_dim - 1 - z)


def calculate_radial_distance(x, y, x_dim, y_dim):
    """
    Calculate the radial distance from the center for given coordinates.

    Args:
        x (int): X coordinate
        y (int): Y coordinate
        x_dim (int): X dimension size
        y_dim (int): Y dimension size

    Returns:
        float: Radial distance from the center
    """
    center_x = x_dim / 2
    center_y = y_dim / 2
    return np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)


def create_radial_plot(values, x_dim, y_dim, z_dim, depth, num_rings):
    """
    Create data for a radial plot at specified depth.

    Args:
        values (dict): Dictionary mapping indices to values
        x_dim (int): X dimension size
        y_dim (int): Y dimension size
        z_dim (int): Z dimension size
        depth (int): Depth level to plot
        num_rings (int): Number of rings for radial averaging

    Returns:
        tuple: (ring_centers, cum_values) where:
            - ring_centers (list): Centers of each radial ring
            - cum_values (list): Cumulative values for each ring
    """
    max_radius = np.sqrt((x_dim / 2) ** 2 + (y_dim / 2) ** 2)
    ring_edges = np.sqrt(np.linspace(0, max_radius ** 2, num_rings + 1))

    ring_data = [[] for _ in range(num_rings)]

    for index, value in values.items():
        x, y, z = index_to_xyz(index, x_dim, y_dim, z_dim)
        if z == depth:
            r = calculate_radial_distance(x, y, x_dim, y_dim)
            ring_idx = np.digitize(r, ring_edges) - 1
            if 0 <= ring_idx < num_rings:
                ring_data[ring_idx].append(value)

    ring_centers = [(ring_edges[i] + ring_edges[i + 1]) / 2 for i in range(num_rings)]
    cum_values = [np.sum(data) if data else 0 for data in ring_data]

    return ring_centers, cum_values


if __name__ == "__main__":
    args = parse_args()

    plt.figure(figsize=(10, 6))

    for file in args.files:
        data_type, values = read_data(file)
        radii, cum_values = create_radial_plot(values, args.x, args.y, args.z, args.d, args.rings)
        plt.plot(radii, cum_values, label=data_type)

    print(cum_values)

    plt.xlabel('Radial Distance (in Voxels)')
    plt.ylabel('Cumulative Value')
    plt.title(f'Radial Plot at Depth d={args.d} Voxels')
    plt.grid(True)
    plt.legend()

    if args.output:
        plt.savefig(args.output)
    else:
        plt.show()
