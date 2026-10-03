#!/usr/bin/env python3
"""
replace_rtdose.py

Replace an Eclipse RTDose's pixel data with a normalized TOPAS-simulated
dose distribution, while keeping RTPlan/RTStruct references intact.

Key points:
  * TOPAS dose is resampled onto the Eclipse grid (physical mm coordinates),
    or kept on its own grid with --keep-geometry-from-topas (no shifting).
  * Output pixel values are capped at 2^31-1 so viewers that interpret
    32-bit RTDOSE as signed (e.g. Weasis) do not wrap the high-dose region
    to negative values ("hollow beam" artifact).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pydicom
from scipy.ndimage import map_coordinates, median_filter

# Safe max integer for both signed and unsigned 32-bit interpretation
SAFE_MAX_INT = 2**31 - 1


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _check_orientation(ds, name):
    iop = np.array(getattr(ds, "ImageOrientationPatient", [1, 0, 0, 0, 1, 0]), float)
    if not np.allclose(iop, [1, 0, 0, 0, 1, 0], atol=1e-4):
        print(f"[WARNING] {name} ImageOrientationPatient={iop.tolist()} is not "
              "axis-aligned; resampling assumes identity orientation.")


def grid_axes_mm(ds):
    """Return (z_mm, y_mm, x_mm) 1D coordinate arrays for an RTDose dataset."""
    ipp = np.array(ds.ImagePositionPatient, dtype=float)
    row_sp, col_sp = (float(v) for v in ds.PixelSpacing)
    nz, ny, nx = int(ds.NumberOfFrames), int(ds.Rows), int(ds.Columns)

    x = ipp[0] + np.arange(nx) * col_sp
    y = ipp[1] + np.arange(ny) * row_sp

    gfov = getattr(ds, "GridFrameOffsetVector", None)
    if gfov is not None and len(gfov) == nz:
        z = ipp[2] + np.array(gfov, dtype=float)
    else:
        dz = float(getattr(ds, "SliceThickness", 0) or 1.0)
        print(f"[WARNING] GridFrameOffsetVector missing/inconsistent; "
              f"using uniform dz={dz} mm.")
        z = ipp[2] + np.arange(nz) * dz
    return z, y, x


def _coord_to_index(coords_dst, coords_src):
    """Map destination mm coordinates to fractional source indices.
    Out-of-range -> -1e6 (filled with 0 by map_coordinates)."""
    idx = np.arange(coords_src.size, dtype=float)
    if coords_src.size > 1 and coords_src[1] < coords_src[0]:
        coords_src, idx = coords_src[::-1], idx[::-1]
    return np.interp(coords_dst, coords_src, idx, left=-1e6, right=-1e6)


def resample_to_grid(src_dose, src_ds, dst_ds):
    """Trilinear resampling of src_dose (z,y,x, float Gy) onto dst_ds grid
    using physical patient coordinates (handles different spacing/size/origin)."""
    _check_orientation(src_ds, "TOPAS")
    _check_orientation(dst_ds, "Eclipse")

    zs, ys, xs = grid_axes_mm(src_ds)
    zd, yd, xd = grid_axes_mm(dst_ds)

    iz = _coord_to_index(zd, zs)
    iy = _coord_to_index(yd, ys)
    ix = _coord_to_index(xd, xs)

    print(f"[RESAMPLE] TOPAS grid {src_dose.shape} -> Eclipse grid "
          f"{(zd.size, yd.size, xd.size)}")
    print(f"[RESAMPLE] TOPAS spacing (z,y,x) ~ "
          f"({np.diff(zs).mean() if zs.size > 1 else 0:.3f}, "
          f"{np.diff(ys).mean():.3f}, {np.diff(xs).mean():.3f}) mm")

    Z, Y, X = np.meshgrid(iz, iy, ix, indexing="ij")
    out = map_coordinates(src_dose, [Z, Y, X], order=1, mode="constant", cval=0.0)

    src_sum, dst_sum = src_dose.sum(), out.sum()
    print(f"[RESAMPLE] Max before/after: {src_dose.max():.4g} / {out.max():.4g} Gy")
    if dst_sum == 0 and src_sum > 0:
        print("[WARNING] Resampled dose is all zero - grids do not overlap!")
    return out


# --------------------------------------------------------------------------
# Dose loading / cleaning
# --------------------------------------------------------------------------
def load_dose_gy(ds):
    """Return dose in Gy as float64 (z,y,x) with DoseGridScaling applied."""
    arr = ds.pixel_array
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]
    dose = arr.astype(np.float64) * float(ds.DoseGridScaling)
    return dose, arr


def check_saturation(raw_arr, mask_saturated=False, dose_gy=None):
    """TOPAS maps its max voxel to the integer max -> one voxel there is normal.
    Many voxels at the max indicate true saturation."""
    max_val = raw_arr.max()
    n_at_max = int(np.sum(raw_arr == max_val))
    bits_max = np.iinfo(raw_arr.dtype).max if np.issubdtype(raw_arr.dtype, np.integer) else None
    print(f"[INFO] TOPAS raw max={max_val} (dtype {raw_arr.dtype}), "
          f"voxels at max: {n_at_max}")
    if bits_max is not None and max_val == bits_max and n_at_max > 1:
        print(f"[WARNING] {n_at_max} voxels at the integer limit -> likely "
              "saturation in TOPAS output. Prefer binary/csv scorer output.")
        if mask_saturated and dose_gy is not None:
            sat = raw_arr == max_val
            filt = median_filter(dose_gy, size=3)
            dose_gy[sat] = filt[sat]
            print(f"[INFO] Replaced {n_at_max} saturated voxels by 3x3x3 median.")
    if np.issubdtype(raw_arr.dtype, np.signedinteger) and raw_arr.min() < 0:
        print(f"[WARNING] Negative raw TOPAS values found (min={raw_arr.min()}): "
              "possible signed overflow in the TOPAS file.")
    return dose_gy


def clean_dose(dose):
    dose = np.nan_to_num(dose, nan=0.0, posinf=0.0, neginf=0.0)
    dose[dose < 0] = 0.0
    return dose


# --------------------------------------------------------------------------
# Histograms / diagnostics
# --------------------------------------------------------------------------
def plot_dose_histograms(topas_dose_gy, eclipse_dose_gy, output_path=None,
                         percentiles=(50, 90, 95, 99, 99.9, 99.99, 100)):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    topas_nonzero = topas_dose_gy[topas_dose_gy > 0]
    eclipse_nonzero = eclipse_dose_gy[eclipse_dose_gy > 0]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for row, (data, color, name) in enumerate(
            [(topas_nonzero, "steelblue", "TOPAS"),
             (eclipse_nonzero, "darkorange", "Eclipse")]):
        for col, log in enumerate([False, True]):
            ax = axes[row, col]
            ax.hist(data, bins=200, color=color)
            if log:
                ax.set_yscale("log")
            ax.set_title(f"{name} dose (nonzero voxels) - {'log' if log else 'linear'}")
            ax.set_xlabel("Dose (Gy)")
            ax.set_ylabel("Voxel count" + (" (log)" if log else ""))

    colors = plt.cm.viridis(np.linspace(0, 1, len(percentiles)))
    t_vals, e_vals = {}, {}
    for p, c in zip(percentiles, colors):
        t_vals[p] = np.percentile(topas_nonzero, p)
        e_vals[p] = np.percentile(eclipse_nonzero, p)
        for ax in axes[0]:
            ax.axvline(t_vals[p], color=c, ls="--", lw=1, label=f"P{p}: {t_vals[p]:.3e} Gy")
        for ax in axes[1]:
            ax.axvline(e_vals[p], color=c, ls="--", lw=1, label=f"P{p}: {e_vals[p]:.3f} Gy")
    for ax in axes.flat:
        ax.legend(fontsize=7, loc="upper right")

    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"[INFO] Dose histogram plot saved to {output_path}")
    plt.close(fig)

    print("\n[HISTOGRAM] Percentile table (nonzero voxels only):")
    print(f"{'Percentile':>10} | {'TOPAS (Gy)':>15} | {'Eclipse (Gy)':>15} | "
          f"{'Implied norm_factor':>20}")
    print("-" * 70)
    for p in percentiles:
        t, e = t_vals[p], e_vals[p]
        nf = e / t if t > 0 else float("nan")
        print(f"{p:>10} | {t:>15.6e} | {e:>15.6f} | {nf:>20.6e}")
    print()
    return t_vals, e_vals


def check_dose_distribution_3d(dose_array_gy):
    total = np.sum(dose_array_gy)
    if total <= 0:
        print("[WARNING] Total dose is zero or negative. Cannot calculate centroid.")
        return (0.0, 0.0, 0.0)
    z, y, x = np.indices(dose_array_gy.shape)
    cx = float(np.sum(dose_array_gy * x) / total)
    cy = float(np.sum(dose_array_gy * y) / total)
    cz = float(np.sum(dose_array_gy * z) / total)
    print(f"[INFO] Dose centroid (voxels): (x={cx:.2f}, y={cy:.2f}, z={cz:.2f})")
    return (cx, cy, cz)


def centroid_mm(dose, ds):
    z, y, x = grid_axes_mm(ds)
    cx, cy, cz = check_dose_distribution_3d(dose)
    mm = (np.interp(cx, np.arange(x.size), x),
          np.interp(cy, np.arange(y.size), y),
          np.interp(cz, np.arange(z.size), z))
    print(f"[INFO] Dose centroid (mm, patient): "
          f"(x={mm[0]:.1f}, y={mm[1]:.1f}, z={mm[2]:.1f})")
    return mm


# --------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------
def normalize_topas_dose(topas_dose, eclipse_dose, method="percentile",
                         percentile=99.0, same_grid=True):
    """Both inputs are float Gy arrays. Returns (normalized_dose, factor)."""
    print(f"[NORMALIZE] method='{method}'")
    print(f"TOPAS dose range: {topas_dose.min():.6g} Gy to {topas_dose.max():.6g} Gy")
    print(f"Eclipse dose range: {eclipse_dose.min():.6g} Gy to {eclipse_dose.max():.6g} Gy")

    if method == "percentile":
        ref_eclipse = np.percentile(eclipse_dose[eclipse_dose > 0], percentile)
        ref_topas = np.percentile(topas_dose[topas_dose > 0], percentile)
    elif method == "point":
        if not same_grid:
            raise ValueError("--norm-method point requires TOPAS dose on the "
                             "Eclipse grid (do not use --keep-geometry-from-topas).")
        idx = np.unravel_index(np.argmax(eclipse_dose), eclipse_dose.shape)
        # average a 3x3x3 neighbourhood for robustness against MC noise
        sl = tuple(slice(max(i - 1, 0), i + 2) for i in idx)
        ref_eclipse = eclipse_dose[sl].mean()
        ref_topas = topas_dose[sl].mean()
    elif method == "max":
        ref_eclipse = eclipse_dose.max()
        ref_topas = topas_dose.max()
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    if not np.isfinite(ref_topas) or ref_topas <= 0:
        raise ValueError(f"Reference TOPAS dose is {ref_topas} (method={method}); "
                         "cannot normalize. Try another method/percentile.")

    norm_factor = ref_eclipse / ref_topas
    normalized = topas_dose * norm_factor

    print(f"[NORMALIZE] ref_eclipse={ref_eclipse:.6g} Gy, ref_topas={ref_topas:.6g} Gy, "
          f"norm_factor={norm_factor:.6e}")
    print(f"[NORMALIZE] Normalized TOPAS dose max: {normalized.max():.6g} Gy")
    return normalized, norm_factor


# --------------------------------------------------------------------------
# Quantization / output
# --------------------------------------------------------------------------
def format_ds(value):
    """Format a float as a valid DICOM DS (max 16 chars)."""
    for prec in range(10, 0, -1):
        s = f"{value:.{prec}g}"
        if len(s) <= 16:
            return s
    raise ValueError(f"Cannot format {value} as DS")


def quantize_dose(dose_gy, headroom_factor=1.05, max_int=SAFE_MAX_INT):
    """Float Gy -> uint32 pixels (values <= max_int) + DoseGridScaling.
    The scaling is recomputed from the formatted DS string so the stored
    value and the pixel data are exactly consistent."""
    max_dose = float(dose_gy.max())
    if max_dose <= 0:
        raise ValueError("Cannot quantize a dose array with max <= 0.")

    scaling_str = format_ds(max_dose * headroom_factor / max_int)
    scaling = float(scaling_str)

    pix = np.round(dose_gy / scaling)
    pix = np.clip(pix, 0, max_int).astype(np.uint32)
    print(f"[QUANTIZE] DoseGridScaling={scaling_str}, max pixel={pix.max()} "
          f"(limit {max_int}), max dose stored={pix.max() * scaling:.6g} Gy")
    return pix, scaling_str


def build_new_rtdose(eclipse_ds, topas_ds, normalized_dose_gy, new_sop_uid=None,
                     keep_geometry_from_topas=False, headroom=1.05):
    new_ds = eclipse_ds.copy()
    print("[INFO] Building new RTDose dataset...")

    if keep_geometry_from_topas:
        print("[INFO] Geometry copied from TOPAS RTDose (dose kept on TOPAS grid, no shift).")
        for tag in ["ImagePositionPatient", "ImageOrientationPatient", "PixelSpacing",
                    "GridFrameOffsetVector", "Rows", "Columns", "NumberOfFrames",
                    "SliceThickness"]:
            if hasattr(topas_ds, tag):
                setattr(new_ds, tag, getattr(topas_ds, tag))
        # FrameOfReferenceUID intentionally kept from Eclipse so it matches
        # RTPlan/RTStruct/CT.
    else:
        print("[INFO] Geometry kept from Eclipse RTDose (dose resampled to Eclipse grid).")

    nz, ny, nx = normalized_dose_gy.shape
    if (int(new_ds.NumberOfFrames), int(new_ds.Rows), int(new_ds.Columns)) != (nz, ny, nx):
        raise ValueError(f"Dose array shape {(nz, ny, nx)} does not match header "
                         f"({new_ds.NumberOfFrames}, {new_ds.Rows}, {new_ds.Columns}).")

    pixel_array, scaling_str = quantize_dose(normalized_dose_gy, headroom_factor=headroom)

    new_ds.BitsAllocated = 32
    new_ds.BitsStored = 32
    new_ds.HighBit = 31
    new_ds.PixelRepresentation = 0
    new_ds.SamplesPerPixel = 1
    new_ds.PhotometricInterpretation = "MONOCHROME2"
    new_ds.DoseGridScaling = scaling_str
    new_ds.PixelData = pixel_array.tobytes()
    new_ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

    new_ds.DoseUnits = "GY"
    new_ds.DoseType = "PHYSICAL"
    if not getattr(new_ds, "DoseSummationType", None):
        new_ds.DoseSummationType = "PLAN"

    if new_sop_uid:
        print(f"[INFO] Assigning new SOPInstanceUID: {new_sop_uid}")
        new_ds.SOPInstanceUID = new_sop_uid
        new_ds.file_meta.MediaStorageSOPInstanceUID = new_sop_uid
    else:
        print("[INFO] Keeping original SOPInstanceUID from Eclipse RTDose.")
    return new_ds


def verify_written_file(path, expected_dose):
    """Read back and confirm no wrap-around (also under signed interpretation)."""
    ds = pydicom.dcmread(str(path))
    arr = ds.pixel_array
    dose = arr.astype(np.float64) * float(ds.DoseGridScaling)
    as_signed = arr.view(np.int32)
    max_err = np.abs(dose - expected_dose).max()
    print(f"[VERIFY] Read back: dtype={arr.dtype}, max pixel={arr.max()}, "
          f"max dose={dose.max():.6g} Gy, max abs error={max_err:.3e} Gy")
    if as_signed.min() < 0:
        print("[VERIFY][WARNING] Pixels would be negative if read as signed int32!")
    else:
        print("[VERIFY] OK: safe under signed and unsigned 32-bit interpretation.")


# --------------------------------------------------------------------------
# Plotting (3D)
# --------------------------------------------------------------------------
def _voxel_points(dose, ds, percentile, max_points):
    z_mm, y_mm, x_mm = grid_axes_mm(ds)
    if not np.any(dose > 0):
        return None
    thresh = np.percentile(dose[dose > 0], percentile)
    inds = np.nonzero(dose >= thresh)
    if inds[0].size == 0:
        return None
    xs, ys, zs = x_mm[inds[2]], y_mm[inds[1]], z_mm[inds[0]]
    vals = dose[inds]
    if xs.size > max_points:
        sel = np.random.default_rng(42).choice(xs.size, size=max_points, replace=False)
        print(f"[INFO] Subsampled plot points from {xs.size} to {max_points}.")
        xs, ys, zs, vals = xs[sel], ys[sel], zs[sel], vals[sel]
    return xs, ys, zs, vals


def plot_dose_3d(dose, ds, output_path, percentile=95.0, max_points=200000):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    pts = _voxel_points(dose, ds, percentile, max_points)
    if pts is None:
        print(f"[WARN] No voxels above P{percentile}; skipping 3D plot.")
        return
    xs, ys, zs, vals = pts
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    p = ax.scatter(xs, ys, zs, c=vals, cmap="inferno", s=1, alpha=0.7)
    ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)"); ax.set_zlabel("Z (mm)")
    fig.colorbar(p, ax=ax, label="Dose (Gy)")
    plt.title(f"3D dose scatter (>= P{percentile})")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[INFO] 3D dose plot saved to {output_path}")


def plot_dose_3d_interactive(dose, ds, output_html, percentile=95.0,
                             max_points=200000, auto_open=False):
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("[ERROR] plotly required: pip install plotly")
        return
    pts = _voxel_points(dose, ds, percentile, max_points)
    if pts is None:
        print(f"[WARN] No voxels above P{percentile}; skipping interactive plot.")
        return
    xs, ys, zs, vals = pts
    fig = go.Figure(
        data=[go.Scatter3d(x=xs, y=ys, z=zs, mode="markers",
                           marker=dict(size=2, color=vals, colorscale="Inferno",
                                       showscale=True, colorbar=dict(title="Dose (Gy)"),
                                       opacity=0.8))],
        layout=go.Layout(scene=dict(xaxis_title="X (mm)", yaxis_title="Y (mm)",
                                    zaxis_title="Z (mm)"),
                         title=f"Interactive 3D dose scatter (>= P{percentile})"))
    fig.write_html(output_html, auto_open=auto_open)
    print(f"[INFO] Interactive 3D plot saved to {output_html}")


# --------------------------------------------------------------------------
# Reference checks
# --------------------------------------------------------------------------
def check_frame_of_reference(rtdose, rtplan, rtstruct):
    print("[INFO] Checking Frame of Reference consistency...")
    f = [getattr(x, "FrameOfReferenceUID", None) for x in (rtdose, rtplan, rtstruct)]
    for name, uid in zip(("RTDose", "RTPlan", "RTStruct"), f):
        print(f"[INFO] FrameOfReferenceUID ({name}): {uid}")
    if f[0] == f[1] == f[2]:
        print("[INFO] FrameOfReferenceUID matches across all three files.")
    else:
        print("[WARNING] FrameOfReferenceUID mismatch detected!")


def check_rtdose_rtplan_reference(rtdose, rtplan):
    print("[INFO] Checking RTDose -> RTPlan reference...")
    seq = getattr(rtdose, "ReferencedRTPlanSequence", None)
    if seq:
        ref = seq[0].ReferencedSOPInstanceUID
        if ref == rtplan.SOPInstanceUID:
            print("[INFO] RTDose correctly references the supplied RTPlan.")
        else:
            print(f"[WARNING] RTDose references {ref}, RTPlan is {rtplan.SOPInstanceUID}.")
    else:
        print("[WARNING] RTDose has no ReferencedRTPlanSequence.")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Replace Eclipse RTDose pixel data with normalized TOPAS dose.")
    p.add_argument("--eclipse-dose", required=True, type=Path)
    p.add_argument("--topas-dose", required=True, type=Path)
    p.add_argument("--rtplan", required=True, type=Path)
    p.add_argument("--rtstruct", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--new-sop-uid", default=None)
    p.add_argument("--keep-geometry-from-topas", action="store_true",
                   help="Keep TOPAS grid & geometry (no resampling/shift). "
                        "Default: resample TOPAS onto the Eclipse grid.")
    p.add_argument("--norm-method", default="percentile", choices=["percentile", "point", "max"])
    p.add_argument("--norm-percentile", type=float, default=99.9)
    p.add_argument("--norm-headroom", type=float, default=1.05)
    p.add_argument("--mask-saturated", action="store_true",
                   help="Replace TOPAS voxels saturated at the integer limit by a local median.")
    p.add_argument("--plot-histogram", action="store_true")
    p.add_argument("--histogram-output", type=Path, default=None)
    p.add_argument("--histogram-only", action="store_true")
    p.add_argument("--plot-3d", action="store_true")
    p.add_argument("--plot-3d-output", type=Path, default=None)
    p.add_argument("--plot-3d-percentile", type=float, default=95.0)
    p.add_argument("--plot-3d-max-points", type=int, default=1000000)
    p.add_argument("--plot-3d-interactive", action="store_true")
    p.add_argument("--plot-3d-html-output", type=Path, default=None)
    p.add_argument("--plot-3d-open", action="store_true")
    args = p.parse_args()

    if args.output.exists() and not args.overwrite:
        print(f"[ERROR] Output {args.output} exists. Use --overwrite.")
        sys.exit(1)

    print("[INFO] Loading input files...")
    eclipse_ds = pydicom.dcmread(str(args.eclipse_dose))
    topas_ds = pydicom.dcmread(str(args.topas_dose))
    rtplan_ds = pydicom.dcmread(str(args.rtplan))
    rtstruct_ds = pydicom.dcmread(str(args.rtstruct))

    check_frame_of_reference(eclipse_ds, rtplan_ds, rtstruct_ds)
    check_rtdose_rtplan_reference(eclipse_ds, rtplan_ds)

    # --- Load doses in Gy (float) ---
    eclipse_dose, _ = load_dose_gy(eclipse_ds)
    topas_dose, topas_raw = load_dose_gy(topas_ds)
    topas_dose = check_saturation(topas_raw, args.mask_saturated, topas_dose)
    topas_dose = clean_dose(topas_dose)

    print(f"[INFO] Eclipse grid shape: {eclipse_dose.shape}")
    print(f"[INFO] TOPAS grid shape  : {topas_dose.shape}")

    print("\n[INFO] Eclipse dose centroid:")
    centroid_mm(eclipse_dose, eclipse_ds)
    print("[INFO] TOPAS dose centroid:")
    centroid_mm(topas_dose, topas_ds)

    # --- Histogram ---
    if args.plot_histogram or args.histogram_only:
        hist_out = args.histogram_output or args.output.with_name(
            args.output.stem + "_dose_histogram.png")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        plot_dose_histograms(topas_dose, eclipse_dose, output_path=hist_out)
        if args.histogram_only:
            print("[INFO] --histogram-only set, exiting.")
            sys.exit(0)

    # --- Put TOPAS dose on the output grid ---
    if args.keep_geometry_from_topas:
        out_dose = topas_dose
        geom_ds = topas_ds
        same_grid = topas_dose.shape == eclipse_dose.shape
    else:
        out_dose = clean_dose(resample_to_grid(topas_dose, topas_ds, eclipse_ds))
        geom_ds = eclipse_ds
        same_grid = True
        print("[INFO] Resampled TOPAS centroid on Eclipse grid:")
        centroid_mm(out_dose, eclipse_ds)

    # --- Normalize ---
    normalized_dose, _ = normalize_topas_dose(
        out_dose, eclipse_dose, method=args.norm_method,
        percentile=args.norm_percentile, same_grid=same_grid)

    # --- Build & save ---
    new_ds = build_new_rtdose(eclipse_ds, topas_ds, normalized_dose,
                              new_sop_uid=args.new_sop_uid,
                              keep_geometry_from_topas=args.keep_geometry_from_topas,
                              headroom=args.norm_headroom)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Saving new RTDose to {args.output} ...")
    new_ds.save_as(str(args.output), write_like_original=False)
    print("[DONE] New RTDose file written successfully.")
    verify_written_file(args.output, normalized_dose)

    # --- Plots (use the geometry the dose actually lives on) ---
    if args.plot_3d:
        out = args.plot_3d_output or args.output.with_name(args.output.stem + "_3d.png")
        plot_dose_3d(normalized_dose, geom_ds, str(out),
                     args.plot_3d_percentile, args.plot_3d_max_points)
    if args.plot_3d_interactive:
        out = args.plot_3d_html_output or args.output.with_name(args.output.stem + "_3d.html")
        plot_dose_3d_interactive(normalized_dose, geom_ds, str(out),
                                 args.plot_3d_percentile, args.plot_3d_max_points,
                                 auto_open=args.plot_3d_open)


if __name__ == "__main__":
    main()