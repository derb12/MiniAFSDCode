# -*- coding: utf-8 -*-
"""
mini_afsd
=========

mini_afsd provides code for running a miniature additive friction stir deposition
machine with both a user interface and a serial port and Labjack data collector.

"""

__version__ = '1.3.0'


# have to import controller last since it imports from the other two files
from .gui import Gui
from .serial_processor import SerialProcessor
from .controller import Controller
