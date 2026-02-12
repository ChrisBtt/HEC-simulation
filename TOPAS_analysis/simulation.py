import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
from typing import Optional, Tuple


class Simulation:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.data_filtered = {}
        self.dimensions = self.get_dimensions()
        self.data_filtered[(self.dimensions[0][1] - self.dimensions[0][0]) / 2] = self.data
        self.current = {}


    def get_dimensions(self):
        x_min, x_max = self.data['x_cm'].min(), self.data['x_cm'].max()
        y_min, y_max = self.data['y_cm'].min(), self.data['y_cm'].max()
        z_min, z_max = self.data['z_cm'].min(), self.data['z_cm'].max()
        return (x_min, x_max), (y_min, y_max), (z_min, z_max)


    def filter_plane_width(self, halfwidth: float) -> None:
        center_x = (self.data['x_cm'].max() + self.data['x_cm'].min()) / 2
        center_y = (self.data['y_cm'].max() + self.data['y_cm'].min()) / 2
        filter_center = (self.data['x_cm'].between(center_x - halfwidth, center_x + halfwidth)) & (self.data['y_cm'].between(center_y - halfwidth, center_y + halfwidth))
        data_filtered = self.data[filter_center]
        self.data_filtered[halfwidth] = data_filtered


    def integrate_current_z(self, z_min: float, z_max: float, pos: float, halfwidth: Optional[float] = None) -> None:
        if halfwidth is None or halfwidth not in self.data_filtered:
            halfwidth = (self.dimensions[0][1] - self.dimensions[0][0]) / 2
        data_in_range = self.data_filtered[halfwidth][(self.data_filtered[halfwidth]['z_cm'] >= z_min) & (self.data_filtered[halfwidth]['z_cm'] <= z_max)]
        volume = (z_max - z_min) * (2 * halfwidth) ** 2  # cm^3
        integrated_current = data_in_range['jz_cm'].sum() / volume
        self.current[(pos, halfwidth)] = integrated_current



class SimulationSeries:
    def __init__(self, simulations: dict[str, Simulation], measurement):
        self.simulations = simulations
        self.measurement = measurement

    def get_simulated_signal(self):
        self.simulation_signals = {i-1: {} for i in range(1, self.measurement.num_channels+1)}
        for name, sim in self.simulations.items():
            transl = int(name.split('S')[1]) * 10
            print(f"Processing simulation {name} with currents: {sim.current.keys()}")
            for i in range(1, self.measurement.num_channels+1):
                curr0 = sim.current[(i-1, (sim.dimensions[0][1] - sim.dimensions[0][0]) / 2)]
                curr1 = sim.current[(i, (sim.dimensions[0][1] - sim.dimensions[0][0]) / 2)]
                sig = curr1 - curr0
                print(f"Simulated signal for {name} at channel {i-1}: {sig:.4e} (curr0={curr0:.4e}, curr1={curr1:.4e})")
                
                self.simulation_signals[i-1][transl] = sig
                if transl != 0:
                    self.simulation_signals[i-1][-transl] = sig
                self.simulation_signals[i-1] = {key:self.simulation_signals[i-1][key] for key in sorted(self.simulation_signals[i-1].keys())}
        print(f"Final simulation signals: {self.simulation_signals}")
        

    def plot_all_channels(self, variable: str = None, show: bool = True, save: bool = False, outdir = None, xlim = None):
        
        if variable in ['time', 'position']:
            fig, axes = plt.subplots(4, 2, figsize=(12, 10), sharex=True, constrained_layout=True)
            axes = axes.ravel()
            figs = [(fig, axes, variable)]
        else:
            figs = []
            for var in ['time', 'position']:
                fig, axes = plt.subplots(4, 2, figsize=(12, 10), sharex=True, constrained_layout=True)
                axes = axes.ravel()
                figs.append((fig, axes, var))

        m = self.measurement
        for fig, axes, variable in figs:
            for ch in range(m.num_channels):
                ax = axes[ch]
                
                if variable in ['time', 'position']:
                    self._show_measurements(ch, ax, variable=variable)
                else: 
                    for var in ['time', 'position']:
                        self._show_measurements(ch, ax, variable=var)
                ax.set_title(f"Channel {ch}")
                ax.grid(True, alpha=0.3)

                if xlim is not None:
                    ax.set_xlim(*xlim)

            fig.suptitle(f"Gantry: {m.gantry}°, Energy: {m.energy}, Field: {m.field_size}, Sampling Rate: {m.sampling_rate}Hz")
            
            fig.supxlabel("Time [s]" if variable == 'time' else "Position [mm]")
            fig.supylabel("Baseline-corrected signal [uV]")

            if save:
                base_name = os.path.splitext(os.path.basename(m.data_path))[0]
                fname = f"{base_name}_all_{m.energy}_{m.field_size}_{m.sampling_rate}Hz_{variable}.pdf"
                os.makedirs(outdir, exist_ok=True) if outdir else None
                outpath = os.path.join(outdir, fname) if outdir else fname
                fig.savefig(outpath, dpi=200)

        if show:
            plt.show()
        else:
            plt.close(fig)


    def _show_measurements(self, ch: int, ax: plt.Axes, variable: str = 'time'):
        """
        Plot all runs of a measurement on a single axis.
        """

        label = self.measurement.notes if isinstance(self.measurement.notes, str) and self.measurement.notes else f"channel {ch}"
        ax2 = ax.twinx()
        if variable == 'time':
            ax.plot(self.measurement.timestamp, self.measurement.channels_cleaned[f"ch{ch}"] * 1e6, alpha=0.7, label=label)
            # # ax.vlines(self.measurement.features['signal_window'][ch], ymin=-500, ymax=500, colors='gray', linestyles='dashed', alpha=0.3, label=f"{label} (signal window)")
            ax2.plot(self.measurement.motor_signal['timestamp'], self.measurement.motor_signal['position'], label="Motor position", linestyle=':')

        elif variable == 'position':
            ax.plot(self.measurement.position, self.measurement.channels_cleaned[f"ch{ch}"] * 1e6, alpha=0.7, label=label)
            ax2.plot(self.simulation_signals[ch].keys(), self.simulation_signals[ch].values(), marker='o', label="Simulated current", color="tab:orange", linestyle='--')
            # ax2.plot(self.measurement.motor_signal['position'], self._cylinder_mass_in_beam(r=25, w_x=10, w_y=70, rho=0.6)[1], label=f"{label} (estimated mass in beam)", color='red', linestyle=':')
        lns1, lbs1 = ax.get_legend_handles_labels()
        lns2, lbs2 = ax2.get_legend_handles_labels()
        ax2.legend(lns1 + lns2, lbs1 + lbs2, loc='best')


    def _cylinder_mass_in_beam(self, r: float = 25, w_x: float = 70, w_y: float = 70, rho: float = 0.6):
        volume = []
        mass = []
        
        for pos in self.measurement.motor_signal['position']:
            x_a = -w_x / 2.0
            x_b = w_x / 2.0

            thickness = lambda x_beam, x: 2.0 * np.sqrt(max(0.0, r**2 - (x_beam - x)**2))

            x_beam = np.linspace(x_a, x_b, 1000)
            thickness_profile = [thickness(x, pos) for x in x_beam]
            vol = np.trapezoid(thickness_profile, x_beam) * w_y # mm^3
            m = vol * rho  # g/mm^3
            volume.append(vol)
            mass.append(m)

        return volume, mass
