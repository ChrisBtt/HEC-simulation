import pandas as pd
import numpy as np


class Preprocessor(object):
    def __init__(self, path: str | list, identifier: str, bin_x: int, bin_y: int, bin_z: int, impute = False):
        self.path = path
        self.identifier = identifier
        self.bin_x = bin_x
        self.bin_y = bin_y
        self.bin_z = bin_z
        self.impute = impute

        if self.identifier not in ['current', 'dose']:
            raise ValueError(f"Identifier '{self.identifier}' not recognized. Use 'current' or 'dose'.")
    
        self.data = self.load_data()
        self.convert_bins_to_cm()
        if self.impute:
            self.impute_missing_values()
        self.calculate_radial_distance()
        if self.identifier == 'current':
            self.calculate_radial_current()


    def load_data(self) -> pd.DataFrame:
        """
        Load the simulated current density starting from the line number where "Cell Current X Y Z ZF ZB" appears
        """
        if self.identifier == 'dose' and isinstance(self.path, str):
            data = pd.read_csv(self.path, 
                names=['x', 'y', 'z', 'dose', 'std', 'hist'], 
                comment='#',
            )
        elif self.identifier == 'current' and isinstance(self.path, list):
            for path in self.path:
                print(f"Loading data from {path}...")
                if 'X' in path:
                    data_x = pd.read_csv(path, 
                        names=['x', 'y', 'z', 'jx', 'stdx', 'hist'],
                        comment='#',
                    )
                elif 'Y' in path:
                    data_y = pd.read_csv(path, 
                        names=['x', 'y', 'z', 'jy', 'stdy', 'hist'],
                        comment='#',
                    )
                elif 'Z' in path:
                    data_z = pd.read_csv(path, 
                        names=['x', 'y', 'z', 'jz', 'stdz', 'hist'],
                        comment='#',
                    )

            data = pd.merge(data_x, data_y, on=['x', 'y', 'z'])
            data = pd.merge(data, data_z, on=['x', 'y', 'z'])

            data.columns = ['x', 'y', 'z', 'jx', 'stdx', 'histx', 'jy', 'stdy', 'histy', 'jz', 'stdz', 'histz']
            data = data.loc[:, ~data.columns.duplicated()]
            data['jx_abs'] = data['jx'].abs()
            data['jy_abs'] = data['jy'].abs()
            data['jz_abs'] = data['jz'].abs()
        else:
            raise ValueError("For 'dose', path must be a single string. For 'current', path must be a list of strings for X, Y, Z components.")

        return data


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
        self.data['x_cm'] = self.data['x'] * self.bin_x
        self.data['y_cm'] = self.data['y'] * self.bin_y
        self.data['z_cm'] = self.data['z'] * self.bin_z
        if self.identifier == 'current':
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
        self.center_x = (self.data['x'].max() + 1) / 2
        self.center_y = (self.data['y'].max() + 1) / 2        
        self.center_x_cm = (self.data['x_cm'].max() + 1) / 2
        self.center_y_cm = (self.data['y_cm'].max() + 1) / 2
        self.data['r'] = np.sqrt((self.data['x'] - self.center_x) ** 2 + (self.data['y'] - self.center_y) ** 2)
        self.data['r_cm'] = self.data['r'] * ((self.bin_x + self.bin_y) / 2)
        print(f"Calculated radial distances from {self.data['r'].min()} to {self.data['r'].max()} with center at ({self.center_x}, {self.center_y})")


    def calculate_radial_current(self):
        """
        Calculate the radial component of the current vector.
        """
        self.data['jr'] = (self.data['jx'] * (self.data['x'] - self.center_x) + self.data['jy'] * (self.data['y'] - self.center_y)) / self.data['r']
        self.data['jr_abs'] = (self.data['jx'].abs() * (self.data['x'] - self.center_x) + self.data['jy'].abs() * (self.data['y'] - self.center_y)) / self.data['r']
        self.data['jr_cm'] = (self.data['jx_cm'] * (self.data['x_cm'] - self.center_x_cm) + self.data['jy_cm'] * (self.data['y_cm'] - self.center_y_cm)) / self.data['r_cm']
        self.data['jr_cm_abs'] = (self.data['jx_cm'].abs() * (self.data['x_cm'] - self.center_x_cm) + self.data['jy_cm'].abs() * (self.data['y_cm'] - self.center_y_cm)) / self.data['r_cm']

