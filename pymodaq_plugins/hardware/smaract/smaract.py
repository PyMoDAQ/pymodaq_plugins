# -*- coding: utf-8 -*-

import ctypes
import os
import re

"""
The support of multiple controllers connected to the machine is not implemented.

This wrapper supports only SmarAct LINEAR positionners (SLC type), with an enabled sensor attached to it.

We suppose that the configuration of the controller (sensor type etc) has been done via the SmarAct MCS Configuration
software.

Tested with one SLC-1740-S (closed loop with nanometer precision sensor) connected via a MCS-3S-EP-SDS15-TAB
(sensor module) to a MCS-3D controller on Windows 7.

The documentation of the .dll is in SmarAct MCS Programmers Guide.
"""

# We suppose the .dll library is in the same directory
# The CDLL function asks for the full path
dir_path = os.path.dirname(os.path.realpath(__file__))
SmaractDll = ctypes.CDLL(os.path.join(dir_path, "MCSControl.dll"))


class SmarAct(object):

    def __init__(self):
        super(SmarAct, self).__init__()

        self.controller_locator = self.get_controller_locator()
        self.system_index = self.init_communication(self.controller_locator)

    def get_controller_locator(self):
        """
            Get the locator (e.g. usb:id:3118167233) of the plugged MCS
            controller. We suppose that only one is connected to the machine.

        Returns
        -------
        controller_locator[0]: str
        """
        ioListSize = 4096
        options = ctypes.c_char()
        outList = (' ' * ioListSize).encode()
        ioListSize = ctypes.c_ulong(ioListSize)

        status = SmaractDll.SA_FindSystems(
            ctypes.byref(options),
            outList,
            ctypes.byref(ioListSize)
        )

        if status != 0:
            raise Exception('SmarAct SA_FindSystems error')

        controller_locator = re.findall("usb:id:[0-9]{10}", outList.decode())

        if not controller_locator:
            raise Exception('No controller found')

        return controller_locator[0]

    def init_communication(self, controller_locator):
        """
            Use the controller locator returned from get_controller_locator
            and return the system index used the refer to the controller

        Parameters
        -------
        controller_locator: str
        """
        systemIndex = ctypes.c_ulong()
        # we choose the synchronous communication mode
        options = 'sync'.encode('ascii')

        status = SmaractDll.SA_OpenSystem(
            ctypes.byref(systemIndex),
            controller_locator.encode('ascii'),
            options
        )

        if status != 0:
            raise Exception('SmarAct SA_OpenSystem failed')

        return systemIndex.value

    def get_number_of_channels(self):
        """
            Return the number of channels of the controller. Note that the
            number of channels does not represent the number positioners and/or
            end effectors that are currently connected to the system.

        Returns
        -------
        numberOfChannels.value: unsigned int
        """
        numberOfChannels = ctypes.c_ulong()

        status = SmaractDll.SA_GetNumberOfChannels(
            ctypes.c_ulong(self.system_index),
            ctypes.byref(numberOfChannels)
        )

        if status != 0:
            self.close_communication()
            raise Exception('SmarAct SA_GetNumberOfChannels failed')

        return numberOfChannels.value

    def close_communication(self):
        """
            Close the communication with the controller.
        """
        status = SmaractDll.SA_CloseSystem(
            ctypes.c_ulong(self.system_index)
        )

        if status != 0:
            raise Exception('SmarAct SA_CloseSystem failed')

    def get_position(self, channel_index):
        """
            Return the current position of the positioner connected to the channel indexed by channel_index
            (starts at 0) in nanometers.

        Parameters
        ----------
        channel_index: unsigned int

        Returns
        -------
        position.value: signed int
        """

        position = ctypes.c_long()

        status = SmaractDll.SA_GetPosition_S(
            ctypes.c_ulong(self.system_index),
            ctypes.c_ulong(channel_index),
            ctypes.byref(position)
        )

        if status != 0:
            self.close_communication()
            raise Exception('SmarAct SA_GetPosition failed')

        return position.value

    def find_reference(self, channel_index):
        """
            Find the physical zero reference of the positioner (starting in the
            forward direction) and reset the position to zero.

        Parameters
        ----------
        channel_index: unsigned int
        """

        # with direction = 0 search for reference starts in the forward
        # direction
        direction = 0
        # hold time = 60,000 ms corresponds to infinite holding
        hold_time = 60000
        # auto zero = 1 will reset the position to zero after reaching
        # the reference mark
        auto_zero = 1

        status = SmaractDll.SA_FindReferenceMark_S(
            ctypes.c_ulong(self.system_index),
            ctypes.c_ulong(channel_index),
            ctypes.c_ulong(direction),
            ctypes.c_ulong(hold_time),
            ctypes.c_ulong(auto_zero)
        )

        if status != 0:
            self.close_communication()
            raise Exception('SmarAct SA_FindReferenceMark failed')

        print('The positionner is referenced !')

    def relative_move(self, channel_index, relative_position):
        """
            Execute a relative move in nanometers
            If a mechanical end stop is detected while the command is in execution,
            the movement will be aborted (without notice).

        Parameters
        ----------
        channel_index: unsigned int
        relative_position: signed int
        """

        # hold time = 60,000 ms corresponds to infinite holding
        hold_time = 60000

        status = SmaractDll.SA_GotoPositionRelative_S(
            ctypes.c_ulong(self.system_index),
            ctypes.c_ulong(channel_index),
            ctypes.c_long(relative_position),
            ctypes.c_ulong(hold_time)
        )

        if status != 0:
            self.close_communication()
            raise Exception('SmarAct SA_GotoPositionRelative failed')

    def absolute_move(self, channel_index, absolute_position):
        """
            Go to an absolute position in nanometers
            If a mechanical end stop is detected while the command is in execution,
            the movement will be aborted (without notice).

        Parameters
        ----------
        channel_index: unsigned int
        absolute_position: signed int
        """

        # hold time = 60,000 ms corresponds to infinite holding
        hold_time = 60000

        status = SmaractDll.SA_GotoPositionAbsolute_S(
            ctypes.c_ulong(self.system_index),
            ctypes.c_ulong(channel_index),
            ctypes.c_long(absolute_position),
            ctypes.c_ulong(hold_time)
        )

        if status != 0:
            self.close_communication()
            raise Exception('SmarAct SA_GotoPositionAbsolute failed')

    def stop(self, channel_index):
        """
            Stop any ongoing movement of the positionner. This command also stops the hold position feature of
            closed-loop commands.

        Parameters
        ----------
        channel_index: unsigned int
        """

        status = SmaractDll.SA_Stop_S(
            ctypes.c_ulong(self.system_index),
            ctypes.c_ulong(channel_index)
        )

        if status != 0:
            self.close_communication()
            raise Exception('SmarAct SA_Stop failed')
