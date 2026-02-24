# INAV Blackbox Decode GUI

This is a standalone GUI application for decoding INAV blackbox flight logs.

## Usage

1. Run `blackbox_decode_gui.exe`
2. Click "Select .TXT Files" to choose your blackbox log files (.TXT)
3. Check any desired options
4. Click "Decode Logs" to process the files
5. The output will show in the text area, and CSV files will be created in the same directory as the input files

## Options

- **Add dateTime column**: Includes UTC date/time in the CSV
- **Merge GPS data into main CSV**: Combines GPS data with flight data instead of separate files
- **Simulate IMU**: Computes tilt, roll, and heading from sensor data
- **Ignore magnetometer**: Don't use magnetometer data for heading calculation

## Requirements

- Windows 7 or later
- No additional software required (fully standalone)

## Output

For each .TXT file, you'll get:
- A .01.csv file with the decoded flight data
- Optionally a .gpx file with GPS track (if GPS data present)
- Statistics printed to the output area

## Original Tool

Based on the INAV blackbox_decode tool by Nicholas Sherlock.