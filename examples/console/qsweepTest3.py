"""
File: qsweepTest3.py

Purpose: Attempting to run 100 cycles of qsweepTest1
"""

import traceback
import numpy as np
import logging

from time import sleep
from time import time
from ctypes import cast, POINTER, c_ushort

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import ScanOptions, FunctionType, Status
from mcculw.ul import ULError

# Logging function
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename = 'console.log',
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s - %(lineno)d'
    handlers = logging.StreamHandler()
)
logging.info("Informational: ")
logging.warning("Warning: ")
logging.error("Error: ")

# Board/Device
use_device_detection = True
board_num = 0
num_cycles = 1000
deviceInfo = DaqDeviceInfo(board_num)
if not deviceInfo.supports_analog_input:
    raise Exception('Error: The DAQ device does not support analog input')
if not deviceInfo.supports_analog_output:
    raise Exception('Error: The DAQ device does not support analog output')
print('Active DAQ Device: ' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')

# Device Info
ao_info = deviceInfo.get_ao_info()
ao_range = ao_info.supported_ranges[0]
ai_info = deviceInfo.get_ai_info()
ai_range = ai_info.supported_ranges[0]
channel, low_chan, high_chan = 0, 0, 0 # Channel defining for qSweep()

# Defining Sine Wave Generation
def sine(numPoints):
    global sineOutput
    xData = np.linspace(0, 2 * np.pi, numPoints)
    sineOutput = np.sin(xData)

# Defining QSweep function
def qSweep(minFreq, maxFreq, stepFreq):
    # Handling memory buffer
    totalPoints = 100 # Total number of points that get scanned. 10 cycles is always 100 points with a
                      # sine(numPoints) of 10.
    memhandle = ul.win_buf_alloc(totalPoints)
    ctypes_array = cast(memhandle, POINTER(c_ushort))
    
    # Frequencies that are specified to be tested
    frequencies = []
    while maxFreq >= minFreq:
        frequencies.append(minFreq)
        minFreq = minFreq + stepFreq
    
    # Main body loop
    # Outputs a frequency (numPoints/rate) to the coil. Reads back a single input (resonance).
    inData = [] # Defining measured data to append
    for freq in frequencies:
        # Define rate. This is our way of adjusting the frequency outputted
        rate = len(sineOutput)/freq
        # Run input using new rate and values within memory buffer. Outputs a sine wave of specified frequency to the coil.
        ul.a_out_scan(board_num, low_chan, high_chan, totalPoints, rate, ao_range, memhandle, ScanOptions.BACKGROUND)
        
        # Slow down mildly to prevent CPU overflow
        print('Waiting for scan...')
        status = Status.RUNNING
        while status != status.IDLE:
            print('.')
            sleep(0.1)
            status, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
        
        # Reading input
        inValue = ul.a_in(board_num, channel, ai_range)
        inData.append(inValue)
        
    # Success
    print('\n' + 'Frequencies: ' + str(frequencies))
    print('Resonance Data: ' + str(inData) + '\n')
    print('Test successful! Press enter to close the script.')
    input()

if __name__ == '__main__':
    sine(10)
    qSweep(50000, 70000, 700)
