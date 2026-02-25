"""Noise analysis helpers for INAV blackbox decoded CSV data.

This module is intentionally free of GUI dependencies so it can be
imported and tested independently of tkinter.
"""

import csv
import math
from pathlib import Path


def _compute_stats(values):
    """Return (mean, std_dev, rms) for a sequence of floats.

    Uses population (not sample) standard deviation.
    Returns (0.0, 0.0, 0.0) for an empty sequence.
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std_dev = math.sqrt(variance)
    rms = math.sqrt(sum(v ** 2 for v in values) / n)
    return mean, std_dev, rms


def _noise_reduction(unfilt_std, filt_std):
    """Return percentage noise reduction (positive = improvement).

    Returns 0.0 when *unfilt_std* is zero to avoid division by zero.
    """
    if unfilt_std == 0:
        return 0.0
    return (1.0 - filt_std / unfilt_std) * 100.0


def analyze_csv_noise(csv_path):
    """Parse a decoded INAV blackbox CSV and return a formatted noise report.

    The following column families are recognised (indices 0/1/2 map to
    Roll / Pitch / Yaw):

    ============================  ================================
    Gyro unfiltered               ``gyroUnfilt[0/1/2]``
    Gyro filtered                 ``gyroADC[0/1/2]``
    Accelerometer unfiltered      ``accADC[0/1/2]``
    Accelerometer filtered        ``accSmooth[0/1/2]``
    ============================  ================================

    Column headers with surrounding whitespace are accepted (INAV decode
    output sometimes pads names with spaces).

    Returns a plain-text report string.
    """
    axis_labels = ["Roll", "Pitch", "Yaw"]

    gyro_unfilt_cols  = ["gyroUnfilt[0]", "gyroUnfilt[1]", "gyroUnfilt[2]"]
    gyro_filt_cols    = ["gyroADC[0]",    "gyroADC[1]",    "gyroADC[2]"]
    accel_unfilt_cols = ["accADC[0]",     "accADC[1]",     "accADC[2]"]
    accel_filt_cols   = ["accSmooth[0]",  "accSmooth[1]",  "accSmooth[2]"]

    all_cols_needed = (
        gyro_unfilt_cols + gyro_filt_cols +
        accel_unfilt_cols + accel_filt_cols
    )

    # Read the CSV.  INAV decode output may have leading/trailing spaces in
    # column headers, so we normalise them when building the lookup.
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)

        data = {col: [] for col in all_cols_needed}

        for row in reader:
            # Strip whitespace from every key in this row
            norm_row = {k.strip(): v for k, v in row.items() if k is not None}
            for col in all_cols_needed:
                raw = norm_row.get(col, "").strip()
                try:
                    data[col].append(float(raw))
                except ValueError:
                    pass  # skip non-numeric / missing cells

    # Use filtered gyro[0] as proxy for total row count
    row_count = len(data[gyro_filt_cols[0]])

    # ------------------------------------------------------------------
    # Build the report
    # ------------------------------------------------------------------
    lines = []
    lines.append("=" * 68)
    lines.append("  INAV BLACKBOX NOISE ANALYSIS REPORT")
    lines.append("=" * 68)
    lines.append(f"  File   : {Path(csv_path).name}")
    lines.append(f"  Rows   : {row_count:,}")
    lines.append("")

    def axis_section(title, unfilt_col, filt_col):
        uf = data[unfilt_col]
        fi = data[filt_col]
        if not uf or not fi:
            return [f"  {title:<8}: No data available"]
        uf_mean, uf_std, uf_rms = _compute_stats(uf)
        fi_mean, fi_std, fi_rms = _compute_stats(fi)
        nr = _noise_reduction(uf_std, fi_std)
        return [
            f"  {title:<8}:",
            f"    Unfiltered  – mean={uf_mean:>10.3f}  std={uf_std:>10.3f}  RMS={uf_rms:>10.3f}",
            f"    Filtered    – mean={fi_mean:>10.3f}  std={fi_std:>10.3f}  RMS={fi_rms:>10.3f}",
            f"    Noise reduction (std): {nr:>+.1f}%",
        ]

    # Gyro section
    gyro_available = any(data[c] for c in gyro_unfilt_cols + gyro_filt_cols)
    lines.append("  GYROSCOPE  (units: deg/s raw ADC)")
    lines.append("  " + "-" * 64)
    if gyro_available:
        for i, axis in enumerate(axis_labels):
            lines.extend(axis_section(axis, gyro_unfilt_cols[i], gyro_filt_cols[i]))
    else:
        lines.append("  Gyro columns not found in this log.")
    lines.append("")

    # Accelerometer section
    accel_available = any(data[c] for c in accel_unfilt_cols + accel_filt_cols)
    lines.append("  ACCELEROMETER  (units: raw ADC counts)")
    lines.append("  " + "-" * 64)
    if accel_available:
        for i, axis in enumerate(axis_labels):
            lines.extend(axis_section(axis, accel_unfilt_cols[i], accel_filt_cols[i]))
    else:
        lines.append("  Accelerometer columns not found in this log.")
    lines.append("")

    # Summary table
    lines.append("  SUMMARY  (Noise Reduction %)")
    lines.append("  " + "-" * 64)
    lines.append(
        f"  {'Axis':<8}  {'Gyro Unfilt std':>15}  {'Gyro Filt std':>13}"
        f"  {'Gyro NR%':>9}  {'Accel Unfilt std':>16}  {'Accel Filt std':>14}"
        f"  {'Accel NR%':>10}"
    )
    lines.append("  " + "-" * 64)
    for i, axis in enumerate(axis_labels):
        uf_g = data[gyro_unfilt_cols[i]]
        fi_g = data[gyro_filt_cols[i]]
        uf_a = data[accel_unfilt_cols[i]]
        fi_a = data[accel_filt_cols[i]]

        _, uf_g_std, _ = _compute_stats(uf_g) if uf_g else (0.0, 0.0, 0.0)
        _, fi_g_std, _ = _compute_stats(fi_g) if fi_g else (0.0, 0.0, 0.0)
        _, uf_a_std, _ = _compute_stats(uf_a) if uf_a else (0.0, 0.0, 0.0)
        _, fi_a_std, _ = _compute_stats(fi_a) if fi_a else (0.0, 0.0, 0.0)

        g_nr = _noise_reduction(uf_g_std, fi_g_std)
        a_nr = _noise_reduction(uf_a_std, fi_a_std)

        lines.append(
            f"  {axis:<8}  {uf_g_std:>15.3f}  {fi_g_std:>13.3f}  {g_nr:>+9.1f}%"
            f"  {uf_a_std:>16.3f}  {fi_a_std:>14.3f}  {a_nr:>+10.1f}%"
        )

    lines.append("=" * 68)
    return "\n".join(lines)
