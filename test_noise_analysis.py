"""Tests for the noise analysis functions in blackbox_decode_gui."""

import csv
import math
import os
import tempfile
import unittest

from noise_analysis import _compute_stats, _noise_reduction, analyze_csv_noise


class TestComputeStats(unittest.TestCase):
    def test_empty(self):
        mean, std, rms = _compute_stats([])
        self.assertEqual(mean, 0.0)
        self.assertEqual(std, 0.0)
        self.assertEqual(rms, 0.0)

    def test_constant_signal(self):
        # constant signal has zero std dev
        mean, std, rms = _compute_stats([5.0, 5.0, 5.0, 5.0])
        self.assertAlmostEqual(mean, 5.0)
        self.assertAlmostEqual(std, 0.0)
        self.assertAlmostEqual(rms, 5.0)

    def test_known_values(self):
        # values [1, 2, 3, 4, 5]
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        mean, std, rms = _compute_stats(values)
        self.assertAlmostEqual(mean, 3.0)
        # population std dev = sqrt(2)
        self.assertAlmostEqual(std, math.sqrt(2.0), places=5)
        # rms = sqrt((1+4+9+16+25)/5) = sqrt(11)
        self.assertAlmostEqual(rms, math.sqrt(11.0), places=5)

    def test_negative_values(self):
        values = [-2.0, -1.0, 0.0, 1.0, 2.0]
        mean, std, rms = _compute_stats(values)
        self.assertAlmostEqual(mean, 0.0)
        self.assertAlmostEqual(rms, math.sqrt(2.0), places=5)


class TestNoiseReduction(unittest.TestCase):
    def test_zero_unfilt_std(self):
        # Division by zero guard
        self.assertEqual(_noise_reduction(0.0, 5.0), 0.0)

    def test_full_reduction(self):
        # Filtered std is 0 => 100% noise reduction
        self.assertAlmostEqual(_noise_reduction(10.0, 0.0), 100.0)

    def test_no_reduction(self):
        # Same std => 0% reduction
        self.assertAlmostEqual(_noise_reduction(10.0, 10.0), 0.0)

    def test_half_reduction(self):
        self.assertAlmostEqual(_noise_reduction(10.0, 5.0), 50.0)

    def test_negative_reduction(self):
        # Filtered is noisier than unfiltered => negative percentage
        result = _noise_reduction(5.0, 10.0)
        self.assertLess(result, 0.0)


class TestAnalyzeCsvNoise(unittest.TestCase):
    """Integration tests that write a temporary CSV and verify the report."""

    # Column names as they appear in INAV blackbox decode output
    GYRO_UNFILT_COLS = ["gyroUnfilt[0]", "gyroUnfilt[1]", "gyroUnfilt[2]"]
    GYRO_FILT_COLS   = ["gyroADC[0]",    "gyroADC[1]",    "gyroADC[2]"]
    ACCEL_UNFILT_COLS = ["accADC[0]",    "accADC[1]",     "accADC[2]"]
    ACCEL_FILT_COLS   = ["accSmooth[0]", "accSmooth[1]",  "accSmooth[2]"]

    def _write_csv(self, rows, extra_header_cols=None):
        """Write a temporary CSV and return its path."""
        all_cols = (
            self.GYRO_UNFILT_COLS + self.GYRO_FILT_COLS +
            self.ACCEL_UNFILT_COLS + self.ACCEL_FILT_COLS
        )
        if extra_header_cols:
            all_cols = extra_header_cols + all_cols

        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=all_cols)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _make_rows(self, n=100, unfilt_std=10.0, filt_std=3.0):
        """Generate synthetic rows with a sinusoidal unfiltered signal and
        a lower-amplitude (filtered) version."""
        rows = []
        for i in range(n):
            t = 2 * math.pi * i / n
            uf = unfilt_std * math.sin(t)
            fi = filt_std * math.sin(t)
            row = {}
            for col in self.GYRO_UNFILT_COLS + self.ACCEL_UNFILT_COLS:
                row[col] = str(uf)
            for col in self.GYRO_FILT_COLS + self.ACCEL_FILT_COLS:
                row[col] = str(fi)
            rows.append(row)
        return rows

    def test_report_contains_axes(self):
        rows = self._make_rows()
        csv_path = self._write_csv(rows)
        try:
            report = analyze_csv_noise(csv_path)
            for axis in ("Roll", "Pitch", "Yaw"):
                self.assertIn(axis, report)
        finally:
            os.unlink(csv_path)

    def test_report_contains_sections(self):
        rows = self._make_rows()
        csv_path = self._write_csv(rows)
        try:
            report = analyze_csv_noise(csv_path)
            self.assertIn("GYROSCOPE", report)
            self.assertIn("ACCELEROMETER", report)
            self.assertIn("SUMMARY", report)
            self.assertIn("Noise reduction", report)
        finally:
            os.unlink(csv_path)

    def test_filtered_has_lower_std(self):
        """The filtered signal has a lower amplitude so its std must be lower."""
        rows = self._make_rows(n=200, unfilt_std=20.0, filt_std=4.0)
        csv_path = self._write_csv(rows)
        try:
            report = analyze_csv_noise(csv_path)
            # Noise reduction should be positive (filtered < unfiltered)
            # The report shows lines like "+80.0%"
            self.assertIn("+", report)
        finally:
            os.unlink(csv_path)

    def test_missing_columns_graceful(self):
        """CSV without gyro/accel columns should not raise an exception."""
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["loopIteration", "time"])
            writer.writeheader()
            writer.writerow({"loopIteration": "1", "time": "1000"})
        try:
            report = analyze_csv_noise(path)
            self.assertIn("not found", report)
        finally:
            os.unlink(path)

    def test_strip_whitespace_headers(self):
        """Column headers with surrounding spaces must still be recognised."""
        all_cols = (
            self.GYRO_UNFILT_COLS + self.GYRO_FILT_COLS +
            self.ACCEL_UNFILT_COLS + self.ACCEL_FILT_COLS
        )
        # Add spaces to simulate real INAV decode output
        padded_cols = [" " + c + " " for c in all_cols]

        rows = self._make_rows(n=50)
        # Remap keys to padded versions
        padded_rows = [
            {" " + k + " ": v for k, v in row.items()}
            for row in rows
        ]

        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=padded_cols)
            writer.writeheader()
            writer.writerows(padded_rows)
        try:
            report = analyze_csv_noise(path)
            self.assertIn("GYROSCOPE", report)
        finally:
            os.unlink(path)

    def test_row_count_in_report(self):
        n = 77
        rows = self._make_rows(n=n)
        csv_path = self._write_csv(rows)
        try:
            report = analyze_csv_noise(csv_path)
            self.assertIn(str(n), report)
        finally:
            os.unlink(csv_path)


if __name__ == "__main__":
    unittest.main()
