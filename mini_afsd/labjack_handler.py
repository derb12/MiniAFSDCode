# -*- coding: utf-8 -*-
"""Class and functions for communicating with a Labjack."""

from collections import deque
import random
import threading
import time
import traceback

from labjack import ljm


class DataHandler:
    """
    A class for maintaining streaming averages within a set time frame.

    Attributes
    ----------
    max_time : float
        The maximum time the object will use for storing data.
    avg_force : float
        The rolling average of recorded force values within the set
        time frame.
    avg_tc1 : float
        The rolling average of recorded temperature values from thermocouple 1, in degrees C,
        within the set time frame.
    avg_tc2 : float
        The rolling average of recorded temperature values from thermocouple 2, in degrees C,
        within the set time frame.

    """

    def __init__(self, max_time):
        """
        Initializes the object.

        Parameters
        ----------
        max_time : float
            The maximum time associated with this data reporter. Upon updating,
            any values associated with data older than `max_time` will be removed
            before statistics are updated.

        """
        self.max_time = max_time
        self.times = deque()
        self.forces = deque()
        self.thermocouple_1 = deque()
        self.thermocouple_2 = deque()

        # use None rather than nan since it works better in excel; matplotlib
        # recognizes None as nan when plotting
        self.avg_force = None
        self.avg_tc1 = None
        self.avg_tc2 = None

    def update(self, time, force, tc1, tc2):
        """Adds new data and removes any data that is too old."""
        self.times.append(time)
        self.forces.append(force)
        self.thermocouple_1.append(tc1)
        self.thermocouple_2.append(tc2)

        # cull older entries
        while time - self.times[0] > self.max_time:
            self.times.popleft()
            self.forces.popleft()
            self.thermocouple_1.popleft()
            self.thermocouple_2.popleft()

        # all containers have the same size, so only measure 1 for simplicity
        size = len(self.times)
        self.avg_force = sum(self.forces) / size
        self.avg_tc1 = sum(self.thermocouple_1) / size
        self.avg_tc2 = sum(self.thermocouple_2) / size


class LabjackHandler:
    """An object for communicating with a LabJack."""

    def __init__(self, controller, tc_time=5., graph_time=60., polling=0.2, collection_time=1.,
                 allow_testing=False):
        """
        Initializes the Labjack handler.

        Parameters
        ----------
        controller : Controller
            The controller for this object.
        tc_time : float, optional
            The time in seconds for the rolling average of the thermocouple values
            reported within the GUI text. Default is 5 seconds.
        graph_time : float, optional
            The time in seconds to retain collected force and temperature data for plotting.
            Default is 60 seconds.
        polling : float, optional
            The time in seconds between polling the LabJack. Default is 0.2 seconds.
        collection_time : float, optional
            The time in seconds for performing the rolling average of measured values
            that will be subsequently written to a file. Default is 1 second.
        allow_testing : bool, optional
            If True, will spawn an emulator of a Labjack for testing purposes if no
            actual Labjack is found upon start-up. Default is False, which will not
            spawn an emulator.

        """
        self.controller = controller
        self.labjackHandle = None
        self.labjackThread = None
        self.polling_time = polling

        # define data handlers for plotting, updating the thermocouple text in the gui,
        # and for logging in data files
        self.plotting_handler = DataHandler(graph_time)
        self.text_handler = DataHandler(tc_time)
        self.reporting_handler = DataHandler(collection_time)

        self.start_threads(allow_testing)

    def start_threads(self, allow_dummy_thread=False):
        """Spawns the thread for communicating with the Labjack."""
        try:
            # T7 device, Any connection, Any identifier
            self.labjackHandle = ljm.openS("T7", "ANY", "ANY")
        except Exception as ex:
            if type(ex).__name__ != "LJMError":  # TODO is this trying to catch ljm.LJMError?
                self.controller.logger.debug('No LabJack Connected')
            if allow_dummy_thread:
                self.labjackHandle = LabJackEmulator()
                self.labjackThread = threading.Thread(target=self.startLabjack, daemon=True)
                self.controller.logger.debug('CONNECTING TO LabJack EMULATOR!!!')
                self.labjackThread.start()
            else:
                self.controller.logger.debug('No LabJack Connected')
        else:
            self.labjackThread = threading.Thread(target=self.startLabjack, daemon=True)
            self.controller.logger.debug('Successfully connected to LabJack')
            self.labjackThread.start()

    def startLabjack(self):
        """The thread for reading data from the LabJack."""
        numFrames = 3  # number of addresses to read from Labjack
        # 7000 == AIN0_EF_READ_A
        # 70004 == AIN2_EF_READ_A
        # 26 == AIN13 -> was used for external force sensor connection
        addresses = [7000, 7004, 26]
        dataTypes = [ljm.constants.FLOAT32, ljm.constants.FLOAT32, ljm.constants.FLOAT32]
        # activates the channels associated with the thermocouples and assigns the corresponding
        # settings; see the following for a step by step guid:
        # https://support.labjack.com/docs/configuring-reading-a-thermocouple
        # 9000 == AIN0_EF_INDEX
        # 9004 == AIN2_EF_INDEX
        # 9300 == AIN0_EF_CONFIG_A
        # 9304 == AIN2_EF_CONFIG_A
        # 41000 == AIN0_NEGATIVE_CH -> set to 2 for AIN1 as negative channel
        # 41002 == AIN2_NEGATIVE_CH -> set to 6 for AIN3 as negative channel
        # so 9000, 9300, 41000 sets AIN0 to a type K thermocouple with units Celsius, with a negative channel of AIN1
        if self.labjackHandle is not None and not isinstance(self.labjackHandle, LabJackEmulator):
            ljm.eWriteAddresses(
                self.labjackHandle, 6, [9000, 9004, 9300, 9304, 41000, 41002],
                [
                    ljm.constants.UINT32, ljm.constants.UINT32,
                    ljm.constants.UINT32, ljm.constants.UINT32,
                    ljm.constants.UINT16, ljm.constants.UINT16
                ],
                # 22 designates type K thermocouple, 1 designates Celsius units, 1 and 3 are negative channels
                [22, 22, 1, 1, 1, 3]
            )
        while True:
            # NOTE: not sure why the eWriteAddress to the LabJack below was needed?? Maybe for
            # some old thermocouple wiring that is no longer used??
            # Essentially, it is setting the voltage on DAC0 to 2.67 V, reading the values,
            # and then later resetting the voltage on DAC0 to 0 V...
            # The line has been around since the first version of this code where only the
            # thermocouple data was read from the LabJack, so no idea... Best to just comment
            # it out and leave it for historical note...
            # address 1000 == DAC0
            # ljm.eWriteAddress(self.labjackHandle, 1000, ljm.constants.FLOAT32, 2.67)
            try:
                current_time = time.time()
                results = self.get_data(numFrames, addresses, dataTypes)
                # NOTE if more measurements are gathered from the LabJack, change the line below
                tc1, tc2, force_voltage = results
                force = self.calc_force(force_voltage)
                for thing in (
                    self.plotting_handler, self.reporting_handler, self.text_handler
                ):
                    thing.update(current_time, force, tc1, tc2)

                self.controller.gui.display(self.plotting_handler, self.text_handler)

                time.sleep(self.polling_time)
            except KeyboardInterrupt:
                break
            except Exception:
                # NOTE: receiving a ljm.LJMError would likely mean the LabJack was disconnected
                self.controller.logger.debug('LabJack error')
                self.controller.logger.debug(traceback.format_exc())
                self.close()
                break
            # See NOTE section above, the line below is likely no longer needed, so just commented
            # out for historical purposes
            # ljm.eWriteAddress(self.labjackHandle, 1000, ljm.constants.FLOAT32, 0)

    def calc_force(self, sensor_voltage):
        """
        Converts recorded voltage into force units.

        Parameters
        ----------
        sensor_voltage : float
            The recorded voltage from the force sensor, in units of V.

        Returns
        -------
        float
            The corresponding force value, in Newtons.

        Notes
        -----
        This calculation will need to be update upon changing force sensors or placement
        of the force sensor within the mill.
        """
        # Converts the load cell range of 0.5-4.5 V and 0 to 50 lbs to the calibrated force in N
        # 333.61 is 6 (lever arm) x 12.5 (50 lbs range / 4 V range) x 4.45 (lbs to N)
        return (sensor_voltage - 0.5) * 333.61

    def get_data(self, num_frames, addresses, data_types):
        """Receives data from a connected LabJack or generates random data."""
        if self.labjackHandle is not None and not isinstance(self.labjackHandle, LabJackEmulator):
            results = ljm.eReadAddresses(
                self.labjackHandle, num_frames, addresses, data_types
            )
        elif isinstance(self.labjackHandle, LabJackEmulator):
            results = self.labjackHandle.generate_data()
        else:
            results = (None, None, None)

        return results

    def close(self):
        """Ensures the Labjack is closed correctly."""
        if self.labjackHandle is not None and not isinstance(self.labjackHandle, LabJackEmulator):
            ljm.close(self.labjackHandle)
            self.labjackHandle = None
            self.labjackThread = None
            self.controller.logger.debug('LabJack disconnected')


class LabJackEmulator:
    "An object for emulating data generation within a LabJack."

    def __init__(self):
        self.depositing = False
        self.cooling = False
        self.start_time = 0
        self.last_time = time.time()

        self.tc1 = 25  # degrees C
        self.tc2 = 25  # degrees C
        self.force = 0.6 # volts; current force sensor can output between 0.5 and 4.5 V

    def generate_data(self):
        """Creates example data."""
        current_time = time.time()
        delta_time = current_time - self.last_time
        self.last_time = current_time
        if self.depositing:
            if self.tc1 < 600:
                # emulate heating at 30 C/s
                self.tc1 += 30 * delta_time
                self.tc2 += 30 * delta_time
            if self.force < 4:
                self.force += 0.5 * delta_time

            if current_time - self.start_time >= 30:  # only emulate depositing for 30 seconds
                self.depositing = False
                self.cooling = True

        elif self.cooling:
            if self.tc1 > 25:
                # emulate cooling at 60 C/s
                self.tc1 -= 60 * delta_time
                self.tc2 -= 60 * delta_time
            if self.force > 0.5:
                self.force -= 0.5 * delta_time

            if current_time - self.start_time >= 60:  # only emulate cooling for 30 seconds
                self.cooling = False

        else:
            if random.uniform(0, 100) < 1:
                self.depositing = True
                self.start_time = time.time()

        # emulate one thermocouple having more variance
        tc1 = random.normalvariate(self.tc1, 5)
        tc2 = random.normalvariate(self.tc1, 1)
        force = random.normalvariate(self.force, 0.05)

        return tc1, tc2, force
