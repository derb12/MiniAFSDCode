# -*- coding: utf-8 -*-
"""The User Interface class for interacting with the mill."""

from collections import deque
import csv
from math import nan
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class Gui:
    """
    The User Interface for controlling the mill.

    Attributes
    ----------
    controller : Controller
        The Controller object that allows communication between the GUI and the
        serial port and LabJack.
    times : tuple
        The time data to use for plotting the temperature versus time graphs. Has
        a fixed length of `display_data`.
    displayData : collections.deque
        The temperature data to use for display. Has a fixed length of `display_data`.
    aAbsVar : tkinter.StringVar
        The label for the absolute position in the actuator direction.
    aRelVar : tkinter.StringVar
        The label for the relative position in the actuator direction.
    xAbsVar : tkinter.StringVar
        The label for the absolute position in the x-direction.
    xRelVar : tkinter.StringVar
        The label for the relative position in the x-direction.
    yAbsVar : tkinter.StringVar
        The label for the absolute position in the y-direction.
    yRelVar : tkinter.StringVar
        The label for the relative position in the y-direction.
    zAbsVar : tkinter.StringVar
        The label for the absolute position in the z-direction.
    zRelVar : tkinter.StringVar
        The label for the relative position in the z-direction.
    topFrame : tkinter.Frame
        The frame for the actuator, traversal, and save frames.
    botFrame : tkinter.Frame
        The frame for the start mill button.
    enXYBut : tkinter.Button
        The button for enabling XY movement.
    """

    def __init__(self, controller, display_size=140, confirm_run=True):
        """
        Initializes the user interface.

        Parameters
        ----------
        controller : Controller
            The controller object for the GUI.
        display_size : int, optional
            The number of data points to display when plotting. Default is 140.
        confirm_run : bool, optional
            If True (default), will ask for confirmation for running a GCode file if
            data collection is not turned on; If False, will directly run the GCode.
        """
        self.controller = controller
        self.times = tuple(t * 3 for t in range(display_size))
        self.displayData = deque([0] * display_size, maxlen=display_size)
        self.displayDataTC1 = deque([0] * display_size, maxlen=display_size)
        self.displayDataTC2 = deque([0] * display_size, maxlen=display_size)
        self.gcode_directory = '/'
        self.confirm_run = confirm_run

        self.createMainFrames()
        self.createTraverseFrame()
        self.createActuatorFrame()
        self.createSaveFrame()
        self.createBottomButtons()

        self.topFrame.columnconfigure(0, weight=1)
        self.topFrame.columnconfigure(1, weight=1)
        self.topFrame.columnconfigure(2, weight=1)
        self.topFrame.rowconfigure(0, weight=1)

    def createMainFrames(self):
        """Creates the main frames for the GUI."""
        self.topFrame = tk.Frame(width=1250, height=600, bg="#e3f0fa")
        self.topFrame.grid(column=0, row=0, sticky=tk.NSEW)
        self.topFrame.grid_propagate(0)

        self.botFrame = tk.Frame(
            width=1250, height=130, bg="#e3f0fa", bd=5, relief="groove", padx=10, pady=10,
        )
        self.botFrame.grid(column=0, row=1, sticky=tk.NSEW)
        self.botFrame.grid_propagate(0)

        self.controller.root.columnconfigure(0, weight=1)
        self.controller.root.rowconfigure(0, weight=4)
        self.controller.root.rowconfigure(1, weight=1)

    def createTraverseFrame(self):
        """Creates the traversal section of the GUI."""
        tFrame = tk.LabelFrame(
            width=500,
            height=600,
            bg="#e3f0fa",
            labelwidget=tk.Label(font=("Times New Roman", 22), text="TRAVERSE", fg="black"),
            bd=5,
            relief="groove",
            padx=10,
            pady=10,
        )
        tFrame.grid(column=0, row=0, in_=self.topFrame, sticky=tk.NSEW)
        tFrame.grid_propagate(0)

        # Create Main Frames
        posFrame = tk.Frame(bg="#e3f0fa", padx=2, pady=2)
        posFrame.grid(column=0, row=0, in_=tFrame, sticky=tk.NSEW)

        commandFrame = tk.Frame(bg="#e3f0fa", padx=2, pady=2)
        commandFrame.grid(column=0, row=1, in_=tFrame, sticky=tk.NSEW)

        overrideFrame = tk.Frame(bg="#e3f0fa", padx=2, pady=2)
        overrideFrame.grid(column=0, row=0, in_=commandFrame, sticky=tk.EW)

        millButtonsFrame = tk.Frame(bg="#e3f0fa", padx=5, pady=5)
        millButtonsFrame.grid(column=1, row=0, in_=commandFrame, sticky=tk.E)

        # Create Position Frame Widgets
        workLabel = tk.Label(
            text="Work", font=("Times New Roman", 12), fg="black", bg="#e3f0fa", width=12,
        )
        workLabel.grid(column=1, row=0, in_=posFrame)

        machineLabel = tk.Label(
            text="Machine", font=("Times New Roman", 12), fg="black", bg="#e3f0fa", width=8,
        )
        machineLabel.grid(column=2, row=0, in_=posFrame)

        tk.Label(
            text="X", font=("Times New Roman", 18), fg="black", bg="#e3f0fa", width=3, pady=10,
        ).grid(column=0, row=1, in_=posFrame)

        tk.Label(
            text="Y", font=("Times New Roman", 18), fg="black", bg="#e3f0fa", width=3, pady=10,
        ).grid(column=0, row=2, in_=posFrame)

        tk.Label(
            text="Z", font=("Times New Roman", 18), fg="black", bg="#e3f0fa", width=3, pady=10,
        ).grid(column=0, row=3, in_=posFrame)

        tk.Label(
            text="A", font=("Times New Roman", 18), fg="black", bg="#e3f0fa", width=3, pady=10,
        ).grid(column=0, row=4, in_=posFrame)

        tk.Label(
            text="State", font=("Times New Roman", 18), fg="black", bg="#e3f0fa", width=5, pady=10,
        ).grid(column=0, row=5, in_=posFrame)

        tk.Label(
            text="Buffer", font=("Times New Roman", 18), fg="black", bg="#e3f0fa", width=5, pady=10,
        ).grid(column=0, row=6, in_=posFrame)

        self.xRelVar = tk.StringVar(value='+0.000')
        xRelLabel = tk.Label(
            textvariable=self.xRelVar,
            width=8,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=6,
        )
        xRelLabel.grid(column=1, row=1, in_=posFrame)

        self.xAbsVar = tk.StringVar(value='+0.000')
        xAbsLabel = tk.Label(
            textvariable=self.xAbsVar,
            width=6,
            font=("Times New Roman", 14),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=2,
        )
        xAbsLabel.grid(column=2, row=1, in_=posFrame)

        self.yRelVar = tk.StringVar(value='+0.000')
        yRelLabel = tk.Label(
            textvariable=self.yRelVar,
            width=8,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=6,
        )
        yRelLabel.grid(column=1, row=2, in_=posFrame)

        self.yAbsVar = tk.StringVar(value='+0.000')
        yAbsLabel = tk.Label(
            textvariable=self.yAbsVar,
            width=6,
            font=("Times New Roman", 14),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=2,
        )
        yAbsLabel.grid(column=2, row=2, in_=posFrame)

        self.zRelVar = tk.StringVar(value='+0.000')
        zRelLabel = tk.Label(
            textvariable=self.zRelVar,
            width=8,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=6,
        )
        zRelLabel.grid(column=1, row=3, in_=posFrame)

        self.zAbsVar = tk.StringVar(value='+0.000')
        zAbsLabel = tk.Label(
            textvariable=self.zAbsVar,
            width=6,
            font=("Times New Roman", 14),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=2,
        )
        zAbsLabel.grid(column=2, row=3, in_=posFrame)

        self.aRelVar = tk.StringVar(value='+0.000')
        aRelLabel = tk.Label(
            textvariable=self.aRelVar,
            width=8,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=6,
        )
        aRelLabel.grid(column=1, row=4, in_=posFrame)

        self.aAbsVar = tk.StringVar(value='+0.000')
        aAbsLabel = tk.Label(
            textvariable=self.aAbsVar,
            width=6,
            font=("Times New Roman", 14),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=2,
        )
        aAbsLabel.grid(column=2, row=4, in_=posFrame)

        self.stateVar = tk.StringVar(value='Idle')
        stateLabel = tk.Label(
            textvariable=self.stateVar,
            width=8,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=4,
        )
        stateLabel.grid(column=1, row=5, in_=posFrame)

        self.bufferVar = tk.IntVar(value='15')
        bufferLabel = tk.Label(
            textvariable=self.bufferVar,
            width=8,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=4,
        )
        bufferLabel.grid(column=1, row=6, in_=posFrame)

        # Create Zero Button Frame Widgets
        zeroXBut = tk.Button(
            text="Zero X",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.zeroCord(b'X'),
        )
        zeroXBut.grid(column=3, row=1, in_=posFrame, pady=5, padx=5)

        zeroYBut = tk.Button(
            text="Zero Y",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.zeroCord(b"Y"),
        )
        zeroYBut.grid(column=3, row=2, in_=posFrame, pady=5)

        zeroZBut = tk.Button(
            text="Zero Z",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.zeroCord(b"Z"),
        )
        zeroZBut.grid(column=3, row=3, in_=posFrame, pady=5)

        zeroABut = tk.Button(
            text="Zero A",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.zeroCord(b"A"),
        )
        zeroABut.grid(column=3, row=4, in_=posFrame, pady=5)

        homeXBut = tk.Button(
            text="Home X",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'$HX', False)
        )
        homeXBut.grid(column=4, row=1, in_=posFrame, pady=5, padx=5)

        homeYBut = tk.Button(
            text="Home Y",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b"$HY", False)
        )
        homeYBut.grid(column=4, row=2, in_=posFrame, pady=5)

        homeZBut = tk.Button(
            text="Home Z",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b"$HZ", False)
        )
        homeZBut.grid(column=4, row=3, in_=posFrame, pady=5)

        homeABut = tk.Button(
            text="Home A",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b"$HA", False)
        )
        homeABut.grid(column=4, row=4, in_=posFrame, pady=5)

        homeAllBut = tk.Button(
            text="Home\nAll",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#91ceff",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b"$H", False)
        )
        homeAllBut.grid(column=4, row=5, in_=posFrame, pady=5, rowspan=2, sticky=tk.NS)

        resetOffsetBut = tk.Button(
            text="Reset &\nOffset",
            font=("Times New Roman", 12),
            width=7,
            pady=5,
            bg="#91ceff",
            fg="black",
            relief="raised",
            command=self.reset_and_offset,
        )
        resetOffsetBut.grid(column=3, row=5, in_=posFrame, pady=5, rowspan=2, sticky=tk.NS)

        self.cancelJogBut = tk.Button(
            text="Cancel Jog",
            font=("Times New Roman bold", 12),
            bg="#8efa8e",
            fg="black",
            command=lambda: self.sendCode(b'\x85', False),
        )
        self.cancelJogBut.grid(column=0, row=0, in_=millButtonsFrame, sticky=tk.EW)

        self.resetBut = tk.Button(
            text="Reset &\nUnlock",
            font=("Times New Roman bold", 12),
            bg="#8efa8e",
            fg="grey",
            command=lambda: [
                self.sendCode(b'\x18', False),
                self.sendCode(b'$X', False),
                self.sendCode(b'$MD', False)
            ],
            state='disabled'
        )
        self.resetBut.grid(column=0, row=1, pady=4, in_=millButtonsFrame, sticky=tk.EW)

        self.enXYBut = tk.Button(  # TODO should probably rename; enable xya is old
            text="Disable Drives",
            font=("Times New Roman", 12),
            width=11,
            pady=5,
            bg="#8efa8e",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b"$MD", False),
        )
        self.enXYBut.grid(column=0, row=2, in_=millButtonsFrame, sticky=tk.EW)

        tk.Label(
            text='Feed', font=('Times New Roman', 18), fg="black", bg="#e3f0fa", width=5, pady=10,
        ).grid(column=0, row=0, padx=3, in_=overrideFrame)

        tk.Label(
            text='Spindle', font=('Times New Roman', 18), fg="black", bg="#e3f0fa", width=5, pady=10,
        ).grid(column=0, row=1, padx=3, in_=overrideFrame)

        self.feed_var = tk.StringVar(value='100%')
        feed_label = tk.Label(
            textvariable=self.feed_var,
            width=5,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=6,
        )
        feed_label.grid(column=1, row=0, in_=overrideFrame)

        feed_minus10_But = tk.Button(
            text='-10',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x92', False),
        )
        feed_minus10_But.grid(column=2, row=0, in_=overrideFrame, padx=3)

        feed_minus1_But = tk.Button(
            text='-1 ',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x94', False),
        )
        feed_minus1_But.grid(column=3, row=0, in_=overrideFrame, padx=3)

        feed_plus1_But = tk.Button(
            text='+1 ',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x93', False),
        )
        feed_plus1_But.grid(column=4, row=0, in_=overrideFrame, padx=3)

        feed_plus10_But = tk.Button(
            text='+10',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x91', False),
        )
        feed_plus10_But.grid(column=5, row=0, in_=overrideFrame, padx=3)

        self.spindle_var = tk.StringVar(value='100%')
        spindle_label = tk.Label(
            textvariable=self.spindle_var,
            width=5,
            font=("Times New Roman", 18),
            fg="black",
            bg="#EEE",
            relief="groove",
            bd=1,
            pady=6,
        )
        spindle_label.grid(column=1, row=1, in_=overrideFrame)

        spindle_minus10_But = tk.Button(
            text='-10',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x9B', False),
        )
        spindle_minus10_But.grid(column=2, row=1, in_=overrideFrame, pady=5)

        spindle_minus1_But = tk.Button(
            text='-1 ',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x9D', False),
        )
        spindle_minus1_But.grid(column=3, row=1, in_=overrideFrame, pady=5)

        spindle_plus1_But = tk.Button(
            text='+1 ',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x9C', False),
        )
        spindle_plus1_But.grid(column=4, row=1, in_=overrideFrame, pady=5)

        spindle_plus10_But = tk.Button(
            text='+10',
            font=("Times New Roman", 12),
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.sendCode(b'\x9A', False),
        )
        spindle_plus10_But.grid(column=5, row=1, in_=overrideFrame, pady=5)

        tFrame.columnconfigure(0, weight=1)
        tFrame.rowconfigure(0, weight=1)
        tFrame.rowconfigure(1, weight=1)

        commandFrame.columnconfigure(0, weight=1)
        commandFrame.columnconfigure(1, weight=1)
        commandFrame.rowconfigure(0, weight=1)

    def createActuatorFrame(self):
        """Creates the actuator control section of the GUI."""
        aFrame = tk.LabelFrame(
            width=420,
            height=600,
            bg="#e3f0fa",
            labelwidget=tk.Label(font=("Times New Roman", 22), text="SPINDLE", fg="black"),
            bd=5,
            relief="groove",
            padx=10,
            pady=10,
        )
        aFrame.grid(column=1, row=0, in_=self.topFrame, sticky=tk.NSEW)
        aFrame.grid_propagate(0)

        displayFrame = tk.Frame(bg="#e3f0fa")
        displayFrame.grid(column=0, row=0, in_=aFrame, sticky=tk.NSEW)

        gCodeFrame = tk.Frame(bg="#e3f0fa")
        gCodeFrame.grid(column=0, row=1, in_=aFrame, pady=5, sticky=tk.NSEW)
        gCodeFrame.grid_propagate(0)

        self.figure = Figure(figsize=(3, 2), tight_layout=True)
        self.axis = self.figure.add_subplot()
        self.temperature_axis = None
        self.temperature_axis = self.axis.twinx()
        self.temperature_axis.set_ylabel('Temperature (°C)')

        self.line = self.axis.plot(self.times, self.displayData)[0]
        self.axis.set_xlabel("Time")
        self.axis.set_ylabel("Force (N)")
        self.axis.set_xticklabels([])
        self.axis.set_xticks([])

        self.canvas = FigureCanvasTkAgg(self.figure)
        self.canvas.get_tk_widget().grid(
            column=0, row=0, in_=displayFrame, sticky=tk.NSEW
        )
        self.canvas.draw_idle()

        gCodeLabel = tk.Label(
            text="Enter GCode:",
            font=("Times New Roman", 14),
            width=35,
            pady=2,
            padx=4,
            bg="#EFF",
            fg="black",
            justify=tk.LEFT,
        )
        gCodeLabel.grid(column=0, row=0, in_=gCodeFrame, sticky=tk.EW)

        self.gCodeText = tk.StringVar()
        gCodeEntry = tk.Entry(
            width=30, font=("Times New Roman", 18), bg="white", fg="black",
            textvariable=self.gCodeText,
        )
        gCodeEntry.grid(column=0, row=1, in_=gCodeFrame, sticky=tk.EW)
        gCodeEntry.bind("<KeyRelease-Return>", self.sendGCode)

        gCodeFileFrame = tk.Frame(bg="#e3f0fa",)
        gCodeFileFrame.grid(column=0, row=2, pady=10, in_=gCodeFrame, sticky=tk.NSEW)

        gCodeFileLabel = tk.Label(
            text="Enter GCode Filepath:",
            font=("Times New Roman", 14),
            width=22,
            pady=2,
            padx=4,
            bg="#EFF",
            fg="black",
            justify=tk.LEFT,
        )
        gCodeFileLabel.grid(column=0, row=0, in_=gCodeFileFrame, sticky=tk.W)

        self.gCodeFileText = tk.StringVar()
        gCodeFileEntry = tk.Entry(
            width=24,
            font=("Times New Roman", 14),
            bg="white",
            fg="black",
            textvariable=self.gCodeFileText,
            state='readonly'
        )
        gCodeFileEntry.grid(column=0, row=1, in_=gCodeFileFrame)

        gCodeFileBrowseButton = tk.Button(
            text="Browse",
            font=("Times New Roman", 12),
            width=7,
            pady=2,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=self.browseFiles,
        )
        gCodeFileBrowseButton.grid(column=1, padx=2, row=1, in_=gCodeFileFrame)

        gCodeFileRunButton = tk.Button(
            text="Run",
            font=("Times New Roman", 12),
            width=7,
            pady=2,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=self.runFile,
        )
        gCodeFileRunButton.grid(column=2, padx=2, row=1, in_=gCodeFileFrame)

        gCodeFileClearButton = tk.Button(
            text="Clear File",
            font=("Times New Roman", 12),
            width=7,
            pady=2,
            bg="#8f8f8f",
            fg="black",
            relief="raised",
            command=lambda: self.gCodeFileText.set(''),
        )
        gCodeFileClearButton.grid(column=1, pady=2, row=2, in_=gCodeFileFrame)

        aFrame.columnconfigure(0, weight=1)
        aFrame.rowconfigure(0, weight=1)
        aFrame.rowconfigure(1, weight=2)

        displayFrame.columnconfigure(0, weight=1)
        displayFrame.rowconfigure(0, weight=1)

        gCodeFrame.columnconfigure(0, weight=1)
        gCodeFrame.rowconfigure(2, weight=1)

        gCodeFileFrame.columnconfigure(0, weight=1)
        gCodeFileFrame.rowconfigure(0, weight=1)
        gCodeFileFrame.rowconfigure(1, weight=1)
        gCodeFileFrame.rowconfigure(2, weight=1)

    def createSaveFrame(self):
        """Creates the section for saving, clearing, and collecting data."""
        sFrame = tk.LabelFrame(
            width=300,
            height=600,
            bg="#e3f0fa",
            labelwidget=tk.Label(font=("Times New Roman", 22), text="SAVE/REPORT", fg="black"),
            bd=5,
            relief="groove",
            padx=10,
            pady=10,
        )
        sFrame.grid(column=2, row=0, in_=self.topFrame, sticky=tk.NSEW)
        sFrame.grid_propagate(0)

        self.startStopDataBut = tk.Button(
            text="Start Data Collection",
            font=("Times New Roman bold", 18),
            width=15,
            pady=5,
            bg="#8efa8e",
            fg="black",
            relief="raised",
            command=self.startStopData,
        )
        self.startStopDataBut.grid(column=0, row=0, in_=sFrame, pady=20, padx=10, sticky=tk.EW)

        self.saveDataBut = tk.Button(
            text="Save All Data",
            font=("Times New Roman bold", 18),
            width=15,
            pady=5,
            bg="#8efa8e",
            fg="grey",
            relief="raised",
        )
        self.saveDataBut.grid(column=0, row=1, in_=sFrame, pady=10, padx=10, sticky=tk.EW)

        self.clearDataBut = tk.Button(
            text="Clear All Data",
            font=("Times New Roman bold", 18),
            width=15,
            pady=5,
            bg="#ff475d",
            fg="grey",
            relief="raised",
        )
        self.clearDataBut.grid(column=0, row=2, in_=sFrame, pady=10, padx=10, sticky=tk.EW)

        tcFrame = tk.Frame(height=20, bg="#e3f0fa")
        tcFrame.grid(column=0, row=3, in_=sFrame, sticky=tk.NW)

        tk.Label(
            text='Thermocouple 1: ', font=("Times New Roman bold", 12), fg="black", bg="#e3f0fa"
        ).grid(column=0, row=0, in_=tcFrame)
        tk.Label(
            text='Thermocouple 2: ', font=("Times New Roman bold", 12), fg="black", bg="#e3f0fa"
        ).grid(column=0, row=1, in_=tcFrame)

        self.tcOneVariable = tk.StringVar(value="N/A")
        tcOneLabel = tk.Label(
            textvariable=self.tcOneVariable, font=("Times New Roman bold", 12),
            pady=5, fg="black", bg="#e3f0fa", width=6
        )
        tcOneLabel.grid(column=1, row=0, in_=tcFrame)

        self.tcTwoVariable = tk.StringVar(value="N/A")
        tcTwoLabel = tk.Label(
            textvariable=self.tcTwoVariable, font=("Times New Roman bold", 12),
            pady=5, fg="black", bg="#e3f0fa", width=6
        )
        tcTwoLabel.grid(column=1, row=1, in_=tcFrame)

        self.tcConnectButton = tk.Button(
            text='Connect LabJack',
            font=("Times New Roman bold", 12),
            width=15,
            pady=5,
            bg="#ff475d",
            fg='black',
            relief="raised",
            command=self.startTC,
        )
        self.tcConnectButton.grid(
            column=0, row=3, columnspan=2, in_=tcFrame, pady=10, padx=10, sticky=tk.EW
        )

        sFrame.columnconfigure(0, weight=1)
        sFrame.rowconfigure(3, weight=1)

    def createBottomButtons(self):
        """Adds the bottom buttons to the bottom frame."""
        self.sBut = tk.Button(
            text="Start Mill",
            font=("Times New Roman bold", 20),
            bg="#8efa8e",
            fg="black",
            command=self.sendStartStop,
            width=15,
            pady=5,
        )
        self.sBut.grid(column=0, row=0, in_=self.botFrame, sticky=tk.NS)

    def sendStartStop(self):
        """Sends the code to turn the mill on and off."""
        if not self.controller.running.is_set():
            # b'$10=3' sets the Grbl data that is sent back when querried with b'?'
            self.sendCode(b'$10=3', False)
            self.sBut.config(text="Stop Mill", bg="#fc4747")
            self.controller.running.set()
        else:
            self.controller.serial_processor.espBuffer.clear()
            self.controller.serial_processor.espTypeBuffer.clear()
            self.sendCode(b'!', False)
            self.sBut.config(text="Start Mill", bg="#8efa8e")
            self.enXYBut.config(text="Enable XYA", bg="#8efa8e")
            self.controller.running.clear()

    def saveFile(self, source=None):
        """
        Saves the collected data from the serial port to a file.

        Parameters
        ----------
        source : tk.TopLevel, optional
            The window to close when saving is finished. Default is None, which
            will not close any windows.
        """
        data = self.controller.return_data()
        if data is None:
            self.clearAllData(source)
            return

        fileTypes = [('CSV', '*.csv'), ('Text', '*.txt'), ('All Files', '*.*')]
        filename = filedialog.asksaveasfilename(filetypes=fileTypes, defaultextension=fileTypes)
        if not filename:
            return
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(data)
        except PermissionError:
            print("File is currently open")
        except Exception:
            print("There was an error saving the file.")
        else:  # only clear data when the save is successful
            self.clearAllData(source)
            self.clearDataBut.configure(fg="grey", command='')
            self.saveDataBut.configure(fg="grey", command='')

    def startStopData(self):
        """Toggles data collection events and GUI elements."""
        if "Start" in self.startStopDataBut["text"]:
            if self.controller.labjack_handler.timeData:
                # have unsaved data, so cache it and then erase data
                self.controller.save_temp_file()
                self.controller.clear_data()
            self.controller.collecting.set()
            self.startStopDataBut.config(text="Stop Data Collection", bg="#ff475d")

        else:
            self.controller.collecting.clear()
            if not self.controller.labjack_handler.timeData:
                self.clearAllData()
            else:
                askSaveWin = tk.Toplevel(self.controller.root, takefocus=True)
                askSaveWin.protocol(
                    "WM_DELETE_WINDOW", lambda: [
                        self.controller.save_temp_file(), askSaveWin.destroy()
                    ]
                )
                askSaveWin.title("Save Data?")
                askSaveLabel = tk.Label(
                    askSaveWin,
                    font=("Times New Roman", 22),
                    text="Would you like to save the data?",
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
                    text="YES",
                    fg="black",
                    bg="#8efa8e",
                    command=lambda: self.saveFile(askSaveWin),
                ).grid(column=0, row=0, padx=30)
                tk.Button(
                    askSaveButFrame,
                    font=("Times New Roman", 22),
                    text="NO",
                    fg="black",
                    bg="#ff475d",
                    command=lambda: [self.controller.save_temp_file(), askSaveWin.destroy()],
                ).grid(column=1, row=0, padx=30)

                askSaveWin.grab_set()  # prevent interaction with main window until dialog closes
                askSaveWin.wm_transient(self.controller.root)  # set dialog above main window

                self.clearDataBut.configure(fg="black", command=self.clearDataPrompt)
                self.saveDataBut.configure(fg="black", command=self.saveFile)

            self.startStopDataBut.configure(text="Start Data Collection", bg="#8efa8e")

    def clearAllData(self, source=None):
        """Clears all collected data and resets GUI elements."""
        self.controller.clear_data()
        self.clearDataBut.configure(fg="grey", command='')
        self.saveDataBut.configure(fg="grey", command='')
        if source is not None:
            source.destroy()

    def clearDataPrompt(self):
        """Asks to save data when closing the window."""
        if not self.controller.labjack_handler.timeData:
            self.clearAllData()
        else:
            askSaveWin = tk.Toplevel(self.controller.root, takefocus=True)
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
            askSaveButFrame = tk.Frame(askSaveWin, width=750, height=80)
            askSaveButFrame.grid(column=0, row=1, pady=10, sticky=tk.E + tk.W)
            tk.Button(
                askSaveButFrame,
                font=("Times New Roman", 22),
                text="SAVE",
                fg="black",
                bg="#8efa8e",
                command=lambda: self.saveFile(askSaveWin),
            ).grid(column=0, row=0, padx=30)
            tk.Button(
                askSaveButFrame,
                font=("Times New Roman", 22),
                text="CLEAR",
                fg="black",
                bg="#ff475d",
                command=lambda: self.clearAllData(askSaveWin),
            ).grid(column=1, row=0, padx=30)

    def sendGCode(self, event):
        """Runs user-input GCode and ensures it is upper-case."""
        gcode = self.gCodeText.get()
        if gcode:
            if self.controller.running.is_set():
                try:
                    if int(event.type) == 3:
                        self.sendCode(gcode.upper().encode(), False)
                except Exception:
                    print("There was an exception?")
            else:
                print("Machine Must Be Started First!")

    def browseFiles(self):
        """Browses files for running GCode."""
        filename = filedialog.askopenfilename(
            initialdir=self.gcode_directory,
            title="Select a File",
            filetypes=(("GCode Files", "*.gcode*"), ("Text files", "*.txt*"), ("All files", "*.*")),
        )
        if filename:
            self.gcode_directory = Path(filename).parent
            self.gCodeFileText.set(filename)

    def runFile(self):
        """Runs GCode from the specified file."""
        filename = self.gCodeFileText.get()
        if not filename:
            return  # ignore if no file is selected

        if not self.controller.collecting.is_set():
            if self.confirm_run:
                self.confirm_run_with_data(filename)
            elif self.confirm_run is None:
                self.startStopData()
                self.write_file_to_buffer(filename)
            else:
                self.write_file_to_buffer(filename)
        else:
            self.write_file_to_buffer(filename)

    def write_file_to_buffer(self, filename):
        with open(filename, 'r') as f:
            self.controller.serial_processor.espBuffer = [line.rstrip('\n').encode() for line in f]
        self.controller.serial_processor.espTypeBuffer = (
            [1] * len(self.controller.serial_processor.espBuffer)
        )
        print(self.controller.serial_processor.espTypeBuffer)

    def set_cofirm_run(self, set_run, confirm_run):
        if set_run and confirm_run:
            self.confirm_run = None
            self.startStopData()
        elif set_run:
            self.startStopData()
        elif confirm_run:
            self.confirm_run = False

    def confirm_run_with_data(self, filename):
        confirmRunWin = tk.Toplevel(self.controller.root, takefocus=True)
        confirmRunWin.title("Running without saving")
        askSaveLabel = tk.Label(
            confirmRunWin,
            font=("Times New Roman", 22),
            text="Turn data collection on?",
            fg="black",
            padx=5,
        )
        askSaveLabel.grid(column=0, row=0, sticky=tk.E + tk.W)
        askSaveLabel.grid(column=0, row=0)
        askSaveButFrame = tk.Frame(confirmRunWin, width=750, height=80)
        askSaveButFrame.grid(column=0, row=1, pady=10)

        checkbox_var = tk.BooleanVar()
        confirm_checkbox = tk.Checkbutton(
            askSaveButFrame, text="Remember Selection", font=("Times New Roman", 18),
            variable=checkbox_var
        )
        confirm_checkbox.grid(column=0, row=0, pady=20)

        tk.Button(
            askSaveButFrame,
            font=("Times New Roman", 22),
            text="YES",
            fg="black",
            bg="#8efa8e",
            command=lambda: [
                self.set_cofirm_run(True, checkbox_var.get()), confirmRunWin.destroy(),
                self.write_file_to_buffer(filename)
            ],
        ).grid(column=0, row=1, padx=30)
        tk.Button(
            askSaveButFrame,
            font=("Times New Roman", 22),
            text="NO",
            fg="black",
            bg="#ff475d",
            command=lambda: [
                self.set_cofirm_run(False, checkbox_var.get()), confirmRunWin.destroy(),
                self.write_file_to_buffer(filename)
            ],
        ).grid(column=1, row=1, padx=30)
        confirmRunWin.grab_set()  # prevent interaction with main window until dialog closes
        confirmRunWin.wm_transient(self.controller.root)  # set dialog above main window

    def display(self, force, thermocouple1, thermocouple2):
        """
        Updates the GUI with new force data.

        """
        for line in self.temperature_axis.lines:
            line.remove()
        for line in self.axis.lines:
            line.remove()

        self.displayData.append(force)
        self.displayDataTC1.append(thermocouple1)
        self.displayDataTC2.append(thermocouple2)

        self.temperature_axis.set_prop_cycle(plt.rcParams['axes.prop_cycle'])
        # plot empty value to advance color cycle so it doesn't overlap with force
        self.temperature_axis.plot(nan, nan)
        self.axis.set_prop_cycle(plt.rcParams['axes.prop_cycle'])
        self.line = self.axis.plot(self.times, self.displayData, label='force')[0]
        tc_line1 = self.temperature_axis.plot(self.times, self.displayDataTC1, label='TC1')[0]
        tc_line2 = self.temperature_axis.plot(self.times, self.displayDataTC2, label='TC2')[0]
        self.axis.legend(handles=[self.line, tc_line1, tc_line2])
        self.canvas.draw_idle()

    def sendCode(self, code, wait_in_queue):
        """
        Sends code to the mill for controlling movement if the serial port is connected.

        Parameters
        ----------
        code : bytes
            The byte G-code to send to the serial port.
        wait_in_queue : bool
            False means send the code immediately and True means to wait for the
            buffer to be open.
        """
        if self.controller.serial_processor.esp is not None:
            self.controller.serial_processor.sendCode(code, wait_in_queue)

    def zeroCord(self, axis):
        """
        Sets the current position as the zero point for the given axis.

        Parameters
        ----------
        axis : {b'X', b'Y', b'Z', b'A'}
            The byte designating which axis to zero.
        """
        if self.controller.serial_processor.esp is not None:
            self.controller.serial_processor.zeroCord(axis)

    def reset_and_offset(self):
        """Resets the mill and then reapplies the current offsets.

        Needed since FluidNC will reset the offsets when the mill is reset, so use
        this to not lose the old offsets.
        """
        if self.controller.serial_processor.esp is not None:
            # copy so that the values do not update while using
            current_offsets = self.controller.serial_processor.work_offsets.copy()
            current_position = (
                float(self.xAbsVar.get()) - current_offsets[0],
                float(self.yAbsVar.get()) - current_offsets[1],
                float(self.zAbsVar.get()) - current_offsets[2],
                float(self.aAbsVar.get()) - current_offsets[3],
            )

            self.sendCode(b'\x18', False),
            self.sendCode(b'$X', False),
            self.sendCode('G92 X{0} Y{1} Z{2} A{3}'.format(*current_position).encode(), False)

    def startTC(self):
        """Attempts to connect to LabJack thermocouples."""
        if self.controller.labjack_handler.labjackHandle is None:
            self.controller.labjack_handler.start_threads(
                allow_dummy_thread=self.controller._testing_mode
            )
        if self.controller.labjack_handler.labjackHandle is not None:
            self.saveDataBut.configure(fg="grey", command='')
