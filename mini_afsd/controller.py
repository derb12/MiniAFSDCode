# -*- coding: utf-8 -*-
"""The controller of the user interfaces and all serial connections.

The function `get_save_location` was adapted from mcetl (https://github.com/derb12/mcetl),
which was licensed under the BSD-3-Clause license included below.

BSD 3-Clause License

Copyright (c) 2020-2022, Donald Erb
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

from collections import defaultdict
import csv
from datetime import datetime
import logging
from math import nan
import os
from pathlib import Path
import sys
import time
from threading import Event, Thread
import tkinter as tk
import traceback

import serial
from serial.tools import list_ports

from .gui import Gui
from .labjack_handler import LabjackHandler
from .serial_processor import SerialProcessor


def get_save_location():
    """
    Gets the filepath for saving the unsaved files depending on the operating system.

    Returns
    -------
    pathlib.Path
        The absolute path to where the files will be saved.

    Notes
    -----
    Tries to use environmental variables before using default locations, and
    tries to follow standard conventions. See the reference links (and the
    additional links in the links) for more information.

    Adapted from mcetl (see included license above).

    References
    ----------
    https://stackoverflow.com/questions/1024114/location-of-ini-config-files-in-linux-unix,
    https://specifications.freedesktop.org/basedir-spec/latest/
    """
    path = None
    if sys.platform.startswith('win'):  # Windows
        path = Path(os.environ.get('LOCALAPPDATA') or '~/AppData/Local').joinpath('mini_afsd')
    elif sys.platform.startswith('darwin'):  # Mac
        path = Path('~/Library/Application Support/mini_afsd')
    elif sys.platform.startswith(('linux', 'freebsd')):  # Linux
        path = Path(os.environ.get('XDG_DATA_HOME') or '~/.local/share').joinpath('mini_afsd')

    if path is not None:
        try:
            if not path.expanduser().parent.is_dir():
                path = None
        except PermissionError:
            # permission is denied in the desired folder; will not really help
            # accessing, but allows this function to not fail so that user can
            # manually set SAVE_FOLDER
            path = None

    if path is None:
        # unspecified os, the Windows/Mac/Linux places were wrong, or access denied
        path = Path('~/.mini_afsd')

    return path.expanduser()


class Controller:
    """
    The main object for interfacing between the user interface and the serial ports.

    Attributes
    ----------
    gui : tk.Tk
        The root for all created windows.
    aPulPerMil : int
        description
    xyPulPerMil : int
        description
    collecting : threading.Event
        The event for when performing data collection. Is set when data collection
        is ongoing.
    running : threading.Event
        The event for when the mill is running. Is set when the mill is running.
    cache_folder : pathlib.Path
        The path where data files are stored when data collection is ended. Default
        is the os-dependent output of `get_save_location`.
    """

    def __init__(self, xyStepsPerMil=40, xyPulPerStep=2, aStepsPerMil=1020,
                 aPulPerStep=4, port_regex='(CP21)', connect_serial=True, confirm_run=True,
                 skip_home=False, averaged_points=10, allow_testing=False):
        """
        Initializes the object.

        Parameters
        ----------
        xyStepsPerMil : int, optional
            _description_. Default is 40.
        xyPulPerStep : int, optional
            _description_. Default is 2.
        aStepsPerMil : int, optional
            _description_. Default is 1020.
        aPulPerStep : int, optional
            _description_. Default is 4.
        port_regex : str, optional
            The regular expression to use for searching for the port to use. Default
            is '(CP21)'.
        connect_serial : bool, optional
            If True (default), will attempt connecting to a serial port to control the movement
            of the mill in addition to connecting to a LabJack to measure temperature and
            potentially force. If False, will only attempt connection to the LabJack.
        confirm_run : bool, optional
            If True (default), will ask for confirmation for running a GCode file if
            data collection is not turned on; If False, will directly run the GCode.
        skip_home : bool, optional
            If True, the serial port will send b'$X' to skip homing and directly
            be ready to send commands. If False (default), b'$X' or b'$H' (home)
            will have to be sent manually through the serial port to begin using
            the mill.
        """
        self.xyPulPerMil = xyStepsPerMil * xyPulPerStep
        self.aPulPerMil = aStepsPerMil * aPulPerStep
        self.running = Event()
        self.collecting = Event()
        self.readTempData = Event()
        self.cache_folder = get_save_location()
        self.log_folder = self.cache_folder.joinpath('Logs')
        self.log_folder.mkdir(exist_ok=True, parents=True)
        self._testing_mode = allow_testing

        formatter = logging.Formatter('%(message)s')
        self.logger = logging.getLogger('mini-afsd')
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(
            self.log_folder.joinpath(datetime.now().strftime('%Y-%m-%d %H-%M-%S.log'))
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug(f"Log started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.gui = Gui(self, confirm_run=confirm_run)

        self.serial_processor = SerialProcessor(self, None, skip_home, allow_testing)
        self.labjack_handler = LabjackHandler(self, averaged_points, allow_testing)

        self.data = None

        if connect_serial:
            matching_ports = list(list_ports.grep(port_regex))
            if len(matching_ports) == 1:
                self.update_serial_port(matching_ports[0][0])
            else:  # multiple or no ports found
                self.serial_selection_dialog(allow_testing)

    def run(self):
        """A simple helper for starting the gui's main loop."""
        self.root.mainloop()

    @property
    def cache_folder(self):
        """The folder where data files are stored if not saved."""
        return self._cache_folder

    @cache_folder.setter
    def cache_folder(self, folder):
        """
        Sets the cache folder and creates it if needed.

        Parameters
        ----------
        folder : str or os.Pathlike
            The folder path for saving unsaved data files.
        """
        self._cache_folder = Path(folder)
        self._cache_folder.mkdir(exist_ok=True, parents=True)

    def update_serial_port(self, port=None):
        """
        Sets the current serial port and potentially connects.

        Parameters
        ----------
        port : str or None, optional
            The port to attempt connection with. Default is None, which will skip the
            connection for testing.
        """
        try:
            self.serial_processor.port = port
        except serial.SerialException:
            self.serial_selection_dialog()

    def serial_selection_dialog(self, allow_testing=False):
        """Launches a popup to select the serial port to use."""
        all_ports = list_ports.comports()
        handles = [' '.join(vals) for vals in all_ports]
        if allow_testing:
            handles.append('testing')

        if not handles:
            self.logger.debug('No serial ports found, entering test mode')
            self.update_serial_port(None)
            return

        port_window = tk.Toplevel(self.root, takefocus=True)
        port_window.protocol(
            "WM_DELETE_WINDOW", lambda: [self.update_serial_port(), port_window.destroy()]
        )
        port_window.title("Select Serial Port")
        port_label = tk.Label(
            port_window,
            font=("Times New Roman", 22),
            text="Select the serial port to use",
            fg="black",
            padx=5,
        )
        port_label.grid(column=0, row=0)
        selection_var = tk.StringVar(value=handles[0])
        port_options = tk.OptionMenu(port_window, selection_var, *handles)
        port_options.grid(column=0, row=1)
        button_frame = tk.Frame(port_window, width=750, height=80)
        button_frame.grid(column=0, row=2, pady=10, sticky='se')
        select_button = tk.Button(
            button_frame,
            text="Select",
            fg="black",
            bg="#8efa8e",
            font=("Times New Roman", 15),
            command=lambda: [
                self.update_serial_port(selection_var.get().split(' ')[0]),
                port_window.destroy(),
            ],
        )
        select_button.grid(column=0, row=0, padx=30)
        port_window.geometry(f"{port_options.winfo_reqwidth()}x160")
        port_window.grab_set()  # prevent interaction with main window until dialog closes
        port_window.wm_transient(self.root)  # set dialog above main window

    def on_closing(self):
        """Tries to save unsaved data before closing."""
        if not self.data:
            self.closeAll()
        else:
            askSaveWin = tk.Toplevel(self.root, takefocus=True)
            askSaveWin.protocol("WM_DELETE_WINDOW", self.closeAll)
            askSaveWin.title("Save Data?")
            askSaveLabel = tk.Label(
                askSaveWin,
                font=("Times New Roman", 22),
                text="Unsaved data. Are you sure?",
                fg="black",
                padx=5,
            )
            askSaveWin.geometry("%ix120" % askSaveLabel.winfo_reqwidth())
            askSaveLabel.grid(column=0, row=0, sticky=tk.E + tk.W)
            askSaveLabel.grid(column=0, row=0)
            askSaveButFrame = tk.Frame(askSaveWin, width=750, height=80)
            askSaveButFrame.grid(column=0, row=1, pady=10)
            tk.Button(
                askSaveButFrame,
                font=("Times New Roman", 22),
                text="SAVE",
                fg="black",
                bg="#8efa8e",
                command=lambda: [self.gui.saveFile(askSaveWin), self.closeAll()],
            ).grid(column=0, row=0, padx=30)
            tk.Button(
                askSaveButFrame,
                font=("Times New Roman", 22),
                text="CLEAR",
                fg="black",
                bg="#ff475d",
                command=self.closeAll,
            ).grid(column=1, row=0, padx=30)

    def closeAll(self):
        """Ensures proper shutdown of the user interface and serial connections."""
        self.root.destroy()
        self.labjack_handler.close()
        self.logger.debug(f"\nLog ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sys.exit()  # TODO serial port hanges when flushing, so exit without closing; check if that
        # is due to not actually being connected to the ESP
        self.serial_processor.close()

    def return_data(self):
        """Collects the current force and thermocouple data."""
        return self.data

    def clear_data(self):
        """Clears all force and thermocouple data from the serial port and LabJack."""
        self.serial_processor.clear_data()
        self.labjack_handler.clear_data()
        self.data = None

    def save_temp_file(self):
        """Caches force and thermocouple data when done collecting data to ensure data recovery."""
        combinedData = self.return_data()
        if combinedData is not None:
            try:
                output_file = self.cache_folder.joinpath(
                    datetime.now().strftime('%Y-%m-%d %H-%M-%S.csv')
                )
                self.write_output(output_file, combinedData)
            except PermissionError:
                pass  # silently ignore permission error when caching data
            except Exception:
                self.logger.warning('WARNING: Failed to save temporary data file.')
                self.logger.warning(traceback.format_exc())
            else:
                # try to remove all but the newest 10 files
                # default sort works since file names use ISO8601 date format
                for old_file in sorted(self.cache_folder.iterdir(), reverse=True)[10:]:
                    try:
                        old_file.unlink()
                    except Exception:
                        pass

    def write_output(self, output_file, data):
        """Defines how output data should be saved.

        Parameters
        ----------
        output_file : str or os.Pathlike
            The file location to save the output.
        data : dict[str, list]
            The data to be saved. Should be a dictionary containing the file headers as
            keys and relevant data as lists.

        """
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(data.keys())
            writer.writerows(zip(*data.values()))

    def start_collection_thread(self):
        """Spawns a thread for collecting machine data."""
        self.col_thread = Thread(target=self.collection_thread, daemon=True)
        self.col_thread.start()

    def collection_thread(self):
        """Collects machine position and Labjack data for saving later."""
        self.data = defaultdict(list)
        start_time = datetime.now()
        while self.collecting.is_set():
            now = datetime.now()
            self.data['Date'].append(now.strftime('%Y-%m-%d'))
            self.data['Time'].append(now.strftime('%H:%M:%S'))
            self.data['Relative_Time_s'].append((now - start_time).seconds)
            # have to cast position values as floats to get rid of "+" signs
            self.data['X_Pos_mm'].append(float(self.gui.xRelVar.get()))
            self.data['Y_Pos_mm'].append(float(self.gui.yRelVar.get()))
            self.data['Z_Pos_mm'].append(float(self.gui.zRelVar.get()))
            self.data['Actuator_Pos_mm'].append(float(self.gui.aRelVar.get()))
            if self.labjack_handler.labjackHandle is not None and self.labjack_handler.timeData:
                self.data['Actuator_Force_N'].append(self.labjack_handler.forceData[-1])
                self.data['Thermocouple_1_C'].append(self.labjack_handler.TC_one_Data[-1])
                self.data['Thermocouple_2_C'].append(self.labjack_handler.TC_two_Data[-1])
            else:
                self.data['Actuator_Force_N'].append(nan)
                self.data['Thermocouple_1_C'].append(nan)
                self.data['Thermocouple_2_C'].append(nan)

            time.sleep(1)   # collect every 1 second
