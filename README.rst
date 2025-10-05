=========
mini_afsd
=========

mini_afsd is a program for controlling a miniturized additive friction stir deposition (AFSD) machine.

* For Python 3.7+
* Source Code: https://github.com/RyTheGuy355/MiniAFSDCode


.. contents:: **Contents**
    :depth: 1


Introduction
------------

This repository contains code for controlling a miniturized AFSD machine and
is used by the `Yu group at Virginia Tech <https://yu.mse.vt.edu>`_.

Communication with the machine is achieved using `FluidNC <https://github.com/bdring/FluidNC>`_,
and future modifications to the firmware or code inputs can be helped by looking
through FluidNC's documentation.


Installation
------------


Dependencies
~~~~~~~~~~~~


Driver Dependencies
^^^^^^^^^^^^^^^^^^^

The `LJM` driver from LabJack must be installed to interface with the
LabJack for measuring the thermocouple outputs, which can be downloaded from
https://labjack.com/support/software/installers/ljm.


The driver needed for computers to properly connect to the serial
port's USB interface is available from
https://oemdrivers.com/usb-cp2104-usb-to-uart-driver.
(Change this in the future if the connector changes)


Python Dependencies
^^^^^^^^^^^^^^^^^^^

mini_afsd requires `Python <https://python.org>`_ version 3.7 or later
and the following Python libraries:

* `labjack-ljm <https://pypi.org/project/labjack-ljm/>`_
* `matplotlib <https://pypi.org/project/matplotlib/>`_ (>=3.4)
* `pyserial <https://pypi.org/project/pyserial/>`_


All of the required Python libraries should be automatically installed when
installing mini_afsd using any of the installation methods below.


Installing Python
~~~~~~~~~~~~~~~~~

Python can be installed multiple ways:

* If on Windows, the easiest way is to use `WinPython <https://winpython.github.io/>`_. The recommended
  installation file (as of June 10, 2022) is WinPython64-3.10.4.0 (or WinPython64-3.10.4.0dot if you don't
  want any preinstalled libraries).
* Use `Anaconda <https://www.anaconda.com/>`_, which comes with many libraries preinstalled.
* Install from Python's official source, https://www.python.org/. Follow the instructions listed at
  https://packaging.python.org/en/latest/tutorials/installing-packages/#requirements-for-installing-packages
  to ensure Python and the Python package manager `pip <https://pip.pypa.io>`_ are correctly installed.


Stable Release
~~~~~~~~~~~~~~

mini_afsd can be installed from `pypi <https://pypi.org/project/mini_afsd>`_
using `pip <https://pip.pypa.io>`_, by running the following command in the terminal:

.. code-block:: console

    pip install -U mini_afsd


Development Version
~~~~~~~~~~~~~~~~~~~

The sources for mini_afsd can be downloaded from the `GitHub repo`_.
To install the current version of mini_afsd from GitHub, run:

.. code-block:: console

    pip install https://github.com/RyTheGuy355/MiniAFSDCode/zipball/main


.. _GitHub repo: https://github.com/RyTheGuy355/MiniAFSDCode


Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~

While not needed, an Arduino IDE (available from https://www.arduino.cc/en/software)
can be used when connected to the serial port of the mill to get more detailed feedback
on the messages sent to and from the port.


Quick Start
-----------

For default usage, mini_afsd can be ran from the a terminal (the command line if
Python was install universally, from an Anaconda terminal if Python was installed with
Anaconda, or from the WinPython Command Prompt if Python was installed using WinPython) using:

.. code-block:: console

  python -m mini_afsd

To list out the various options when using mini_afsd from the terminal, simply do:

.. code-block:: console

  python -m mini_afsd -h


Alternatively, mini_afsd can be used from a Python file by doing the following:

.. code-block:: python

    from mini_afsd import Controller

    Controller().run()


Configuring LabJack
-------------------

For determining proper addresses to connections on the LabJack, use
the Kipling software included with LJM to find the pin addresses within
the "Register Matrix" section.

Sending Commands to FluidNC
---------------------------

Commands sent from the GUI to FluidNC for control of the mill can be split into 2 categories:

1) G-Code (and subsequent M-Codes, etc.): These are prefixed by "G", "M", etc., and follow their
   standard usage. See http://wiki.fluidnc.com/en/features/supported_gcodes for the G-Codes
   supported by FluiNC.

2) Codes to FluiNC or Grbl. These can include things liking homing ("$H"), status query ("?"), or
   soft reset ("0x18" == "CTRL+X"). When adding new commands under this category, it is recommended
   to add a comment as to what these commands are doing since it is not immediately clear and makes
   maintenance difficult. A full listing of commands can be found at
   http://wiki.fluidnc.com/en/features/commands_and_settings.

Contributing
------------

Contributions are welcomed and greatly appreciated. For information on
submitting bug reports, pull requests, or general feedback, please refer
to the `contributing guide`_.

.. _contributing guide: https://github.com/RyTheGuy355/MiniAFSDCode/tree/main/docs/contributing.rst


License
-------

mini_afsd is all rights reserved. For more information, refer to the license_.

.. _license: https://github.com/RyTheGuy355/MiniAFSDCode/tree/main/LICENSE.txt


Author
------

* Ryan Gottwald <insert_email_here>
