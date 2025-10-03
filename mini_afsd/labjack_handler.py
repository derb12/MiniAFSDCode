# -*- coding: utf-8 -*-
"""Class and functions for communicating with a Labjack."""

import random
import threading
import time

from labjack import ljm


class LabjackHandler:
    """An object for controlling communication to the mill through a serial port."""

    def __init__(self, controller, averaged_points=10, allow_testing=False):
        """
        Initializes the Labjack handler.

        Parameters
        ----------
        controller : _type_
            _description_
        measure_force : bool, optional
            _description_. Default is False.
        """
        self.controller = controller
        self.labjackHandle = None
        self.labjackThread = None
        self.numDataAvg = averaged_points
        self.startTime = 0
        self.timeData = []

        self.forceData = []
        self.TC_one_Data = []
        self.TC_two_Data = []

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
                self.labjackHandle = 'dummy'
                self.labjackThread = threading.Thread(target=self.startLabjackDummy, daemon=True)
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
        # so 9000, 9300, 41000 sets AIN0 to a type K thermocouple with units celcius, with a negative channel of AIN1
        ljm.eWriteAddresses(
            self.labjackHandle, 6, [9000, 9004, 9300, 9304, 41000, 41002],
            [
                ljm.constants.UINT32, ljm.constants.UINT32,
                ljm.constants.UINT32, ljm.constants.UINT32,
                ljm.constants.UINT16, ljm.constants.UINT16
            ],
            # 22 designates type K thermocouple, 1 desginates Celcius units, 1 and 3 3are negative channels
            [22, 22, 1, 1, 1, 3]
        )
        while True:
            if self.controller.collecting.wait(timeout=1):
                self.startTime = time.time()
                # 1000 == DAC0
                ljm.eWriteAddress(self.labjackHandle, 1000, ljm.constants.FLOAT32, 2.67)
                # Made from trial and error, sets the AIN pins for the thermocouples
                # to output compensated temperatures in C
                avgNum = 0
                avgResults = [0, 0, 0]
                while self.controller.collecting.is_set():
                    try:
                        results = ljm.eReadAddresses(
                            self.labjackHandle, numFrames, addresses, dataTypes
                        )
                        avgResults[0] += results[0]
                        avgResults[1] += results[1]
                        avgResults[2] += results[2]
                        avgNum += 1
                        if (avgNum == self.numDataAvg):
                            avgResults[0] /= self.numDataAvg
                            avgResults[1] /= self.numDataAvg
                            avgResults[2] /= self.numDataAvg
                            force = (avgResults[2] - 0.5) * 333.61  #Converts the load cell range of 0.5-4.5 V and 0 to 50 lbs to the calibrated force in N
                                                                    #333.61 is 6 (lever arm) x 12.5 (50 lbs range / 4 V range) x 4.45 (lbs to N)
                            self.TC_one_Data.append(avgResults[0])
                            self.TC_two_Data.append(avgResults[1])
                            self.forceData.append(force)
                            self.controller.gui.tcOneVariable.set(f'{avgResults[0]:.2f} °C')
                            self.controller.gui.tcTwoVariable.set(f'{avgResults[1]:.2f} °C')
                            self.timeData.append(
                                round(time.time() - self.startTime, 2)
                            )
                            self.controller.gui.display(force, avgResults[0], avgResults[1])
                            avgResults = [0, 0, 0]
                            avgNum = 0
                    except KeyboardInterrupt:
                        break
                    except Exception as ex:
                        self.controller.logger.debug(f'LabJack error: {ex}')
                        if type(ex).__name__ != "LJMError":
                            break
                ljm.eWriteAddress(self.labjackHandle, 1000, ljm.constants.FLOAT32, 0)
            else:
                try:
                    results = ljm.eReadAddresses(self.labjackHandle, numFrames, addresses, dataTypes)
                    self.controller.gui.tcOneVariable.set(f'{results[0]:.2f} °C')
                    self.controller.gui.tcTwoVariable.set(f'{results[1]:.2f} °C')
                    force = (results[2] - 0.5) * 333.61
                    self.controller.gui.display(force, results[0], results[1])
                except ljm.LJMError as ex:  # failed to read, disconnect connection
                    self.controller.logger.debug(f'LabJack error: {ex}')
                    self.close()
                    break


    def startLabjackDummy(self):
        """The thread for reading data from the LabJack."""
        while True:
            if self.controller.collecting.wait(timeout=0.2):
                self.startTime = time.time()
                avgNum = 0
                avgResults = [0, 0, 0]
                while self.controller.collecting.is_set():
                    try:
                        results = [
                            random.normalvariate(25, 5),
                            random.normalvariate(25, 0.5),
                            random.normalvariate(1, 0.2)
                        ]
                        avgResults[0] += results[0]
                        avgResults[1] += results[1]
                        avgResults[2] += results[2]
                        avgNum += 1
                        if (avgNum == self.numDataAvg):
                            avgResults[0] /= self.numDataAvg
                            avgResults[1] /= self.numDataAvg
                            avgResults[2] /= self.numDataAvg
                            force = (avgResults[2] - 0.5) * 333.61
                            self.timeData.append(
                                round(time.time() - self.startTime, 2)
                            )
                            self.TC_one_Data.append(avgResults[0])
                            self.TC_two_Data.append(avgResults[1])
                            self.forceData.append(force)
                            self.controller.gui.tcOneVariable.set(f'{avgResults[0]:.2f} °C')
                            self.controller.gui.tcTwoVariable.set(f'{avgResults[1]:.2f} °C')
                            self.controller.gui.display(force, avgResults[0], avgResults[1])
                            avgResults = [0, 0, 0]
                            avgNum = 0
                    except KeyboardInterrupt:
                        break
                    except Exception as ex:
                        print(ex)
                        if type(ex).__name__ != "LJMError":
                            break

                    time.sleep(0.1)
            else:
                results = [
                    random.normalvariate(25, 5),
                    random.normalvariate(25, 0.5),
                    random.normalvariate(1, 0.2)
                ]
                self.controller.gui.tcOneVariable.set(f'{results[0]:.2f} °C')
                self.controller.gui.tcTwoVariable.set(f'{results[1]:.2f} °C')
                force = (results[2] - 0.5) * 333.61
                self.controller.gui.display(force, results[0], results[1])

    def clear_data(self):
        """Cleans up all of the collected data."""
        self.forceData = []
        self.TC_one_Data = []
        self.TC_two_Data = []
        self.timeData = []

    def close(self):
        """Ensures the Labjack is closed correctly."""
        if self.labjackHandle not in (None, 'dummy'):
            ljm.close(self.labjackHandle)
            self.labjackHandle = None
            self.labjackThread = None
            self.controller.logger.debug('LabJack disconnected')
