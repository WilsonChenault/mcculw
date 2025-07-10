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
log = logging.getLogger(__name__)
logging.basicConfig(
    filename = 'console.log',
    filemode = 'w',
    format = '%(asctime)s - %(filename)s - %(lineno)d :: %(message)s', 
    level=logging.INFO
)

# Board/Device
use_device_detection = True
board_num = 0
deviceInfo = DaqDeviceInfo(board_num)
if not deviceInfo.supports_analog_input:
    raise Exception('Error: The DAQ device does not support analog input')
if not deviceInfo.supports_analog_output:
    raise Exception('Error: The DAQ device does not support analog output')
print('Active DAQ Device: ' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')
log.info('Active DAQ Device: ' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')

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
    sineHold = np.ndarray.tolist(np.sin(xData) * 10)
    log.info(sineHold) # DEBUG
    sineOutput = []
    for i in sineHold:
        valueHold = ul.from_eng_units(board_num, ao_range, i)
        sineOutput.append(valueHold)
    log.info(sineOutput) # DEBUG

# Defining QSweep function
def qSweep(minFreq, maxFreq, stepFreq):
    # Handling memory buffer
    totalPoints = 50 # Total number of points that get scanned. 10 cycles is always 100 points with a  sine(numPoints) of 10.
    inputPoints = 100
    scanBuffer = ul.win_buf_alloc(totalPoints)
    inputBuffer = ul.win_buf_alloc(inputPoints)
    outputArray = cast(scanBuffer, POINTER(c_ushort))
    inputArray = cast(inputBuffer, POINTER(c_ushort))
    
    # Writing scan data into buffer
    sineExtend = sineOutput * (int(totalPoints/len(sineOutput)) - 1)
    sineOutput.extend(sineExtend) # Copying the sine output over the course of the buffer
    for i in range(len(sineOutput)):
        outputArray[i] = sineOutput[i]
    log.info(outputArray) # DEBUG
    
    # Frequencies that are specified to be tested
    frequencies = []
    while maxFreq >= minFreq:
        frequencies.append(minFreq)
        minFreq = minFreq + stepFreq
    
    # Main body loop
    # Outputs a frequency (numPoints/rate) to the coil. Reads back a single input (resonance).
    inData = [] # Defining measured data to append
    print('Waiting for scan...')
    time = time()
    log.info('Scan started at ' + time)
    for freq in frequencies:
        # Define rate. This is our way of adjusting the frequency outputted
        rate = freq * 10 # * 10 because 10 points is one cycle
        inRate = 10000 # Input sample rate. Set value as to not skew data
        inputHold = [] # Input samples data. Hold takes in the buffer, writes to data, and then gets rewritten.
        inputData = []
        log.info(rate) # DEBUG
        # Run input using new rate and values within memory buffer. Outputs a sine wave of specified frequency to the coil.
        try:
            ul.a_out_scan(board_num, low_chan, high_chan, totalPoints, rate, ao_range, scanBuffer, ScanOptions.BACKGROUND)
        except ULError as e:
            print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            log.error('ERROR: ' + '\n' + "A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            traceback.print_exc()
            input("Press enter to close script...")
        
        # Reading input. Using the scan feature to create an array for each sample set of data.
        try:
            ul.a_in_scan(board_num, low_chan, high_chan, inputPoints, inRate, ai_range, inputBuffer, ScanOptions.BACKGROUND)
            inStatus = Status.RUNNING
            while inStatus != inStatus.IDLE:
                inStatus, _, _ = ul.get_status(board_num, FunctionType.AIFUNCTION)
                if inStatus == inStatus.IDLE:
                    ul.win_buf_to_array(inputBuffer, inputArray, 0, 50)
                    for i in range(inputPoints):
                        inputData.append(inputArray[i])
                    inData.append(inputData)
                    log.info(inputArray) # DEBUG
                    log.info(inputData) # DEBUG
        except ULError as e:
            print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            log.error('ERROR: ' + '\n' + "A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            traceback.print_exc()
            input("Press enter to close script...")
            
        # Slow down mildly to prevent CPU overflow
        outStatus = Status.RUNNING
        while outStatus != outStatus.IDLE:
            sleep(0.1)
            outStatus, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
            log.info(outStatus) # DEBUG
        
    # Success
    print('\n' + 'Frequencies: ' + str(frequencies))
    print('Resonance Data: ' + str(inData) + '\n')
    print('Test successful! Press enter to close the script.')
    input()

if __name__ == '__main__':
    try:
        sine(10)
        qSweep(20000, 30000, 100)
    except Exception as e:
        file = open('console.log', 'a')
        file.write(traceback.format_exc())
        f.close()
