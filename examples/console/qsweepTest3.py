"""
File: qsweepTest3.py

Purpose: Attempting to run 100 cycles of qsweepTest1
"""

from time import sleep
from time import time
import traceback
import numpy as np

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import ULRange
from mcculw.ul import ULError

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
channel = 0

# Defining Sine Wave Generation
def sine(numPoints):
    global sineOutput
    xData = np.linspace(0, 2 * np.pi, numPoints)
    sineOutput = np.sin(xData)

# Defining QSweep function
def qSweep(minFreq, maxFreq, stepFreq):
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
        ul.a_out_scan(board_num, low_chan, high_chan, ao_range, rate, memhandle, options=NONE)
        

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
