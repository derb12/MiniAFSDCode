# -*- coding: utf-8 -*-
"""Class and functions for communicating with serial ports."""

from collections import deque
import random
import threading
import time

import serial


class SerialProcessor:
    """
    An object for controlling communication to the mill through a serial port.

    Attributes
    ----------
    esp : serial.Serial or None
        The connected serial port. Is None if not connected to any serial port.
    port : str or None
        The string denoting the connected port. Is None if not connected to a serial port.
    buffer_length : int
        The buffer length of the connected serial port. Initially starts at 15 (0-indexed) and
        reduces to 0 if buffer is full.
    work_offsets : list(int, int, int, int)
        The offsets for the x, y, z, and a axes on the mill, respectively.
    close_port : threading.Event

    commandInvalid : threading.Event

    serialUnlocked : threading.Event

    """

    def __init__(self, controller, port=None, skip_home=False, allow_testing=False):
        """
        Initializes the serial port processor.

        Parameters
        ----------
        controller : Controller
            The controller for this object.
        port : str, optional
            The port to connect to. Default is None, which will not connect to a port.
            If a port is given, will try to connect upon initialization.
        skip_home : bool, optional
            If True, the serial port will send b'$X' to skip homing and directly
            be ready to send commands. If False (default), b'$X' or b'$H' (home)
            will have to be sent manually through the serial port to begin using
            the mill.
        allow_testing : bool, optional
            If True, will spawn an emulator of the serial port for testing purposes.
            Default is False, which will not spawn an emulator.

        """
        self.controller = controller
        self.esp = None
        self.allow_testing = allow_testing
        # commands that can be sent even if mill is off
        self.mill_off_commands = {b'\x85', b'!', b'~', b'$MD'}
        self.port = port
        self.buffer_length = 15
        self.state = 'Idle'
        self.work_offsets = [0, 0, 0, 0]

        self.close_port = threading.Event()
        self.commandInvalid = threading.Event()
        self.serialReadUnlocked = threading.Event()
        self.serialReadUnlocked.set()
        self.serialWriteUnlocked = threading.Event()
        self.serialWriteUnlocked.set()
        self.state_exact = threading.Event()

        self.espBuffer = []
        self.espTypeBuffer = []

        if skip_home:
            self.sendCode(b'$X', False)

    @property
    def port(self):
        """The current port for the processor.

        Returns
        -------
        str or None
            The current port.
        """
        return self._port

    @port.setter
    def port(self, port):
        """Sets the COM port and tries to initiate communication.

        Parameters
        ----------
        port : str or None
            The port to connect to. If None, no connection attempt will be made; otherwise,
            the port will be opened for communication.

        Raises
        ------
        serial.SerialException
            Raised if the port connection failed.
        """
        self._port = port
        if self._port is None:
            self.esp = None
        elif self._port == 'testing':
            self.controller.logger.debug('CONNECTING TO SERIAL PORT EMULATOR!!!')
            self.esp = DummySerial(port=port, baudrate=115200, timeout=1)
            self.start_threads()
        else:
            try:
                self.esp = serial.Serial(port=self._port, baudrate=115200, timeout=1)
            except serial.SerialException:  # wrong port selected
                self._port = None
                self.controller.logger.debug('Failed to connect to serial port')
                raise
            else:
                self.controller.logger.debug(f'Successfully connected to serial port: {self.port}')
                self.start_threads()

    def start_threads(self):
        """Spawns the threads for communicating with the serial ports and Labjack."""
        self.listener = threading.Thread(target=self.serialListen, daemon=True)
        self.listener.start()

        self.reporter = threading.Thread(target=self.serialReporter, daemon=True)
        self.reporter.start()

        self.status_updater = threading.Thread(target=self.status_update, daemon=True)
        self.status_updater.start()

    def serialListen(self):
        """The event loop for the thread that reads messages from the serial port."""
        self.controller.logger.debug("Starting serial listener")
        while not self.close_port.is_set():
            if self.serialReadUnlocked.wait(timeout=0.5) and self.esp.in_waiting:
                self.serialReadUnlocked.clear()
                try:
                    data = self.esp.read_until(b'\n')
                    data.strip(b'\n')
                    if (b'\r' in data):
                        data = data.strip(b'\r')

                    #if b'|' in data:
                    #    self.parse_state_message(data)
                    if not data:
                        continue
                    else:
                        self.controller.logger.debug(data)
                except Exception:
                    pass
                self.serialReadUnlocked.set()
            time.sleep(0.01)

        self.controller.logger.debug("Stopping serial listener")
        self.esp.flush()
        self.esp.close()
        try:
            self.controller.gui.sBut["state"] = "disabled"
        except Exception:
            self.controller.logger.debug("Window appears to be closed")

    def serialReporter(self):
        """The event loop for the thread that sends messages to the serial port."""
        self.controller.logger.debug("Starting serial reporter")
        while self.esp.is_open:
            if len(self.espBuffer) > 0:
                for i, (bufferValue, wait_in_queue) in enumerate(
                    zip(self.espBuffer, self.espTypeBuffer)
                ):
                    if (
                        not self.controller.running.is_set()
                        and not any(val in self.espBuffer for val in self.mill_off_commands)
                    ):
                        break

                    if (
                        (not wait_in_queue and self.buffer_length > 1)
                        or (self.buffer_length > 8 and not self.commandInvalid.is_set())
                    ):
                        self.serialWriteUnlocked.wait()
                        self.serialWriteUnlocked.clear()
                        break_loop = False
                        if not self.valid_message(bufferValue):
                            self.commandInvalid.set()
                        else:
                            self.commandInvalid.clear()
                            self.esp.write(bufferValue)
                            self.esp.write(b'\n')
                            self.espBuffer.pop(i)
                            self.espTypeBuffer.pop(i)
                            self.buffer_length += 1
                            break_loop = True

                        self.serialWriteUnlocked.set()
                        if break_loop:
                            break

                # reset so commands can be tried again in case state has changed
                self.commandInvalid.clear()
            time.sleep(0.01)

    def valid_message(self, message):
        """
        Ensures the next message to the serial port is valid with the current state.

        Parameters
        ----------
        message : bytes
            The message to be sent to the serial port.

        Returns
        -------
        valid_command : bool
            Whether the message is valid with the current state of the serial
            port and can be sent.
        """
        valid_command = True
        new_state = ''

        try:
            message = message.decode()
        except UnicodeDecodeError:
            if message == b'\x85':
                #self.state = 'Idle'
                pass  # let mill confirm that it went to idle
        else:
            if message:
                if message[0] in ('G', 'M', 'S'):
                    if self.state != 'Jog':
                        new_state = 'Run'
                    else:
                        valid_command = False
                elif message.startswith('$J'):
                    if self.state == 'Idle':
                        new_state = 'Jog'
                    else:
                        valid_command = False

        if new_state:
            self.state = new_state

        return valid_command

    def parse_state_message(self, message):
        """
        Parses the state message output by the serial port by sending b'?'.

        Updates the state, positions, and buffer length in the GUI depending
        on the message contents.

        Parameters
        ----------
        message : bytes
            The state message from the serial port.
        """
        machine_position = None
        work_position = None
        buffer_length = None
        total_message = message.decode().split('|')
        feed_override = None
        spindle_override = None
        spindle_speed = None
        if len(total_message) < 2:  # accidentally received b'ok'
            return
        # See https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface#real-time-status-reports for detailed
        # explanations of the status report sent by the machine
        #
        # A typical message is received as
        # b'<state|MPos:x,y,z,a|BF:#,#|FS:#,#|WCO:x,y,z,a>'
        # where "state" can be Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep,
        # and possible headers including:
        # MPos == machine position
        # WCO == work coordinate offsets
        # WPos == work position, where WPos = MPos - WCO
        # Bf == machine buffer state; first value denoates available machine buffer (ie. how
        # many commands it can receive)
        # Ov == override values; typically Ov:100,100,100; denotes override values for feed (G1,
        # G2, G3 motion), rapid (G0 motion), and spindle, respectively, in percentages
        # FS (or just F) == current feed rate (F) and potentially spindle speed
        # Pn == input pin states; ignored here
        # Note that not all headers may be included in each message
        total_message[0] = total_message[0].lstrip('<')
        total_message[-1] = total_message[-1].rstrip('>')
        old_state = self.state
        for entry in total_message:
            if ':' not in entry:
                self.state = entry
            else:
                try:
                    header, values = entry.split(':')
                except ValueError:  # message has multiple : at startup
                    self.controller.logger.debug(f'Encountered parsing error from: {entry}')
                    break
                if header == 'MPos':
                    machine_position = [float(val) for val in values.split(',')]
                elif header == 'WCO':
                    work_position = [float(val) for val in values.split(',')]
                elif header == 'Bf':
                    buffer_length = int(values.split(',')[0])
                elif header == 'Ov':
                    feed_override, _, spindle_override = [int(val) for val in values.split(',')]
                elif header == 'FS':
                    spindle_speed = int(values.split(',')[-1])
        # print(message.decode())
        if machine_position is not None:
            machine_x = machine_position[0]
            machine_y = machine_position[1]
            machine_z = machine_position[2]
            machine_a = machine_position[3]
            xSign = "+" if machine_position[0] >= 0 else ""
            ySign = "+" if machine_position[1] >= 0 else ""
            zSign = "+" if machine_position[2] >= 0 else ""
            aSign = "+" if machine_position[3] >= 0 else ""

            self.controller.gui.xAbsVar.set(f'{xSign}{machine_position[0]:.3f}')
            self.controller.gui.yAbsVar.set(f'{ySign}{machine_position[1]:.3f}')
            self.controller.gui.zAbsVar.set(f'{zSign}{machine_position[2]:.3f}')
            self.controller.gui.aAbsVar.set(f'{aSign}{machine_position[3]:.3f}')

            if work_position is None:
                work_position = self.work_offsets
            else:
                self.work_offsets = work_position

            rel_x, rel_y, rel_z, rel_a = work_position
            work_x = machine_x - rel_x
            work_y = machine_y - rel_y
            work_z = machine_z - rel_z
            work_a = machine_a - rel_a
            xSign = "+" if work_x >= 0 else ""
            ySign = "+" if work_y >= 0 else ""
            zSign = "+" if work_z >= 0 else ""
            aSign = "+" if work_a >= 0 else ""

            self.controller.gui.xRelVar.set(f'{xSign}{work_x:.3f}')
            self.controller.gui.yRelVar.set(f'{ySign}{work_y:.3f}')
            self.controller.gui.zRelVar.set(f'{zSign}{work_z:.3f}')
            self.controller.gui.aRelVar.set(f'{aSign}{work_a:.3f}')

        if buffer_length is not None:
            self.controller.gui.bufferVar.set(buffer_length)
            self.buffer_length = buffer_length

        if old_state != self.state:
            if old_state == 'Alarm':
                self.controller.gui.resetBut.configure(fg="grey", state='disabled')
            elif self.state == 'Alarm':
                self.controller.gui.resetBut.configure(fg='black', state='normal')

        if feed_override is not None:
            self.controller.gui.feed_override.set(f'{feed_override}%')
            self.controller.gui.spindle_override.set(f'{spindle_override}%')
        if spindle_speed is not None:
            self.controller.gui.spindle_speed.set(f'{spindle_speed}')

        self.controller.gui.stateVar.set(self.state)
        self.state_exact.set()

    def status_update(self):
        """Sends and receives queries to the port to receive the position and state of the mill."""
        while not self.close_port.wait(timeout=0.5):
            if not self.controller.running.wait(timeout=0.5):
                continue
            self.serialWriteUnlocked.wait()
            self.serialWriteUnlocked.clear()
            self.serialReadUnlocked.wait()
            self.serialReadUnlocked.clear()
            try:
                self.esp.write(b'?')
                message = self.esp.read_until(b'\n').strip(b'\r\n')
                self.parse_state_message(message)
            except Exception:  # need to ensure all locks are reset so ignore errors
                pass
            self.serialReadUnlocked.set()
            self.serialWriteUnlocked.set()

    def close(self):
        """Ensures the serial port is closed correctly."""
        self.close_port.set()
        if self.esp is not None:
            self.esp.write(b"S")
            self.esp.write(b"\x03\x04")
            self.esp.flush()
            self.esp.close()

    def zeroCord(self, axis):
        """
        Sets the current position as the zero point for the given axis.

        Parameters
        ----------
        axis : {b'A', b'X', b'Y'}
            The byte designating which axis to zero.
        """
        if self.controller.running.is_set():
            code = b"G92 " + axis + b"0"
            self.sendCode(code, False)

    def sendCode(self, code, wait_in_queue):
        """
        Sends the specified code the the ESP.

        Parameters
        ----------
        code : bytes
            The byte G-code to send to the serial port.
        wait_in_queue : bool
            False means send the code immediately and True means to wait for the
            buffer to be open.
        """
        self.espBuffer.append(code)
        self.espTypeBuffer.append(wait_in_queue)
        self.controller.logger.debug(f'added to buffer: {code}')
        self.controller.logger.debug(f'internal buffer: {len(self.espBuffer)}')


class DummySerial:
    """A stand-in for testing the expected serial port usage.

    Notes
    -----
    Does not have all attributes of a serial.Serial object, only the ones that
    are currently used within `mini_afsd`.
    """

    def __init__(self, port='', baudrate=115200, timeout=1, *args, **kwargs):
        self.state = 'Alarm'
        self.is_open = True
        self.loops = 0
        self._buffer = 15
        self.acknowledge = threading.Event()
        self.inputs = deque()
        self.outputs = deque()
        self.machine_position = (0, 0, 0, 0)
        self.offsets = (0, 0, 0, 0)
        # speeds for feed (G1,G2,G3 motion), rapid (G0 motion), and spindle
        self.speeds = [100, 100, 100]
        self.spindle = 0.0

        self._read_thread = threading.Thread(target=self.main_loop, daemon=True)
        self._read_thread.start()

    def main_loop(self):
        """The main loop of the serial emulator in which it does its logic."""
        while True:
            if self.inputs and not self.acknowledge.is_set():
                message_bytes = self.inputs.popleft()
                try:
                    message = message_bytes.decode().strip('\n')
                except UnicodeDecodeError:
                    if message_bytes == b'\x85':
                        message = 'cancel jog'
                    else:
                        message = message_bytes.hex()

                if not message:
                    continue

                output = b'ok'
                if message != '?':
                    print(f'Serial emulator received: {message_bytes}')

                if self.state == 'Alarm':
                    if not (message.startswith('$H') or message in ('$X', '?')):
                        continue
                    elif message != '?':
                        self.state = 'Idle'

                if message in ('cancel jog', 'reset'):
                    self.state = 'Idle'
                    self.buffer = 15
                elif message[0] in ('G', 'M', 'S'):
                    if self.state != 'Jog':
                        self.state = 'Run'
                        self.buffer = self.buffer - 1
                        if message[0] == 'S':
                            self.spindle = float(message.split(' ')[0][1:])
                    else:
                        output = b'error:9'
                elif message.startswith('$'):
                    if self.state == 'Idle':
                        if message.startswith('$J'):
                            self.state = 'Jog'
                        elif message != '$10=3':  # $10=3 denotes the report state
                            self.state = 'Other'
                    else:
                        output = b'error:9'
                elif message == '91':  # b'\x91' increase feed rate by 10%
                    self.speeds[0] += 10
                elif message == '92':  # b'\x92' decrease feed rate by 10%
                    self.speeds[0] -= 10
                elif message == '93':  # b'\x93' increase feed rate by 1%
                    self.speeds[0] += 1
                elif message == '94':  # b'\x94' decrease feed rate by 1%
                    self.speeds[0] -= 1
                elif message == '9a':  # b'\x9A' increase spindle rate by 10%
                    self.speeds[2] += 10
                    self.spindle *= 1.1
                elif message == '9b':  # b'\x9B' decrease spindle rate by 10%
                    self.speeds[2] -= 10
                    self.spindle *= 0.9
                elif message == '9c':  # b'\x9C' increase spindle rate by 1%
                    self.speeds[2] += 1
                    self.spindle *= 1.01
                elif message == '9d':  # b'\x9D' decrease spindle rate by 1%
                    self.speeds[2] -= 1
                    self.spindle *= 0.99
                elif message == '?':
                    if self.state not in ('Idle', 'Alarm'):
                        self.machine_position = (
                            random.uniform(0, 300), random.uniform(0, 300),
                            random.uniform(0, 300), random.uniform(0, 100)
                        )
                        self.offsets = (
                            random.uniform(0, 3),
                            random.uniform(0, 3),
                            random.uniform(0, 3),
                            random.uniform(0, 3)
                        )
                    output = f'<{self.state}|MPos:{self.machine_position[0]:.3f},{self.machine_position[1]:.3f},{self.machine_position[2]:.3f},{self.machine_position[3]:.3f}|Bf:{self.buffer},127|FS:0,{self.spindle:.0f}>'
                    if random.choice([0, 0, 0, 1]):
                        output = output[:-1] + f'|WCO:{self.offsets[0]:.3f},{self.offsets[1]:.3f},{self.offsets[2]:.3f},{self.offsets[3]:.3f}>'
                    elif random.choice([0, 0, 0, 1]):
                        output = output[:-1] + f'|Ov:{self.speeds[0]},{self.speeds[1]},{self.speeds[2]}>'
                    output = output.encode()
                elif message.lower() == 'alarm':
                    self.state = 'Alarm'
                    output = b'Setting into alarm state'

                self.outputs.append(output)
                if self.state not in ('Idle', 'Jog', 'Alarm'):
                    self.loops += 1
                    if self.loops > 20:
                        self.state = 'Idle'
                        self.loops = 0
                        self.buffer = 15
                self.acknowledge.set()

            time.sleep(0.2)

    @property
    def buffer(self):
        """The number of values in the internal buffer of the serial port."""
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        """
        Sets the new internal buffer and ensures it is between 0 and 15.

        Parameters
        ----------
        value : int
            The new internal buffer value.
        """
        self._buffer = min(15, value)
        if self._buffer < 0:
            print('overloaded buffer!!!!!!')
            self.outputs.append(b'error:9')
            self._buffer = 0

    def write(self, message_bytes):
        """
        Adds the input message to the serial port's input queue.

        Parameters
        ----------
        message_bytes : bytes
            The input message.
        """
        self.inputs.append(message_bytes)

    @property
    def in_waiting(self):
        """
        The number of bytes waiting to be read from the serial port.

        Just a dummy function, so any integer could be returned for
        the desired effect.
        """
        if self.outputs:
            output = 10
        else:
            output = 0
        return output

    def read_until(self, endpoint=b'\n'):
        r"""
        Returns the current output of the serial port.

        Parameters
        ----------
        endpoint : bytes, optional
            The expected endpoint, which is automatically added to
            the end of the output. Default is b'\n'.

        Returns
        -------
        output : bytes
            The output message.
        """
        output = b''
        if self.acknowledge.wait(timeout=5):
            if self.outputs:
                output = self.outputs.popleft()
            self.acknowledge.clear()
        return output

    def flush(self):
        """Dummy method."""

    def close(self):
        """Closes the port."""
        self.is_open = False
