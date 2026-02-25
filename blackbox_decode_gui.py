"""GUI for INAV Blackbox Decode.

This tool provides a graphical interface to decode INAV blackbox .TXT logs to CSV
using the blackbox_decode executable.
"""

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import subprocess
import threading
import sys
import os
from pathlib import Path

from noise_analysis import analyze_csv_noise


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class BlackboxDecodeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("INAV Blackbox Decode GUI")
        self.root.geometry("900x680")
        self.selected_files = []
        self.datetime_var = tk.BooleanVar()
        self.merge_gps_var = tk.BooleanVar()
        self.simulate_imu_var = tk.BooleanVar()
        self.imu_ignore_mag_var = tk.BooleanVar()
        self.noise_report_var = tk.BooleanVar()
        self.create_widgets()

    def create_widgets(self):
        # --- File selection frame ---
        file_frame = tk.Frame(self.root)
        file_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        self.file_listbox = tk.Listbox(file_frame, height=5)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(file_frame)
        button_frame.pack(side=tk.RIGHT, padx=(5, 0))

        select_button = tk.Button(button_frame, text="Select .TXT Files",
                                  command=self.select_files)
        select_button.pack(fill=tk.X, pady=(0, 4))

        clear_button = tk.Button(button_frame, text="Clear",
                                 command=self.clear_files)
        clear_button.pack(fill=tk.X)

        # --- Options frame ---
        options_frame = tk.LabelFrame(self.root, text="Options")
        options_frame.pack(fill=tk.X, padx=10, pady=6)

        tk.Checkbutton(options_frame, text="Add dateTime column",
                       variable=self.datetime_var, anchor=tk.W).pack(fill=tk.X)
        tk.Checkbutton(options_frame, text="Merge GPS data into main CSV",
                       variable=self.merge_gps_var, anchor=tk.W).pack(fill=tk.X)
        tk.Checkbutton(options_frame, text="Simulate IMU (compute tilt/roll/heading)",
                       variable=self.simulate_imu_var, anchor=tk.W).pack(fill=tk.X)
        tk.Checkbutton(options_frame, text="Ignore magnetometer for heading",
                       variable=self.imu_ignore_mag_var, anchor=tk.W).pack(fill=tk.X)
        tk.Checkbutton(options_frame,
                       text="Generate gyro/accel noise report after decode",
                       variable=self.noise_report_var, anchor=tk.W).pack(fill=tk.X)

        # --- Action buttons ---
        action_frame = tk.Frame(self.root)
        action_frame.pack(fill=tk.X, padx=10, pady=4)

        run_button = tk.Button(action_frame, text="Decode Logs",
                               command=self.run_decode)
        run_button.pack(side=tk.LEFT, padx=(0, 8))

        noise_button = tk.Button(action_frame, text="Analyze Noise Report",
                                 command=self.open_and_analyze_noise)
        noise_button.pack(side=tk.LEFT)

        # --- Output frame ---
        output_frame = tk.LabelFrame(self.root, text="Output")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select INAV Blackbox .TXT files",
            filetypes=[("INAV Blackbox logs", "*.TXT *.txt"), ("All files", "*.*")]
        )
        self.selected_files = list(files)
        self.update_file_list()

    def clear_files(self):
        self.selected_files = []
        self.update_file_list()

    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for file in self.selected_files:
            self.file_listbox.insert(tk.END, Path(file).name)

    # ------------------------------------------------------------------
    # Decode
    # ------------------------------------------------------------------

    def run_decode(self):
        if not self.selected_files:
            messagebox.showerror("Error", "Please select at least one .TXT file")
            return

        exe_path = self.get_exe_path()
        if not exe_path:
            messagebox.showerror("Error", "Could not find blackbox_decode.exe")
            return

        cmd = [exe_path]
        if self.datetime_var.get():
            cmd.append("--datetime")
        if self.merge_gps_var.get():
            cmd.append("--merge-gps")
        if self.simulate_imu_var.get():
            cmd.append("--simulate-imu")
        if self.imu_ignore_mag_var.get():
            cmd.append("--imu-ignore-mag")
        cmd.extend(self.selected_files)

        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Running: " + " ".join(cmd) + "\n\n")

        generate_noise = self.noise_report_var.get()
        thread = threading.Thread(
            target=self.run_command,
            args=(cmd, generate_noise),
            daemon=True
        )
        thread.start()

    def get_exe_path(self):
        possible_paths = []
        if hasattr(sys, "_MEIPASS"):
            possible_paths.append(os.path.join(sys._MEIPASS, "blackbox_decode.exe"))
        possible_paths.append(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "blackbox_decode.exe")
        )
        possible_paths.append(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "obj", "blackbox_decode.exe")
        )
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def run_command(self, cmd, generate_noise=False):
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(cmd[0])
            )
            output = result.stdout.decode(errors="replace")
            if result.stderr:
                output += "\nSTDERR:\n" + result.stderr.decode(errors="replace")
            self.output_text.insert(tk.END, output)
            if result.returncode == 0:
                self.output_text.insert(tk.END, "\nDecoding completed successfully!\n")
                if generate_noise:
                    self._run_noise_analysis_on_decoded_files()
            else:
                self.output_text.insert(
                    tk.END,
                    "\nDecoding failed with return code " + str(result.returncode) + "\n"
                )
        except Exception as e:
            self.output_text.insert(tk.END, "\nError running command: " + str(e) + "\n")

    # ------------------------------------------------------------------
    # Noise analysis
    # ------------------------------------------------------------------

    def _run_noise_analysis_on_decoded_files(self):
        """Auto-run noise analysis on each .TXT file's primary CSV output."""
        self.output_text.insert(tk.END, "\n")
        found_any = False
        for txt_path in self.selected_files:
            # blackbox_decode produces <base>.01.csv for the first log in a file
            csv_path = str(Path(txt_path).with_suffix("")) + ".01.csv"
            if os.path.exists(csv_path):
                found_any = True
                try:
                    report = analyze_csv_noise(csv_path)
                    self.output_text.insert(tk.END, report + "\n\n")
                except Exception as ex:
                    self.output_text.insert(
                        tk.END,
                        f"Could not analyze {Path(csv_path).name}: {ex}\n"
                    )
        if not found_any:
            self.output_text.insert(
                tk.END,
                "No decoded CSV files found for noise analysis.\n"
            )

    def open_and_analyze_noise(self):
        """Open a file dialog to select decoded CSV files and show the report."""
        csv_files = filedialog.askopenfilenames(
            title="Select Decoded CSV Files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not csv_files:
            return

        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Analyzing noise...\n\n")
        self.root.update_idletasks()

        for csv_path in csv_files:
            try:
                report = analyze_csv_noise(csv_path)
                self.output_text.insert(tk.END, report + "\n\n")
            except Exception as ex:
                self.output_text.insert(
                    tk.END,
                    f"Could not analyze {Path(csv_path).name}: {ex}\n"
                )


if __name__ == "__main__":
    root = tk.Tk()
    app = BlackboxDecodeGUI(root)
    root.mainloop()
