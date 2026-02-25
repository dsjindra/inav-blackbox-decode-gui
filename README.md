# INAV Blackbox Decode GUI

This is a standalone GUI application for decoding INAV blackbox flight logs.

## Usage

1. Run `blackbox_decode_gui.exe`  (or `python blackbox_decode_gui.py` from source)
2. Click "Select .TXT Files" to choose your blackbox log files (.TXT)
3. Check any desired options
4. Click "Decode Logs" to process the files
5. The output will show in the text area, and CSV files will be created in the same
   directory as the input files

## Options

- **Add dateTime column**: Includes UTC date/time in the CSV
- **Merge GPS data into main CSV**: Combines GPS data with flight data instead of
  separate files
- **Simulate IMU**: Computes tilt, roll, and heading from sensor data
- **Ignore magnetometer**: Don't use magnetometer data for heading calculation
- **Generate gyro/accel noise report after decode**: Automatically analyses the
  decoded CSV and prints a noise comparison report (see below)

## Noise Analysis Report

After decoding, the GUI can compare **unfiltered** versus **filtered** gyroscope and
accelerometer data across the Roll, Pitch, and Yaw axes and print a summary report.

### Triggering the report

Two ways to run the analysis:

| Method | How |
|--------|-----|
| Auto (after decode) | Check **"Generate gyro/accel noise report after decode"** before clicking *Decode Logs* |
| Manual (existing CSV) | Click **"Analyze Noise Report"** and select one or more already-decoded `.csv` files |

### Columns analysed

| Signal | CSV columns |
|--------|-------------|
| Gyro unfiltered | `gyroUnfilt[0]` (Roll), `gyroUnfilt[1]` (Pitch), `gyroUnfilt[2]` (Yaw) |
| Gyro filtered | `gyroADC[0]` (Roll), `gyroADC[1]` (Pitch), `gyroADC[2]` (Yaw) |
| Accel unfiltered | `accADC[0]` (Roll), `accADC[1]` (Pitch), `accADC[2]` (Yaw) |
| Accel filtered | `accSmooth[0]` (Roll), `accSmooth[1]` (Pitch), `accSmooth[2]` (Yaw) |

### Metrics

For each axis and sensor the report shows:

- **Mean** – average signal value
- **Std** – population standard deviation (proxy for noise level)
- **RMS** – root-mean-square value
- **Noise reduction %** – `(1 − filtered_std / unfiltered_std) × 100 %`
  A positive value means the filter reduced noise; a negative value means the
  filtered signal is noisier than the raw signal (should not normally occur).

### Example output

```
====================================================================
  INAV BLACKBOX NOISE ANALYSIS REPORT
====================================================================
  File   : LOG00001.01.csv
  Rows   : 12,450

  GYROSCOPE  (units: deg/s raw ADC)
  ----------------------------------------------------------------
  Roll    :
    Unfiltered  – mean=     0.412  std=    38.271  RMS=    38.273
    Filtered    – mean=     0.388  std=     9.543  RMS=     9.551
    Noise reduction (std): +75.1%
  Pitch   :
    ...
  Yaw     :
    ...

  ACCELEROMETER  (units: raw ADC counts)
  ----------------------------------------------------------------
  ...

  SUMMARY  (Noise Reduction %)
  ----------------------------------------------------------------
  Axis      Gyro Unfilt std  Gyro Filt std   Gyro NR%  Accel Unfilt std  Accel Filt std   Accel NR%
  ----------------------------------------------------------------
  Roll               38.271          9.543      +75.1%           512.400         128.200       +75.0%
  Pitch              ...
  Yaw                ...
====================================================================
```

## Requirements

- Windows 7 or later
- No additional software required (fully standalone)

### Running from source

```
pip install -r requirements.txt   # only needed once
python blackbox_decode_gui.py
```

## Output

For each .TXT file you'll get:
- A `.01.csv` file with the decoded flight data
- Optionally a `.gpx` file with GPS track (if GPS data present)
- Statistics printed to the output area
- (Optional) A noise analysis report printed to the output area

## Original Tool

Based on the INAV blackbox_decode tool by Nicholas Sherlock.
