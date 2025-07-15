"""
File: qsweepTest2.py

Purpose: Second attempt. Attempt 1 worked but fell short on using ul.a_out_scan for timed cycles.
"""

from ctypes import cast, POINTER, c_ushort
from time import sleep
from time import time
import traceback

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import ScanOptions, FunctionType, Status
from mcculw.ul import ULError

# Board/Device
use_device_detection = True
board_num = 0
deviceInfo = DaqDeviceInfo(board_num)
memhandle = None
if not deviceInfo.supports_analog_input:
    raise Exception('Error: The DAQ device does not support analog input')
if not deviceInfo.supports_analog_output:
    raise Exception('Error: The DAQ device does not support analog output')
print('Active DAQ Device: ' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')

# Channel info
low_chan = 0
high_chan = 0
num_chans = 1

rate = 100
outputCount = 100

# Device Info
ao_info = deviceInfo.get_ao_info()
ao_range = ao_info.supported_ranges[0]
ai_info = deviceInfo.get_ai_info()
ai_range = ai_info.supported_ranges[0]
channel = 0

sleep(1)

# Allocating memory buffer & converting it to ctype array
memhandle = ul.win_buf_alloc(outputCount)
ctypes_array = cast(memhandle, POINTER(c_ushort))
if not memhandle:
    raise Exception('Error: Failed to allocate memory')
    traceback.print_exc()
    input("Press enter to close script...")

sleep(1)

# Defining sine wave generation function
def sin():
    xData = np.linspace(

# Defining QSweep function
def qSweep(minFreq, maxFreq, stepFreq):
    # Frequencies that are specified to be tested
    frequencies = []
    while maxFreq >= minFreq:
        frequencies.append(minFreq)
        minFreq = minFreq + stepFreq
    
    # Main body loop
    # Creates an output value, sends it through, reads an input, and then continues the loop once and input has been read
    for freq in frequencies:
        start = time()
        try:
            ul.a_out_scan(board_num, low_chan, high_chan, outputCount, rate, freq, memhandle, ScanOptions.BACKGROUND)
            
            status = Status.RUNNING
            while status != Status.IDLE:
                print('.', end='')

                # Slow down the status check so as not to flood the CPU
                sleep(0.5)

                status, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
            print('')

            print('Scan completed successfully')
        except ULError as e:
            # Print error
            print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            traceback.print_exc()
            input("Press enter to close script...")
        # Printing output value (mostly debug reasons)
        print('Output value[' + str(frequencies.index(freq)) + ']: ' + str(freq))
        
        # Reading the input channel
        try:
            inValue = ul.a_in(board_num, channel, ai_range)
            print('Input Value[' + str(frequencies.index(freq)) + ']: ' + str(inValue))
            print('\n')
        except ULError as e:
            # Print error
            print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            traceback.print_exc()
            input("Press enter to close script...")
        end = time()
        print(str(end - start))
    # Success
    print('Test successful! Press enter to close the script.')
    input()

if __name__ == '__main__':
    qSweep(50000, 70000, 700)