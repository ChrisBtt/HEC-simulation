import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy import signal
import matplotlib.pyplot as plt


class Measurement:
	"""Represents one measurement file and its per-channel data."""

	def __init__(
		self,
		data_path: str,
		gantry: float,
		energy: str,
		field_size: str,
		mu: float,
		mu_rate: float,
		sampling_rate: float,
		motor_path: Optional[str] = None,
		time_offset: float = 0.0,
		notes: str = "",
		root_dir: Optional[str] = None,
	) -> None:
		if isinstance(data_path, (list, tuple)):
			if len(data_path) != 1:
				raise ValueError("Measurement accepts a single file. Use Experiment to group multiple files.")
			data_path = data_path[0]

		self.data_path = self._resolve_path(data_path, root_dir)
		self.root_dir = root_dir
		self.gantry = gantry
		self.energy = energy
		self.field_size = field_size
		self.mu = mu
		self.mu_rate = mu_rate
		self.sampling_rate = sampling_rate
		self.notes = notes
		self.motor_path = motor_path
		self.t: np.ndarray = np.array([])
		self.time_offset = time_offset
		self.channels: Dict[int, np.ndarray] = {}
		self.features: Dict[str, Dict[int, Any]] = {}
		self.channels_components: Dict[str, Dict[int, Any]] = {c: {} for c in ["baseline", "signal_beam", "signal_motion", "signal_noise", "signal_filter"]}

		self._load_data_file()
		if self.motor_path:
			self._load_motor_file()

	@staticmethod
	def _resolve_path(data_path: str, root_dir: Optional[str]) -> str:
		if root_dir and not os.path.isabs(data_path):
			return os.path.join(root_dir, data_path)
		return data_path

	def _load_data_file(self) -> None:
		try:
			data = np.loadtxt(self.data_path, skiprows=6)
		except Exception as exc:  # pragma: no cover - relies on external files
			raise IOError(f"Could not load file {self.data_path}: {exc}") from exc

		self.t = data[:, 0].astype(float)
		n_channels = max(0, data.shape[1] - 1)
		if self.notes == "Reverse":
			self.channels = {ch: data[:, data.shape[1] - (ch + 1)].astype(float) for ch in range(n_channels)}
		else:
			self.channels = {ch: data[:, ch + 1].astype(float) for ch in range(n_channels)}
		
		try:
			with open(self.data_path, 'r') as f:
				date_str = f.readline().strip()
				time_str = f.readline().strip()
				timestamp_str = f"{date_str} {time_str}"
				file_timestamp = pd.to_datetime(timestamp_str, format="%m/%d/%Y %I:%M:%S %p")
				self.timestamp = (pd.to_timedelta(self.t, unit='s') + file_timestamp).values
		except Exception:
			print(f"Warning: Could not parse timestamp from file {self.data_path}. Using relative time only.")


	def _load_motor_file(self) -> None:
		try:
			self.motor_signal: Dict[str, np.ndarray] = {}
			data_motor = np.loadtxt(self.motor_path, delimiter=',', skiprows=1, usecols=(1, 2, 3), dtype=float)
			self.motor_signal['time'] = data_motor[:, 0].astype(float)
			self.motor_signal['position'] = data_motor[:, 2].astype(float)
			
			timestamps = np.loadtxt(self.motor_path, delimiter=',', skiprows=1, usecols=(0,), dtype=str)
			self.motor_signal['timestamp'] = pd.to_datetime(timestamps).values
			if self.time_offset != 0.0:
				self.timestamp += pd.to_timedelta(self.time_offset, unit='s')
				self.t += self.time_offset

			self.position = np.interp(self.timestamp.astype(np.int64), self.motor_signal['timestamp'].astype(np.int64), self.motor_signal['position'])
		except Exception as exc:
			raise IOError(f"Could not load motor file {self.motor_path}: {exc}") from exc


	def baseline_constant_from_window(self, channel: int, t: np.ndarray, y: np.ndarray, duration: float) -> Tuple[np.ndarray, float]:
		mask_begin = (t >= 0) & (t <= duration)
		mask_end = (t >= t[-1] - duration) & (t <= t[-1])
		mask = mask_begin | mask_end
		if mask.sum() < 3:
			mask = mask_begin if mask_begin.sum() >= mask_end.sum() else mask_end
		if mask.sum() == 0:
			x = y
		else:
			x = y[mask]
		baseline = np.full_like(y, np.median(x), dtype=float)
		sigma = float(np.std(x))
		self.channels_components["baseline"][channel] = baseline
		return baseline, sigma

	@staticmethod
	def remove_overshoot(
		y: np.ndarray,
		prominence: float = 10.0,
		distance: int = 100,
	) -> np.ndarray:
		peaks, _ = signal.find_peaks(np.abs(y), prominence=prominence, distance=distance)
		if len(peaks) == 0:
			return y

		y_clean = y.copy()
		for peak in sorted(peaks, reverse=True):
			start = max(0, peak - 2)
			end = min(len(y_clean), peak + 3)
			y_clean[start:end] = y_clean[start - 1]
		return y_clean

	@staticmethod
	def moving_average(signal: np.ndarray, window_size: int) -> Tuple[np.ndarray, np.ndarray]:
		if window_size < 1:
			window_size = 1
		smoothed = np.convolve(signal, np.ones(window_size) / window_size, mode="valid")
		# Pad the beginning with the first valid smoothed value to match original length
		pad_length = window_size - 1
		smoothed = np.concatenate([np.full(pad_length, smoothed[0]), smoothed])
		return smoothed

	@staticmethod
	def extract_peak_features(
		t: np.ndarray,
		y_corr: np.ndarray,
		noise_sigma: float,
		peak_sign: str = "auto",
		threshold_sigma: float = 5.0,
	) -> Dict[str, Any]:
		y = y_corr
		if peak_sign == "auto":
			sign = 1 if np.abs(y.max()) >= np.abs(y.min()) else -1
		elif peak_sign == "positive":
			sign = 1
		else:
			sign = -1

		y_s = sign * y
		peak_idx = int(np.argmax(y_s))
		peak_amp = float(y_s[peak_idx])
		peak_time = float(t[peak_idx])
		snr = float(peak_amp / noise_sigma) if noise_sigma > 0 else np.inf

		thr = float(threshold_sigma * noise_sigma) if noise_sigma > 0 else 0.0

		left = peak_idx
		while left > 0 and y_s[left] > thr:
			left -= 1
		onset_time = float(t[left]) if left < peak_idx else float(t[0])

		right = peak_idx
		while right < len(y_s) - 1 and y_s[right] > thr:
			right += 1
		end_time = float(t[right]) if right > peak_idx else float(t[-1])
		duration_above_thr = float(end_time - onset_time)

		area = float(np.trapezoid(y, t))

		half = 0.5 * peak_amp
		l2 = peak_idx
		while l2 > 0 and y_s[l2] > half:
			l2 -= 1
		r2 = peak_idx
		while r2 < len(y_s) - 1 and y_s[r2] > half:
			r2 += 1
		fwhm = float(t[r2] - t[l2]) if r2 > l2 else 0.0

		return {
			"peak_sign": "positive" if sign == 1 else "negative",
			"peak_amp": float(sign * peak_amp),
			"peak_time": peak_time,
			"snr": snr,
			"onset_time": onset_time,
			"end_time": end_time,
			"duration_above_thr": duration_above_thr,
			"fwhm": fwhm,
			"area": area,
		}

	def get_channel(self, channel: int) -> Tuple[np.ndarray, np.ndarray, float]:
		if channel not in self.channels:
			raise IndexError(f"Channel {channel} not found in measurement.")
		if hasattr(self, "channels_cleaned") and f"sig{channel}" in self.channels_cleaned:
			y = self.channels_cleaned[f"ch{channel}"]
			sigma = self.channels_cleaned[f"sig{channel}"]
		else:
			y = self.channels[channel]
			sigma = 0.0
		return self.t, y, sigma


	def clean_signal(
		self,
		duration: Optional[float] = None,
		remove_peaks: bool = False,
		moving_avg_window: Optional[int] = None,
		overshoot_prominence: float = 10.0,
		overshoot_distance: int = 100,
	) -> None:
		
		self.channels_cleaned: Dict[str, np.ndarray | float] = {}
		for ch in self.channels:
			print(f"Cleaning channel {ch}...")
			t, y, _ = self.get_channel(ch)
			if duration is not None:
				baseline, sigma = self.baseline_constant_from_window(ch, t, y, duration)
				y = y - baseline
			if remove_peaks:
				y = self.remove_overshoot(y, prominence=overshoot_prominence, distance=overshoot_distance)
			if moving_avg_window is not None:
				y = self.moving_average(y, moving_avg_window)
			self.channels_cleaned[f"ch{ch}"] = y
			self.channels_cleaned[f"sig{ch}"] = sigma

	@property
	def num_channels(self) -> int:
		return len(self.channels)

	def metadata(self) -> Dict[str, Any]:
		return {
			"gantry": self.gantry,
			"energy": self.energy,
			"field_size": self.field_size,
			"mu": self.mu,
			"mu_rate": self.mu_rate,
			"sampling_rate": self.sampling_rate,
			"notes": self.notes,
			"data_path": self.data_path,
		}

	def compute_features(
		self,
		duration: Optional[float] = 1.0,
		peak_sign: str = "auto",
		threshold_sigma: float = 5.0,
	) -> pd.DataFrame:
		if self.t.size == 0:
			return pd.DataFrame()

		rows: List[Dict[str, Any]] = []
		self.clean_signal(
			duration=duration,
			remove_peaks=True,
			moving_avg_window=None,
		)
		self.detect_signal_window()
		for ch in range(self.num_channels):
			feats = self.extract_peak_features(
				t=self.channels_cleaned[f"t{ch}"],
				y_corr=self.channels_cleaned[f"ch{ch}"],
				noise_sigma=self.channels_cleaned[f"sig{ch}"],
				peak_sign=peak_sign,
				threshold_sigma=threshold_sigma,
			)

			rows.append({
				"run_idx": 0,
				"channel": ch,
				"noise_sigma": self.channels_cleaned[f"sig{ch}"],
				**feats,
				**self.metadata(),
			})

		return pd.DataFrame(rows)


	def detect_signal_window(self, noise_multiplier: float = 3.0, min_duration: float = 0.05) -> None:
		"""
		Detect signal window boundaries based on noise level and signal characteristics.
		
		Finds the first point above threshold from the start and the last point above 
		threshold from the end, assuming a single continuous signal.
		"""

		self.features['signal_window'] = {}
		print(f"Detect signal window for channels: {list(self.channels)}")
		for ch in self.channels:
			t, y, sigma = self.get_channel(ch)
		
			if len(t) < 2:
				self.features['signal_window'][ch] = (float(t[0]), float(t[-1]))
				continue
			
			threshold = noise_multiplier * sigma
			above_threshold = np.abs(y) > threshold
			
			if not above_threshold.any():
				self.features['signal_window'][ch] = (float(t[0]), float(t[-1]))
				continue
			
			# Find first index above threshold from start
			start_idx = np.where(above_threshold)[0][0]
			
			# Find last index above threshold from end
			end_idx = np.where(above_threshold)[0][-1]
			
			t_start = float(t[start_idx])
			t_end = float(t[end_idx])
			
			# Ensure minimum duration
			if t_end - t_start < min_duration:
				mid = (t_start + t_end) / 2
				t_start = max(float(t[0]), mid - min_duration / 2)
				t_end = min(float(t[-1]), mid + min_duration / 2)
		
			self.features['signal_window'][ch] = (t_start, t_end)


	@staticmethod
	def _ensure_band(
		f_lo: float, f_hi: float, fs: float, min_hz: float = 1e-4, guard: float = 0.99
	) -> Tuple[float, float]:
		"""
		Ensure [f_lo, f_hi] is valid: 0 < f_lo < f_hi < Nyquist*guard.
		"""
		nyq = fs / 2.0
		f_lo = max(min_hz, float(f_lo))
		f_hi = float(f_hi)
		f_hi = min(f_hi, guard * nyq)
		if not (f_lo < f_hi):
			# fallback to something tiny but valid
			f_lo = max(min_hz, 0.01)
			f_hi = min(guard * nyq, 0.1)
		return f_lo, f_hi

	@staticmethod
	def _butter_sos(
		order: int,
		fs: float,
		btype: str,
		Wn: float | Tuple[float, float],
	) -> np.ndarray:
		"""
		Design a Butterworth SOS filter using scipy.signal.butter with fs-based cutoff(s).
		"""
		return signal.butter(order, Wn=Wn, btype=btype, fs=fs, output="sos")

	@staticmethod
	def _sosfiltfilt_safe(sos: np.ndarray, x: np.ndarray) -> np.ndarray:
		"""
		Zero-phase filtering. Falls back to forward-only filtering if signal is too short.
		"""
		x = np.asarray(x, dtype=float)
		# filtfilt requires enough samples; heuristic: > 3*(2*sections) is usually safe
		n_sections = sos.shape[0]
		min_len = max(25, 6 * n_sections + 1)
		if x.size < min_len:
			return signal.sosfilt(sos, x)
		return signal.sosfiltfilt(sos, x)

	@staticmethod
	def _rolling_median(x: np.ndarray, win: int) -> np.ndarray:
		"""
		Fast-ish rolling median using padding + sliding windows. Good baseline estimator
		for step-like signals (preserves edges better than low-pass).
		"""
		x = np.asarray(x, dtype=float)
		win = int(max(1, win))
		if win == 1:
			return x.copy()
		# ensure odd window for symmetric median
		if win % 2 == 0:
			win += 1
		pad = win // 2
		xp = np.pad(x, (pad, pad), mode="edge")
		# sliding window view (numpy >= 1.20)
		w = np.lib.stride_tricks.sliding_window_view(xp, win)
		return np.median(w, axis=-1)

	# ---------- requested top-level method ----------

	def separate_signal_components(
		self,
		motion_freq: float = 1.0 / 6.0,
		noise_freq: float = 25.0,
	) -> None:
		"""
		Separate signal into:
			- baseline / beam (step-like low-frequency component)
			- motion (quasi-periodic oscillation around motion_freq)
			- noise (high-frequency component above noise_freq)

		This follows a robust pipeline:
			1) baseline via rolling median (preserves step edges)
			2) motion via band-pass around motion_freq on (signal - baseline)
			3) noise via high-pass on residual after removing baseline+motion
			4) beam/step estimate = baseline (optionally could refine via change-points)

		Args:
			motion_freq: Expected fundamental frequency (Hz) of motion (e.g. ~1/6 ≈ 0.167 Hz).
			noise_freq:  High-pass cutoff (Hz) for noise component.
		"""
		fs = float(self.sampling_rate)
		if fs <= 0:
			raise ValueError("sampling_rate must be > 0")

		center = float(motion_freq)
		if center <= 0:
			raise ValueError("motion_freq must be > 0 (Hz)")

		bw_lo_factor = 0.25
		bw_hi_factor = 60
		f_lo = center * bw_lo_factor
		f_hi = center * bw_hi_factor

		f_lo, f_hi = self._ensure_band(f_lo, f_hi, fs)

		period_s = 1.0 / center
		baseline_window_s = 5 * period_s
		baseline_win = int(max(5, round(baseline_window_s * fs)))

		# Noise cutoff sanity
		nyq = fs / 2.0
		noise_fc = float(max(1e-4, min(0.99 * nyq, float(noise_freq))))

		print(
			f"[separate_signal_components] fs={fs:.3f} Hz | motion≈{center:.4f} Hz "
			f"(band {f_lo:.4f}–{f_hi:.4f} Hz) | baseline_win≈{baseline_win} samples "
			f"({baseline_win/fs:.2f} s) | noise_hp={noise_fc:.3f} Hz"
		)

		# Design filters (SOS)
		sos_bp_motion = self._butter_sos(order=4, fs=fs, btype="bandpass", Wn=(f_lo, f_hi))
		sos_hp_noise = self._butter_sos(order=4, fs=fs, btype="highpass", Wn=noise_fc)

		for ch in self.channels:
			t, y, _ = self.get_channel(ch)
			y = np.asarray(y, dtype=float)

			# 1) Baseline / beam (step-like)
			baseline = self._rolling_median(y, baseline_win)

			# 2) Motion (band-pass on detrended signal)
			detrended = y - baseline
			motion = self._sosfiltfilt_safe(sos_bp_motion, detrended)

			# 3) Noise (high-pass on residual after removing baseline + motion)
			residual = y - baseline - motion
			noise = self._sosfiltfilt_safe(sos_hp_noise, residual)

			# 4) Beam/step signal estimate: baseline (optionally subtract very-low-f drift etc.)
			beam = baseline  # This is your step component (incl. any slow drift)

			# Store components
			self.channels_components["signal_motion"][ch] = motion
			self.channels_components["signal_noise"][ch] = noise
			self.channels_components["signal_beam"][ch] = beam
			self.channels_components["signal_filter"][ch] = self.channels_cleaned[f"ch{ch}"] - noise


	@staticmethod
	def _exponential_decay(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
		"""Exponential decay fitting function: a * exp(-b * x) + c"""
		return a * np.exp(-b * x) + c

	@staticmethod
	def _gaussian(x: np.ndarray, a: float, mu: float, sigma: float) -> np.ndarray:
		"""Gaussian fitting function"""
		return a * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))

	def integrate_signal_basic(
		self,
		duration: Optional[float] = None,
		remove_peaks: bool = True,
		moving_avg_window: int = 5,
		overshoot_prominence: float = 100.0,
		overshoot_distance: int = 100,
		preserve_sign: bool = False,
	) -> None:
		"""
		Basic signal integration approach:
		- Subtract baseline
		- Remove overshoot peaks
		- Apply moving average for smoothing
		- Integrate using trapezoidal rule
		
		Args:
			duration: Duration for baseline estimation
			remove_peaks: Whether to remove overshoot peaks
			moving_avg_window: Moving average window size in samples
			overshoot_prominence: Prominence threshold for peak removal
			overshoot_distance: Minimum distance between peaks
			
		Returns:
			Integrated signal value (Volt·seconds). By default returns magnitude
			(area under |signal|). If preserve_sign=True, returns signed integral
			over the processed signal.
		"""
		self.clean_signal(
			duration=duration,
			remove_peaks=remove_peaks,
			moving_avg_window=moving_avg_window,
			overshoot_prominence=overshoot_prominence,
			overshoot_distance=overshoot_distance,
		)
		self.integrals: Dict[int, float] = {}
		for ch in self.channels:
			t = self.channels_cleaned[f"t{ch}"]
			y = self.channels_cleaned[f"ch{ch}"]
		
			if len(t) < 2:
				integral = 0.0
			
			# Integrate using trapezoidal rule
			if preserve_sign:
				integral = float(np.trapezoid(y, t))
			else:
				integral = float(np.trapezoid(np.abs(y), t))
			self.integrals[ch] = integral


	def integrate_signal_advanced(
		self,
		duration: Optional[float] = None,
		remove_peaks: bool = True,
		moving_avg_window: int = 5,
		overshoot_prominence: float = 100.0,
		overshoot_distance: int = 100,
		noise_multiplier: float = 3.0,
		fit_type: str = "exponential",
		preserve_sign: bool = False,
	) -> Dict[str, float]:
		"""
		Advanced signal integration approach:
		- Preprocess signal (baseline, peaks, smoothing)
		- Detect signal window automatically
		- Fit curve to signal within window
		- Integrate the fitted curve
		
		Args:
			channel: Channel index
			duration: Duration for baseline estimation
			remove_peaks: Whether to remove overshoot peaks
			moving_avg_window: Moving average window size in samples
			overshoot_prominence: Prominence threshold for peak removal
			overshoot_distance: Minimum distance between peaks
			noise_multiplier: Multiplier for noise threshold in window detection
			fit_type: Type of fit - "exponential" or "gaussian"
			preserve_sign: Whether to preserve the sign of the integral
		Returns:
			Dictionary with keys:
			- 'integral': absolute integrated value of fitted signal (backward compatible)
			- 'integral_abs': same as 'integral' (explicit)
			- 'integral_signed': signed integral using the sign from original windowed signal
			- 'signal_sign': +1 or -1 inferred from original signal within window
			- 'window_start': signal window start time
			- 'window_end': signal window end time
			- 'fit_params': fitted curve parameters
			- 'fit_quality': R-squared value
		"""
		self.clean_signal(
			duration=duration,
			remove_peaks=remove_peaks,
			moving_avg_window=moving_avg_window,
			overshoot_prominence=overshoot_prominence,
			overshoot_distance=overshoot_distance,
		)
		self.detect_signal_window(noise_multiplier=noise_multiplier)

		self.integrals: Dict[int, float] = {}
		for ch in self.channels:
			t = self.channels_cleaned[f"t{ch}"]
			y = self.channels_cleaned[f"ch{ch}"]
		
			if len(t) < 2:
				return {
					'integral': 0.0,
					'integral_abs': 0.0,
					'integral_signed': 0.0,
					'signal_sign': 0.0,
					'window_start': float(t[0]) if len(t) > 0 else 0.0,
					'window_end': float(t[-1]) if len(t) > 0 else 0.0,
					'fit_params': [],
					'fit_quality': 0.0,
				}
			t_start, t_end = self.features['signal_window'][ch]
			
			mask = (t >= t_start) & (t <= t_end)
			t_window = t[mask]
			y_window = y[mask]
			
			if len(t_window) < 3:
				integral_abs = float(np.trapezoid(np.abs(y), t))
				integral_signed = float(np.trapezoid(y, t))
				signal_sign = float(np.sign(integral_signed)) if integral_abs > 0 else 0.0
				return {
					'integral': integral_abs,
					'integral_abs': integral_abs,
					'integral_signed': integral_signed,
					'signal_sign': signal_sign,
					'window_start': t_start,
					'window_end': t_end,
					'fit_params': [],
					'fit_quality': 0.0,
				}
			
			# Normalize time for fitting
			t_norm = t_window - t_window[0]
			y_abs = np.abs(y_window)
			
			# Fit curve
			fit_params = []
			fit_quality = 0.0
			y_fitted = y_abs.copy()
			
			try:
				if fit_type == "exponential":
					# Initial guess for exponential decay
					p0 = [y_abs.max(), 1.0, 0.0]
					popt, _ = curve_fit(
						self._exponential_decay, t_norm, y_abs, p0=p0, maxfev=10000
					)
					y_fitted = self._exponential_decay(t_norm, *popt)
					fit_params = list(popt)
					
				elif fit_type == "gaussian":
					# Initial guess for Gaussian
					p0 = [y_abs.max(), t_norm[len(t_norm) // 2], (t_norm[-1] - t_norm[0]) / 4]
					popt, _ = curve_fit(
						self._gaussian, t_norm, y_abs, p0=p0, maxfev=10000
					)
					y_fitted = self._gaussian(t_norm, *popt)
					fit_params = list(popt)
				
				# Calculate R-squared
				ss_res = np.sum((y_abs - y_fitted) ** 2)
				ss_tot = np.sum((y_abs - y_abs.mean()) ** 2)
				fit_quality = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
				
			except Exception:
				# Fitting failed, use original signal
				y_fitted = y_abs
				fit_quality = 0.0
			
			# Integrate fitted signal
			integral_abs = float(np.trapezoid(y_fitted, t_norm))
			integral_signed_orig = float(np.trapezoid(y_window, t_norm))
			signal_sign = float(np.sign(integral_signed_orig)) if integral_abs > 0 else 0.0
			integral_signed = signal_sign * integral_abs
			
			result = {
				'integral': integral_abs,
				'integral_abs': integral_abs,
				'integral_signed': integral_signed,
				'signal_sign': signal_sign,
				'window_start': t_start,
				'window_end': t_end,
				'fit_params': fit_params,
				'fit_quality': fit_quality,
			}
			
			# If preserve_sign requested, mirror legacy 'integral' to signed value
			if preserve_sign:
				result['integral'] = result['integral_signed']

			self.integrals[ch] = result


	def calculate_currents(self):

		self.currents = {}

		self.clean_signal(duration=1, remove_peaks=True, moving_avg_window=5)
		self.detect_signal_window()
		self.separate_signal_components()

		for ch in range(self.num_channels):
			summed = np.sum([self.channels_cleaned[f"ch{i}"] for i in range(ch + 1)], axis=0)
			self.currents[ch] = summed / 1e6  # Convert from V to A assuming 1 MOhm resistor