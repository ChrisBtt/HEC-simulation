import pandas as pd
import numpy as np


class Preprocessor(object):
    def __init__(self, path: list|str, bin_x: int, bin_y: int, bin_z: int, impute = False, center=False, central_voxel: bool = False, downsample_factor: int = 1):
        self.path = path
        self.bin_x = bin_x
        self.bin_y = bin_y
        self.bin_z = bin_z
        self.impute = impute
        self.central_voxel = central_voxel
        self.downsample_factor = downsample_factor

        self.data = self.load_data()
        if center:
            self._shift_to_beam_center()
        self.convert_bins_to_cm()
        if self.impute:
            self.impute_missing_values()
        self.calculate_radial_distance()
        self.calculate_radial_current()


    def load_data(self) -> pd.DataFrame:
        """
        Load the simulated current density starting from the line number where "Cell Current X Y Z ZF ZB" appears
        """

        if isinstance(self.path, str):
            data = pd.read_csv(self.path, comment='#', header=0)
            data = data[['x', 'y', 'z', 'jx', 'stdx', 'histx', 'jy', 'stdy', 'histy', 'jz', 'stdz', 'histz', 'dose', 'stdd', 'histd']]
        elif isinstance(self.path, list):
            for path in self.path:
                print(f"Loading data from {path}...")
                if 'Dose' in path:
                    data_d = pd.read_csv(path, 
                        names=['x', 'y', 'z', 'dose', 'stdd', 'histd'], 
                        comment='#',
                    )
                elif 'X' in path:
                    data_x = pd.read_csv(path, 
                        names=['x', 'y', 'z', 'jx', 'stdx', 'histx'],
                        comment='#',
                    )
                elif 'Y' in path:
                    data_y = pd.read_csv(path, 
                        names=['x', 'y', 'z', 'jy', 'stdy', 'histy'],
                        comment='#',
                    )
                elif 'Z' in path:
                    data_z = pd.read_csv(path, 
                        names=['x', 'y', 'z', 'jz', 'stdz', 'histz'],
                        comment='#',
                    )
            data = pd.merge(data_x, data_y, on=['x', 'y', 'z'])
            data = pd.merge(data, data_z, on=['x', 'y', 'z'])
            data = pd.merge(data, data_d, on=['x', 'y', 'z'])
        else:
            raise ValueError("Path must be a string or a list of strings.")

        if self.downsample_factor > 1:
            data = self._downsample_data(data)

        print(f"Range x: {data['x'].min()} to {data['x'].max()}")
        print(f"Range y: {data['y'].min()} to {data['y'].max()}")
        print(f"Range z: {data['z'].min()} to {data['z'].max()}")

        data['jx_abs'] = data['jx'].abs()
        data['jy_abs'] = data['jy'].abs()
        data['jz_abs'] = data['jz'].abs()

        return data
    
    def _downsample_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Downsample the data by the specified downsample factor.
        """

        dataOut = data.copy()
        dataOut.drop(columns=['x', 'y', 'z'], inplace=True)
        dataOut["x_new"] = (data["x"] // self.downsample_factor)
        dataOut["y_new"] = (data["y"] // self.downsample_factor)
        dataOut["z_new"] = (data["z"] // self.downsample_factor)

        dataOut = dataOut.groupby(["x_new", "y_new", "z_new"]).agg("sum").reset_index()

        dataOut = dataOut.rename(columns={"x_new": "x", "y_new": "y", "z_new": "z"})
        print(dataOut.columns)
        return dataOut


    def _shift_to_beam_center(self):
        """
        Shift the coordinates so that the beam is centered at (0,0).
        """
        x_center = self.data['x'].unique()[len(self.data['x'].unique()) // 2]
        y_center = self.data['y'].unique()[len(self.data['y'].unique()) // 2]
        self.data['x'] = self.data['x'] - x_center
        self.data['y'] = self.data['y'] - y_center

    def impute_missing_values(self) -> True:
        """
        Impute missing indices and set the current densities to None.
        """
        data_imputed = self.data.set_index('index')

        # 3. Determine the full, continuous range for the index
        min_idx = data_imputed.index.min()
        max_idx = data_imputed.index.max()
        full_range = range(min_idx, max_idx + 1)

        # 4. Reindex the DataFrame. This is the magic step 🪄
        # It creates new rows for missing indices and fills them with NaN.
        df_imputed = data_imputed.reindex(full_range)

        # 5. (Optional) Move the index back to being a regular column
        self.data = df_imputed.reset_index()


    def convert_bins_to_cm(self) -> bool:
        """
        Convert linear index to 3D coordinates (x, y, z).
        """
        self.data['x_cm'] = self.data['x'] * self.bin_x + self.bin_x / 2 if self.central_voxel else self.data['x'] * self.bin_x
        self.data['y_cm'] = self.data['y'] * self.bin_y + self.bin_y / 2 if self.central_voxel else self.data['y'] * self.bin_y
        self.data['z_cm'] = self.data['z'] * self.bin_z + self.bin_z / 2 if self.central_voxel else self.data['z'] * self.bin_z

        self.data['jx_cm'] = self.data['jx'] / self.bin_x**2
        self.data['jy_cm'] = self.data['jy'] / self.bin_y**2
        self.data['jz_cm'] = self.data['jz'] / self.bin_z**2
        self.data['stdx_cm'] = self.data['stdx'] / self.bin_x**2
        self.data['stdy_cm'] = self.data['stdy'] / self.bin_y**2
        self.data['stdz_cm'] = self.data['stdz'] / self.bin_z**2
        self.data['jx_cm_abs'] = self.data['jx_cm'].abs()
        self.data['jy_cm_abs'] = self.data['jy_cm'].abs()
        self.data['jz_cm_abs'] = self.data['jz_cm'].abs()
        return True
    

    def calculate_radial_distance(self):
        """
        Calculate the radial distance from the center in the xy-plane.
        """
        print(f"Range x: {self.data['x'].min()} to {self.data['x'].max()}")
        print(f"Range y: {self.data['y'].min()} to {self.data['y'].max()}")
        print(f"Range z: {self.data['z'].min()} to {self.data['z'].max()}")
        self.center_x = (self.data['x'].max() + self.data['x'].min()) / 2
        self.center_y = (self.data['y'].max() + self.data['y'].min()) / 2        
        self.center_x_cm = (self.data['x_cm'].max() + self.data['x_cm'].min()) / 2
        self.center_y_cm = (self.data['y_cm'].max() + self.data['y_cm'].min()) / 2
        self.data['r'] = np.sqrt((self.data['x'] - self.center_x) ** 2 + (self.data['y'] - self.center_y) ** 2)
        self.data['r_cm'] = self.data['r'] * ((self.bin_x + self.bin_y) / 2)
        print(f"Calculated radial distances from {self.data['r'].min()} to {self.data['r'].max()} with center at ({self.center_x}, {self.center_y})")


    def calculate_radial_current(self):
        """
        Calculate the radial component of the current vector.
        """
        self.data['jr'] = (self.data['jx'] * (self.data['x'] - self.center_x) + self.data['jy'] * (self.data['y'] - self.center_y)) / self.data['r']
        self.data['jr_abs'] = np.abs(self.data['jr'])
        self.data['jr_cm'] = (self.data['jx_cm'] * (self.data['x_cm'] - self.center_x_cm) + self.data['jy_cm'] * (self.data['y_cm'] - self.center_y_cm)) / self.data['r_cm']
        self.data['jr_cm_abs'] = np.abs(self.data['jr_cm'])
