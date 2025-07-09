"""
File: test_input.py

Purpose: various testing.
"""

from __future__ import absolute_import, division, print_function
from builtins import *

from mcculw import ul
from mcculw.enums import ScanOptions, FunctionType, Status
from mcculw.device_info import DaqDeviceInfo

from time import sleep
from ctypes import cast, POINTER, c_ushort

try:
    from console_examples_util import config_first_detected_device
except ImportError:
    from .console_examples_util import config_first_detected_device
   
# Code

def aoutput(minFreq, maxFreq, stepFreq):
    # By default, the example detects and displays all available devices and
    # selects the first device listed. Use the dev_id_list variable to filter
    # detected devices by device ID (see UL documentation for device IDs).
    # If use_device_detection is set to False, the board_num variable needs to
    # match the desired board number configured with Instacal.
    use_device_detection = True
    dev_id_list = []
    board_num = 0
    memhandle = None

    try:
        if use_device_detection:
            config_first_detected_device(board_num, dev_id_list)

        daq_dev_info = DaqDeviceInfo(board_num)
        if not daq_dev_info.supports_analog_output:
            raise Exception('Error: The DAQ device does not support '
                            'analog output')

        print('\nActive DAQ device: ', daq_dev_info.product_name, ' (',
              daq_dev_info.unique_id, ')\n', sep='')

        ao_info = daq_dev_info.get_ao_info()
        
        low_chan = 0
        high_chan = min(3, ao_info.num_chans - 1)
        num_chans = high_chan - low_chan + 1

        rate = 100
        points_per_channel = 1000
        total_count = points_per_channel * num_chans

        ao_range = ao_info.supported_ranges[0]

        # Allocate a buffer for the scan
        memhandle = ul.win_buf_alloc(total_count)
        # Convert the memhandle to a ctypes array
        # Note: the ctypes array will no longer be valid after win_buf_free
        # is called.
        # A copy of the buffer can be created using win_buf_to_array
        # before the memory is freed. The copy can be used at any time.
        ctypes_array = cast(memhandle, POINTER(c_ushort))
        
        # Check if the buffer was successfully allocated
        if not memhandle:
            raise Exception('Error: Failed to allocate memory')
            
        #numFreq = (maxFreq - minFreq) % stepFreq
        #frequencies = []
        #for i in range(numFreq)
        #    holdFreq = minFreq + (i * stepFreq)
        #    frequencies.append(holdFreq)
        #print(frequencies)
        
        frequencies = [1000, 2000]
        
        for ch_num in range(low_chan, high_chan + 1):
            print('Channel', ch_num, 'Output Signal Frequency:',
                  frequencies[ch_num - low_chan])

        # Start the scan
        ul.a_out_scan(board_num, low_chan, high_chan, total_count, rate,
                      ao_range, memhandle, ScanOptions.BACKGROUND)

        # Wait for the scan to complete
        print('Waiting for output scan to complete...', end='')
        status = Status.RUNNING
        while status != Status.IDLE:
            print('.', end='')

            # Slow down the status check so as not to flood the CPU
            sleep(0.5)

            status, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
        print('')

        print('Scan completed successfully')
    except Exception as e:
        print('\n', e)
    finally:
        if memhandle:
            # Free the buffer in a finally block to prevent a memory leak.
            ul.win_buf_free(memhandle)
        if use_device_detection:
            ul.release_daq_device(board_num)
        
if __name__ == '__main__':
    aoutput(100, 1000, 100)